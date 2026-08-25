import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


st.set_page_config(
    page_title="Energy Tariff Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://energy_user:energy_pass@localhost:5432/energy_db",
)
NAVY = "#12243A"
TEAL = "#00A6A6"
BLUE = "#2878B5"
AMBER = "#F2A900"
GRID = "rgba(18,36,58,.10)"


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


@st.cache_data(ttl=60, show_spinner=False)
def load_pipeline_runs() -> pd.DataFrame:
    query = text("""
        SELECT run_id, started_at, finished_at, status, duration_seconds,
               rows_processed, error_message
        FROM pipeline_runs
        ORDER BY started_at DESC
    """)
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=300, show_spinner=False)
def load_predictions() -> pd.DataFrame:
    query = text("""
        SELECT operador_de_red, nivel, last_observed_period, last_cu,
               target_period, predicted_cu
        FROM tariff_predictions
        ORDER BY operador_de_red, nivel, target_period
    """)
    return pd.read_sql(query, get_engine())


@st.cache_data(ttl=300, show_spinner=False)
def load_tariff_history() -> pd.DataFrame:
    query = text("""
        SELECT operador_de_red, nivel, a_o, periodo, cu_total
        FROM energy_tariffs
    """)
    return pd.read_sql(query, get_engine())


def apply_chart_style(fig: go.Figure, height: int = 330) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=16, r=16, t=42, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", color=NAVY),
        hoverlabel=dict(bgcolor="white", font_color=NAVY),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def format_duration(seconds) -> str:
    if pd.isna(seconds):
        return "—"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:,.1f} s"
    minutes, remaining = divmod(seconds, 60)
    return f"{int(minutes)} min {remaining:02.0f} s"


def render_pipeline_monitoring(runs: pd.DataFrame) -> None:
    st.markdown('<div class="section-label">OPERACIÓN</div>', unsafe_allow_html=True)
    st.subheader("Pipeline Monitoring")

    if runs.empty:
        st.info("Todavía no hay ejecuciones registradas en pipeline_runs.")
        return

    runs = runs.copy()
    runs["started_at"] = pd.to_datetime(runs["started_at"], errors="coerce")
    runs["finished_at"] = pd.to_datetime(runs["finished_at"], errors="coerce")
    runs["duration_seconds"] = pd.to_numeric(runs["duration_seconds"], errors="coerce")
    runs["rows_processed"] = pd.to_numeric(runs["rows_processed"], errors="coerce")
    latest = runs.sort_values("started_at", ascending=False).iloc[0]
    status = str(latest["status"]).strip() if pd.notna(latest["status"]) else "Sin estado"
    is_error = bool(pd.notna(latest["error_message"]) and str(latest["error_message"]).strip())
    error_count = int(is_error or status.lower() in {"failed", "failure", "error"})
    started = latest["started_at"]
    started_label = started.strftime("%d %b %Y · %H:%M") if pd.notna(started) else "—"

    cols = st.columns(5)
    cols[0].metric("Estado última ejecución", status.upper())
    cols[1].metric("Fecha / hora", started_label)
    cols[2].metric("Duración", format_duration(latest["duration_seconds"]))
    cols[3].metric("Registros procesados", f"{latest['rows_processed']:,.0f}" if pd.notna(latest["rows_processed"]) else "—")
    cols[4].metric("Errores", f"{error_count}")

    chronological = runs.sort_values("started_at")
    chart_left, chart_right = st.columns(2)
    with chart_left:
        duration_fig = go.Figure(go.Scatter(
            x=chronological["started_at"], y=chronological["duration_seconds"],
            mode="lines+markers", line=dict(color=TEAL, width=3),
            marker=dict(size=7), fill="tozeroy", fillcolor="rgba(0,166,166,.08)",
            hovertemplate="%{x|%d %b %H:%M}<br><b>%{y:.1f} s</b><extra></extra>",
        ))
        duration_fig.update_layout(title="Duración por ejecución")
        duration_fig.update_yaxes(title="Segundos")
        st.plotly_chart(apply_chart_style(duration_fig), use_container_width=True)
    with chart_right:
        volume_fig = go.Figure(go.Bar(
            x=chronological["started_at"], y=chronological["rows_processed"],
            marker_color=BLUE,
            hovertemplate="%{x|%d %b %H:%M}<br><b>%{y:,.0f} registros</b><extra></extra>",
        ))
        volume_fig.update_layout(title="Volumen procesado")
        volume_fig.update_yaxes(title="Registros")
        st.plotly_chart(apply_chart_style(volume_fig), use_container_width=True)

    st.markdown("#### Historial de ejecuciones")
    table = runs.rename(columns={
        "run_id": "Ejecución", "started_at": "Inicio", "finished_at": "Fin",
        "status": "Estado", "duration_seconds": "Duración (s)",
        "rows_processed": "Registros", "error_message": "Detalle de error",
    })
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Inicio": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm:ss"),
            "Fin": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm:ss"),
            "Duración (s)": st.column_config.NumberColumn(format="%.2f"),
            "Registros": st.column_config.NumberColumn(format="%d"),
        },
    )


def build_history_date(history: pd.DataFrame) -> pd.DataFrame:
    history = history.copy()
    month_names = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
        "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
        "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    }
    raw_period = history["periodo"].astype(str).str.strip().str.lower()
    numeric_month = pd.to_numeric(raw_period, errors="coerce")
    mapped_month = raw_period.map(month_names)
    history["mes"] = numeric_month.fillna(mapped_month)
    history["fecha"] = pd.to_datetime(
        dict(year=pd.to_numeric(history["a_o"], errors="coerce"), month=history["mes"], day=1),
        errors="coerce",
    )
    history["cu_total"] = pd.to_numeric(history["cu_total"], errors="coerce")
    return history.dropna(subset=["fecha", "cu_total"]).sort_values("fecha")


def render_tariff_predictions(predictions: pd.DataFrame, history: pd.DataFrame) -> None:
    st.markdown('<div class="section-label">ANALÍTICA</div>', unsafe_allow_html=True)
    st.subheader("Predicción de Tarifas")

    if predictions.empty:
        st.info("Todavía no hay predicciones disponibles en tariff_predictions.")
        return

    predictions = predictions.copy()
    for col in ["last_observed_period", "target_period"]:
        predictions[col] = pd.to_datetime(predictions[col], errors="coerce")
    for col in ["last_cu", "predicted_cu"]:
        predictions[col] = pd.to_numeric(predictions[col], errors="coerce")
    predictions["variacion_pct"] = (
        (predictions["predicted_cu"] - predictions["last_cu"])
        / predictions["last_cu"].replace(0, pd.NA) * 100
    )

    filter_a, filter_b, _ = st.columns([1.25, 1.25, 2.5])
    operators = sorted(predictions["operador_de_red"].dropna().astype(str).unique())
    with filter_a:
        operator = st.selectbox("Operador de red", operators)
    available_levels = sorted(
        predictions.loc[predictions["operador_de_red"].astype(str) == operator, "nivel"]
        .dropna().astype(str).unique()
    )
    with filter_b:
        level = st.selectbox("Nivel", available_levels)

    selected = predictions[
        (predictions["operador_de_red"].astype(str) == operator)
        & (predictions["nivel"].astype(str) == level)
    ].sort_values("target_period")
    if selected.empty:
        st.warning("No hay datos para la combinación seleccionada.")
        return
    current = selected.iloc[-1]
    variation = current["variacion_pct"]
    delta = f"{variation:+.2f}%" if pd.notna(variation) else None

    cols = st.columns(4)
    cols[0].metric("Último CU observado", f"${current['last_cu']:,.2f}" if pd.notna(current["last_cu"]) else "—")
    cols[1].metric("CU predicho", f"${current['predicted_cu']:,.2f}" if pd.notna(current["predicted_cu"]) else "—", delta=delta)
    cols[2].metric("Periodo objetivo", current["target_period"].strftime("%B %Y").capitalize() if pd.notna(current["target_period"]) else "—")
    cols[3].metric("Variación esperada", f"{variation:+.2f}%" if pd.notna(variation) else "—")

    history = build_history_date(history)
    series = history[
        (history["operador_de_red"].astype(str) == operator)
        & (history["nivel"].astype(str) == level)
    ]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series["fecha"], y=series["cu_total"], name="CU histórico",
        mode="lines", line=dict(color=BLUE, width=2.5),
        hovertemplate="%{x|%b %Y}<br><b>$%{y:,.2f}</b><extra></extra>",
    ))
    prediction_line = pd.DataFrame({
        "fecha": [current["last_observed_period"], current["target_period"]],
        "valor": [current["last_cu"], current["predicted_cu"]],
    })
    fig.add_trace(go.Scatter(
        x=prediction_line["fecha"], y=prediction_line["valor"], name="Predicción",
        mode="lines+markers", line=dict(color=AMBER, width=3, dash="dash"),
        marker=dict(size=10, symbol="diamond"),
        hovertemplate="%{x|%b %Y}<br><b>$%{y:,.2f}</b><extra></extra>",
    ))
    fig.update_layout(title=f"Evolución del CU · {operator} · {level}")
    fig.update_yaxes(title="CU total")
    st.plotly_chart(apply_chart_style(fig, 410), use_container_width=True)

    st.markdown("#### Todas las predicciones")
    table = predictions.rename(columns={
        "operador_de_red": "Operador de red", "nivel": "Nivel",
        "last_observed_period": "Último periodo observado", "last_cu": "Último CU",
        "target_period": "Periodo objetivo", "predicted_cu": "CU predicho",
        "variacion_pct": "Variación esperada (%)",
    })
    st.dataframe(
        table, use_container_width=True, hide_index=True,
        column_config={
            "Último periodo observado": st.column_config.DateColumn(format="MM/YYYY"),
            "Periodo objetivo": st.column_config.DateColumn(format="MM/YYYY"),
            "Último CU": st.column_config.NumberColumn(format="$ %.2f"),
            "CU predicho": st.column_config.NumberColumn(format="$ %.2f"),
            "Variación esperada (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


def inject_styles() -> None:
    st.markdown("""
        <style>
        .stApp { background: #F6F8FB; }
        [data-testid="stSidebar"] { background: #12243A; }
        [data-testid="stSidebar"] * { color: #F4F7FA !important; }
        .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1500px; }
        h1, h2, h3, h4 { color: #12243A; letter-spacing: -.025em; }
        .section-label { color: #00A6A6; font-size: .72rem; font-weight: 800; letter-spacing: .14em; margin-top: 1.8rem; }
        [data-testid="stMetric"] { background: white; border: 1px solid #E7ECF2; border-radius: 12px; padding: 18px 20px; box-shadow: 0 3px 12px rgba(18,36,58,.04); min-height: 118px; }
        [data-testid="stMetricLabel"] { color: #64748B; }
        [data-testid="stMetricValue"] { color: #12243A; font-weight: 700; font-size: 1.55rem; }
        [data-testid="stDataFrame"] { border: 1px solid #E7ECF2; border-radius: 10px; overflow: hidden; }
        hr { border-color: #E7ECF2; margin: 2.5rem 0; }
        </style>
    """, unsafe_allow_html=True)


def main() -> None:
    inject_styles()
    with st.sidebar:
        st.markdown("## ⚡ Energy Intelligence")
        st.caption("Control operativo y proyección tarifaria")
        st.markdown("---")
        st.caption("FUENTE")
        st.markdown("PostgreSQL · actualización en caché")
        if st.button("Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.title("Energy Tariff Intelligence")
    st.caption("Visión ejecutiva del pipeline y las proyecciones de costo unitario")

    try:
        runs = load_pipeline_runs()
        predictions = load_predictions()
        history = load_tariff_history()
    except SQLAlchemyError as exc:
        st.error(
            "No fue posible conectar con PostgreSQL o consultar las tablas requeridas. "
            "Verifica que el servicio esté activo y que DATABASE_URL sea correcta."
        )
        st.caption(f"Detalle técnico: {exc}")
        st.stop()
    except Exception as exc:
        st.error("Ocurrió un error inesperado al cargar los datos del dashboard.")
        st.caption(f"Detalle técnico: {exc}")
        st.stop()

    render_pipeline_monitoring(runs)
    st.divider()
    render_tariff_predictions(predictions, history)


if __name__ == "__main__":
    main()
