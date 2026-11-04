#!/usr/bin/env python3
"""Busca y descarga imágenes de Pexels y Pixabay para usar en presentaciones.

Solo usa la biblioteca estándar de Python (no hay que instalar nada).

Claves de API (gratuitas), leídas de variables de entorno:
    PEXELS_API_KEY   -> https://www.pexels.com/api/
    PIXABAY_API_KEY  -> https://pixabay.com/api/docs/

Ejemplos:
    python3 herramientas/imagenes.py buscar "oficina moderna"
    python3 herramientas/imagenes.py buscar "seguridad industrial" --fuente pixabay -n 5
    python3 herramientas/imagenes.py descargar "trabajo en equipo" --destino imagenes/ -n 3

Por defecto pide imágenes horizontales (las que mejor encajan en una diapositiva)
y guarda un archivo creditos.json con el autor y el enlace de cada imagen.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

USER_AGENT = "mi-primer-repo-imagenes/1.0"
TIMEOUT = 30


@dataclass
class Imagen:
    fuente: str
    id: str
    descripcion: str
    autor: str
    autor_url: str
    pagina_url: str
    descarga_url: str
    ancho: int
    alto: int

    @property
    def credito(self) -> str:
        sitio = "Pexels" if self.fuente == "pexels" else "Pixabay"
        return f"Foto de {self.autor} en {sitio}"


class ErrorFuente(Exception):
    pass


def _get_json(url: str, headers: dict[str, str] | None = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise ErrorFuente(f"clave de API rechazada o sin permiso (HTTP {e.code})") from e
        if e.code == 429:
            raise ErrorFuente("límite de peticiones alcanzado (HTTP 429); espera un poco") from e
        raise ErrorFuente(f"error HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise ErrorFuente(f"no se pudo conectar: {e.reason}") from e


def _clave(nombre: str) -> str:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ErrorFuente(f"falta la variable de entorno {nombre}")
    return valor


# Pexels y Pixabay usan nombres distintos para la orientación.
_ORIENT_PEXELS = {"horizontal": "landscape", "vertical": "portrait", "cuadrada": "square"}
_ORIENT_PIXABAY = {"horizontal": "horizontal", "vertical": "vertical"}


def buscar_pexels(consulta: str, n: int, orientacion: str | None, idioma: str) -> list[Imagen]:
    # Pexels espera el idioma como "es-ES"; Pixabay como "es".
    locale = {"es": "es-ES", "en": "en-US", "pt": "pt-BR", "fr": "fr-FR"}.get(idioma, idioma)
    params = {"query": consulta, "per_page": min(max(n, 1), 80), "locale": locale}
    if orientacion in _ORIENT_PEXELS:
        params["orientation"] = _ORIENT_PEXELS[orientacion]
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(params)
    datos = _get_json(url, {"Authorization": _clave("PEXELS_API_KEY")})
    return [
        Imagen(
            fuente="pexels",
            id=str(f["id"]),
            descripcion=f.get("alt") or "",
            autor=f.get("photographer") or "",
            autor_url=f.get("photographer_url") or "",
            pagina_url=f.get("url") or "",
            descarga_url=f["src"].get("large2x") or f["src"]["original"],
            ancho=f.get("width", 0),
            alto=f.get("height", 0),
        )
        for f in datos.get("photos", [])[:n]
    ]


def buscar_pixabay(consulta: str, n: int, orientacion: str | None, idioma: str) -> list[Imagen]:
    params = {
        "key": _clave("PIXABAY_API_KEY"),
        "q": consulta[:100],
        "per_page": min(max(n, 3), 200),  # Pixabay exige mínimo 3
        "image_type": "photo",
        "safesearch": "true",
        "lang": idioma,
    }
    if orientacion in _ORIENT_PIXABAY:
        params["orientation"] = _ORIENT_PIXABAY[orientacion]
    url = "https://pixabay.com/api/?" + urllib.parse.urlencode(params)
    datos = _get_json(url)
    return [
        Imagen(
            fuente="pixabay",
            id=str(h["id"]),
            descripcion=h.get("tags") or "",
            autor=h.get("user") or "",
            autor_url=f"https://pixabay.com/users/{h.get('user')}-{h.get('user_id')}/",
            pagina_url=h.get("pageURL") or "",
            descarga_url=h.get("largeImageURL") or h["webformatURL"],
            ancho=h.get("imageWidth", 0),
            alto=h.get("imageHeight", 0),
        )
        for h in datos.get("hits", [])[:n]
    ]


FUENTES = {"pexels": buscar_pexels, "pixabay": buscar_pixabay}


def buscar(consulta: str, fuentes: list[str], n: int, orientacion: str | None, idioma: str) -> list[Imagen]:
    """Consulta cada fuente; si una falla, avisa y sigue con las demás."""
    resultados: list[Imagen] = []
    for nombre in fuentes:
        try:
            resultados.extend(FUENTES[nombre](consulta, n, orientacion, idioma))
        except ErrorFuente as e:
            print(f"[aviso] {nombre}: {e}", file=sys.stderr)
    return resultados


def _nombre_archivo(img: Imagen, consulta: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", consulta.lower()).strip("-")[:40] or "imagen"
    ext = Path(urllib.parse.urlparse(img.descarga_url).path).suffix.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    return f"{base}-{img.fuente}-{img.id}{ext}"


def descargar(imagenes: list[Imagen], destino: Path, consulta: str) -> list[dict]:
    destino.mkdir(parents=True, exist_ok=True)
    creditos_path = destino / "creditos.json"
    creditos = json.loads(creditos_path.read_text("utf-8")) if creditos_path.exists() else []
    nuevos = []
    for img in imagenes:
        archivo = destino / _nombre_archivo(img, consulta)
        req = urllib.request.Request(img.descarga_url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                archivo.write_bytes(resp.read())
        except urllib.error.URLError as e:
            print(f"[aviso] no se pudo descargar {img.descarga_url}: {e}", file=sys.stderr)
            continue
        registro = {"archivo": archivo.name, "credito": img.credito, **asdict(img)}
        creditos = [c for c in creditos if c.get("archivo") != archivo.name] + [registro]
        nuevos.append(registro)
        print(f"✔ {archivo}  ({img.credito})")
    creditos_path.write_text(json.dumps(creditos, ensure_ascii=False, indent=2) + "\n", "utf-8")
    return nuevos


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="accion", required=True)
    for nombre, ayuda in (("buscar", "lista resultados"), ("descargar", "descarga resultados")):
        s = sub.add_parser(nombre, help=ayuda)
        s.add_argument("consulta", help='qué buscar, p. ej. "reunión de equipo"')
        s.add_argument("--fuente", choices=["pexels", "pixabay", "ambas"], default="ambas")
        s.add_argument("-n", type=int, default=5, help="resultados por fuente (por defecto 5)")
        s.add_argument("--orientacion", choices=["horizontal", "vertical", "cuadrada", "cualquiera"],
                       default="horizontal")
        s.add_argument("--idioma", default="es", help="idioma de la búsqueda (por defecto es)")
        s.add_argument("--json", action="store_true", help="salida en JSON")
        if nombre == "descargar":
            s.add_argument("--destino", type=Path, default=Path("imagenes"))
    a = p.parse_args(argv)

    fuentes = ["pexels", "pixabay"] if a.fuente == "ambas" else [a.fuente]
    orient = None if a.orientacion == "cualquiera" else a.orientacion
    resultados = buscar(a.consulta, fuentes, a.n, orient, a.idioma)
    if not resultados:
        raise SystemExit("No se obtuvo ninguna imagen (revisa los avisos de arriba).")

    if a.accion == "descargar":
        nuevos = descargar(resultados, a.destino, a.consulta)
        if a.json:
            print(json.dumps(nuevos, ensure_ascii=False, indent=2))
        return 0 if nuevos else 1

    if a.json:
        print(json.dumps([{**asdict(i), "credito": i.credito} for i in resultados], ensure_ascii=False, indent=2))
    else:
        for i in resultados:
            print(f"[{i.fuente}] {i.ancho}x{i.alto}  {i.descripcion[:60]}\n    {i.descarga_url}\n    {i.credito}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
