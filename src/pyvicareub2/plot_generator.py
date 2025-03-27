import matplotlib

matplotlib.use(
    "Agg"
)  # Set the backend to non-interactive 'Agg' before any other matplotlib imports
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

logger = logging.getLogger("ViCareUB2")


class PlotGenerator:
    def __init__(self):
        plt.style.use("dark_background")
        self.colors = {
            "background": "#1a1a1a",
            "plot_background": "#2d2d2d",
            "grid": "gray",
            "text": "white",
        }
        # Ensure static directory exists
        self.static_dir = Path("static")
        self.static_dir.mkdir(exist_ok=True)

    def _style_plot(self, ax):
        """Apply consistent styling to plot axes"""
        ax.xaxis.set_tick_params(rotation=30, colors=self.colors["text"])
        ax.yaxis.set_tick_params(colors=self.colors["text"])
        for spine in ax.spines.values():
            spine.set_color(self.colors["text"])
        ax.grid(True, color=self.colors["grid"], alpha=0.2)

    def _add_night_spans(self, ax, start_time: datetime):
        """Add night time spans to plot"""
        now = datetime.now()
        x1 = start_time.replace(hour=21, minute=30, second=0, microsecond=0)
        x2 = x1 + timedelta(hours=8)

        while x1 < now:
            ax.axvspan(x1, x2, 0, 10, color="#404040", alpha=0.3)
            x1 = x1 + timedelta(hours=24)
            x2 = x1 + timedelta(hours=8)
            if x2 > now:
                x2 = now

    def generate_plots(self, data: pd.DataFrame) -> Optional[datetime]:
        """Generate system and temperature plots"""
        try:
            # System metrics plot
            fig1, ax1 = plt.subplots(figsize=(12, 8))
            fig1.patch.set_facecolor(self.colors["background"])
            ax1.set_facecolor(self.colors["plot_background"])

            system_metrics = [
                "hours",
                "active",
                "modulation",
                "starts",
                "solar_production",
                "solar_pump",
            ]
            sns.lineplot(
                data=data[data.variable.isin(system_metrics)],
                x="time",
                y="value",
                hue="variable",
                ax=ax1,
            )
            ax1.set_title("System Metrics", color=self.colors["text"], pad=20)
            self._style_plot(ax1)
            self._add_night_spans(ax1, datetime.now() + timedelta(days=-2))

            plt.tight_layout()
            system_metrics_path = self.static_dir / "system_metrics.png"
            plt.savefig(
                system_metrics_path,
                facecolor=self.colors["background"],
                edgecolor="none",
                bbox_inches="tight",
                pad_inches=0.5,
            )
            plt.close(fig1)

            # Temperature metrics plot
            fig2, ax2 = plt.subplots(figsize=(12, 8))
            fig2.patch.set_facecolor(self.colors["background"])
            ax2.set_facecolor(self.colors["plot_background"])

            temps = [
                "temp_boiler",
                "temp_hotwater",
                "temp_hotwater_target",
                "temp_solcollector",
                "temp_solstorage",
            ]

            sns.lineplot(
                data=data[data.variable.isin(temps)],
                x="time",
                y="value",
                hue="variable",
                ax=ax2,
            )

            ax2_twin = ax2.twinx()
            sns.lineplot(
                data=data[data.variable == "temp_out"],
                x="time",
                y="value",
                color="violet",
                ax=ax2_twin,
            )

            ax2.set_title("Temperature Metrics", color=self.colors["text"], pad=20)
            self._style_plot(ax2)
            self._style_plot(ax2_twin)
            self._add_night_spans(ax2, datetime.now() + timedelta(days=-2))

            plt.tight_layout()
            temp_metrics_path = self.static_dir / "temperature_metrics.png"
            plt.savefig(
                temp_metrics_path,
                facecolor=self.colors["background"],
                edgecolor="none",
                bbox_inches="tight",
                pad_inches=0.5,
            )
            plt.close(fig2)

            logger.info(f"Successfully saved plots to {self.static_dir}")
            return data.iloc[-1, 0]  # Return last timestamp

        except Exception as e:
            logger.error(f"Failed to generate plots: {e}")
            raise
