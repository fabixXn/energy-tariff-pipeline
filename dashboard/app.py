import os
from pathlib import Path

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
NAVY = "#12372A"
TEAL = "#16A36A"
BLUE = "#2F7D65"
AMBER = "#D8A31A"
GRID = "rgba(18,55,42,.11)"
ARCHITECTURE_IMAGE = Path(__file__).parent / "assets" / "pipeline_architecture.png"


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
               target_period, predicted_cu, model_name, validation_mae,
               baseline_mae, generated_at
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
        template="plotly_white",
        height=height,
        margin=dict(l=16, r=16, t=42, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Arial, sans-serif", color=NAVY, size=13),
        title=dict(font=dict(color=NAVY, size=18)),
        hoverlabel=dict(bgcolor="white", font_color=NAVY),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    axis_font = dict(color=NAVY, size=12)
    axis_title_font = dict(color=NAVY, size=13)
    fig.update_xaxes(
        showgrid=False, linecolor=GRID, tickfont=axis_font,
        title_font=axis_title_font, color=NAVY,
    )
    fig.update_yaxes(
        gridcolor=GRID, zeroline=False, tickfont=axis_font,
        title_font=axis_title_font, color=NAVY,
    )
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

    model_name = str(predictions["model_name"].dropna().iloc[0])
    validation_mae = pd.to_numeric(predictions["validation_mae"], errors="coerce").median()
    baseline_mae = pd.to_numeric(predictions["baseline_mae"], errors="coerce").median()
    improvement = (
        (baseline_mae - validation_mae) / baseline_mae * 100
        if pd.notna(baseline_mae) and baseline_mae else 0
    )
    generated = pd.to_datetime(predictions["generated_at"], errors="coerce", utc=True).max()
    model_cols = st.columns(4)
    model_cols[0].metric("Modelo publicado", model_name)
    model_cols[1].metric("MAE de validación", f"{validation_mae:,.2f}")
    model_cols[2].metric("MAE baseline", f"{baseline_mae:,.2f}")
    model_cols[3].metric(
        "Mejora vs. baseline", f"{improvement:+.1f}%",
        help="Si ningún modelo supera el baseline temporal, se publica el baseline.",
    )
    if pd.notna(generated):
        st.caption(f"Predicciones generadas: {generated.strftime('%d/%m/%Y %H:%M UTC')}")

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
    st.download_button(
        "Descargar predicciones (CSV)",
        predictions.to_csv(index=False).encode("utf-8"),
        file_name="tariff_predictions.csv",
        mime="text/csv",
    )


def render_how_it_works() -> None:
    st.markdown('<div class="section-label">ARQUITECTURA</div>', unsafe_allow_html=True)
    st.subheader("Cómo funciona la solución")
    st.write(
        "El proyecto convierte una fuente pública de tarifas en datos confiables, "
        "predicciones verificadas y métricas operativas listas para consultar."
    )

    st.image(
        str(ARCHITECTURE_IMAGE),
        caption="Arquitectura de extremo a extremo del pipeline de tarifas",
        use_container_width=True,
    )

    st.markdown("### Recorrido de los datos")
    left, right = st.columns(2)
    with left:
        st.markdown("""
        **1. Fuente y extracción**

        `extract.py` consulta Datos Abiertos Colombia mediante HTTP y convierte la
        respuesta JSON en un DataFrame. Prefect aplica reintentos ante fallos de red.

        **2. Transformación y calidad**

        `transform.py` normaliza operadores, niveles, meses y columnas económicas.
        `validate.py` bloquea conjuntos vacíos, nulos, negativos, años inválidos y
        periodos duplicados.

        **3. Persistencia**

        Los registros validados reemplazan la fotografía de `energy_tariffs` en
        PostgreSQL, que actúa como fuente única para el dashboard.
        """)
    with right:
        st.markdown("""
        **4. Preparación temporal**

        `prepare_model.py` crea fechas y rezagos de uno, dos y tres meses sin confundir
        observaciones separadas por huecos temporales.

        **5. Selección y predicción**

        El sistema compara Ridge, Extra Trees, Random Forest y Gradient Boosting contra
        un baseline. Publica automáticamente la alternativa con menor MAE temporal.

        **6. Observabilidad y consumo**

        Prefect registra tareas y reintentos; `pipeline_runs` conserva estado, duración
        y volumen. Streamlit presenta operación, histórico y predicciones.
        """)

    st.markdown("### Qué guarda PostgreSQL")
    table_cols = st.columns(3)
    table_cols[0].success(
        "**energy_tariffs**\n\nHistórico limpio de tarifas y componentes de costo."
    )
    table_cols[1].success(
        "**tariff_predictions**\n\nÚltima observación, proyección, modelo y métricas."
    )
    table_cols[2].success(
        "**pipeline_runs**\n\nEstado, tiempos, volumen y detalle de errores."
    )

    st.markdown("### Decisión importante del modelo")
    st.info(
        "Un algoritmo complejo no se publica solo por ser más sofisticado. Si no "
        "supera al baseline en datos futuros, el pipeline conserva la alternativa "
        "más precisa y fácil de explicar."
    )


def inject_styles() -> None:
    st.markdown("""
        <style>
        :root {
            --forest: #0B2E25;
            --forest-soft: #123F32;
            --emerald: #16A36A;
            --mint: #EAF7F0;
            --lime: #B7DC5A;
            --ink: #12372A;
        }
        .stApp {
            background:
                radial-gradient(circle at 86% 4%, rgba(183,220,90,.18), transparent 26rem),
                linear-gradient(145deg, #F4FBF7 0%, #E8F5EE 100%);
        }
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] {
            color: #12372A !important;
        }
        [data-testid="stMain"] p,
        [data-testid="stMain"] span,
        [data-testid="stMain"] label,
        [data-testid="stMain"] li {
            color: #294F41;
        }
        [data-testid="stHeader"] { background: rgba(244,251,247,.82); }
        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 15% 8%, rgba(183,220,90,.13), transparent 15rem),
                linear-gradient(180deg, #123D31 0%, #09251E 100%);
            border-right: 1px solid rgba(183,220,90,.18);
        }
        [data-testid="stSidebar"] * { color: #F3FBF6 !important; }
        [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12); }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            border-radius: 9px;
            padding: .36rem .55rem;
            margin-bottom: .15rem;
            transition: background .2s ease, transform .2s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(255,255,255,.08);
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            line-height: 1.45;
        }
        [data-testid="stSidebar"] .stButton button {
            background: linear-gradient(135deg, #20B978, #13895A) !important;
            border: 1px solid rgba(255,255,255,.18) !important;
            color: white !important;
            font-weight: 700;
            min-height: 3rem;
            box-shadow: 0 8px 20px rgba(0,0,0,.18);
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background: linear-gradient(135deg, #2CC986, #179664) !important;
            color: white !important;
            border-color: #B7DC5A !important;
        }
        .block-container { padding-top: 2.5rem; padding-bottom: 3rem; max-width: 1480px; }
        h1, h2, h3, h4 { color: #12372A; letter-spacing: -.03em; }
        h1 { font-weight: 800 !important; }
        .section-label { color: #13895A; font-size: .72rem; font-weight: 800; letter-spacing: .16em; margin-top: 1.8rem; }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(255,255,255,.96), rgba(239,250,244,.96));
            border: 1px solid rgba(22,163,106,.18);
            border-top: 4px solid #16A36A;
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 10px 28px rgba(18,55,42,.08);
            min-height: 122px;
        }
        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] * { color: #527065 !important; font-weight: 600; }
        [data-testid="stMetricValue"],
        [data-testid="stMetricValue"] * { color: #0B2E25 !important; font-weight: 800; font-size: 1.6rem; }
        [data-testid="stMetricDelta"],
        [data-testid="stMetricDelta"] * { color: #13895A !important; }
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(22,163,106,.2);
            border-radius: 14px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(18,55,42,.06);
        }
        [data-testid="stPlotlyChart"] {
            background: rgba(255,255,255,.72);
            border: 1px solid rgba(22,163,106,.15);
            border-radius: 16px;
            padding: .75rem;
            box-shadow: 0 10px 28px rgba(18,55,42,.06);
        }
        [data-testid="stAlert"] { border-radius: 12px; }
        hr { border-color: rgba(22,163,106,.16); margin: 2.5rem 0; }
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
        page = st.radio(
            "NAVEGACIÓN",
            ["Resumen", "Operación", "Predicciones", "Cómo funciona"],
            label_visibility="visible",
        )
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

    if page == "Resumen":
        latest = runs.sort_values("started_at", ascending=False).iloc[0]
        predicted = pd.to_numeric(predictions["predicted_cu"], errors="coerce")
        current = pd.to_numeric(predictions["last_cu"], errors="coerce")
        change = (predicted - current) / current.replace(0, pd.NA) * 100
        summary = st.columns(4)
        summary[0].metric("Estado del pipeline", str(latest["status"]).upper())
        summary[1].metric("Series proyectadas", f"{len(predictions):,}")
        summary[2].metric("CU promedio predicho", f"${predicted.mean():,.2f}")
        summary[3].metric("Variación promedio", f"{change.mean():+.2f}%")
        chart_data = predictions.copy()
        chart_data["serie"] = (
            chart_data["operador_de_red"].astype(str)
            + " · " + chart_data["nivel"].astype(str)
        )
        chart_data["predicted_cu"] = predicted
        chart_data = chart_data.sort_values("predicted_cu")
        overview = go.Figure(go.Bar(
            x=chart_data["predicted_cu"], y=chart_data["serie"],
            orientation="h", marker_color=TEAL,
            hovertemplate="%{y}<br><b>$%{x:,.2f}</b><extra></extra>",
        ))
        overview.update_layout(title="CU proyectado por operador y nivel")
        overview.update_xaxes(title="CU proyectado")
        st.plotly_chart(apply_chart_style(overview, 390), use_container_width=True)
        selected_model = str(predictions["model_name"].dropna().iloc[0])
        if selected_model == "Baseline persistente":
            st.info(
                "El baseline obtuvo el menor error temporal. Por eso la proyección "
                "mantiene el último CU observado y la variación esperada es 0 %."
            )
        else:
            st.success(
                f"{selected_model} superó el baseline y fue publicado automáticamente."
            )
    elif page == "Operación":
        render_pipeline_monitoring(runs)
    elif page == "Predicciones":
        render_tariff_predictions(predictions, history)
    else:
        render_how_it_works()


if __name__ == "__main__":
    main()
