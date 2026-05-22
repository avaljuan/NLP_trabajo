import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
import json
import gspread
import requests
from dotenv import load_dotenv
import html

load_dotenv(override=True)

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================

TOPICS_DISPONIBLES = [
    "Economía",
    "Medioambiente",
    "Política",
    "Tecnología",
    "Ciencia",
    "Salud",
    "Deportes",
    "Cultura",
    "Educación",
    "Internacional",
    "Sociedad",
    "Opinión"
]

COLUMNAS_USUARIOS = [
    "nombre",
    "email",
    "password_hash",
    "topics",
    "topics_personalizados",
    "recibir_email",
    "fecha_actualizacion"
]

AZUL = "#1f4e79"
AZUL_CLARO = "#2b7bbb"
AZUL_FONDO = "#f3f8ff"
AZUL_BORDE = "#d8e8f7"
TEXTO = "#1f2937"
BLANCO = "#ffffff"


# =========================================================
# CONFIGURACIÓN DE PÁGINA
# =========================================================

st.set_page_config(
    page_title="Preferencias de noticias",
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
        max-width: 1180px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }}

    h1, h2, h3, h4, h5, h6, p, label, span, li {{
        color: {TEXTO} !important;
    }}

    .hero {{
        background: linear-gradient(135deg, {AZUL}, {AZUL_CLARO});
        padding: 2.3rem 2.7rem;
        border-radius: 26px;
        margin-bottom: 1.6rem;
        box-shadow: 0 12px 34px rgba(31, 78, 121, 0.22);
    }}

    .hero-title {{
        color: white !important;
        font-size: 2.4rem;
        font-weight: 850;
        margin-bottom: 0.8rem;
    }}

    .hero-text {{
        color: white !important;
        font-size: 1.08rem;
        line-height: 1.7;
        max-width: 900px;
    }}

    .info-card {{
        background-color: {AZUL_FONDO};
        border: 1px solid {AZUL_BORDE};
        border-radius: 18px;
        padding: 1rem 1.2rem;
        margin-bottom: 1.2rem;
        color: {AZUL} !important;
        font-weight: 700;
    }}

    .topic-badge {{
        display: inline-block;
        background-color: {AZUL_FONDO};
        color: {AZUL} !important;
        border: 1px solid {AZUL_BORDE};
        border-radius: 999px;
        padding: 0.45rem 0.8rem;
        margin: 0.25rem 0.25rem 0.25rem 0;
        font-weight: 700;
        font-size: 0.92rem;
    }}

    .topic-badge-custom {{
        display: inline-block;
        background-color: #eef6ff;
        color: #245f99 !important;
        border: 1px dashed #8bb8e8;
        border-radius: 999px;
        padding: 0.45rem 0.8rem;
        margin: 0.25rem 0.25rem 0.25rem 0;
        font-weight: 700;
        font-size: 0.92rem;
    }}

    .chat-user {{
        background-color: {AZUL};
        color: white !important;
        padding: 0.9rem 1rem;
        border-radius: 16px 16px 4px 16px;
        margin: 0.6rem 0 0.6rem auto;
        max-width: 78%;
        box-shadow: 0 5px 14px rgba(31, 78, 121, 0.16);
    }}

    .chat-user * {{
        color: white !important;
    }}

    .chat-note {{
        background-color: #ffffff;
        border-left: 4px solid {AZUL};
        padding: 0.7rem 0.9rem;
        margin: 0.8rem 0 1.2rem 0;
        color: #64748b !important;
        font-size: 0.95rem;
    }}

    [data-testid="stForm"] {{
        background-color: #ffffff !important;
        border: 1px solid {AZUL_BORDE} !important;
        border-radius: 22px !important;
        padding: 1.5rem !important;
        box-shadow: 0 8px 24px rgba(31, 78, 121, 0.07) !important;
    }}

    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {{
        background-color: #ffffff !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 13px !important;
        box-shadow: none !important;
        outline: none !important;
    }}

    div[data-baseweb="input"] > div:focus-within,
    div[data-baseweb="textarea"] > div:focus-within {{
        border: 2px solid {AZUL_CLARO} !important;
        box-shadow: 0 0 0 3px rgba(43, 123, 187, 0.12) !important;
        outline: none !important;
    }}

    input,
    textarea {{
        background-color: #ffffff !important;
        color: {TEXTO} !important;
        -webkit-text-fill-color: {TEXTO} !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }}

    input::placeholder,
    textarea::placeholder {{
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
        opacity: 1 !important;
    }}

    div[data-baseweb="input"] button,
    div[data-baseweb="input"] button:hover,
    div[data-baseweb="input"] button:focus,
    div[data-baseweb="input"] button:active {{
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }}

    .stButton > button,
    .stFormSubmitButton > button {{
        background-color: {AZUL} !important;
        color: white !important;
        border: 1px solid {AZUL} !important;
        border-radius: 13px !important;
        padding: 0.7rem 1rem !important;
        font-weight: 800 !important;
        box-shadow: 0 6px 16px rgba(31, 78, 121, 0.20);
    }}

    .stButton > button:hover,
    .stFormSubmitButton > button:hover {{
        background-color: {AZUL_CLARO} !important;
        border-color: {AZUL_CLARO} !important;
        color: white !important;
    }}

    button[data-baseweb="tab"] {{
        color: #64748b !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
    }}

    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {AZUL} !important;
    }}

    [data-baseweb="tab-highlight"] {{
        background-color: {AZUL} !important;
    }}

    [data-baseweb="tab-border"] {{
        background-color: #e5eef7 !important;
    }}

    [data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {AZUL_BORDE} !important;
        border-radius: 22px !important;
        box-shadow: 0 8px 24px rgba(31, 78, 121, 0.07) !important;
        background-color: #ffffff !important;
    }}

    [data-testid="stAlert"] {{
        border-radius: 15px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# FUNCIONES GOOGLE SHEETS
# =========================================================

def conectar_google_sheets():
    """
    Conecta con Google Sheets usando las credenciales del .env.
    Necesita GOOGLE_CREDENTIALS_JSON.
    """
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

    if not creds_json:
        raise ValueError("No se ha encontrado GOOGLE_CREDENTIALS_JSON en el archivo .env.")

    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)

    return gc


def obtener_hoja_usuarios():
    """
    Obtiene la hoja de usuarios desde Google Sheets.
    Usa ID_SPREADSHEET del .env.
    """
    spreadsheet_id = os.getenv("ID_SPREADSHEET")

    if not spreadsheet_id:
        raise ValueError("No se ha encontrado ID_SPREADSHEET en el archivo .env.")

    gc = conectar_google_sheets()
    spreadsheet = gc.open_by_key(spreadsheet_id)

    hoja = spreadsheet.sheet1

    return hoja


def inicializar_hoja_usuarios_si_vacia(hoja):
    """
    Si la hoja está vacía, crea la cabecera.
    """
    valores = hoja.get_all_values()

    if not valores:
        hoja.update("A1:G1", [COLUMNAS_USUARIOS])
        return

    cabecera = valores[0]

    if cabecera != COLUMNAS_USUARIOS:
        hoja.clear()
        hoja.update("A1:G1", [COLUMNAS_USUARIOS])


def cargar_usuarios():
    """
    Carga usuarios desde Google Sheets.
    """
    hoja = obtener_hoja_usuarios()
    inicializar_hoja_usuarios_si_vacia(hoja)

    registros = hoja.get_all_records()

    df = pd.DataFrame(registros, dtype=str)

    if df.empty:
        df = pd.DataFrame(columns=COLUMNAS_USUARIOS)

    for col in COLUMNAS_USUARIOS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNAS_USUARIOS]
    df = df.fillna("")
    df = df.astype(str)

    return df


def guardar_usuarios(df):
    """
    Guarda el DataFrame completo de usuarios en Google Sheets.
    """
    hoja = obtener_hoja_usuarios()

    df = df.copy()
    df = df.astype(str).fillna("")

    for col in COLUMNAS_USUARIOS:
        if col not in df.columns:
            df[col] = ""

    df = df[COLUMNAS_USUARIOS]

    datos = [COLUMNAS_USUARIOS] + df.values.tolist()

    hoja.clear()
    hoja.update("A1", datos)


# =========================================================
# FUNCIONES AUXILIARES
# =========================================================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def usuario_existe(df, email):
    if df.empty:
        return False

    return email in df["email"].values


def verificar_password(df, email, password):
    password_hash = hash_password(password)
    usuario = df[df["email"] == email]

    if usuario.empty:
        return False

    password_guardada = usuario.iloc[0]["password_hash"]

    return password_hash == password_guardada


def obtener_usuario(df, email):
    usuario = df[df["email"] == email]

    if usuario.empty:
        return None

    return usuario.iloc[0]


def convertir_texto_a_lista(texto):
    if not isinstance(texto, str) or not texto.strip():
        return []

    return [
        topic.strip()
        for topic in texto.split(",")
        if topic.strip()
    ]


def convertir_lista_a_texto(lista):
    if not lista:
        return ""

    return ", ".join(lista)


def render_badges(topics, tipo="normal"):
    if not topics:
        st.write("No hay topics seleccionados.")
        return

    clase = "topic-badge" if tipo == "normal" else "topic-badge-custom"

    html_topics = ""

    for topic in topics:
        topic_seguro = html.escape(str(topic))
        html_topics += f"<span class='{clase}'>{topic_seguro}</span>"

    st.markdown(html_topics, unsafe_allow_html=True)


def guardar_o_actualizar_usuario(
    df,
    nombre,
    email,
    password,
    topics,
    topics_personalizados,
    recibir_email=True
):
    df = df.astype(str).fillna("")

    password_hash = hash_password(password)

    topics_str = convertir_lista_a_texto(topics)
    topics_personalizados_str = convertir_lista_a_texto(topics_personalizados)

    fecha_actualizacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    nueva_fila = {
        "nombre": str(nombre),
        "email": str(email),
        "password_hash": str(password_hash),
        "topics": str(topics_str),
        "topics_personalizados": str(topics_personalizados_str),
        "recibir_email": str(recibir_email),
        "fecha_actualizacion": str(fecha_actualizacion)
    }

    if usuario_existe(df, email):
        for columna, valor in nueva_fila.items():
            df.loc[df["email"] == email, columna] = valor
    else:
        df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)

    guardar_usuarios(df)

    return df


# =========================================================
# FUNCIONES DEL CHAT
# =========================================================

@st.cache_data(ttl=300)
def cargar_noticias_historicas():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    spreadsheet_id = os.getenv("ID_SPREADSHEET_CHAT")

    if not creds_json:
        raise ValueError("No se ha encontrado GOOGLE_CREDENTIALS_JSON en el archivo .env.")

    if not spreadsheet_id:
        raise ValueError("No se ha encontrado ID_SPREADSHEET_CHAT en el archivo .env.")

    creds_dict = json.loads(creds_json)
    gc = gspread.service_account_from_dict(creds_dict)
    hoja = gc.open_by_key(spreadsheet_id).sheet1

    df = pd.DataFrame(hoja.get_all_records(), dtype=str)
    df = df.fillna("")

    return df


def preparar_contexto_noticias(df_noticias, max_noticias=80):
    if df_noticias.empty:
        return "No hay noticias disponibles en el histórico."

    columnas_necesarias = ["fecha", "titulo", "resumen"]

    for col in columnas_necesarias:
        if col not in df_noticias.columns:
            df_noticias[col] = ""

    df_contexto = df_noticias.tail(max_noticias)

    contexto = "\n".join([
        f"- Fecha: {fila['fecha']} | Título: {fila['titulo']} | Resumen: {fila['resumen']}"
        for _, fila in df_contexto.iterrows()
    ])

    return contexto


def llamar_llama(mensajes):
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError("No se ha encontrado OPENROUTER_API_KEY en el archivo .env.")

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "meta-llama/llama-3.3-70b-instruct",
        "messages": mensajes,
        "temperature": 0.2
    }

    response = requests.post(url, headers=headers, json=data, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(f"Error en OpenRouter: {response.status_code} - {response.text}")

    respuesta_json = response.json()

    return respuesta_json["choices"][0]["message"]["content"]


def pintar_mensaje_chat(role, content):
    if role == "user":
        contenido_seguro = html.escape(str(content)).replace("\n", "<br>")

        st.markdown(
            f"""
            <div class="chat-user">
                <strong>Tú</strong><br>
                {contenido_seguro}
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        with st.container(border=True):
            st.markdown("**Asistente**")
            st.markdown(content)


# =========================================================
# ESTADO DE SESIÓN
# =========================================================

if "logueado" not in st.session_state:
    st.session_state.logueado = False

if "email_usuario" not in st.session_state:
    st.session_state.email_usuario = None

if "nombre_usuario" not in st.session_state:
    st.session_state.nombre_usuario = None

if "password_usuario" not in st.session_state:
    st.session_state.password_usuario = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# =========================================================
# CABECERA
# =========================================================

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-title">⚡FlashNews </div>
        <div class="hero-text">
            Configura tus intereses informativos, consulta tu perfil y conversa con un asistente
            basado en el histórico de noticias recopiladas.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# CARGA DE USUARIOS DESDE GOOGLE SHEETS
# =========================================================

try:
    df_usuarios = cargar_usuarios()
except Exception as e:
    st.error("No se ha podido cargar la hoja de usuarios desde Google Sheets.")
    st.exception(e)
    st.stop()


# =========================================================
# LOGIN / REGISTRO
# =========================================================

if not st.session_state.logueado:

    col_login, col_info = st.columns([1.35, 0.75], gap="large")

    with col_login:
        with st.container(border=True):
            st.subheader("🔐 Inicio de sesión o registro")
            st.write(
                "Introduce tu nombre, email y contraseña. Si el email ya existe, se usará "
                "como inicio de sesión. Si no existe, se creará un nuevo perfil."
            )

            with st.form("form_login"):
                nombre = st.text_input("Nombre", placeholder="Ejemplo: Iyán")
                email = st.text_input("Email", placeholder="ejemplo@email.com")
                password = st.text_input("Contraseña", type="password")

                boton_login = st.form_submit_button(
                    "Entrar / Crear perfil",
                    use_container_width=True
                )

        if boton_login:
            if not nombre or not email or not password:
                st.error("Por favor, completa nombre, email y contraseña.")

            else:
                email = email.strip().lower()
                nombre = nombre.strip()

                if usuario_existe(df_usuarios, email):
                    if verificar_password(df_usuarios, email, password):
                        usuario = obtener_usuario(df_usuarios, email)

                        st.session_state.logueado = True
                        st.session_state.email_usuario = email
                        st.session_state.nombre_usuario = usuario["nombre"]
                        st.session_state.password_usuario = password

                        st.success("Inicio de sesión correcto.")
                        st.rerun()
                    else:
                        st.error("La contraseña no es correcta.")

                else:
                    st.session_state.logueado = True
                    st.session_state.email_usuario = email
                    st.session_state.nombre_usuario = nombre
                    st.session_state.password_usuario = password

                    st.success("Nuevo perfil iniciado. Ahora puedes configurar tus preferencias.")
                    st.rerun()

    with col_info:
        with st.container(border=True):
            st.subheader("✨ ¿Qué puedes hacer aquí?")
            st.write("✅ Crear un perfil de preferencias.")
            st.write("✅ Elegir temas de interés.")
            st.write("✅ Añadir topics personalizados.")
            st.write("✅ Consultar noticias recopiladas.")
            st.write("✅ Chatear con memoria durante la sesión.")


# =========================================================
# APP PRINCIPAL
# =========================================================

if st.session_state.logueado:

    tab_preferencias, tab_perfil, tab_chat = st.tabs(
        ["⚙️ Preferencias", "👤 Mi perfil", "💬 Chat de noticias"]
    )

    email_actual = st.session_state.email_usuario
    usuario_actual = obtener_usuario(df_usuarios, email_actual)

    if usuario_actual is not None:
        nombre_actual = usuario_actual["nombre"]
        topics_previos = convertir_texto_a_lista(usuario_actual["topics"])
        personalizados_previos = usuario_actual["topics_personalizados"]
        recibir_email_previo = str(usuario_actual["recibir_email"]).lower() == "true"
    else:
        nombre_actual = st.session_state.nombre_usuario
        topics_previos = []
        personalizados_previos = ""
        recibir_email_previo = True

    password_actual = st.session_state.password_usuario

    # =====================================================
    # TAB PREFERENCIAS
    # =====================================================

    with tab_preferencias:

        st.markdown(
            """
            <div class="info-card">
                Configura aquí los temas que más te interesan. Estos datos se guardarán en Google Sheets.
            </div>
            """,
            unsafe_allow_html=True
        )

        col_form, col_help = st.columns([1.35, 0.8], gap="large")

        with col_form:
            with st.container(border=True):
                st.subheader("⚙️ Configura tus intereses")
                st.write(
                    "Selecciona los temas sobre los que quieres recibir información. "
                    "También puedes añadir topics personalizados separados por comas."
                )

                with st.form("form_preferencias"):

                    st.markdown("### Topics disponibles")

                    topics_seleccionados = []

                    filas_topics = [
                        TOPICS_DISPONIBLES[i:i + 3]
                        for i in range(0, len(TOPICS_DISPONIBLES), 3)
                    ]

                    for fila in filas_topics:
                        cols = st.columns(3)

                        for i, topic in enumerate(fila):
                            with cols[i]:
                                seleccionado = st.checkbox(
                                    topic,
                                    value=topic in topics_previos,
                                    key=f"topic_{topic}"
                                )

                                if seleccionado:
                                    topics_seleccionados.append(topic)

                    st.write("")

                    ampliar = st.checkbox(
                        "Añadir otros topics personalizados",
                        value=bool(personalizados_previos)
                    )

                    if ampliar:
                        topics_personalizados_texto = st.text_area(
                            "Topics personalizados",
                            value=personalizados_previos,
                            placeholder="Ejemplo: vivienda, energía nuclear, inteligencia artificial, empleo juvenil"
                        )
                    else:
                        topics_personalizados_texto = ""

                    recibir_email = st.checkbox(
                        "Quiero recibir un resumen diario por email",
                        value=recibir_email_previo
                    )

                    boton_guardar = st.form_submit_button(
                        "💾 Guardar preferencias",
                        use_container_width=True
                    )

            if boton_guardar:
                topics_personalizados = convertir_texto_a_lista(topics_personalizados_texto)

                if not topics_seleccionados and not topics_personalizados:
                    st.error("Selecciona al menos un topic o añade uno personalizado.")

                else:
                    try:
                        df_usuarios = guardar_o_actualizar_usuario(
                            df=df_usuarios,
                            nombre=nombre_actual,
                            email=email_actual,
                            password=password_actual,
                            topics=topics_seleccionados,
                            topics_personalizados=topics_personalizados,
                            recibir_email=recibir_email
                        )

                        if recibir_email:
                            st.success("Preferencias guardadas correctamente en Google Sheets.")
                        else:
                            st.warning(
                                "Preferencias guardadas en Google Sheets. Has indicado que no quieres recibir el resumen diario por email."
                            )

                        st.rerun()

                    except Exception as e:
                        st.error("No se han podido guardar las preferencias en Google Sheets.")
                        st.exception(e)

        with col_help:
            with st.container(border=True):
                st.subheader("💡 Consejo")
                st.write(
                    "Los topics disponibles sirven para clasificar las noticias de forma general. "
                    "Los personalizados permiten afinar mucho más el resumen."
                )

                st.markdown("**Ejemplos de topics personalizados:**")
                st.markdown(
                    """
                    - Inteligencia artificial
                    - Vivienda
                    - Energía nuclear
                    - Empleo juvenil
                    - Mercado laboral
                    - Universidades
                    """
                )

            st.write("")

            with st.container(border=True):
                st.subheader("📌 Recomendación")
                st.write(
                    "Para obtener mejores resultados, combina temas generales con algunos "
                    "temas personalizados más concretos."
                )

    # =====================================================
    # TAB PERFIL
    # =====================================================

    with tab_perfil:

        try:
            df_actualizado = cargar_usuarios()
        except Exception as e:
            st.error("No se ha podido recargar la hoja de usuarios.")
            st.exception(e)
            df_actualizado = df_usuarios

        usuario_perfil = obtener_usuario(df_actualizado, email_actual)

        if usuario_perfil is None:

            with st.container(border=True):
                st.info("Todavía no has guardado tus preferencias.")

        else:
            nombre_perfil = str(usuario_perfil["nombre"])
            email_perfil = str(usuario_perfil["email"])
            estado_email = "Sí" if str(usuario_perfil["recibir_email"]).lower() == "true" else "No"

            topics_usuario = convertir_texto_a_lista(usuario_perfil["topics"])
            topics_personalizados_usuario = convertir_texto_a_lista(
                usuario_perfil["topics_personalizados"]
            )

            fecha_actualizacion = usuario_perfil["fecha_actualizacion"]

            if not fecha_actualizacion:
                fecha_actualizacion = "Todavía no hay fecha de actualización."

            col1, col2, col3 = st.columns(3, gap="medium")

            with col1:
                with st.container(border=True):
                    st.markdown("**Nombre**")
                    st.markdown(f"### {nombre_perfil}")

            with col2:
                with st.container(border=True):
                    st.markdown("**Email**")
                    st.markdown(f"### {email_perfil}")

            with col3:
                with st.container(border=True):
                    st.markdown("**Recibe email**")
                    st.markdown(f"### {estado_email}")

            st.write("")

            with st.container(border=True):
                st.markdown("## 👤 Mi perfil")

                st.markdown("### Topics seleccionados")
                render_badges(topics_usuario, tipo="normal")

                st.markdown("### Topics personalizados")
                render_badges(topics_personalizados_usuario, tipo="custom")

                st.markdown("### Última actualización")
                st.write(fecha_actualizacion)

    # =====================================================
    # TAB CHAT
    # =====================================================

    with tab_chat:

        with st.container(border=True):
            st.subheader("💬 Chat de noticias")
            st.write(
                "Pregunta sobre las noticias recopiladas. El asistente responderá usando únicamente "
                "el histórico de noticias."
            )

        st.markdown(
            """
            <div class="chat-note">
                Nota: el chat recuerda los mensajes anteriores solo durante esta sesión.
            </div>
            """,
            unsafe_allow_html=True
        )

        try:
            df_noticias = cargar_noticias_historicas()

            st.markdown(
                f"""
                <div class="info-card">
                    🗞️ Noticias cargadas desde Google Sheets: {len(df_noticias)}
                </div>
                """,
                unsafe_allow_html=True
            )

            for msg in st.session_state.chat_history:
                pintar_mensaje_chat(msg["role"], msg["content"])

            with st.form("form_chat", clear_on_submit=True):
                pregunta = st.text_area(
                    "Escribe tu pregunta",
                    placeholder="Ejemplo: ¿Qué noticias importantes hay sobre tecnología?",
                    height=100
                )

                col_enviar, col_limpiar = st.columns([0.75, 0.25])

                with col_enviar:
                    enviar = st.form_submit_button(
                        "Enviar pregunta",
                        use_container_width=True
                    )

                with col_limpiar:
                    limpiar = st.form_submit_button(
                        "Limpiar chat",
                        use_container_width=True
                    )

            if limpiar:
                st.session_state.chat_history = []
                st.rerun()

            if enviar:
                if not pregunta.strip():
                    st.warning("Escribe una pregunta primero.")
                else:
                    pregunta = pregunta.strip()

                    st.session_state.chat_history.append(
                        {"role": "user", "content": pregunta}
                    )

                    contexto = preparar_contexto_noticias(df_noticias, max_noticias=80)

                    mensajes = [
                        {
                            "role": "system",
                            "content": f"""
Eres un asistente especializado en analizar noticias que YA han sido recopiladas previamente.

INSTRUCCIONES IMPORTANTES:
- SOLO puedes usar la información del histórico de noticias que te proporciono.
- NO puedes usar conocimiento externo.
- NO puedes decir que no tienes acceso a información actual.
- NO puedes mencionar tu fecha de corte.
- SIEMPRE debes responder como si las noticias del histórico fueran las noticias reales disponibles.
- Si el usuario pregunta “qué ha pasado hoy”, responde usando SOLO las noticias del histórico.
- Si el usuario pregunta por algo que NO está en el histórico, responde:
  “Solo puedo responder basándome en las noticias recopiladas. Esto es lo que aparece en el histórico: …”
- Responde de forma clara, breve y ordenada.
- Usa formato Markdown limpio.
- Usa títulos en negrita para cada bloque temático.
- Usa listas con guiones para enumerar noticias.
- Si hay varias noticias relevantes, agrúpalas por tema.

HISTÓRICO DE NOTICIAS:
{contexto}
"""
                        }
                    ] + st.session_state.chat_history

                    with st.spinner("Analizando noticias..."):
                        respuesta = llamar_llama(mensajes)

                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": respuesta}
                    )

                    st.rerun()

        except Exception as e:
            st.error("No se ha podido cargar el chat de noticias.")
            st.exception(e)