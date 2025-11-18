import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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


def build_figure(df_plot: pd.DataFrame) -> go.Figure:
    unique_countries = sorted(df_plot["Country Name"].unique())

    fig = go.Figure()
    trace_indices_map: dict[str, dict[str, int]] = {}
    current_trace_index = 0

    for country in unique_countries:
        country_data = df_plot[df_plot["Country Name"] == country]
        if country_data.empty:
            continue

        first_year_data = country_data.sort_values(by="Year").iloc[0]
        last_year_data = country_data.sort_values(by="Year").iloc[-1]
        initial_visibility = country in INITIAL_SELECTED_COUNTRIES

        fig.add_trace(
            go.Scatter(
                x=country_data["Coal_Percentage_Value"],
                y=country_data["Electricity_Consumption_Value"],
                mode="lines+markers",
                name=country,
                visible=initial_visibility,
                showlegend=True,
            )
        )
        line_trace_idx = current_trace_index
        current_trace_index += 1

        fig.add_trace(
            go.Scatter(
                x=[first_year_data["Coal_Percentage_Value"]],
                y=[first_year_data["Electricity_Consumption_Value"]],
                mode="text",
                text=[str(first_year_data["Year"])],
                textposition="bottom right",
                name=f"{country} Start Year",
                visible=initial_visibility,
                showlegend=False,
            )
        )
        start_text_trace_idx = current_trace_index
        current_trace_index += 1

        fig.add_trace(
            go.Scatter(
                x=[last_year_data["Coal_Percentage_Value"]],
                y=[last_year_data["Electricity_Consumption_Value"]],
                mode="text",
                text=[str(last_year_data["Year"])],
                textposition="top left",
                name=f"{country} End Year",
                visible=initial_visibility,
                showlegend=False,
            )
        )
        end_text_trace_idx = current_trace_index
        current_trace_index += 1

        trace_indices_map[country] = {
            "line": line_trace_idx,
            "start_text": start_text_trace_idx,
            "end_text": end_text_trace_idx,
        }

    total_traces = current_trace_index

    buttons = []
    visibility_initial_5 = [False] * total_traces
    for country in INITIAL_SELECTED_COUNTRIES:
        if country not in trace_indices_map:
            continue
        indices = trace_indices_map[country]
        visibility_initial_5[indices["line"]] = True
        visibility_initial_5[indices["start_text"]] = True
        visibility_initial_5[indices["end_text"]] = True

    buttons.append(
        dict(
            label="Selected 5 Countries",
            method="update",
            args=[
                {"visible": visibility_initial_5},
                {
                    "title": (
                        "Electricity Consumption vs. Coal Percentage "
                        f"({', '.join(INITIAL_SELECTED_COUNTRIES)})"
                    )
                },
            ],
        )
    )

    buttons.append(
        dict(
            label="All Countries",
            method="update",
            args=[
                {"visible": [True] * total_traces},
                {
                    "title": "Electricity Consumption vs. Coal Percentage (All Countries)",
                },
            ],
        )
    )

    for country, indices in trace_indices_map.items():
        visibility_country = [False] * total_traces
        visibility_country[indices["line"]] = True
        visibility_country[indices["start_text"]] = True
        visibility_country[indices["end_text"]] = True

        buttons.append(
            dict(
                label=country,
                method="update",
                args=[
                    {"visible": visibility_country},
                    {
                        "title": (
                            "Electricity Consumption vs. Coal Percentage "
                            f"({country})"
                        )
                    },
                ],
            )
        )

    x_min = df_plot["Coal_Percentage_Value"].min() * 0.95
    x_max = df_plot["Coal_Percentage_Value"].max() * 1.05
    y_min = df_plot["Electricity_Consumption_Value"].min() * 0.95
    y_max = df_plot["Electricity_Consumption_Value"].max() * 1.05

    fig.update_layout(
        updatemenus=[
            go.layout.Updatemenu(
                active=0,
                buttons=buttons,
                direction="down",
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.1,
                yanchor="top",
            )
        ],
        title_text=(
            "Electricity Consumption vs. Coal Percentage "
            f"({', '.join(INITIAL_SELECTED_COUNTRIES)})"
        ),
        xaxis_title="Electricity from Coal (% of total)",
        yaxis_title="Electric power consumption (kWh per capita)",
        xaxis=dict(range=[x_min, x_max]),
        yaxis=dict(range=[y_min, y_max]),
        hovermode="closest",
        height=700,
    )

    return fig


def main() -> None:
    st.title("Electricity Consumption vs. Coal Reliance")
    st.markdown(
        """
        Explore how the share of electricity generated from coal correlates with
        per-capita electricity consumption across countries. Use the dropdown in
        the Plotly figure to switch between all countries, the highlighted five,
        or any specific nation you are interested in.
        """
    )

    with st.spinner("Loading data and preparing the visualization..."):
        df_plot = load_data(DATA_PATH)
        fig = build_figure(df_plot)

    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
