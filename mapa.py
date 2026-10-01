"""
GeoMapa Express - mapa.py
Renderiza a geometria sobre basemap (satélite ou OSM) com zoom automático.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import contextily as ctx
import geopandas as gpd
from shapely.geometry import GeometryCollection
from matplotlib_scalebar.scalebar import ScaleBar
import numpy as np


# Fator de buffer ao redor da área (20% da dimensão)
BUFFER_FATOR = 0.2


def geometrias_para_gdf(geometrias: list, epsg: int = 4326):
    """
    Converte lista de geometrias Shapely em GeoDataFrame.
    """
    gdf = gpd.GeoDataFrame(geometry=geometrias, crs=f"EPSG:{epsg}")
    return gdf


def calcular_extent_com_buffer(bbox: tuple, fator: float = BUFFER_FATOR):
    """
    Adiciona buffer ao bounding box para dar respiro visual ao mapa.
    bbox: (minx, miny, maxx, maxy) em WGS84
    Retorna: (minx, miny, maxx, maxy) com buffer
    """
    minx, miny, maxx, maxy = bbox
    dx = (maxx - minx) * fator
    dy = (maxy - miny) * fator

    # Buffer mínimo para pontos ou áreas muito pequenas
    if dx < 0.005:
        dx = 0.005
    if dy < 0.005:
        dy = 0.005

    return (minx - dx, miny - dy, maxx + dx, maxy + dy)


def renderizar_mapa_principal(geometrias: list, titulo: str = "", basemap: str = "satelite"):
    """
    Renderiza o mapa principal com a área de estudo.
    
    Parâmetros:
        geometrias: lista de geometrias Shapely (WGS84)
        titulo: título do mapa
        basemap: 'satelite' ou 'osm'
    
    Retorna:
        fig, ax do matplotlib
    """
    # Converte para GeoDataFrame em Web Mercator (necessário para tiles)
    gdf = geometrias_para_gdf(geometrias, epsg=4326)
    gdf_mercator = gdf.to_crs(epsg=3857)

    # Calcula bbox com buffer
    bbox_original = GeometryCollection(geometrias).bounds
    bbox_buffer = calcular_extent_com_buffer(bbox_original)

    # Cria GDF auxiliar para definir extent do plot
    gdf_extent = geometrias_para_gdf([
        GeometryCollection(geometrias).envelope
    ], epsg=4326)
    gdf_extent_mercator = gdf_extent.to_crs(epsg=3857)

    # Cria figura
    fig, ax = plt.subplots(1, 1, figsize=(12, 9))

    # Plota a geometria
    gdf_mercator.plot(
        ax=ax,
        facecolor="none",
        edgecolor="#CC0000",
        linewidth=2.5,
        zorder=5
    )

    # Define extent com buffer
    gdf_buffer = geometrias_para_gdf([
        _bbox_para_poligono(bbox_buffer)
    ], epsg=4326).to_crs(epsg=3857)

    bounds = gdf_buffer.total_bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])

    # Adiciona basemap
    try:
        if basemap == "satelite":
            ctx.add_basemap(
                ax,
                crs=gdf_mercator.crs,
                source=ctx.providers.Esri.WorldImagery,
                zoom="auto",
                attribution=False
            )
        else:
            ctx.add_basemap(
                ax,
                crs=gdf_mercator.crs,
                source=ctx.providers.OpenStreetMap.Mapnik,
                zoom="auto",
                attribution=False
            )
    except Exception as e:
        print(f"Aviso: não foi possível carregar basemap ({e}). Continuando sem imagem de fundo.")

    # Remove eixos
    ax.set_axis_off()

    return fig, ax


def adicionar_norte(ax, x=0.95, y=0.95, tamanho=0.05):
    """
    Adiciona seta Norte ao mapa.
    x, y: posição relativa no axes (0 a 1)
    """
    ax.annotate(
        "",
        xy=(x, y),
        xytext=(x, y - tamanho),
        xycoords="axes fraction",
        textcoords="axes fraction",
        arrowprops=dict(
            arrowstyle="-|>",
            color="white",
            lw=2,
            mutation_scale=20
        )
    )
    ax.text(
        x, y + 0.015,
        "N",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=14,
        fontweight="bold",
        color="white",
        bbox=dict(boxstyle="round,pad=0.1", facecolor="black", alpha=0.6, edgecolor="none")
    )


def adicionar_escala(ax, gdf_mercator):
    """
    Adiciona escala gráfica ao mapa.
    """
    scalebar = ScaleBar(
        1,
        units="m",
        location="lower left",
        length_fraction=0.2,
        height_fraction=0.015,
        border_pad=0.5,
        color="white",
        box_color="black",
        box_alpha=0.6,
        font_properties={"size": 9}
    )
    ax.add_artist(scalebar)


def _bbox_para_poligono(bbox: tuple):
    """
    Converte bbox (minx, miny, maxx, maxy) em Polygon Shapely.
    """
    from shapely.geometry import box
    return box(bbox[0], bbox[1], bbox[2], bbox[3])


# ─── Teste rápido ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.parser import carregar_arquivo, obter_bbox

    if len(sys.argv) < 2:
        print("Uso: python mapa.py <arquivo.kml ou arquivo.geojson>")
        sys.exit(1)

    arquivo = sys.argv[1]
    print(f"Carregando: {arquivo}")

    geometrias, tipo, _ = carregar_arquivo(arquivo)
    bbox = obter_bbox(geometrias)
    print(f"BBox: {bbox}")

    print("Renderizando mapa (aguarde download do basemap)...")
    fig, ax = renderizar_mapa_principal(geometrias, titulo="Área de Teste", basemap="satelite")

    adicionar_norte(ax)

    gdf = geometrias_para_gdf(geometrias, epsg=4326).to_crs(epsg=3857)
    adicionar_escala(ax, gdf)

    # Salva PNG de teste
    saida = "teste_mapa.png"
    fig.savefig(saida, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    print(f"\n✓ Mapa gerado: {saida}")
    print("Abra o arquivo para verificar a qualidade visual.")
