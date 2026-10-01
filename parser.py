"""
GeoMapa Express - parser.py
Responsabilidade única: ler qualquer arquivo geoespacial,
detectar o SRC, reprojetar para WGS84 e retornar geometrias Shapely prontas.

Formatos suportados: KML, KMZ, GeoJSON, GeoPackage (.gpkg), Shapefile (.zip)
SRC suportados: qualquer projeção reconhecida pelo pyproj (UTM, SIRGAS, WGS84, etc.)
"""

import json
import re
import zipfile
import tempfile
from pathlib import Path
from shapely.geometry import shape, GeometryCollection


# ── ENTRADA PÚBLICA ───────────────────────────────────────────────────────────

def carregar_arquivo(caminho: str):
    """
    Ponto de entrada único do parser.
    Detecta formato, lê geometrias e garante saída em WGS84 (EPSG:4326).

    Retorna:
        (geometrias: list[Shapely], tipo: str, src_original: str)
    """
    path = Path(caminho)
    ext  = path.suffix.lower()

    if ext in (".geojson", ".json"):
        gdf = _ler_com_geopandas(caminho)
        src = str(gdf.crs) if gdf.crs else "EPSG:4326"
        gdf = _garantir_wgs84(gdf)
        return list(gdf.geometry), "geojson", src

    elif ext == ".kml":
        # KML é sempre WGS84 por especificação OGC
        geometrias = _ler_kml(caminho)
        return geometrias, "kml", "EPSG:4326"

    elif ext == ".kmz":
        geometrias = _ler_kmz(caminho)
        return geometrias, "kmz", "EPSG:4326"

    elif ext == ".gpkg":
        gdf = _ler_com_geopandas(caminho)
        src = str(gdf.crs) if gdf.crs else "desconhecido"
        gdf = _garantir_wgs84(gdf)
        return list(gdf.geometry), "geopackage", src

    elif ext == ".zip":
        gdf, src = _ler_shapefile_zip(caminho)
        gdf = _garantir_wgs84(gdf)
        return list(gdf.geometry), "shapefile", src

    else:
        raise ValueError(
            f"Formato '{ext}' não suportado.\n"
            "Use: .kml · .kmz · .geojson · .gpkg · .zip (Shapefile)"
        )


# ── REPROJEÇÃO ────────────────────────────────────────────────────────────────

def _garantir_wgs84(gdf):
    """
    Reprojeta GeoDataFrame para WGS84 (EPSG:4326) se necessário.
    Funciona com qualquer SRC reconhecido pelo pyproj.
    """
    import geopandas as gpd

    if gdf.crs is None:
        # Sem SRC definido: assume WGS84
        gdf = gdf.set_crs(epsg=4326)
        return gdf

    if gdf.crs.to_epsg() == 4326:
        return gdf  # já está em WGS84

    # Reprojeta de qualquer SRC → WGS84
    return gdf.to_crs(epsg=4326)


# ── LEITORES POR FORMATO ──────────────────────────────────────────────────────

def _ler_com_geopandas(caminho: str):
    """Lê GeoJSON ou GeoPackage via GeoPandas."""
    import geopandas as gpd
    gdf = gpd.read_file(caminho)
    if gdf.empty:
        raise ValueError("Arquivo carregado mas nenhuma feição encontrada.")
    return gdf


def _ler_shapefile_zip(caminho: str):
    """
    Extrai .zip contendo Shapefile e lê com GeoPandas.
    Retorna (GeoDataFrame, src_original_str).
    """
    import geopandas as gpd

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(caminho, "r") as z:
            z.extractall(tmpdir)

        shp_files = list(Path(tmpdir).glob("**/*.shp"))
        if not shp_files:
            raise ValueError(
                "Nenhum arquivo .shp encontrado dentro do .zip.\n"
                "Verifique se o zip contém os arquivos .shp, .dbf e .prj."
            )

        gdf = gpd.read_file(str(shp_files[0]))
        src = str(gdf.crs) if gdf.crs else "desconhecido"

    return gdf, src


def _ler_kmz(caminho: str):
    """Extrai o KML interno de um arquivo KMZ e retorna geometrias."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(caminho, "r") as z:
            z.extractall(tmpdir)

        kml_files = list(Path(tmpdir).glob("**/*.kml"))
        if not kml_files:
            raise ValueError("Nenhum arquivo KML encontrado dentro do KMZ.")

        return _ler_kml(str(kml_files[0]))


def _ler_kml(caminho: str):
    """
    Lê KML por expressão regular.
    KML é sempre WGS84 por especificação — sem necessidade de reprojeção.
    """
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()

    geometrias = []

    # Polygon
    for coords_raw in re.findall(
        r"<Polygon>.*?<coordinates>(.*?)</coordinates>.*?</Polygon>",
        conteudo, re.DOTALL
    ):
        coords = _parsear_coords_kml(coords_raw)
        if len(coords) >= 3:
            from shapely.geometry import Polygon
            geometrias.append(Polygon(coords))

    # LineString
    for coords_raw in re.findall(
        r"<LineString>.*?<coordinates>(.*?)</coordinates>.*?</LineString>",
        conteudo, re.DOTALL
    ):
        coords = _parsear_coords_kml(coords_raw)
        if len(coords) >= 2:
            from shapely.geometry import LineString
            geometrias.append(LineString(coords))

    # Point
    for coords_raw in re.findall(
        r"<Point>.*?<coordinates>(.*?)</coordinates>.*?</Point>",
        conteudo, re.DOTALL
    ):
        coords = _parsear_coords_kml(coords_raw)
        if coords:
            from shapely.geometry import Point
            geometrias.append(Point(coords[0]))

    if not geometrias:
        raise ValueError("Nenhuma geometria encontrada no KML.")

    return geometrias


def _parsear_coords_kml(coords_raw: str):
    """Converte string KML (lon,lat,alt) em lista de tuplas (lon, lat)."""
    coords = []
    for item in coords_raw.strip().split():
        partes = item.strip().split(",")
        if len(partes) >= 2:
            try:
                coords.append((float(partes[0]), float(partes[1])))
            except ValueError:
                continue
    return coords


# ── UTILITÁRIOS ───────────────────────────────────────────────────────────────

def obter_bbox(geometrias: list):
    """Retorna (minx, miny, maxx, maxy) da coleção de geometrias."""
    return GeometryCollection(geometrias).bounds


def obter_centroide(geometrias: list):
    """Retorna (lon, lat) do centroide da coleção."""
    c = GeometryCollection(geometrias).centroid
    return (c.x, c.y)


# ── TESTE ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python parser.py <arquivo>")
        sys.exit(1)

    arquivo = sys.argv[1]
    print(f"\nCarregando: {arquivo}")

    geometrias, tipo, src = carregar_arquivo(arquivo)
    bbox = obter_bbox(geometrias)
    centroide = obter_centroide(geometrias)

    print(f"Tipo:          {tipo.upper()}")
    print(f"SRC original:  {src}")
    print(f"SRC saída:     WGS84 (EPSG:4326)")
    print(f"Geometrias:    {len(geometrias)}")
    print(f"Tipos:         {[g.geom_type for g in geometrias]}")
    print(f"BBox:          {bbox}")
    print(f"Centroide:     Lon {centroide[0]:.6f} | Lat {centroide[1]:.6f}")
    print("\n✓ Parser OK — geometrias em WGS84 prontas para uso.")
    