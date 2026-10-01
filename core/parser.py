"""
GeoMapa Express - parser.py
Responsabilidade única: ler qualquer arquivo geoespacial,
detectar o SRC, reprojetar para WGS84 e retornar geometrias Shapely prontas.
"""

import json
import re
import zipfile
import tempfile
from pathlib import Path
from shapely.geometry import shape, GeometryCollection

# ── ENTRADA PÚBLICA ───────────────────────────────────────────────────────────

def carregar_arquivo(caminho: str):
    path = Path(caminho)
    ext  = path.suffix.lower()

    if ext in (".geojson", ".json"):
        gdf = _ler_com_geopandas(caminho)
        src = str(gdf.crs) if gdf.crs else "EPSG:4326"
        gdf = _garantir_wgs84(gdf)
        return list(gdf.geometry), "geojson", src

    elif ext == ".kml":
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


def _garantir_wgs84(gdf):
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
        return gdf
    if gdf.crs.to_epsg() == 4326:
        return gdf
    return gdf.to_crs(epsg=4326)


def _ler_com_geopandas(caminho: str):
    import geopandas as gpd
    gdf = gpd.read_file(caminho)
    if gdf.empty:
        raise ValueError("Arquivo carregado mas nenhuma feição encontrada.")
    return gdf


def _ler_shapefile_zip(caminho: str):
    import geopandas as gpd
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(caminho, "r") as z:
            z.extractall(tmpdir)
        shp_files = list(Path(tmpdir).glob("**/*.shp"))
        if not shp_files:
            raise ValueError("Nenhum arquivo .shp encontrado dentro do .zip.")
        gdf = gpd.read_file(str(shp_files[0]))
        src = str(gdf.crs) if gdf.crs else "desconhecido"
    return gdf, src


def _ler_kmz(caminho: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(caminho, "r") as z:
            z.extractall(tmpdir)
        kml_files = list(Path(tmpdir).glob("**/*.kml"))
        if not kml_files:
            raise ValueError("Nenhum arquivo KML encontrado dentro do KMZ.")
        return _ler_kml(str(kml_files[0]))


def _ler_kml(caminho: str):
    with open(caminho, encoding="utf-8") as f:
        conteudo = f.read()

    geometrias = []
    for coords_raw in re.findall(r"<Polygon>.*?<coordinates>(.*?)</coordinates>.*?</Polygon>", conteudo, re.DOTALL):
        coords = _parsear_coords_kml(coords_raw)
        if len(coords) >= 3:
            from shapely.geometry import Polygon
            geometrias.append(Polygon(coords))

    for coords_raw in re.findall(r"<LineString>.*?<coordinates>(.*?)</coordinates>.*?</LineString>", conteudo, re.DOTALL):
        coords = _parsear_coords_kml(coords_raw)
        if len(coords) >= 2:
            from shapely.geometry import LineString
            geometrias.append(LineString(coords))

    for coords_raw in re.findall(r"<Point>.*?<coordinates>(.*?)</coordinates>.*?</Point>", conteudo, re.DOTALL):
        coords = _parsear_coords_kml(coords_raw)
        if coords:
            from shapely.geometry import Point
            geometrias.append(Point(coords[0]))

    if not geometrias:
        raise ValueError("Nenhuma geometria encontrada no KML.")

    return geometrias


def _parsear_coords_kml(coords_raw: str):
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
    return GeometryCollection(geometrias).bounds


def obter_centroide(geometrias):
    if hasattr(geometrias, "unary_union"):
        c = geometrias.unary_union.centroid
        return (c.x, c.y)
    c = GeometryCollection(geometrias).centroid
    return (c.x, c.y)


# ── NOVAS FUNÇÕES PARA O RELATORIO REVISADO ───────────────────────────────────

def carregar_geodataframe(caminho: str):
    import geopandas as gpd
    geos, tipo, src = carregar_arquivo(caminho)
    gdf = gpd.GeoDataFrame(geometry=geos, crs="EPSG:4326")
    return gdf, tipo, src


def obter_area_hectares(gdf) -> float:
    gdf_area = gdf.to_crs("EPSG:6933")
    area_m2 = gdf_area.geometry.area.sum()
    return float(area_m2 / 10000.0)


def obter_ponto_destino(gdf, coord_entrada=None):
    if coord_entrada:
        return float(coord_entrada[1]), float(coord_entrada[0])
    c = gdf.geometry.unary_union.centroid
    return (c.x, c.y)


def validar_coordenada(lat, lon):
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError(f"Coordenada inválida: Lat {lat}, Lon {lon}")
    return True
