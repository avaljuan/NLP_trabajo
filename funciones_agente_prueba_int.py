from datetime import datetime
import hashlib
import json
import os

from dotenv import load_dotenv
import gspread
import pandas as pd
import streamlit as st

# Cargar variables de entorno (.env)
load_dotenv()

# =========================================================
# CONFIGURACIÓN
# =========================================================

# Definimos las columnas exactas que usará nuestra hoja en la nube
COLUMNAS_SHEETS = [
    "nombre",
    "email",
    "password_hash",
    "topics",
    "topics_personalizados",
    "recibir_email",
    "fecha_actualizacion",
]

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
    "Opinión",
]


# =========================================================
# CONEXIÓN A GOOGLE SHEETS
# =========================================================


def conectar_google_sheets():
    """Establece y devuelve la conexión con la primera pestaña de tu Google Sheet."""
    credenciales_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    id_hoja = os.getenv("ID_SPREADSHEET")

    if not credenciales_json:
        st.error(
            "❌ Error: Falta la variable GOOGLE_CREDENTIALS_JSON en el archivo .env"
        )
        st.stop()

    if not id_hoja:
        st.error("❌ Error: Falta la variable SPREADSHEET_ID en el archivo .env")
        st.stop()

    try:
        creds_dict = json.loads(credenciales_json)
        gc = gspread.service_account_from_dict(creds_dict)
        return gc.open_by_key(id_hoja).sheet1
    except Exception as e:
        st.error(f"❌ Error crítico al conectar con Google Sheets: {e}")
        st.stop()


# =========================================================
# FUNCIONES DE PERSISTENCIA Y LÓGICA
# =========================================================


def hash_password(password):
    """Convierte la contraseña en un hash SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def cargar_usuarios():
    """Descarga los datos de Google Sheets y los convierte en un DataFrame de Pandas."""
    hoja = conectar_google_sheets()
    registros = hoja.get_all_records()

    # Si la hoja está completamente vacía, insertamos la fila de encabezados
    if not registros and hoja.row_values(1) == []:
        hoja.append_row(COLUMNAS_SHEETS)
        return pd.DataFrame(columns=COLUMNAS_SHEETS)

    df = pd.DataFrame(registros, dtype=str)

    # Asegurar que existen todas las columnas esperadas
    for col in COLUMNAS_SHEETS:
        if col not in df.columns:
            df[col] = ""

    # Quedarnos solo con las columnas ordenadas y rellenar nulos
    df = df[COLUMNAS_SHEETS].fillna("")
    return df


def usuario_existe(df, email):
    """Comprueba si ya existe un usuario con ese email."""
    return email in df["email"].values


def verificar_password(df, email, password):
    """Comprueba si la contraseña introducida coincide con el hash guardado."""
    password_hash = hash_password(password)
    usuario = df[df["email"] == email]

    if usuario.empty:
        return False

    password_guardada = usuario.iloc[0]["password_hash"]
    return password_hash == password_guardada


def obtener_usuario(df, email):
    """Devuelve una serie de Pandas con los datos de un usuario concreto."""
    usuario = df[df["email"] == email]
    if usuario.empty:
        return None
    return usuario.iloc[0]


def guardar_o_actualizar_usuario(
    df,
    nombre,
    email,
    password,
    topics,
    topics_personalizados,
    recibir_email=True,
):
    """Escribe o sobrescribe los datos del usuario directamente en Google Sheets."""
    hoja = conectar_google_sheets()

    password_hash = hash_password(password)
    topics_str = ", ".join(topics)
    topics_personalizados_str = ", ".join(topics_personalizados)
    fecha_actualizacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Preparamos la fila exactamente en el orden de COLUMNAS_SHEETS
    valores_fila = [
        str(nombre),
        str(email),
        str(password_hash),
        str(topics_str),
        str(topics_personalizados_str),
        str(recibir_email),
        str(fecha_actualizacion),
    ]

    try:
        # Obtenemos todos los emails de la columna B (índice 2 en Sheets)
        emails_existentes = hoja.col_values(2)

        if email in emails_existentes:
            # Si existe, localizamos su número de fila exacto
            # Sumamos 1 porque la lista de Python empieza en 0, pero Sheets en 1
            fila_idx = emails_existentes.index(email) + 1

            # Actualizamos de forma directa el rango de su fila (A:G)
            hoja.update(
                f"A{fila_idx}:G{fila_idx}",
                [valores_fila],
                value_input_option="USER_ENTERED",
            )
        else:
            # Si no existe, lo insertamos al final del documento
            hoja.append_row(valores_fila, value_input_option="USER_ENTERED")

    except Exception as e:
        st.error(f"❌ Error al guardar en Google Sheets: {e}")
        return df

    # Devolvemos el DataFrame fresco descargado de la nube para actualizar la UI
    return cargar_usuarios()


def convertir_texto_a_lista(texto):
    """Convierte un texto separado por comas en una lista limpia."""
    if not texto.strip():
        return []
    return [topic.strip() for topic in texto.split(",") if topic.strip()]


# =========================================================
# INTERFAZ STREAMLIT
# =========================================================

st.set_page_config(
    page_title="Preferencias de noticias", page_icon="📰", layout="centered"
)

st.title("📰 Configuración de preferencias de noticias")
st.write(
    "Introduce tus datos y selecciona los temas sobre los que quieres recibir "
    "un resumen diario por correo electrónico."
)

# Carga inicial desde la nube
df_usuarios = cargar_usuarios()

# Inicializar variables de sesión
if "logueado" not in st.session_state:
    st.session_state.logueado = False

if "email_usuario" not in st.session_state:
    st.session_state.email_usuario = None


# =========================================================
# FORMULARIO DE LOGIN / REGISTRO
# =========================================================

st.subheader("Inicio de sesión o registro")

with st.form("form_login"):
    nombre = st.text_input("Nombre")
    email = st.text_input("Email")
    password = st.text_input("Contraseña", type="password")
    boton_login = st.form_submit_button("Entrar / Crear perfil")

if boton_login:
    if not nombre or not email or not password:
        st.error("Por favor, completa nombre, email y contraseña.")
    else:
        if usuario_existe(df_usuarios, email):
            if verificar_password(df_usuarios, email, password):
                st.session_state.logueado = True
                st.session_state.email_usuario = email
                st.success(
                    "Inicio de sesión correcto. Puedes modificar tus preferencias."
                )
            else:
                st.error("La contraseña no es correcta.")
        else:
            st.session_state.logueado = True
            st.session_state.email_usuario = email
            st.session_state.nombre_usuario = nombre
            st.session_state.password_usuario = password
            st.success(
                "Nuevo perfil iniciado. Selecciona tus preferencias y guárdalas."
            )


# =========================================================
# FORMULARIO DE PREFERENCIAS
# =========================================================

if st.session_state.logueado:
    st.divider()
    st.subheader("Selecciona tus topics de interés")

    email_actual = st.session_state.email_usuario
    usuario_actual = obtener_usuario(df_usuarios, email_actual)

    # Precargar datos si el usuario ya existía en la nube
    if usuario_actual is not None:
        nombre_actual = usuario_actual["nombre"]
        password_actual = password

        topics_previos = []
        if isinstance(usuario_actual["topics"], str) and usuario_actual["topics"]:
            topics_previos = [
                t.strip()
                for t in usuario_actual["topics"].split(",")
                if t.strip()
            ]

        personalizados_previos = ""
        if isinstance(usuario_actual["topics_personalizados"], str):
            personalizados_previos = usuario_actual["topics_personalizados"]
    else:
        nombre_actual = nombre
        password_actual = password
        topics_previos = []
        personalizados_previos = ""

    with st.form("form_preferencias"):
        topics_seleccionados = st.multiselect(
            "Topics disponibles",
            options=TOPICS_DISPONIBLES,
            default=topics_previos,
        )

        ampliar = st.checkbox("Ampliar con otros topics personalizados")

        if ampliar:
            topics_personalizados_texto = st.text_area(
                "Añade otros topics separados por comas",
                value=personalizados_previos,
                placeholder="Ejemplo: vivienda, energía nuclear, inteligencia artificial",
            )
        else:
            topics_personalizados_texto = personalizados_previos

        recibir_email = st.checkbox(
            "Quiero recibir un resumen diario por email", value=True
        )
        boton_guardar = st.form_submit_button("Guardar preferencias")

    if boton_guardar:
        topics_personalizados = convertir_texto_a_lista(
            topics_personalizados_texto
        )

        if not topics_seleccionados and not topics_personalizados:
            st.error("Selecciona al menos un topic o añade uno personalizado.")
        else:
            if not recibir_email:
                st.warning(
                    "Preferencias guardadas. Has indicado que no quieres recibir el email diario."
                )

            # Actualizamos la hoja de cálculo en tiempo real
            df_usuarios = guardar_o_actualizar_usuario(
                df=df_usuarios,
                nombre=nombre_actual,
                email=email_actual,
                password=password_actual,
                topics=topics_seleccionados,
                topics_personalizados=topics_personalizados,
                recibir_email=recibir_email,
            )
            st.success("¡Preferencias guardadas correctamente en la nube!")


# =========================================================
# PERFIL DEL USUARIO LOGUEADO
# =========================================================

if st.session_state.logueado:
    st.divider()
    st.subheader("Mi perfil")

    # Consultamos el DataFrame global fresco
    df_actualizado = cargar_usuarios()
    email_actual = st.session_state.email_usuario
    usuario_actual = df_actualizado[df_actualizado["email"] == email_actual]

    if not usuario_actual.empty:
        usuario_actual = usuario_actual.iloc[0]

        st.write(f"**Nombre:** {usuario_actual['nombre']}")
        st.write(f"**Email:** {usuario_actual['email']}")
        st.write(
            f"**Recibir Resumen Diario:** {'Sí' if usuario_actual['recibir_email'] == 'True' else 'No'}"
        )

        st.write("**Topics seleccionados:**")
        if usuario_actual["topics"]:
            st.write(
                [t.strip() for t in usuario_actual["topics"].split(",") if t.strip()]
            )
        else:
            st.write("No hay topics seleccionados.")

        st.write("**Topics personalizados:**")
        if usuario_actual["topics_personalizados"]:
            st.write(
                [
                    t.strip()
                    for t in usuario_actual["topics_personalizados"].split(",")
                    if t.strip()
                ]
            )
        else:
            st.write("No hay topics personalizados.")

        st.write(
            f"**Última actualización:** {usuario_actual['fecha_actualizacion']}"
        )
    else:
        st.info("Todavía no has guardado tus preferencias.")