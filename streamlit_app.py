from __future__ import annotations

from io import BytesIO
import importlib.util
from itertools import cycle

import pandas as pd
import plotly.express as px
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
            yaxis_title="Electric power consumption (kWh per capita)",
        )
        return fig

    x_min = df_filtered["Coal_Percentage_Value"].min() * 0.95
    x_max = df_filtered["Coal_Percentage_Value"].max() * 1.05
    y_min = df_filtered["Electricity_Consumption_Value"].min() * 0.95
    y_max = df_filtered["Electricity_Consumption_Value"].max() * 1.05

    palette_cycle = cycle(COLOR_PALETTE)
    color_map: dict[str, str] = {}
    for country in unique_countries:
        color_map[country] = next(palette_cycle)

    fig = px.scatter(
        df_filtered,
        x="Coal_Percentage_Value",
        y="Electricity_Consumption_Value",
        animation_frame="Year",
        animation_group="Country Name",
        color="Country Name",
        hover_name="Country Name",
        category_orders={"Country Name": unique_countries},
        color_discrete_map=color_map,
        labels={
            "Coal_Percentage_Value": "Electricity from Coal (% of total)",
            "Electricity_Consumption_Value": "Electric power consumption (kWh per capita)",
        },
    )

    for country in unique_countries:
        country_data = (
            df_filtered[df_filtered["Country Name"] == country]
            .sort_values(by="Year")
            .drop_duplicates(subset="Year")
        )
        fig.add_trace(
            go.Scatter(
                x=country_data["Coal_Percentage_Value"],
                y=country_data["Electricity_Consumption_Value"],
                mode="lines",
                line=dict(color=color_map[country], width=1.5),
                name=f"{country} trend",
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_layout(
        title_text=(
            "Electricity Consumption vs. Coal Percentage "
            f"({', '.join(selected_countries or unique_countries)})"
        ),
        xaxis_title="Electricity from Coal (% of total)",
        yaxis_title="Electric power consumption (kWh per capita)",
        xaxis=dict(range=[x_min, x_max]),
        yaxis=dict(range=[y_min, y_max]),
        hovermode="closest",
        height=700,
    )

    if fig.layout.updatemenus:
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 800
        fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 200

    return fig


def figure_to_gif(fig: go.Figure) -> bytes:
    """Render the current Plotly figure into a GIF image and return raw bytes."""

    try:
        image_bytes = fig.to_image(format="png", width=1400, height=800, scale=2)
    except ValueError as exc:  # Raised when Kaleido is not available.
        raise RuntimeError("Kaleido is required to export the chart as a GIF.") from exc

    png_image = Image.open(BytesIO(image_bytes))
    output = BytesIO()
    png_image.save(output, format="GIF")
    output.seek(0)
    return output.read()


def kaleido_available() -> bool:
    """Check whether Kaleido is importable in the current environment."""

    return importlib.util.find_spec("kaleido") is not None


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
        except RuntimeError:
            st.warning(
                "Kaleido is installed but failed to initialize. Please restart the app.",
                icon="⚠️",
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
