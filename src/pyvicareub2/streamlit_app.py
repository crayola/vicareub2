"""
Streamlit app for ViCareUB2.
Provides interactive visualization of heating system data.
"""

import logging

# Add parent directory to path for imports
import os
import sys
from datetime import datetime

import pytz

from pyvicareub2.config import settings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import altair as alt
import pandas as pd
import streamlit as st

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
    st.markdown(
        """
    <style>

    .main {
        background-color: #1a1a1a;
        color: white;
    }

    /* thing that appears when scrolling up or down */
    .stApp {
        background-color: #2a2a2a;
    }

    /* More specific targeting for Vega charts */
    # div[data-testid="stVerticalBlock"] div.element-container div.stVegaLiteChart {
    #     background-color: #252525 ;
    #     border-radius: 26px ;
    #     box-shadow: 0 8px 16px rgba(0, 0, 0, 0.6) ;
    #     overflow: hidden ;
    #     border: 1px solid #3d3d3d ;
    #     padding: 10px ;
    # }

    /* Apply rounded corners to Vega-Lite chart elements */
    .vega-embed .marks {
        border: 1px solid #4d4d4d;
        border-radius: 25px;
        max-width: 100% ;
    }
    # .vega-embed .chart-wrapper {
    #     border: 1px solid #4d4d4d;
    #     border-radius: 25px;
    #     max-width: 100% ;
    # }
    .stHeading {
        margin-top: 1.5rem;
    }

    /* metric */
    .big-metric {
        font-size: 3rem ;
        font-weight: bold;
        color: #e0e0e0;
    }
    .metric-label {
        font-size: 1.2rem;
        color: #CCCCCC;
        margin-bottom: 0.5rem;
    }
    .target-temp {
        font-size: 1.5rem;
        color: #999999;
        padding-left: 10px;
    }
    .metric-container {
        background-color: #2d2d2d;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.6);
        border: 1px solid #3d3d3d;
    }

    .block-container {
        padding-top: 1rem;
        background-color: #1a1a1a;
        padding-bottom: 1rem;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


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
                boolean_col = pd.to_numeric(df_for_pivot.loc[mask, "value"], errors="coerce")
                # TODO: find a better way to make pyright happy
                if not isinstance(boolean_col, pd.Series):
                    continue
                df_for_pivot.loc[mask, "value"] = boolean_col.fillna(0).astype(int)

        # Reverse the modulation normalization (modulation = 2 + original/50)
        # So original = (modulation - 2) * 50
        mask = df_for_pivot.variable == "modulation"
        if mask.any():
            df_for_pivot.loc[mask, "value"] = (df_for_pivot.loc[mask, "value"] - 2) * 50

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
            st.sidebar.write(
                f"Min: {df_wide['modulation'].min():.1f}, Max: {df_wide['modulation'].max():.1f}"
            )

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
        id_vars=["time"], value_vars=system_temp_cols, var_name="Temperature", value_name="Value"
    ).dropna()

    if system_data.empty:
        st.warning("No system temperature data available after removing null values.")
        return None

    # Calculate appropriate y-axis domain with padding
    system_min = system_data["Value"].min()
    system_max = system_data["Value"].max()
    padding = (system_max - system_min) * 0.1

    # Create day/night background data
    time_range = [pd.to_datetime(df["time"].min()), pd.to_datetime(df["time"].max())]
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
            night_bands.append({"start": evening_start, "end": evening_end})

        # Morning (midnight-05:30)
        morning_start = current_date.normalize()  # midnight
        if morning_start < time_range[0]:
            morning_start = time_range[0]

        morning_end = current_date.replace(hour=5, minute=30, second=0)
        if morning_end > time_range[1]:
            morning_end = time_range[1]

        if morning_start < morning_end and morning_end > time_range[0]:
            night_bands.append({"start": morning_start, "end": morning_end})

        current_date += pd.Timedelta(days=1)

    # Create night bands dataframe
    night_df = pd.DataFrame(night_bands)

    # Create the main temperature chart with thin lines for most temperatures
    base_chart = (
        alt.Chart(system_data)
        .mark_line(
            strokeWidth=0.8  # Thinner lines
        )
        .encode(
            x=alt.X("time:T", title="Time", axis=alt.Axis(labelPadding=10)),
            y=alt.Y(
                "Value:Q",
                title="System Temperature (°C)",
                scale=alt.Scale(domain=[system_min - padding, system_max + padding], zero=False),
                axis=alt.Axis(format=".1f"),
            ),
            color=alt.Color(
                "Temperature:N",
                legend=alt.Legend(orient="top", title=None),
                scale=alt.Scale(
                    domain=[
                        "temp_hotwater_target",
                        "temp_hotwater",
                        "temp_solcollector",
                        "temp_boiler",
                        "temp_heating",
                        "temp_solstorage",
                    ],
                    range=[
                        "rgba(153,153,153,0.8)",
                        "rgba(0,0,255,0.8)",
                        "rgba(255,0,0,0.8)",
                        "rgba(0,191,255,0.7)",
                        "rgba(0,255,0,0.7)",
                        "rgba(255,255,0,0.7)",
                    ],
                ),
            ),
            tooltip=["time:T", "Temperature:N", alt.Tooltip("Value:Q", format=".1f")],
        )
        .transform_filter(
            ~alt.FieldOneOfPredicate(
                field="Temperature",
                oneOf=["temp_hotwater", "temp_solcollector", "temp_hotwater_target"],
            )
        )
        .properties()
    )

    # Special chart for hotwater and solcollector with thicker lines
    special_temp_chart = (
        alt.Chart(system_data)
        .mark_line(
            strokeWidth=1.5  # Thicker lines
        )
        .encode(
            x=alt.X("time:T"),
            y=alt.Y(
                "Value:Q", scale=alt.Scale(domain=[system_min - padding, system_max + padding])
            ),
            color=alt.Color(
                "Temperature:N",
                scale=alt.Scale(
                    domain=["temp_hotwater", "temp_solcollector"],
                    range=["rgba(0,0,255,0.8)", "rgba(255,0,0,0.8)"],
                ),
            ),
            tooltip=["time:T", "Temperature:N", alt.Tooltip("Value:Q", format=".1f")],
        )
        .transform_filter(
            alt.FieldOneOfPredicate(
                field="Temperature", oneOf=["temp_hotwater", "temp_solcollector"]
            )
        )
    )

    # Special chart for target temperature with dotted lines
    target_temp_chart = (
        alt.Chart(system_data)
        .mark_line(strokeWidth=0.8, strokeDash=[2, 2])
        .encode(
            x=alt.X("time:T"),
            y=alt.Y(
                "Value:Q", scale=alt.Scale(domain=[system_min - padding, system_max + padding])
            ),
            color=alt.value("rgba(153,153,153,0.8)"),
            tooltip=["time:T", "Temperature:N", alt.Tooltip("Value:Q", format=".1f")],
        )
        .transform_filter(alt.datum.Temperature == "temp_hotwater_target")
    )

    # Night bands chart (only if we have night bands data)
    night_band_chart = None
    if not night_df.empty:
        # Draw night time rectangles with dark blue color and increased opacity
        night_band_chart = (
            alt.Chart(night_df)
            .mark_rect(
                color="#141110",  # Dark blue instead of black
                opacity=0.45,  # Increased opacity for better visibility
            )
            .encode(
                x="start:T",
                x2="end:T",
                y=alt.value(0),  # Span the entire height
                y2=alt.value(540),
                tooltip=alt.value(None),  # Disable tooltip
            )
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
            day_bands.append({"start": day_start, "end": day_end})

        current_date += pd.Timedelta(days=1)

    # Create day bands dataframe
    day_df = pd.DataFrame(day_bands)

    # Day bands chart
    day_band_chart = None
    if not day_df.empty:
        # Draw day time rectangles with slightly lighter color
        day_band_chart = (
            alt.Chart(day_df)
            .mark_rect(
                color="#191b10",  # Slightly lighter than background
                opacity=0.45,  # Subtle opacity
            )
            .encode(
                x="start:T",
                x2="end:T",
                y=alt.value(0),
                y2=alt.value(540),
                tooltip=alt.value(None),  # Disable tooltip
            )
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
    chart_layers.append(special_temp_chart)
    chart_layers.append(target_temp_chart)

    # Create the combined chart
    chart_with_bands = alt.layer(*chart_layers).properties(
        width=900  # Set fixed width to prevent extending too far right
    )

    # If we have outside temperature data, add it on a secondary y-axis
    if has_outside_temp:
        outside_data = df[["time", "temp_out"]].dropna().copy()
        outside_data.columns = ["time", "Value"]

        if not outside_data.empty:
            # Calculate different y-axis domains for better visibility
            outside_min = outside_data["Value"].min()
            outside_max = outside_data["Value"].max()
            outside_padding = (outside_max - outside_min) * 0.1

            outside_chart = (
                alt.Chart(outside_data)
                .mark_line(
                    color="rgba(238,130,238,0.7)",  # Faded violet
                    strokeDash=[5, 5],
                    strokeWidth=1.2,  # Slightly thinner
                )
                .encode(
                    x=alt.X("time:T"),
                    y=alt.Y(
                        "Value:Q",
                        title="Outside Temperature (°C)",
                        scale=alt.Scale(
                            domain=[outside_min - outside_padding, outside_max + outside_padding],
                            zero=False,
                        ),
                        axis=alt.Axis(format=".1f", grid=False),
                    ),
                    tooltip=[
                        alt.Tooltip("time:T"),
                        alt.Tooltip("Value:Q", title="temp_out", format=".1f"),
                    ],
                )
            )

            # First create a layer chart without properties
            layered_base = alt.layer(
                chart_with_bands,  # Use chart with night bands
                outside_chart,
            ).resolve_scale(y="independent")

            # Then add the properties to the final chart
            final_chart = layered_base.properties(
                padding={"left": 30, "top": 30, "right": 30, "bottom": 30},
                width=900,  # Set fixed width to prevent extending too far right
                height=700,
            )

            return final_chart.configure(background="#2d2d2d")

    # If no outside temperature, apply properties to the final chart
    return chart_with_bands.properties(
        # padding={"left": 30, "top": 30, "right": 30, "bottom": 30},
        # width=900,  # Set fixed width
        # height=500
    ).configure(background="#2d2d2d")


def plot_system_metrics(df):
    """Plot system metrics using Altair"""
    system_cols = ["hours", "starts", "solar_production"]

    # Only keep columns that exist in the dataframe
    available_cols = [col for col in system_cols if col in df.columns]

    if not available_cols:
        st.warning("No system metrics data available.")
        return None

    # Data for the chart
    chart_data = df.melt(
        id_vars=["time"], value_vars=available_cols, var_name="Metric", value_name="Value"
    )

    # Remove rows with null values
    chart_data = chart_data.dropna()

    if chart_data.empty:
        st.warning("No system metrics data available after removing null values.")
        return None

    # Create base chart with added horizontal padding
    chart = (
        alt.Chart(chart_data)
        .mark_line(
            strokeWidth=0.8  # Thinner lines
        )
        .encode(
            x=alt.X("time:T", title="Time", axis=alt.Axis(labelPadding=10, grid=True)),
            y=alt.Y("Value:Q", title="Value", axis=alt.Axis(grid=True)),
            color=alt.Color("Metric:N", legend=alt.Legend(orient="top", title=None)),
            tooltip=["time:T", "Metric:N", "Value:Q"],
        )
        .properties(
            height=400,
            padding={"left": 30, "top": 30, "right": 30, "bottom": 30},
            width=900,  # Set fixed width
        )
    )

    return chart.configure(
        background="#2d2d2d",
        axis=alt.AxisConfig(
            gridColor="#444444", gridOpacity=0.3, labelColor="white", titleColor="white"
        ),
    )


def plot_boolean_status(df):
    """Plot boolean status of pumps and devices"""
    boolean_cols = ["active", "solar_pump", "circulation_pump", "dhw_pump"]

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
            df[col] = pd.Series(pd.to_numeric(df[col], errors="coerce")).fillna(0).astype(int)

    # Print raw data for debugging
    st.sidebar.write("Sample boolean data (5 rows):")
    for col in available_cols:
        sample_data = df[["time", col]].head(5)
        st.sidebar.write(f"{col}:\n", sample_data)

    # Create charts for boolean variables
    charts = []

    for device in available_cols:
        # Create individual device dataframe
        device_data = df[["time", device]].copy()
        device_data.columns = ["time", "Status"]  # Rename for consistency

        # Create individual step chart
        device_chart = (
            alt.Chart(device_data)
            .mark_line(
                interpolate="step-after",
                strokeWidth=0.8,  # Even thinner lines
                color="rgba(1,255,112,0.7)",  # Faded green
            )
            .encode(
                x=alt.X("time:T", title=None, axis=alt.Axis(grid=True)),
                y=alt.Y(
                    "Status:Q",
                    scale=alt.Scale(domain=[-0.1, 1.1]),
                    axis=alt.Axis(title=None, labels=False, ticks=False),
                ),
                tooltip=["time:T", alt.Tooltip("Status:Q", title=device)],
            )
            .properties(title=device, height=50)
        )

        # Add a baseline
        baseline = (
            alt.Chart(pd.DataFrame({"y": [0]}))
            .mark_rule(strokeDash=[2, 2], stroke="#444444", strokeWidth=1)
            .encode(y="y")
        )

        charts.append(device_chart + baseline)

    # Add modulation as a special case if it exists
    if "modulation" in df.columns:
        # Create modulation dataframe
        mod_data = df[["time", "modulation"]].copy().dropna()

        # Handle missing values but don't multiply by 100
        mod_data["modulation"] = pd.Series(
            pd.to_numeric(mod_data["modulation"], errors="coerce")
        ).fillna(0)

        # Use fixed domain of 0-100
        mod_chart = (
            alt.Chart(mod_data)
            .mark_line(
                color="rgba(253,151,31,0.7)",  # Faded orange
                strokeWidth=0.8,  # Thinner line
            )
            .encode(
                x=alt.X("time:T", title=None, axis=alt.Axis(grid=True)),
                y=alt.Y(
                    "modulation:Q",
                    title="Modulation %",
                    axis=alt.Axis(grid=True),
                    scale=alt.Scale(domain=[0, 100]),
                ),
                tooltip=["time:T", alt.Tooltip("modulation:Q", title="Modulation %", format=".1f")],
            )
            .properties(
                title="modulation",
                height=100,  # Taller than binary status rows
            )
        )

        # Add to charts list
        charts.append(mod_chart)

    # Combine charts with spacing
    if charts:
        final_chart = (
            alt.vconcat(*charts)
            .resolve_scale(x="shared")
            .properties(
                padding={"left": 30, "top": 30, "right": 30, "bottom": 30},
            )
        )
        return final_chart.configure(
            background="#2d2d2d",
            axis=alt.AxisConfig(
                gridColor="#444444", gridOpacity=0.3, labelColor="white", titleColor="white"
            ),
        )

    return None


def create_sparkline(df, column, last_hours=2):
    """Create a small sparkline chart for a temperature column"""
    # Get the last X hours of data
    last_x_hours = df["time"].iloc[-1] - pd.Timedelta(hours=last_hours)
    sparkline_data = df[df["time"] >= last_x_hours][["time", column]].dropna().copy()

    if sparkline_data.empty or len(sparkline_data) < 2:
        return None, None, None

    # Determine if temperature is increasing or decreasing
    start_temp = sparkline_data[column].iloc[0]
    end_temp = sparkline_data[column].iloc[-1]
    is_increasing = end_temp > start_temp
    line_color = "#4CAF50" if is_increasing else "#F44336"  # Material design green/red

    # Create a sparkline chart that's properly sized for the dashboard
    chart = (
        alt.Chart(sparkline_data)
        .mark_line(color=line_color, strokeWidth=2)
        .encode(
            x=alt.X("time:T", axis=None),
            y=alt.Y(column, axis=None, scale=alt.Scale(zero=False))
        )
        .properties(height=40, width=100, padding={"top": 0, "right": 0, "bottom": 0, "left": 0})
    )

    # Add trend indicator
    trend_icon = "▲" if is_increasing else "▼"
    temp_diff = end_temp - start_temp
    trend_text = f"{trend_icon} {abs(temp_diff):.1f}°C"

    return chart, trend_text, line_color


def main():
    """Main function for the Streamlit app"""
    setup_page()

    st.title("ViCare Monitoring")

    # Create a three-column layout for the top section
    left_col, middle_col, _, right_col = st.columns([2, 2, 2, 1], vertical_alignment="center")

    # Time Range selector in right column
    with right_col:
        days = st.selectbox("Time Range (days)", [1, 2, 3, 7, 14, 30], index=1)

    # Load data
    df = load_data(days=days)

    if df is not None:
        with left_col:
            # Center the content vertically
            last_update = datetime.now(pytz.timezone(settings.timezone)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            df["time"] = df["time"].dt.tz_convert(settings.timezone)
            last_data_point = df["time"].iloc[-1].strftime("%Y-%m-%d %H:%M:%S")
            # last_data_point = (
            #     (pd.to_datetime(df.iloc[-1]["timestamp"], unit="s", utc=True))
            #     .tz_convert(settings.timezone)
            #     .strftime("%Y-%m-%d %H:%M:%S")
            # )
            st.markdown(
                f"""
                    <p>Last refresh: {last_update}</p>
                    <p>Last data update: {last_data_point}</p>
                """,
                unsafe_allow_html=True,
            )
        # Display current DHW temperature in middle column
        if "temp_hotwater" in df.columns:
            current_temp = df["temp_hotwater"].iloc[-1]  # Get most recent value

            # Get solar storage temps if available
            has_solar_storage = "temp_solstorage" in df.columns
            solar_current = df["temp_solstorage"].iloc[-1] if has_solar_storage else None

            # Get metrics and create sparklines
            dhw_sparkline, dhw_trend_text, dhw_color = create_sparkline(df, "temp_hotwater") or (
                None,
                "",
                "",
            )
            solar_sparkline, solar_trend_text, solar_color = (
                create_sparkline(df, "temp_solstorage") if has_solar_storage else (None, "", "")
            )

            # Apply custom CSS for styling
            middle_col.markdown(
                """
            <style>

            .temp-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 5px;
            }

            .vega-embed .marks {
                border: .3px solid #4d4d4d;
                border-radius: 10px;
                max-width: 100% ;
            }

            .metric-label {
                font-size: 1.2rem;
                color: #CCCCCC;
                margin-bottom: 0;
                margin-right: 20px;
            }

            .metric-value {
                font-size: 3rem;
                font-weight: bold;
                color: #e0e0e0;
                margin: 0;
            }

            .trend-label {
                font-size: 12px;
                font-weight: bold;
                margin: 0;
            }

            .sparkline-container {
                width: 100px;
            }
            </style>
            """,
                unsafe_allow_html=True,
            )

            # Create dashboard container directly in the column
            # middle_col.markdown('<div class="metric-dashboard">', unsafe_allow_html=True)

            # Hot water sparkline with integrated temperature
            if dhw_sparkline is not None:
                with middle_col:
                    midleft_col, midright_col = st.columns([3, 2])
                    midleft_col.markdown(
                        f"""
                    <div class="sparkline-container">
                        <div class="temp-header">
                            <div class="metric-label">Hot Water:</div>
                            <div class="metric-value">{current_temp:.1f}°C</div>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    midright_col.markdown(
                        f"""
                    <div class="trend-label" style="color: {dhw_color}">Last 2h: {dhw_trend_text}</div>
                    """,
                        unsafe_allow_html=True,
                    )
                    midright_col.altair_chart(
                        dhw_sparkline.properties(width=100).configure(background="#2a2a2a"),
                        use_container_width=False,
                    )

            # Solar storage section if available
            if has_solar_storage and solar_current is not None and solar_sparkline is not None:
                # Add divider
                middle_col.markdown(
                    '<hr style="border: none; height: 1px; background-color: #3d3d3d; margin: 0px 0 0px 0;">',
                    unsafe_allow_html=True,
                )

                with middle_col:
                    midleft_col, midright_col = st.columns([3, 2])
                    # Solar sparkline with integrated temperature
                    midleft_col.markdown(
                        f"""
                    <div class="sparkline-container">
                        <div class="temp-header">
                            <div class="metric-label">Solar Storage:</div>
                            <div class="metric-value">{solar_current:.1f}°C</div>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
                    midright_col.markdown(
                        f"""<div class="trend-label" style="color: {solar_color}">Last 2h: {solar_trend_text}</div>
                    """,
                        unsafe_allow_html=True,
                    )
                midright_col.altair_chart(
                    solar_sparkline.properties(width=100).configure(background="#2a2a2a"),
                    use_container_width=False,
                )

            # Close container
            # middle_col.markdown('</div>', unsafe_allow_html=True)

        # Temperature metrics
        st.subheader("Temperature Metrics")
        temp_chart = plot_temperatures(df)
        if temp_chart:
            st.altair_chart(temp_chart)

        # Plot boolean status
        st.subheader("Device Activity Status")
        boolean_chart = plot_boolean_status(df)
        if boolean_chart:
            st.altair_chart(boolean_chart, use_container_width=True)

        # System metrics
        st.subheader("System Metrics")
        system_chart = plot_system_metrics(df)
        if system_chart:
            st.altair_chart(system_chart, use_container_width=True)


if __name__ == "__main__":
    main()
