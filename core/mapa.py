"""
GeoMapa Express - mapa.py
Funções unificadas para desenho (basemap, escala, norte e plotagem).
"""

import matplotlib.pyplot as plt
import contextily as ctx
import geopandas as gpd
from matplotlib_scalebar.scalebar import ScaleBar

BUFFER_FATOR = 0.2

def _bbox_para_poligono(bbox: tuple):
    """Converte bbox (minx, miny, maxx, maxy) em Polygon Shapely."""
    from shapely.geometry import box
    return box(bbox[0], bbox[1], bbox[2], bbox[3])

def calcular_extent_com_buffer(bbox: tuple, fator: float = BUFFER_FATOR):
    """Adiciona folga visual no bounding box."""
    minx, miny, maxx, maxy = bbox
    dx = (maxx - minx) * fator
    dy = (maxy - miny) * fator
    if dx < 0.005: dx = 0.005
    if dy < 0.005: dy = 0.005
    return (minx - dx, miny - dy, maxx + dx, maxy + dy)

def adicionar_basemap(ax, basemap="satelite"):
    """Insere a imagem de satélite ou mapa de ruas como fundo."""
    try:
        if basemap == "satelite":
            ctx.add_basemap(ax, crs="EPSG:3857", source=ctx.providers.Esri.WorldImagery, zoom="auto", attribution=False)
        else:
            ctx.add_basemap(ax, crs="EPSG:3857", source=ctx.providers.OpenStreetMap.Mapnik, zoom="auto", attribution=False)
    except Exception as e:
        print(f"Basemap ignorado (offline ou falha): {e}")

def adicionar_norte(ax, x=0.95, y=0.95, tamanho=0.05):
    """Desenha a seta apontando para o Norte."""
    ax.annotate(
        "", xy=(x, y), xytext=(x, y - tamanho),
        xycoords="axes fraction", textcoords="axes fraction",
        arrowprops=dict(arrowstyle="-|>", color="white", lw=2, mutation_scale=20)
    )
    ax.text(
        x, y + 0.015, "N", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=14, fontweight="bold", color="white",
        bbox=dict(boxstyle="round,pad=0.1", facecolor="black", alpha=0.6, edgecolor="none")
    )

def adicionar_escala(ax, param=None):
    """Adiciona a régua de escala gráfica."""
    scalebar = ScaleBar(
        1, units="m", location="lower left", length_fraction=0.2, 
        height_fraction=0.015, border_pad=0.5, color="white", 
        box_color="black", box_alpha=0.6, font_properties={"size": 9}
    )
    ax.add_artist(scalebar)

def salvar_figura(fig, caminho_img, dpi=170):
    """Salva a imagem e retorna o caminho."""
    fig.savefig(caminho_img, dpi=dpi, bbox_inches="tight", facecolor="white")
    return caminho_img

# --- Retrocompatibilidade com Ferramenta 2 ---
def geometrias_para_gdf(geometrias: list, epsg: int = 4326):
    return gpd.GeoDataFrame(geometry=geometrias, crs=f"EPSG:{epsg}")
