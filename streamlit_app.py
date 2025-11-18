from __future__ import annotations

from io import BytesIO
import importlib.util
from itertools import cycle

import pandas as pd
import plotly.graph_objects as go
from plotly.express import colors as px_colors
import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="Coal vs Electricity Consumption",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = "cleaned_country_data.csv"
INITIAL_SELECTED_COUNTRIES = [
    "United States",
    "China",
    "India",
    "Germany",
    "South Africa",
]


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
    """Read the cleaned dataset that ships with the repository."""
    df = pd.read_csv(path)
    df["Country Name"] = df["Country Name"].replace({"Korea, Rep": "South Korea"})
    return df.dropna(subset=["Electricity_Consumption_Value", "Coal_Percentage_Value"])


COLOR_PALETTE = px_colors.qualitative.Safe


def build_figure(
    df_plot: pd.DataFrame,
    selected_countries: list[str],
) -> go.Figure:
    df_filtered = df_plot.copy()

    if selected_countries:
        df_filtered = df_filtered[df_filtered["Country Name"].isin(selected_countries)]

    unique_countries = sorted(df_filtered["Country Name"].unique())
    if not unique_countries:
        fig = go.Figure()
        fig.update_layout(
            title_text="No data available for the selected filters",
            xaxis_title="Electricity from Coal (% of total)",
            yaxis_title="Electricity consumption per capita (kWh)",
        )
        return fig

    df_filtered = (
        df_filtered.sort_values(by=["Country Name", "Year"])
        .drop_duplicates(subset=["Country Name", "Year"], keep="last")
    )

    x_min = df_filtered["Coal_Percentage_Value"].min() * 0.95
    x_max = df_filtered["Coal_Percentage_Value"].max() * 1.05
    y_min = df_filtered["Electricity_Consumption_Value"].min() * 0.95
    y_max = df_filtered["Electricity_Consumption_Value"].max() * 1.05

    palette_cycle = cycle(COLOR_PALETTE)
    color_map: dict[str, str] = {}
    for country in unique_countries:
        color_map[country] = next(palette_cycle)

    years = sorted(df_filtered["Year"].unique())
    country_data_map: dict[str, pd.DataFrame] = {}
    for country in unique_countries:
        country_data_map[country] = df_filtered[df_filtered["Country Name"] == country]

    frames: list[go.Frame] = []
    for year in years:
        frame_traces: list[go.Scatter] = []
        for country in unique_countries:
            country_data = country_data_map[country]
            history = country_data[country_data["Year"] <= year]
            if history.empty:
                continue

            frame_traces.append(
                go.Scatter(
                    x=history["Coal_Percentage_Value"],
                    y=history["Electricity_Consumption_Value"],
                    mode="lines",
                    line=dict(color=color_map[country], width=2),
                    name=f"{country} trajectory",
                    showlegend=False,
                    hoverinfo="skip",
                    legendgroup=country,
                )
            )

            current_point = history.iloc[-1]
            frame_traces.append(
                go.Scatter(
                    x=[current_point["Coal_Percentage_Value"]],
                    y=[current_point["Electricity_Consumption_Value"]],
                    mode="markers",
                    marker=dict(color=color_map[country], size=10),
                    name=country,
                    legendgroup=country,
                    hovertemplate=(
                        "Country: %{customdata[0]}<br>Year: %{customdata[1]}<br>"
                        "Coal from electricity: %{x:.2f}%<br>"
                        "Consumption: %{y:.0f} kWh<extra></extra>"
                    ),
                    customdata=[[country, int(current_point["Year"])]],
                )
            )

        frames.append(go.Frame(data=frame_traces, name=str(year)))

    if frames:
        initial_data = frames[0].data
    else:
        initial_data = []

    fig = go.Figure(data=initial_data, frames=frames)

    fig.update_layout(
        title_text=(
            "Electricity Consumption vs. Coal Percentage "
            f"({', '.join(selected_countries or unique_countries)})"
        ),
        xaxis_title="Electricity from Coal (% of total)",
        yaxis_title="Electricity consumption per capita (kWh)",
        xaxis=dict(
            range=[x_min, x_max],
            tickfont={"size": 14},
            title_font={"size": 18},
        ),
        yaxis=dict(
            range=[y_min, y_max],
            tickfont={"size": 14},
            title_font={"size": 18},
        ),
        hovermode="closest",
        height=700,
        updatemenus=[
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.0,
                "y": -0.1,
                "showactive": False,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "frame": {"duration": 400, "redraw": True},
                                "transition": {"duration": 100},
                                "fromcurrent": True,
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [[None], {"frame": {"duration": 0}, "mode": "immediate"}],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "y": -0.15,
                "x": 0.05,
                "len": 0.9,
                "pad": {"b": 10, "t": 50},
                "currentvalue": {"prefix": "Year: ", "visible": True},
                "steps": [
                    {
                        "args": [[str(year)], {"frame": {"duration": 0}, "mode": "immediate"}],
                        "label": str(year),
                        "method": "animate",
                    }
                    for year in years
                ],
            }
        ],
    )

    return fig


def figure_to_gif(fig: go.Figure) -> bytes:
    """Render the current Plotly figure into a GIF image and return raw bytes."""

    try:
        image_bytes = fig.to_image(format="png", width=1400, height=800, scale=2)
    except ValueError as exc:  # Raised when Kaleido is not available or misconfigured.
        raise RuntimeError(str(exc)) from exc

    png_image = Image.open(BytesIO(image_bytes))
    output = BytesIO()
    png_image.save(output, format="GIF")
    output.seek(0)
    return output.read()


def kaleido_available() -> bool:
    """Check whether Kaleido is importable in the current environment."""

    spec = importlib.util.find_spec("kaleido")
    if spec is None:
        return False

    try:
        importlib.util.module_from_spec(spec)
    except Exception:
        return False
    return True


def main() -> None:
    st.title("Electricity Consumption vs. Coal Reliance")
    st.markdown(
        """
        Explore how the share of electricity generated from coal correlates with
        per-capita electricity consumption across countries. Use the controls
        below to compare multiple countries and then press play on the chart to
        watch the full historical timeline animate.
        """
    )

    with st.spinner("Loading data and preparing the visualization..."):
        df_plot = load_data(DATA_PATH)

    st.subheader("Customize the view")

    all_countries = sorted(df_plot["Country Name"].unique())
    country_selection = st.multiselect(
        "Select countries to display",
        options=all_countries,
        default=[c for c in INITIAL_SELECTED_COUNTRIES if c in all_countries],
        help="Choose any number of countries to display at once.",
    )

    fig = build_figure(df_plot, country_selection)

    st.plotly_chart(fig, width="stretch")
    st.caption("Press the ▶️ button below the chart to watch the timeline animate.")

    if kaleido_available():
        try:
            gif_bytes = figure_to_gif(fig)
        except RuntimeError as exc:
            st.error(
                "Plotly could not talk to Kaleido to export the chart. "
                "Please reinstall `kaleido` (e.g., `pip install --force-reinstall kaleido`) "
                "and then refresh the app.\n\n"
                f"Details: {exc}",
                icon="🚫",
            )
        else:
            st.download_button(
                label="Download current chart as GIF",
                data=gif_bytes,
                file_name="electricity_vs_coal.gif",
                mime="image/gif",
                use_container_width=True,
            )
    else:
        st.download_button(
            label="Install `kaleido` to enable GIF downloads",
            data=b"",
            disabled=True,
            help="Add kaleido to your environment (e.g., `pip install kaleido`) to export charts.",
        )


if __name__ == "__main__":
    main()
