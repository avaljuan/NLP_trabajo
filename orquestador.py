"""
Orquestador centralizado de noticias con LangChain y OpenRouter (Llama 3.3 70B).
Adaptado nativamente para consumir funciones de scraping que devuelven DataFrames de Pandas.
"""

from __future__ import annotations

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import smtplib
from typing import Literal

from dotenv import load_dotenv
import gspread
#from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import pandas as pd
from pydantic import BaseModel, Field

# IMPORTACIÓN DE TUS SCRAPERS REALES
from scrapers.elDiario_agente import *
from scrapers.elespanol_diario import *
from scrapers.scraper_larazon import *
from scrapers.scraper_publico import *
from scrapers.tercera_informacion_agente import *

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODELO_POR_DEFECTO = "meta-llama/llama-3.3-70b-instruct"
TEMPERATURA_POR_DEFECTO = 0.1

# =====================================================================
# ALMACÉN GLOBAL EN MEMORIA (Para que el agente consulte textos largos)
# =====================================================================
POOL_NOTICIAS_COMPLETAS = {}


# =====================================================================
# 1. HERRAMIENTAS DEL AGENTE
# =====================================================================
class LeerNoticiaArgs(BaseModel):
    id_noticia: str = Field(
        description="Identificador único de la noticia (ej. 'n1', 'n2') que decides consultar a fondo."
    )


@tool("leer_texto_noticia", args_schema=LeerNoticiaArgs)
def leer_texto_noticia(id_noticia: str) -> str:
    """Tool que el agente DECIDE usar para obtener el texto completo de una noticia en memoria RAM."""
    return POOL_NOTICIAS_COMPLETAS.get(
        id_noticia, "Error: ID de noticia no encontrado."
    )


class EnviarEmailArgs(BaseModel):
    destinatario: str = Field(description="Email del usuario.")
    asunto: Literal["Noticias relevantes diarias"] = Field(
        description="Debe ser estrictamente 'Noticias relevantes diarias'."
    )
    cuerpo: str = Field(
        description="Código HTML final con las noticias curadas o el aviso de vacío."
    )


@tool("enviar_email", args_schema=EnviarEmailArgs)
def enviar_email(destinatario: str, asunto: str, cuerpo: str) -> str:
    """Tool para ejecutar el envío del correo final vía SMTP."""
    remitente = os.getenv("EMAIL_REMITENTE")
    password = os.getenv("EMAIL_PASSWORD")
    if not remitente or not password:
        return "Error: Credenciales SMTP no configuradas."

    msg = MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "html"))
    try:
        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.sendmail(remitente, destinatario, msg.as_string())
        servidor.quit()
        return f"Éxito: Correo enviado a {destinatario}."
    except Exception as exc:
        return f"Error SMTP: {exc}"


# =====================================================================
# 2. INICIALIZACIÓN DEL LLM Y AGENTE
# =====================================================================
def crear_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=MODELO_POR_DEFECTO,
        temperature=TEMPERATURA_POR_DEFECTO,
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=OPENROUTER_BASE_URL,
    )


def crear_agente() -> AgentExecutor:
    llm = crear_llm()
    herramientas = [leer_texto_noticia, enviar_email]

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Eres un agente curador con capacidad de investigación. "
                "Recibes un listado de titulares. Sigue este razonamiento estricto:\n"
                "1. Analiza los titulares frente al perfil del usuario.\n"
                "2. Si un titular te parece potencialmente relevante pero necesitas verificar los detalles, DECIDES llamar a la herramienta 'leer_texto_noticia' pasándole su ID para leer el cuerpo completo.\n"
                "3. Puedes consultar tantas noticias como consideres necesario.\n"
                "4. Una vez tengas absoluta certeza de cuáles encajan, DEBES ejecutar 'enviar_email' para mandar el boletín HTML final.",
            ),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    agente = create_tool_calling_agent(llm, herramientas, prompt)
    return AgentExecutor(
        agent=agente,
        tools=herramientas,
        verbose=True,
        handle_parsing_errors=True,
    )


# =====================================================================
# 3. FUNCIONES AUXILIARES Y DE CONEXIÓN
# =====================================================================
def ejecutar_scraper_seguro(
    nombre_fuente: str, funcion_scraper, **kwargs
) -> pd.DataFrame:
    """Ejecuta una función de scraping asegurando que siempre devuelva un DataFrame."""
    print(f"Consultando fuentes de: {nombre_fuente}...")
    try:
        df = funcion_scraper(**kwargs)
        # Garantizamos que la salida sea un DataFrame válido de Pandas
        if isinstance(df, pd.DataFrame):
            return df
        else:
            print(
                f"⚠️ Aviso: {nombre_fuente} no devolvió un DataFrame. Convirtiendo..."
            )
            return pd.DataFrame(df)
    except Exception as e:
        print(f"⚠️ Fallo crítico en {nombre_fuente}: {e}")
        return pd.DataFrame()  # Devuelve un DataFrame vacío si colapsa


def obtener_dataframe_usuarios() -> pd.DataFrame:
    creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
    gc = gspread.service_account_from_dict(creds_dict)
    hoja = gc.open_by_key(os.getenv("ID_SPREADSHEET")).sheet1
    return pd.DataFrame(hoja.get_all_records(), dtype=str)


# =====================================================================
# 4. FLUJO PRINCIPAL DE EJECUCIÓN
# =====================================================================
def main():
    print(f"\n--- 🚀 INICIANDO ORQUESTADOR CENTRAL ({MODELO_POR_DEFECTO}) ---")
    global POOL_NOTICIAS_COMPLETAS

    # A. Volcado de noticias (Capturando DataFrames con parámetros explícitos)
    dfs_recopilados = []

    # Llamada 1
    dfs_recopilados.append(
        ejecutar_scraper_seguro(
            "Periódico 1", scrape_elespanol_opinion, max_paginas=8, max_articulos=10, espera=0.5
        )
    )

    # Llamada 2
    # dfs_recopilados.append(
    #     ejecutar_scraper_seguro(
    #         "Periódico 2", scrape_larazon_opinion, objetivo=10, headless=True, paginas_max=30
    #     )
    # )

    # # Llamada 3
    dfs_recopilados.append(
        ejecutar_scraper_seguro("Periódico 3", scrape_opinion_articles_hoy, limit = 10, target_date= None)
    )

    # # Llamada 4
    # dfs_recopilados.append(
    #     ejecutar_scraper_seguro(
    #         "Periódico 4", scrapear_p4, url_base="https://ejemplo.com"
    #     )
    # )

    # # Llamada 5
    # dfs_recopilados.append(ejecutar_scraper_seguro("Periódico 5", scrapear_p5))

    # Filtramos DataFrames vacíos por seguridad
    dfs_validos = [df for df in dfs_recopilados if not df.empty]

    if not dfs_validos:
        print("❌ Todas las fuentes fallaron o devolvieron DataFrames vacíos.")
        return

    # Unificamos todos los DataFrames en un único dataset maestro
    df_pool = pd.concat(dfs_validos, ignore_index=True)
    print(
        f"📥 Volcado masivo completado: {len(df_pool)} noticias unificadas en el DataFrame."
    )   
    # Preparamos las estructuras para la memoria del Agente
    menu_ligero_noticias = []
    POOL_NOTICIAS_COMPLETAS.clear()

    # Asumimos que tus DataFrames tienen columnas llamadas 'titulo', 'enlace' y 'texto_completo'
    for idx, fila in df_pool.iterrows():
        id_noticia = f"n{idx+1}"

        # Usamos .get() sobre la Serie de Pandas por si alguna columna llegara a faltar
        titulo = fila.get("titulo", "Sin título")
        enlace = fila.get("enlace", "")
        texto_completo = fila.get("texto_completo", "Sin contenido disponible.")

        # Menú ligero para inyectar en el prompt inicial
        menu_ligero_noticias.append(
            {"id": id_noticia, "titulo": str(titulo), "enlace": str(enlace)}
        )

        # Almacenamiento del texto completo en memoria rápida
        POOL_NOTICIAS_COMPLETAS[id_noticia] = str(texto_completo)

    # B. Carga de usuarios desde Google Sheets
    try:
        df_usuarios = obtener_dataframe_usuarios()
    except Exception as exc:
        print(f"❌ Error descargando preferencias: {exc}")
        return

    # C. Ejecución del Agente
    agente_executor = crear_agente()

    for _, usuario in df_usuarios.iterrows():
        nombre = usuario.get("nombre", "Usuario")
        email = usuario.get("email", "")
        topics = usuario.get("topics", "")
        topics_pers = usuario.get("topics_personalizados", "")
        recibir_email = usuario.get("recibir_email", "True")

        if not email or recibir_email.lower() == "false":
            continue

        print(f"\n🧠 Agente investigando para: {email}")

        instruccion = (
            f"Usuario: {nombre} ({email})\n"
            f"- Temas generales: {topics}\n"
            f"- Intereses específicos: {topics_pers}\n\n"
            f"Titulares de hoy disponibles para consulta:\n{json.dumps(menu_ligero_noticias, ensure_ascii=False, indent=2)}\n\n"
            f"Mando: Revisa los titulares. Si alguno promete pero necesitas confirmar, DECIDES usar 'leer_texto_noticia' con su ID. "
            f"Al finalizar tu investigación, DEBES usar 'enviar_email' para mandar el reporte final."
        )

        try:
            agente_executor.invoke({"input": instruccion})
        except Exception as exc:
            print(f"❌ Fallo en agente para {email}: {exc}")

    print("\n--- 🏁 PROCESO FINALIZADO ---")


import os
import threading
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "🟢 Orquestador de noticias activo y esperando la alarma."

@app.route('/disparar-agente')
def trigger():
    """Ruta que será llamada por nuestra alarma externa todos los días a las 07:30."""
    # Ejecutamos tu función main() en un hilo secundario.
    # Esto es VITAL porque scrapear y consultar al LLM tarda un rato,
    # y así evitamos que el servidor de Render colapse esperando la respuesta.
    hilo = threading.Thread(target=main)
    hilo.start()
    return jsonify({"status": "Ejecución del Agente iniciada en segundo plano"}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)