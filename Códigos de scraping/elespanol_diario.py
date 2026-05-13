"""
Scraper diario de la sección de Opinión de El Español.

Este archivo está pensado para ejecutarse como script independiente o para ser
importado desde un agente.

Uso desde terminal:
    python elespanol_diario.py

Uso desde otro archivo/agente:
    from elespanol_diario import scrape_elespanol_opinion
    df = scrape_elespanol_opinion()
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup


SECCIONES_BASE = [
    "https://www.elespanol.com/opinion/",
]

MAX_PAGINAS = 4
MAX_ARTICULOS = 13
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_soup(url: str) -> BeautifulSoup:
    """Descarga una página y devuelve su HTML parseado."""
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def es_articulo(url: str) -> bool:
    """Comprueba si una URL parece ser un artículo de opinión."""
    return "/opinion/" in url and url.count("/") > 4


def obtener_urls_articulos(
    secciones_base: Iterable[str] = SECCIONES_BASE,
    max_paginas: int = MAX_PAGINAS,
    max_articulos: int = MAX_ARTICULOS,
    espera: float = 0.5,
) -> list[str]:
    """Obtiene URLs de artículos desde las páginas de la sección."""
    urls: list[str] = []
    urls_set: set[str] = set()

    for seccion in secciones_base:
        print(f"Sección: {seccion}")

        for pagina in range(1, max_paginas + 1):
            if len(urls) >= max_articulos:
                break

            url = seccion if pagina == 1 else f"{seccion}{pagina}/"
            print(f"  Página {pagina}")

            try:
                soup = get_soup(url)
                enlaces = soup.select("a[href]")
                nuevos = 0

                for enlace in enlaces:
                    href = enlace["href"]

                    if href.startswith("https://") and es_articulo(href):
                        if href not in urls_set:
                            urls_set.add(href)
                            urls.append(href)
                            nuevos += 1

                    if len(urls) >= max_articulos:
                        break

                print(f"    +{nuevos} nuevos (total {len(urls)})")

            except Exception as error:
                print(f"Error obteniendo URLs en {url}: {error}")

            time.sleep(espera)

        if len(urls) >= max_articulos:
            break

    return urls


def scrape_article(url: str) -> dict[str, str]:
    """Scrapea un artículo concreto y devuelve sus campos principales."""
    soup = get_soup(url)

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else ""

    paragraphs = soup.select("article p")
    text = " ".join(paragraph.get_text(strip=True) for paragraph in paragraphs)

    return {
        "periodico": "el español",
        "fecha_scrapeo": datetime.now().strftime("%Y-%m-%d"),
        "titulo": title.lower(),
        "texto": text.lower(),
        "url": url.lower(),
    }


def scrape_elespanol_opinion(
    max_paginas: int = MAX_PAGINAS,
    max_articulos: int = MAX_ARTICULOS,
    guardar_csv: bool = True,
    output_dir: str | Path = ".",
    espera: float = 0.5,
) -> pd.DataFrame:
    """
    Ejecuta el scraping completo y devuelve un DataFrame.

    Si guardar_csv=True, guarda también un CSV con nombre:
    elespanol_opinion_YYYY-MM-DD.csv
    """
    urls = obtener_urls_articulos(
        max_paginas=max_paginas,
        max_articulos=max_articulos,
        espera=espera,
    )

    rows: list[dict[str, str]] = []

    for url in urls:
        try:
            articulo = scrape_article(url)

            if articulo["titulo"] and articulo["texto"]:
                rows.append(articulo)

            if len(rows) >= max_articulos:
                break

            time.sleep(espera)

        except Exception as error:
            print(f"Error scrapeando artículo {url}: {error}")

    print("Artículos scrapeados:", len(rows))

    df = pd.DataFrame(rows)

    if guardar_csv:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y-%m-%d")
        output_path = output_dir / f"elespanol_opinion_{fecha}.csv"
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"CSV guardado en: {output_path}")

    return df


if __name__ == "__main__":
    scrape_elespanol_opinion()
