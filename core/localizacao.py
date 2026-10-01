"""
GeoMapa Express - localizacao.py
Renderiza o mapa de localização do MS com o município destacado e identifica as cidades.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
from shapely.geometry import GeometryCollection
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_ESTADO = BASE_DIR / "dados" / "estado_ms.geojson"
CAMINHO_MUNICIPIOS = BASE_DIR / "dados" / "municipios_ms.geojson"
CAMPO_MUNICIPIO = "NM_MUN"


def identificar_municipio(geometrias: list, caminho_municipios: str = None) -> str:
    """Função legada: Retorna apenas o primeiro município."""
    if caminho_municipios is None: caminho_municipios = str(CAMINHO_MUNICIPIOS)
    if not Path(caminho_municipios).exists(): return ""
    try:
        gdf_municipios = gpd.read_file(caminho_municipios)
        gdf_area = gpd.GeoDataFrame(geometry=geometrias, crs="EPSG:4326")
        if gdf_municipios.crs != gdf_area.crs:
            gdf_municipios = gdf_municipios.to_crs(gdf_area.crs)
        join = gpd.sjoin(gdf_area, gdf_municipios, how="left", predicate="intersects")
        if not join.empty and CAMPO_MUNICIPIO in join.columns:
            muns = join[CAMPO_MUNICIPIO].dropna()
            if not muns.empty: return str(muns.iloc[0])
    except: pass
    return ""

def identificar_municipios(gdf_area, caminho_municipios: str = None) -> list:
    """Função nova: Retorna lista com todos os municípios cruzados pela área."""
    if caminho_municipios is None: caminho_municipios = str(CAMINHO_MUNICIPIOS)
    if not Path(caminho_municipios).exists(): return []
    try:
        gdf_municipios = gpd.read_file(caminho_municipios)
        if gdf_municipios.crs != gdf_area.crs:
            gdf_municipios = gdf_municipios.to_crs(gdf_area.crs)
        join = gpd.sjoin(gdf_area, gdf_municipios, how="inner", predicate="intersects")
        if CAMPO_MUNICIPIO in join.columns:
            muns = join[CAMPO_MUNICIPIO].dropna().unique().tolist()
            return [str(m).title() for m in muns]
    except: pass
    return []


def renderizar_mapa_estado(geometrias: list, ax, caminho_estado: str = None, caminho_municipios: str = None):
    if caminho_estado is None: caminho_estado = str(CAMINHO_ESTADO)
    if caminho_municipios is None: caminho_municipios = str(CAMINHO_MUNICIPIOS)

    if Path(caminho_estado).exists():
        gdf_estado = gpd.read_file(caminho_estado)
        gdf_estado.plot(ax=ax, facecolor="#2d6a2d", edgecolor="white", linewidth=0.8, zorder=1)

    if Path(caminho_municipios).exists():
        gdf_municipios = gpd.read_file(caminho_municipios)
        gdf_municipios.plot(ax=ax, facecolor="none", edgecolor="white", linewidth=0.3, zorder=2)

    colecao = GeometryCollection(geometrias)
    centroide = colecao.centroid
    gdf_area = gpd.GeoDataFrame(geometry=[colecao.envelope], crs="EPSG:4326")
    gdf_area.plot(ax=ax, facecolor="none", edgecolor="#FF0000", linewidth=1.5, zorder=5)
    ax.plot(centroide.x, centroide.y, marker="*", color="#FF0000", markersize=10, zorder=6)
    
    ax.set_axis_off()
    ax.set_title("Localização no Estado", fontsize=7, pad=3, color="white",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a1a", edgecolor="none"))


def renderizar_mapa_municipio(geometrias: list, ax, nome_municipio: str = "", caminho_municipios: str = None):
    if caminho_municipios is None: caminho_municipios = str(CAMINHO_MUNICIPIOS)

    if not Path(caminho_municipios).exists():
        ax.set_axis_off()
        return

    gdf_municipios = gpd.read_file(caminho_municipios)
    if nome_municipio:
        gdf_mun = gdf_municipios[gdf_municipios[CAMPO_MUNICIPIO].str.upper() == nome_municipio.upper()]
    else:
        gdf_mun = gpd.GeoDataFrame()

    gdf_municipios.plot(ax=ax, facecolor="#c8e6c9", edgecolor="#555555", linewidth=0.4, zorder=1)

    if not gdf_mun.empty:
        gdf_mun.plot(ax=ax, facecolor="#66bb6a", edgecolor="#222222", linewidth=1.0, zorder=2)
        bounds = gdf_mun.total_bounds
        dx = (bounds[2] - bounds[0]) * 0.3
        dy = (bounds[3] - bounds[1]) * 0.3
        ax.set_xlim(bounds[0] - dx, bounds[2] + dx)
        ax.set_ylim(bounds[1] - dy, bounds[3] + dy)

    gdf_area = gpd.GeoDataFrame(geometry=geometrias, crs="EPSG:4326")
    gdf_area.plot(ax=ax, facecolor="none", edgecolor="#CC0000", linewidth=1.5, zorder=5)

    ax.set_axis_off()
    titulo = f"Município: {nome_municipio}" if nome_municipio else "Localização Municipal"
    ax.set_title(titulo, fontsize=7, pad=3, color="white",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a1a", edgecolor="none"))
