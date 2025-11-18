from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.graph_objects as go
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


def build_figure(
    df_plot: pd.DataFrame,
    selected_countries: list[str],
    year_range: tuple[int, int],
) -> go.Figure:
    df_filtered = df_plot[
        (df_plot["Year"] >= year_range[0]) & (df_plot["Year"] <= year_range[1])
    ]

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

    fig = go.Figure()

    for country in unique_countries:
        country_data = df_filtered[df_filtered["Country Name"] == country]
        if country_data.empty:
            continue

        first_year_data = country_data.sort_values(by="Year").iloc[0]
        last_year_data = country_data.sort_values(by="Year").iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=country_data["Coal_Percentage_Value"],
                y=country_data["Electricity_Consumption_Value"],
                mode="lines+markers",
                name=country,
                visible=True,
                showlegend=True,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[first_year_data["Coal_Percentage_Value"]],
                y=[first_year_data["Electricity_Consumption_Value"]],
                mode="text",
                text=[str(first_year_data["Year"])],
                textposition="bottom right",
                name=f"{country} Start Year",
                visible=True,
                showlegend=False,
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[last_year_data["Coal_Percentage_Value"]],
                y=[last_year_data["Electricity_Consumption_Value"]],
                mode="text",
                text=[str(last_year_data["Year"])],
                textposition="top left",
                name=f"{country} End Year",
                visible=True,
                showlegend=False,
            )
        )

    x_min = df_filtered["Coal_Percentage_Value"].min() * 0.95
    x_max = df_filtered["Coal_Percentage_Value"].max() * 1.05
    y_min = df_filtered["Electricity_Consumption_Value"].min() * 0.95
    y_max = df_filtered["Electricity_Consumption_Value"].max() * 1.05

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


def main() -> None:
    st.title("Electricity Consumption vs. Coal Reliance")
    st.markdown(
        """
        Explore how the share of electricity generated from coal correlates with
        per-capita electricity consumption across countries. Use the controls
        below to scroll through the historical timeline and compare multiple
        countries side by side.
        """
    )

    with st.spinner("Loading data and preparing the visualization..."):
        df_plot = load_data(DATA_PATH)

    min_year = int(df_plot["Year"].min())
    max_year = int(df_plot["Year"].max())

    st.subheader("Customize the view")
    selected_years = st.slider(
        "Timeline (year range)",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1,
    )

    all_countries = sorted(df_plot["Country Name"].unique())
    country_selection = st.multiselect(
        "Select countries to display",
        options=all_countries,
        default=[c for c in INITIAL_SELECTED_COUNTRIES if c in all_countries],
        help="Choose any number of countries to display at once.",
    )

    fig = build_figure(df_plot, country_selection, selected_years)

    st.plotly_chart(fig, width="stretch")

    try:
        gif_bytes = figure_to_gif(fig)
    except RuntimeError:
        st.info(
            "Install the optional `kaleido` dependency to enable GIF downloads.",
            icon="ℹ️",
        )
    else:
        st.download_button(
            label="Download current chart as GIF",
            data=gif_bytes,
            file_name="electricity_vs_coal.gif",
            mime="image/gif",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
