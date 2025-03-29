"""
Streamlit app for ViCareUB2.
Provides interactive visualization of heating system data.
"""
import logging
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for imports
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pandas as pd
import streamlit as st
import altair as alt

from pyvicareub2.config import settings
from pyvicareub2.database import DatabaseService

logger = logging.getLogger("ViCareUB2")

def setup_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="ViCare Monitoring",
        page_icon="🔥",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main {
        background-color: #1a1a1a;
        color: white;
    }
    .stApp {
        background-color: #1a1a1a;
    }
    .stPlot {
        background-color: #2d2d2d;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

def load_data(days=2):
    """Load data from the database"""
    try:
        db = DatabaseService()
        df = db.get_data_for_plotting(days=days)
        
        if df.empty:
            st.error("No data available for the selected time period.")
            return None
        
        # Convert to wide format for easier handling in Streamlit
        # First ensure boolean variables maintain their 0/1 values by converting to int
        df_for_pivot = df.copy()
        boolean_vars = ["active", "solar_pump", "circulation_pump", "dhw_pump"]
        
        # Ensure each boolean variable is properly converted to numeric
        for var in boolean_vars:
            mask = df_for_pivot.variable == var
            if mask.any():
                # First handle NA values by filling with 0 before conversion
                df_for_pivot.loc[mask, 'value'] = pd.to_numeric(
                    df_for_pivot.loc[mask, 'value'], 
                    errors='coerce'
                ).fillna(0).astype(int)
        
        # Reverse the modulation normalization (modulation = 2 + original/50)
        # So original = (modulation - 2) * 50
        mask = df_for_pivot.variable == "modulation"
        if mask.any():
            df_for_pivot.loc[mask, 'value'] = (df_for_pivot.loc[mask, 'value'] - 2) * 50
        
        # Now pivot the data
        df_wide = df_for_pivot.pivot(index="time", columns="variable", values="value").reset_index()
        
        # Fill NA values for boolean columns after pivot
        for var in boolean_vars:
            if var in df_wide.columns:
                df_wide[var] = df_wide[var].fillna(0)
        
        # Add debug info
        st.sidebar.write("Debug Information")
        for var in boolean_vars:
            if var in df_wide.columns:
                values = df_wide[var].value_counts()
                st.sidebar.write(f"{var} count: {values.to_dict()}")
        
        if "modulation" in df_wide.columns:
            st.sidebar.write("Modulation range:")
            st.sidebar.write(f"Min: {df_wide['modulation'].min():.1f}, Max: {df_wide['modulation'].max():.1f}")
        
        return df_wide
    
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        st.error(f"Error loading data: {str(e)}")
        return None

def plot_temperatures(df):
    """Plot temperature metrics using Altair"""
    # Get available temperature columns
    available_temp_cols = [col for col in df.columns if col.startswith("temp_")]
    
    if not available_temp_cols:
        st.warning("No temperature data available.")
        return None
    
    # Separate temp_out from other temperature columns
    system_temp_cols = [col for col in available_temp_cols if col != "temp_out"]
    has_outside_temp = "temp_out" in available_temp_cols
    
    if not system_temp_cols:
        st.warning("No system temperature data available.")
        return None
    
    # Create base chart for system temperatures
    system_data = df.melt(
        id_vars=["time"],
        value_vars=system_temp_cols,
        var_name="Temperature",
        value_name="Value"
    ).dropna()
    
    if system_data.empty:
        st.warning("No system temperature data available after removing null values.")
        return None
    
    # Calculate appropriate y-axis domain with padding
    system_min = system_data['Value'].min()
    system_max = system_data['Value'].max()
    padding = (system_max - system_min) * 0.1
    
    # Create day/night background data
    time_range = [pd.to_datetime(df['time'].min()), pd.to_datetime(df['time'].max())]
    night_bands = []
    
    # Start with the first day at midnight
    current_date = pd.to_datetime(time_range[0]).normalize()
    end_date = pd.to_datetime(time_range[1])
    
    # Build night bands data (21:30-05:30)
    while current_date <= end_date:
        # Evening (21:30-midnight)
        evening_start = current_date.replace(hour=21, minute=30, second=0)
        if evening_start < time_range[0]:
            evening_start = time_range[0]
        
        evening_end = (current_date + pd.Timedelta(days=1)).normalize()  # midnight
        if evening_end > time_range[1]:
            evening_end = time_range[1]
            
        if evening_start < evening_end:
            night_bands.append({'start': evening_start, 'end': evening_end})
        
        # Morning (midnight-05:30)
        morning_start = current_date.normalize()  # midnight
        if morning_start < time_range[0]:
            morning_start = time_range[0]
            
        morning_end = current_date.replace(hour=5, minute=30, second=0)
        if morning_end > time_range[1]:
            morning_end = time_range[1]
            
        if morning_start < morning_end and morning_end > time_range[0]:
            night_bands.append({'start': morning_start, 'end': morning_end})
        
        current_date += pd.Timedelta(days=1)
    
    # Create night bands dataframe
    night_df = pd.DataFrame(night_bands)
    
    # Create the main temperature chart
    base_chart = alt.Chart(system_data).mark_line().encode(
        x=alt.X('time:T', 
                title='Time',
                axis=alt.Axis(labelPadding=10),
                scale=alt.Scale(padding=30)),  # Add horizontal padding
        y=alt.Y('Value:Q', 
                title='System Temperature (°C)',
                scale=alt.Scale(domain=[system_min - padding, system_max + padding], zero=False),
                axis=alt.Axis(format='.1f')),
        color=alt.Color('Temperature:N', 
                      legend=alt.Legend(orient='top', title=None),
                      scale=alt.Scale(
                          domain=['temp_hotwater_target', 'temp_hotwater', 'temp_solcollector', 
                                 'temp_boiler', 'temp_heating', 'temp_solstorage'],
                          range=['#999999', 'blue', 'red', 
                                '#00BFFF', '#00FF00', '#FFFF00']
                      )),
        strokeDash=alt.condition(
            alt.datum.Temperature == 'temp_hotwater_target',
            alt.value([2, 2]),
            alt.value([0])
        ),
        strokeWidth=alt.condition(
            alt.FieldOneOfPredicate(field='Temperature', oneOf=['temp_hotwater', 'temp_solcollector']),
            alt.value(2),  # For hotwater and solcollector
            alt.value(1)   # For everything else including target
        ),
        tooltip=['time:T', 'Temperature:N', alt.Tooltip('Value:Q', format='.1f')]
    ).properties(
        height=500
    )
    
    # Night bands chart (only if we have night bands data)
    night_band_chart = None
    if not night_df.empty:
        # Draw night time rectangles with dark blue color and increased opacity
        night_band_chart = alt.Chart(night_df).mark_rect(
            color='#141110',  # Dark blue instead of black
            opacity=0.35      # Increased opacity for better visibility
        ).encode(
            x='start:T',
            x2='end:T',
            y=alt.value(0),  # Span the entire height
            y2=alt.value(500)
        )
    
    # Create day time bands for contrast
    day_bands = []
    current_date = pd.to_datetime(time_range[0]).normalize()
    
    # Build day bands data (05:30-21:30)
    while current_date <= end_date:
        day_start = current_date.replace(hour=5, minute=30, second=0)
        if day_start < time_range[0]:
            day_start = time_range[0]
            
        day_end = current_date.replace(hour=21, minute=30, second=0)
        if day_end > time_range[1]:
            day_end = time_range[1]
            
        if day_start < day_end:
            day_bands.append({'start': day_start, 'end': day_end})
        
        current_date += pd.Timedelta(days=1)
    
    # Create day bands dataframe
    day_df = pd.DataFrame(day_bands)
    
    # Day bands chart
    day_band_chart = None
    if not day_df.empty:
        # Draw day time rectangles with slightly lighter color
        day_band_chart = alt.Chart(day_df).mark_rect(
            color='#292b30',  # Slightly lighter than background
            opacity=0.3       # Subtle opacity
        ).encode(
            x='start:T',
            x2='end:T',
            y=alt.value(0),
            y2=alt.value(500)
        )
    
    # Combine base chart with night and day bands if available
    chart_layers = []
    
    # Add bands in correct order (first background layers, then data)
    if day_band_chart:
        chart_layers.append(day_band_chart)
    if night_band_chart:
        chart_layers.append(night_band_chart)
    
    # Add the temperature data on top
    chart_layers.append(base_chart)
    
    # Create the combined chart
    chart_with_bands = alt.layer(*chart_layers)
    
    # If we have outside temperature data, add it on a secondary y-axis
    if has_outside_temp:
        outside_data = df[['time', 'temp_out']].dropna().copy()
        outside_data.columns = ['time', 'Value']
        
        if not outside_data.empty:
            # Calculate different y-axis domains for better visibility
            outside_min = outside_data['Value'].min()
            outside_max = outside_data['Value'].max()
            outside_padding = (outside_max - outside_min) * 0.1
            
            outside_chart = alt.Chart(outside_data).mark_line(
                color='violet',
                strokeDash=[5, 5],
                strokeWidth=2
            ).encode(
                x=alt.X('time:T'),
                y=alt.Y('Value:Q',
                        title='Outside Temperature (°C)',
                        scale=alt.Scale(domain=[outside_min - outside_padding, outside_max + outside_padding], zero=False),
                        axis=alt.Axis(format='.1f', grid=False)),
                tooltip=[alt.Tooltip('time:T'), 
                         alt.Tooltip('Value:Q', title='temp_out', format='.1f')]
            )
            
            # Create a layered chart with dual y-axes
            layered_chart = alt.layer(
                chart_with_bands,  # Use chart with night bands
                outside_chart
            ).resolve_scale(
                y='independent'
            )
            
            return layered_chart
    
    # If no outside temperature, return just the base chart
    return chart_with_bands

def plot_system_metrics(df):
    """Plot system metrics using Altair"""
    system_cols = [
        "hours",
        "starts",
        "solar_production"
    ]
    
    # Only keep columns that exist in the dataframe
    available_cols = [col for col in system_cols if col in df.columns]
    
    if not available_cols:
        st.warning("No system metrics data available.")
        return None
    
    # Data for the chart
    chart_data = df.melt(
        id_vars=["time"],
        value_vars=available_cols,
        var_name="Metric",
        value_name="Value"
    )
    
    # Remove rows with null values
    chart_data = chart_data.dropna()
    
    if chart_data.empty:
        st.warning("No system metrics data available after removing null values.")
        return None
    
    # Configure the chart's overall appearance
    config = alt.Config(
        background='#2d2d2d',
        axis=alt.AxisConfig(
            gridColor='#444444',
            gridOpacity=0.3,
            labelColor='white',
            titleColor='white'
        )
    )
    
    # Create base chart with added horizontal padding
    chart = alt.Chart(
        chart_data
    ).mark_line().encode(
        x=alt.X('time:T', 
               title='Time',
               axis=alt.Axis(labelPadding=10, grid=True),
               scale=alt.Scale(padding=30)),  # Add horizontal padding
        y=alt.Y('Value:Q', 
               title='Value',
               axis=alt.Axis(grid=True)),
        color=alt.Color('Metric:N', legend=alt.Legend(
            orient='top',
            title=None
        )),
        tooltip=['time:T', 'Metric:N', 'Value:Q']
    ).properties(
        height=400
    )
    
    return chart.configure(
        background='#2d2d2d',
        axis=alt.AxisConfig(
            gridColor='#444444',
            gridOpacity=0.3,
            labelColor='white',
            titleColor='white'
        )
    )

def plot_boolean_status(df):
    """Plot boolean status of pumps and devices"""
    boolean_cols = [
        "active",
        "solar_pump",
        "circulation_pump", 
        "dhw_pump"
    ]
    
    # Only keep columns that exist in the dataframe
    available_cols = [col for col in boolean_cols if col in df.columns]
    
    if not available_cols:
        st.warning("No boolean status data available.")
        return None
    
    # Handle any missing values before conversion
    for col in available_cols:
        if col in df.columns:
            # First make sure we don't have any nulls
            df[col] = df[col].fillna(0)
            # Then convert to numeric with error handling
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Print raw data for debugging
    st.sidebar.write("Sample boolean data (5 rows):")
    for col in available_cols:
        sample_data = df[['time', col]].head(5)
        st.sidebar.write(f"{col}:\n", sample_data)
    
    # Create charts for boolean variables
    charts = []
    
    # Configure the chart's overall appearance
    config = alt.Config(
        background='#2d2d2d',
        axis=alt.AxisConfig(
            gridColor='#444444',
            gridOpacity=0.3,
            labelColor='white',
            titleColor='white'
        )
    )
    
    for device in available_cols:
        # Create individual device dataframe
        device_data = df[['time', device]].copy()
        device_data.columns = ['time', 'Status']  # Rename for consistency
        
        # Create individual step chart
        device_chart = alt.Chart(
            device_data
        ).mark_line(
            interpolate='step-after',
            strokeWidth=1  # Make lines thinner
        ).encode(
            x=alt.X('time:T', 
                   title=None,
                   axis=alt.Axis(grid=True),
                   scale=alt.Scale(padding=30)),  # Add horizontal padding
            y=alt.Y('Status:Q', 
                   scale=alt.Scale(domain=[-0.1, 1.1]),
                   axis=alt.Axis(title=None, labels=False, ticks=False)),
            color=alt.value('#01FF70'),
            tooltip=['time:T', alt.Tooltip('Status:Q', title=device)]
        ).properties(
            title=device,
            height=50
        )
        
        # Add a baseline
        baseline = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
            strokeDash=[2, 2],
            stroke='#444444',
            strokeWidth=1
        ).encode(y='y')
        
        charts.append(device_chart + baseline)
    
    # Add modulation as a special case if it exists
    if 'modulation' in df.columns:
        # Create modulation dataframe
        mod_data = df[['time', 'modulation']].copy().dropna()
        
        # Handle missing values but don't multiply by 100
        mod_data['modulation'] = pd.to_numeric(mod_data['modulation'], errors='coerce').fillna(0)
        
        # Use fixed domain of 0-100
        mod_chart = alt.Chart(
            mod_data
        ).mark_line(
            color='#FD971F',  # Orange color for modulation
            strokeWidth=1  # Make line thinner
        ).encode(
            x=alt.X('time:T', 
                   title=None,
                   axis=alt.Axis(grid=True),
                   scale=alt.Scale(padding=30)),  # Add horizontal padding
            y=alt.Y('modulation:Q', 
                   title='Modulation %',
                   axis=alt.Axis(grid=True),
                   scale=alt.Scale(domain=[0, 100])),
            tooltip=['time:T', alt.Tooltip('modulation:Q', title='Modulation %', format='.1f')]
        ).properties(
            title='modulation',
            height=100  # Taller than binary status rows
        )
        
        # Add to charts list
        charts.append(mod_chart)
    
    # Combine charts with spacing
    if charts:
        final_chart = alt.vconcat(*charts).resolve_scale(
            x='shared'
        )
        return final_chart.configure(
            background='#2d2d2d',
            axis=alt.AxisConfig(
                gridColor='#444444',
                gridOpacity=0.3,
                labelColor='white',
                titleColor='white'
            )
        )
    
    return None

def main():
    """Main function for the Streamlit app"""
    setup_page()
    
    st.title("ViCare Monitoring")
    
    # Date range selector
    col1, col2 = st.columns([3, 1])
    with col2:
        days = st.selectbox("Time Range (days)", [1, 2, 3, 7, 14, 30], index=1)
    
    with col1:
        st.write(f"Data from the last {days} days")
        last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.write(f"Last update: {last_update}")
    
    # Load data
    df = load_data(days=days)
    
    if df is not None:
        # Temperature metrics first, now as a separate visualization (not in tabs)
        st.subheader("Temperature Metrics")
        temp_chart = plot_temperatures(df)
        if temp_chart:
            st.altair_chart(temp_chart, use_container_width=True)
            
        # Plot boolean status
        st.subheader("Device Activity Status")
        boolean_chart = plot_boolean_status(df)
        if boolean_chart:
            st.altair_chart(boolean_chart, use_container_width=True)
        
        # System metrics still in its own section
        st.subheader("System Metrics")
        system_chart = plot_system_metrics(df)
        if system_chart:
            st.altair_chart(system_chart, use_container_width=True)


if __name__ == "__main__":
    main() 