import streamlit as st
import subprocess
import sys
import os
import re
import time
from datetime import datetime
from pathlib import Path
import html

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

APP_DIR = Path(__file__).resolve().parent
ORQUESTADOR_PATH = APP_DIR / "orquestador.py"

AZUL = "#1f4e79"
AZUL_CLARO = "#2b7bbb"
AZUL_FONDO = "#f3f8ff"
AZUL_BORDE = "#d8e8f7"
TEXTO = "#1f2937"
TEXTO_SUAVE = "#64748b"
BLANCO = "#ffffff"


# =========================================================
# CONFIGURACIÓN DE PÁGINA
# =========================================================

st.set_page_config(
    page_title="FlashNews | Panel interno",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# CSS
# =========================================================

st.markdown(
    f"""
    <style>
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {BLANCO} !important;
        color: {TEXTO} !important;
    }}

    [data-testid="stHeader"] {{
        background-color: transparent !important;
    }}

    .block-container {{
        max-width: 1220px;
        padding-top: 1.4rem;
        padding-bottom: 3rem;
    }}

    h1, h2, h3, h4, h5, h6, p, label, span, li {{
        color: {TEXTO} !important;
    }}

    .hero {{
        background: linear-gradient(135deg, {AZUL}, {AZUL_CLARO});
        padding: 2.3rem 2.7rem;
        border-radius: 26px;
        margin-bottom: 1.4rem;
        box-shadow: 0 12px 34px rgba(31, 78, 121, 0.22);
    }}

    .hero-title {{
        color: white !important;
        font-size: 2.35rem;
        font-weight: 850;
        margin-bottom: 0.55rem;
    }}

    .hero-text {{
        color: white !important;
        font-size: 1.04rem;
        line-height: 1.65;
        max-width: 950px;
    }}

    .metric-card {{
        background-color: #ffffff;
        border: 1px solid {AZUL_BORDE};
        border-radius: 20px;
        padding: 1.1rem 1.2rem;
        box-shadow: 0 8px 24px rgba(31, 78, 121, 0.07);
        min-height: 112px;
    }}

    .metric-label {{
        color: {TEXTO_SUAVE} !important;
        font-weight: 800;
        font-size: 0.88rem;
        margin-bottom: 0.35rem;
    }}

    .metric-value {{
        color: {AZUL} !important;
        font-weight: 900;
        font-size: 2rem;
        line-height: 1.1;
    }}

    .metric-help {{
        color: {TEXTO_SUAVE} !important;
        font-size: 0.82rem;
        margin-top: 0.35rem;
    }}

    .stage-card {{
        background-color: #ffffff;
        border: 1px solid {AZUL_BORDE};
        border-radius: 18px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.75rem;
        box-shadow: 0 6px 18px rgba(31, 78, 121, 0.05);
    }}

    .stage-title {{
        font-weight: 850;
        color: {TEXTO} !important;
    }}

    .stage-desc {{
        color: {TEXTO_SUAVE} !important;
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }}

    .status-pill {{
        display: inline-block;
        padding: 0.28rem 0.65rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 850;
        margin-left: 0.45rem;
    }}

    .status-pending {{
        background-color: #f1f5f9;
        color: #64748b !important;
        border: 1px solid #e2e8f0;
    }}

    .status-running {{
        background-color: #fff7ed;
        color: #c2410c !important;
        border: 1px solid #fed7aa;
    }}

    .status-ok {{
        background-color: #ecfdf5;
        color: #15803d !important;
        border: 1px solid #bbf7d0;
    }}

    .status-stopped {{
        background-color: #f8fafc;
        color: #475569 !important;
        border: 1px solid #cbd5e1;
    }}

    .console {{
        background-color: #0f172a;
        color: #e5e7eb !important;
        border-radius: 18px;
        padding: 1rem 1.1rem;
        border: 1px solid #1e293b;
        min-height: 360px;
        max-height: 560px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-family: Consolas, Monaco, "Courier New", monospace;
        font-size: 0.86rem;
        line-height: 1.45;
        box-shadow: 0 10px 26px rgba(15, 23, 42, 0.16);
    }}

    .console * {{
        color: #e5e7eb !important;
    }}

    [data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {AZUL_BORDE} !important;
        border-radius: 22px !important;
        box-shadow: 0 8px 24px rgba(31, 78, 121, 0.07) !important;
        background-color: #ffffff !important;
    }}

    .stButton > button {{
        background-color: {AZUL} !important;
        color: white !important;
        border: 1px solid {AZUL} !important;
        border-radius: 13px !important;
        padding: 0.72rem 1rem !important;
        font-weight: 850 !important;
        box-shadow: 0 6px 16px rgba(31, 78, 121, 0.20);
    }}

    .stButton > button:hover {{
        background-color: {AZUL_CLARO} !important;
        border-color: {AZUL_CLARO} !important;
        color: white !important;
    }}

    [data-testid="stAlert"] {{
        border-radius: 15px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# ESTADO DE SESIÓN
# =========================================================

if "logs" not in st.session_state:
    st.session_state.logs = ""

if "ultima_ejecucion" not in st.session_state:
    st.session_state.ultima_ejecucion = None

if "ultimo_returncode" not in st.session_state:
    st.session_state.ultimo_returncode = None

if "duracion" not in st.session_state:
    st.session_state.duracion = None


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def limpiar_log_para_html(texto: str) -> str:
    return html.escape(texto).replace("\n", "<br>")


def extraer_ultimo_numero(patron: str, logs: str, default=0) -> int:
    matches = re.findall(patron, logs, flags=re.IGNORECASE)
    if not matches:
        return default

    try:
        return int(matches[-1])
    except Exception:
        return default


def calcular_metricas(logs: str) -> dict:
    fuentes = len(
        re.findall(
            r"Consultando fuente:|Consultando fuentes de:",
            logs,
            flags=re.IGNORECASE
        )
    )

    noticias_scrapeadas = extraer_ultimo_numero(
        r"Noticias scrapeadas en esta ejecución:\s*(\d+)",
        logs,
        default=0
    )

    if noticias_scrapeadas == 0:
        noticias_obtenidas = re.findall(
            r"Noticias obtenidas:\s*(\d+)",
            logs,
            flags=re.IGNORECASE
        )
        noticias_scrapeadas = sum(int(x) for x in noticias_obtenidas) if noticias_obtenidas else 0

    noticias_nuevas = extraer_ultimo_numero(
        r"Noticias realmente nuevas:\s*(\d+)",
        logs,
        default=0
    )

    if noticias_nuevas == 0:
        noticias_nuevas = extraer_ultimo_numero(
            r"Volcado masivo completado:\s*(\d+)\s*noticias",
            logs,
            default=0
        )

    usuarios = extraer_ultimo_numero(
        r"Total usuarios encontrados:\s*(\d+)",
        logs,
        default=0
    )

    if usuarios == 0:
        usuarios = len(
            re.findall(
                r"Agente investigando para:",
                logs,
                flags=re.IGNORECASE
            )
        )

    emails = len(
        re.findall(
            r"Éxito: Correo enviado",
            logs,
            flags=re.IGNORECASE
        )
    )

    historico = extraer_ultimo_numero(
        r"Total de noticias que quedarán guardadas en Sheets:\s*(\d+)",
        logs,
        default=0
    )

    return {
        "fuentes": fuentes,
        "noticias_scrapeadas": noticias_scrapeadas,
        "noticias_nuevas": noticias_nuevas,
        "usuarios": usuarios,
        "emails": emails,
        "historico": historico,
    }


def estado_etapa(logs: str, etapa: str, proceso_activo: bool, returncode):
    logs_lower = logs.lower()

    if etapa == "inicio":
        if "iniciando orquestador" in logs_lower:
            return "ok"
        return "running" if proceso_activo else "pending"

    if etapa == "scraping":
        if "dataframes unidos correctamente" in logs_lower:
            return "ok"
        if "volcado masivo completado" in logs_lower:
            return "ok"
        if "consultando fuente:" in logs_lower or "consultando fuentes de:" in logs_lower:
            return "running"
        return "pending"

    if etapa == "sheets":
        if "histórico actualizado correctamente" in logs_lower:
            return "ok"
        if "no hay noticias para guardar en google sheets" in logs_lower:
            return "ok"
        if "iniciando guardado de noticias en google sheets" in logs_lower:
            return "running"
        if "dataframes unidos correctamente" in logs_lower:
            return "running"
        return "pending"

    if etapa == "preparacion":
        if "usuarios cargados desde google sheets" in logs_lower:
            return "ok"
        if "preparando noticias para el agente" in logs_lower:
            return "running"
        if "volcado masivo completado" in logs_lower:
            return "running"
        return "pending"

    if etapa == "agente":
        if "proceso finalizado" in logs_lower:
            return "ok"
        if "agente investigando para:" in logs_lower:
            return "running"
        if "usuarios cargados desde google sheets" in logs_lower:
            return "running"
        return "pending"

    if etapa == "fin":
        if returncode == 0 and "proceso finalizado" in logs_lower:
            return "ok"
        if returncode not in (None, 0):
            return "stopped"
        return "running" if proceso_activo else "pending"

    return "pending"


def pintar_estado(nombre, descripcion, estado):
    labels = {
        "pending": "Pendiente",
        "running": "En ejecución",
        "ok": "Completado",
        "stopped": "Finalizado"
    }

    iconos = {
        "pending": "○",
        "running": "●",
        "ok": "✓",
        "stopped": "■"
    }

    st.markdown(
        f"""
        <div class="stage-card">
            <div class="stage-title">
                {iconos[estado]} {nombre}
                <span class="status-pill status-{estado}">{labels[estado]}</span>
            </div>
            <div class="stage-desc">{descripcion}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def pintar_metric_card(label, value, help_text):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def pintar_paneles(logs, proceso_activo, returncode, stages_placeholder, metrics_placeholder):
    metricas = calcular_metricas(logs)

    with metrics_placeholder.container():
        col1, col2, col3, col4, col5 = st.columns(5, gap="medium")

        with col1:
            pintar_metric_card(
                "Fuentes",
                metricas["fuentes"],
                "Periódicos consultados"
            )

        with col2:
            pintar_metric_card(
                "Recopiladas",
                metricas["noticias_scrapeadas"],
                "Noticias obtenidas"
            )

        with col3:
            pintar_metric_card(
                "Nuevas",
                metricas["noticias_nuevas"],
                "Noticias para analizar"
            )

        with col4:
            pintar_metric_card(
                "Usuarios",
                metricas["usuarios"],
                "Perfiles cargados"
            )

        with col5:
            pintar_metric_card(
                "Emails",
                metricas["emails"],
                "Boletines enviados"
            )

    with stages_placeholder.container():
        pintar_estado(
            "Inicio del proceso",
            "Se lanza el orquestador central y se cargan las variables necesarias.",
            estado_etapa(logs, "inicio", proceso_activo, returncode)
        )

        pintar_estado(
            "Recopilación de noticias",
            "Se ejecutan las fuentes configuradas y se obtienen los artículos.",
            estado_etapa(logs, "scraping", proceso_activo, returncode)
        )

        pintar_estado(
            "Actualización del histórico",
            "Se normalizan las noticias, se eliminan duplicados y se actualiza Google Sheets.",
            estado_etapa(logs, "sheets", proceso_activo, returncode)
        )

        pintar_estado(
            "Preparación del agente",
            "Se preparan las noticias y se cargan los usuarios con sus preferencias.",
            estado_etapa(logs, "preparacion", proceso_activo, returncode)
        )

        pintar_estado(
            "Curación personalizada",
            "El agente revisa titulares, consulta textos completos y genera el boletín personalizado.",
            estado_etapa(logs, "agente", proceso_activo, returncode)
        )

        pintar_estado(
            "Finalización",
            "Se cierra la ejecución del flujo interno.",
            estado_etapa(logs, "fin", proceso_activo, returncode)
        )


def calcular_progreso(logs: str) -> int:
    logs_lower = logs.lower()
    progreso = 5

    if "iniciando orquestador" in logs_lower:
        progreso = max(progreso, 10)

    if "consultando fuente:" in logs_lower or "consultando fuentes de:" in logs_lower:
        progreso = max(progreso, 25)

    if "dataframes unidos correctamente" in logs_lower:
        progreso = max(progreso, 40)

    if "iniciando guardado de noticias en google sheets" in logs_lower:
        progreso = max(progreso, 52)

    if "histórico actualizado correctamente" in logs_lower:
        progreso = max(progreso, 65)

    if "preparando noticias para el agente" in logs_lower:
        progreso = max(progreso, 72)

    if "usuarios cargados desde google sheets" in logs_lower:
        progreso = max(progreso, 80)

    if "agente investigando para:" in logs_lower:
        progreso = max(progreso, 88)

    if "proceso finalizado" in logs_lower:
        progreso = 100

    return progreso


def ejecutar_orquestador(log_placeholder, progress_placeholder, stages_placeholder, metrics_placeholder):
    if not ORQUESTADOR_PATH.exists():
        st.error(f"No encuentro el archivo: {ORQUESTADOR_PATH}")
        return

    inicio = time.time()
    st.session_state.logs = ""
    st.session_state.ultimo_returncode = None
    st.session_state.duracion = None

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    comando = [
        sys.executable,
        "-u",
        str(ORQUESTADOR_PATH)
    ]

    proceso = subprocess.Popen(
        comando,
        cwd=str(APP_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        bufsize=1
    )

    while True:
        linea = proceso.stdout.readline()

        if linea:
            st.session_state.logs += linea

            logs = st.session_state.logs
            progreso = calcular_progreso(logs)

            progress_placeholder.progress(
                progreso,
                text=f"Ejecución en curso... {progreso}%"
            )

            pintar_paneles(
                logs=logs,
                proceso_activo=True,
                returncode=None,
                stages_placeholder=stages_placeholder,
                metrics_placeholder=metrics_placeholder
            )

            log_placeholder.markdown(
                f"<div class='console'>{limpiar_log_para_html(logs)}</div>",
                unsafe_allow_html=True
            )

        if linea == "" and proceso.poll() is not None:
            break

    returncode = proceso.poll()
    fin = time.time()

    st.session_state.ultimo_returncode = returncode
    st.session_state.ultima_ejecucion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.duracion = round(fin - inicio, 1)

    progreso_final = 100 if returncode == 0 else calcular_progreso(st.session_state.logs)

    if returncode == 0:
        progress_placeholder.progress(100, text="Ejecución completada")
    else:
        progress_placeholder.progress(progreso_final, text="Ejecución finalizada")

    pintar_paneles(
        logs=st.session_state.logs,
        proceso_activo=False,
        returncode=returncode,
        stages_placeholder=stages_placeholder,
        metrics_placeholder=metrics_placeholder
    )

    log_placeholder.markdown(
        f"<div class='console'>{limpiar_log_para_html(st.session_state.logs)}</div>",
        unsafe_allow_html=True
    )


# =========================================================
# CABECERA
# =========================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-title">📰 FlashNews · Panel interno</div>
        <div class="hero-text">
            Monitorización del flujo interno de recopilación, actualización del histórico,
            análisis personalizado y distribución de noticias.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# BLOQUE SUPERIOR
# =========================================================

col_run, col_info = st.columns([1.25, 0.85], gap="large")

with col_run:
    with st.container(border=True):
        st.subheader("🚀 Ejecutar orquestador")
        st.write(
            "Pulsa el botón para lanzar el flujo completo. "
            "La salida del proceso aparecerá en tiempo real en la consola inferior."
        )

        if ORQUESTADOR_PATH.exists():
            st.success(f"Archivo detectado: {ORQUESTADOR_PATH.name}")
        else:
            st.error("No se ha encontrado orquestador.py en esta carpeta.")

        ejecutar = st.button(
            "▶️ Run orquestador",
            use_container_width=True,
            type="primary"
        )

with col_info:
    with st.container(border=True):
        st.subheader("📌 Última ejecución")

        if st.session_state.ultima_ejecucion:
            st.write(f"**Fecha:** {st.session_state.ultima_ejecucion}")
            st.write(f"**Duración:** {st.session_state.duracion} segundos")

            if st.session_state.ultimo_returncode == 0:
                st.success("Última ejecución completada correctamente.")
            else:
                st.info("Última ejecución finalizada. Revisa la consola para ver el detalle.")
        else:
            st.info("Todavía no se ha ejecutado el orquestador desde este panel.")

        st.write("")
        st.caption("Este panel ejecuta el proceso real definido en el archivo del orquestador.")


# =========================================================
# MÉTRICAS Y ESTADOS
# =========================================================

st.write("")

metrics_placeholder = st.empty()
stages_inicial_placeholder = st.empty()

pintar_paneles(
    logs=st.session_state.logs,
    proceso_activo=False,
    returncode=st.session_state.ultimo_returncode,
    stages_placeholder=stages_inicial_placeholder,
    metrics_placeholder=metrics_placeholder
)

st.write("")

col_etapas, col_logs = st.columns([0.85, 1.25], gap="large")

with col_etapas:
    st.subheader("🧭 Flujo de ejecución")
    stages_placeholder = st.empty()

with col_logs:
    st.subheader("🖥️ Consola")
    progress_placeholder = st.empty()
    log_placeholder = st.empty()

    if st.session_state.logs:
        log_placeholder.markdown(
            f"<div class='console'>{limpiar_log_para_html(st.session_state.logs)}</div>",
            unsafe_allow_html=True
        )
    else:
        log_placeholder.markdown(
            "<div class='console'>Esperando ejecución...</div>",
            unsafe_allow_html=True
        )

pintar_paneles(
    logs=st.session_state.logs,
    proceso_activo=False,
    returncode=st.session_state.ultimo_returncode,
    stages_placeholder=stages_placeholder,
    metrics_placeholder=metrics_placeholder
)


# =========================================================
# EJECUCIÓN
# =========================================================

if ejecutar:
    with st.spinner("Ejecutando orquestador..."):
        ejecutar_orquestador(
            log_placeholder=log_placeholder,
            progress_placeholder=progress_placeholder,
            stages_placeholder=stages_placeholder,
            metrics_placeholder=metrics_placeholder
        )

    if st.session_state.ultimo_returncode == 0:
        st.success("Orquestador ejecutado correctamente.")
    else:
        st.info("Ejecución finalizada. Revisa la consola para ver el detalle.")