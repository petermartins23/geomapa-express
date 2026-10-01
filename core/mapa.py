"""
GeoMapa Express - mapa.py
Funções unificadas de desenho de mapa e basemaps para os relatórios.
"""

import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
from shapely.geometry import GeometryCollection, box
from matplotlib_scalebar.scalebar import ScaleBar

BUFFER_FATOR = 0.2

def calcular_extent_com_buffer(bbox: tuple, fator: float = BUFFER_FATOR):
    minx, miny, maxx, maxy = bbox
    dx = (maxx - minx) * fator
    dy = (maxy - miny) * fator
    if dx < 0.005: dx = 0.005
    if dy < 0.005: dy = 0.005
    return (minx - dx, miny - dy, maxx + dx, maxy + dy)

def adicionar_basemap(ax, basemap_type="satelite"):
    if basemap_type == "satelite":
        source = ctx.providers.Esri.WorldImagery
    else:
        source = ctx.providers.OpenStreetMap.Mapnik
    ctx.add_basemap(ax, source=source, zoom="auto", attribution=False)

def adicionar_norte(ax, x=0.95, y=0.95, tamanho=0.05):
    ax.annotate("", xy=(x, y), xytext=(x, y - tamanho),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="white", lw=2, mutation_scale=20))
    ax.text(x, y + 0.015, "N", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=14, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.1", facecolor="black", alpha=0.6, edgecolor="none"))

def adicionar_escala(ax, lat_ref=None):
    scalebar = ScaleBar(1, units="m", location="lower left", length_fraction=0.2,
                        height_fraction=0.015, border_pad=0.5, color="white",
                        box_color="black", box_alpha=0.6, font_properties={"size": 9})
    ax.add_artist(scalebar)

def salvar_figura(fig, caminho, dpi=170):
    fig.savefig(caminho, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return caminho

def renderizar_mapa_principal(geometrias: list, titulo: str = "", basemap: str = "satelite"):
    gdf = gpd.GeoDataFrame(geometry=geometrias, crs="EPSG:4326")
    gdf_mercator = gdf.to_crs(epsg=3857)
    bbox_buffer = calcular_extent_com_buffer(GeometryCollection(geometrias).bounds)
    fig, ax = plt.subplots(1, 1, figsize=(12, 9))
    gdf_mercator.plot(ax=ax, facecolor="none", edgecolor="#CC0000", linewidth=2.5, zorder=5)
    
    gdf_buffer_mercator = gpd.GeoDataFrame(geometry=[box(*bbox_buffer)], crs="EPSG:4326").to_crs(epsg=3857)
    bounds = gdf_buffer_mercator.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    
    adicionar_basemap(ax, basemap)
    ax.set_axis_off()
    return fig, ax
