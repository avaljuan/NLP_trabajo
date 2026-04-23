"""
Scraper de noticias sobre Ormuz en El Español
Periodo: enero 2026 - 21 abril 2026
Output: data_elespanol.csv
Columnas: periodico, fecha, titulo, texto, url (sin mayusculas ni acentos)

Uso:
    pip install requests beautifulsoup4 lxml
    python scraper_elespanol.py
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import unicodedata
import re
from datetime import datetime
from urllib.parse import urlencode

# ── Configuracion ─────────────────────────────────────────────────────────────

TERMINO      = "Ormuz"
FECHA_INICIO = datetime(2026, 1, 1)
FECHA_FIN    = datetime(2026, 4, 21)
OUTPUT_CSV   = "data_elespanol.csv"
DELAY        = 1.5      # segundos entre peticiones
MAX_PAGINAS  = 20       # paginas del buscador a recorrer

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.elespanol.com/",
}

# ── Utilidades ────────────────────────────────────────────────────────────────

def quitar_acentos(texto):
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_tilde = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_tilde.lower()


def limpiar(texto):
    if not texto:
        return ""
    texto = re.sub(r"\s+", " ", texto).strip()
    return quitar_acentos(texto)


def fecha_de_url(url):
    m = re.search(r"/(\d{8})/", url)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d")
        except ValueError:
            pass
    return None


def en_rango(url):
    dt = fecha_de_url(url)
    if dt is None:
        return True
    return FECHA_INICIO <= dt <= FECHA_FIN


# ── Busqueda ──────────────────────────────────────────────────────────────────

def urls_busqueda(termino, n_paginas):
    """
    El buscador de El Español:
      GET https://www.elespanol.com/buscador/?text=TERMINO&page=N
    Verificado en el HTML: <form action="/buscador/"> <input name="text">
    """
    base = "https://www.elespanol.com/buscador/"
    return [f"{base}?{urlencode({'text': termino, 'page': p})}" for p in range(1, n_paginas + 1)]


def extraer_links_pagina(html):
    """
    Extrae hrefs de articulos de una pagina de resultados.
    El Español usa: <h2 class="art__title"><a href="...">
    """
    soup = BeautifulSoup(html, "lxml")
    links = []

    # Estructura exacta confirmada en el HTML analizado
    for h2 in soup.find_all("h2", class_="art__title"):
        a = h2.find("a", href=True)
        if a:
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.elespanol.com" + href
            links.append(href)

    # Fallback: cualquier <a> con patron /YYYYMMDD/ en la URL
    if not links:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("http"):
                href = "https://www.elespanol.com" + href
            if re.search(r"elespanol\.com.*?/\d{8}/", href):
                links.append(href)

    # Deduplicar
    vistos = set()
    unicos = []
    for l in links:
        if l not in vistos:
            vistos.add(l)
            unicos.append(l)
    return unicos


# ── Extraccion de articulo ────────────────────────────────────────────────────

def extraer_noticia(url, session):
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [ERROR descarga] {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # ── Titulo ──
    # En articulos individuales El Español usa <h1 class="art__title">
    titulo_tag = (
        soup.find("h1", class_="art__title")
        or soup.find("h1", class_=re.compile(r"title|titular", re.I))
        or soup.find("h1")
    )
    titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""

    # ── Fecha ──
    fecha_str = ""

    # 1) <time datetime="YYYY-MM-DD"> — confirmado en el HTML analizado
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        fecha_str = time_tag["datetime"][:10]

    # 2) Meta tags
    if not fecha_str:
        for prop in ["article:published_time", "datePublished"]:
            meta = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if meta and meta.get("content"):
                fecha_str = meta["content"][:10]
                break

    # 3) Desde la URL
    if not fecha_str:
        dt = fecha_de_url(url)
        if dt:
            fecha_str = dt.strftime("%Y-%m-%d")

    # Verificar rango de fechas
    if fecha_str:
        try:
            dt_check = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
            if not (FECHA_INICIO <= dt_check <= FECHA_FIN):
                return None
        except ValueError:
            pass

    # ── Cuerpo ──
    # Selectores por orden de preferencia para El Español
    cuerpo = (
        soup.find(class_=re.compile(r"art__body[-_]?content", re.I))
        or soup.find(class_=re.compile(r"article[-_]?body", re.I))
        or soup.find(class_=re.compile(r"news[-_]?body", re.I))
        or soup.find("article")
    )

    if cuerpo:
        for tag in cuerpo.find_all(
            ["script", "style", "figure", "figcaption", "aside",
             "nav", "iframe", "noscript", "blockquote", "button"]
        ):
            tag.decompose()
        parrafos = cuerpo.find_all("p")
        texto = " ".join(p.get_text(strip=True) for p in parrafos if p.get_text(strip=True))
    else:
        # Ultimo recurso: todos los parrafos largos de la pagina
        parrafos = soup.find_all("p")
        texto = " ".join(p.get_text(strip=True) for p in parrafos if len(p.get_text(strip=True)) > 40)

    if not titulo and not texto:
        return None

    return {
        "periodico": "el espanol",
        "fecha":     limpiar(fecha_str),
        "titulo":    limpiar(titulo),
        "texto":     limpiar(texto),
        "url":       url,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    session = requests.Session()
    session.headers.update(HEADERS)

    print("=" * 65)
    print(f"  Scraper El Espanol | Termino: '{TERMINO}'")
    print(f"  Rango: {FECHA_INICIO.date()} -> {FECHA_FIN.date()}")
    print("=" * 65)

    # ── FASE 1: Recoger URLs candidatas del buscador ───────────────────────
    candidatas = set()
    paginas = urls_busqueda(TERMINO, MAX_PAGINAS)

    for i, url_b in enumerate(paginas, 1):
        print(f"\n[Busqueda {i:02d}/{len(paginas)}] {url_b}")
        try:
            resp = session.get(url_b, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  -> ERROR: {e}")
            time.sleep(DELAY)
            continue

        links = extraer_links_pagina(resp.text)
        en_periodo = [l for l in links if en_rango(l)]
        print(f"  -> {len(links)} links | {len(en_periodo)} en rango de fechas")

        # Parar si todos los resultados son anteriores al rango de interes
        fechas_pagina = [fecha_de_url(l) for l in links if fecha_de_url(l)]
        if fechas_pagina and max(fechas_pagina) < FECHA_INICIO:
            print("  -> Resultados anteriores al rango. Deteniendo busqueda.")
            break

        candidatas.update(en_periodo)
        time.sleep(DELAY)

    candidatas = list(candidatas)
    print(f"\n{'─'*65}")
    print(f"Total URLs candidatas: {len(candidatas)}")
    print(f"{'─'*65}\n")

    if not candidatas:
        print("AVISO: No se encontraron URLs candidatas.")
        print("Comprueba manualmente: https://www.elespanol.com/buscador/?text=Ormuz")
        return

    # ── FASE 2: Extraer contenido ──────────────────────────────────────────
    noticias = []
    for i, url in enumerate(candidatas, 1):
        print(f"[{i:03d}/{len(candidatas)}] {url[:75]}...")
        noticia = extraer_noticia(url, session)
        if noticia:
            noticias.append(noticia)
            print(f"  OK [{noticia['fecha']}] {noticia['titulo'][:60]}...")
        else:
            print(f"  -- Descartado")
        time.sleep(DELAY)

    # Ordenar por fecha
    noticias.sort(key=lambda x: x["fecha"])

    # ── FASE 3: Guardar CSV ────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print(f"Noticias validas: {len(noticias)}")

    if noticias:
        campos = ["periodico", "fecha", "titulo", "texto", "url"]
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(noticias)
        print(f"\nCSV guardado: {OUTPUT_CSV}  ({len(noticias)} filas)")
        print("\nVista previa (primeras 3):")
        for n in noticias[:3]:
            print(f"  {n['fecha']} | {n['titulo'][:55]}...")
    else:
        print("\nSin resultados. Posibles causas:")
        print("  1. El Espanol bloquea el scraping desde este entorno")
        print("  2. Ejecuta el script desde tu maquina local")
        print("  3. Aumenta DELAY si recibes errores 429")


if __name__ == "__main__":
    main()