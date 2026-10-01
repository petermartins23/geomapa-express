"""
GeoMapa Express - localizacao.py
Renderiza o mapa de localização do MS com o município destacado.
Gera dois mapas: estado completo e município em detalhe.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
from shapely.geometry import GeometryCollection
from pathlib import Path
import os


# Caminhos padrão das camadas base
BASE_DIR = Path(__file__).resolve().parent.parent
CAMINHO_ESTADO = BASE_DIR / "dados" / "estado_ms.geojson"
CAMINHO_MUNICIPIOS = BASE_DIR / "dados" / "municipios_ms.geojson"

# Campo do nome do município
CAMPO_MUNICIPIO = "NM_MUN"


def identificar_municipio(geometrias: list, caminho_municipios: str = None) -> str:
    """
    Identifica automaticamente o município da área de estudo
    por interseção espacial com a camada de municípios do MS.
    Retorna o nome do município ou string vazia se não encontrar.
    """
    if caminho_municipios is None:
        caminho_municipios = str(CAMINHO_MUNICIPIOS)

    if not Path(caminho_municipios).exists():
        return ""

    try:
        gdf_municipios = gpd.read_file(caminho_municipios)
        gdf_area = gpd.GeoDataFrame(
            geometry=geometrias, crs="EPSG:4326"
        )

        # Garante mesmo CRS
        if gdf_municipios.crs != gdf_area.crs:
            gdf_municipios = gdf_municipios.to_crs(gdf_area.crs)

        # Interseção espacial
        join = gpd.sjoin(gdf_area, gdf_municipios, how="left", predicate="intersects")

        if not join.empty and CAMPO_MUNICIPIO in join.columns:
            municipios_validos = join[CAMPO_MUNICIPIO].dropna()
            if not municipios_validos.empty:
                return str(municipios_validos.iloc[0])
    except Exception as e:
        print(f"Aviso: não foi possível identificar município automaticamente ({e})")

    return ""


def renderizar_mapa_estado(geometrias: list, ax, caminho_estado: str = None,
                            caminho_municipios: str = None):
    """
    Renderiza o mapa do estado do MS com a área de estudo destacada.
    Usado no painel de localização (canto inferior).
    """
    if caminho_estado is None:
        caminho_estado = str(CAMINHO_ESTADO)
    if caminho_municipios is None:
        caminho_municipios = str(CAMINHO_MUNICIPIOS)

    # Carrega estado
    if Path(caminho_estado).exists():
        gdf_estado = gpd.read_file(caminho_estado)
        gdf_estado.plot(
            ax=ax,
            facecolor="#2d6a2d",
            edgecolor="white",
            linewidth=0.8,
            zorder=1
        )
    else:
        print(f"Aviso: arquivo do estado não encontrado: {caminho_estado}")

    # Carrega municípios (contorno interno)
    if Path(caminho_municipios).exists():
        gdf_municipios = gpd.read_file(caminho_municipios)
        gdf_municipios.plot(
            ax=ax,
            facecolor="none",
            edgecolor="white",
            linewidth=0.3,
            zorder=2
        )

    # Plota a área de estudo destacada (ponto/bbox centralizado)
    colecao = GeometryCollection(geometrias)
    centroide = colecao.centroid

    # Retângulo vermelho indicando a área
    gdf_area = gpd.GeoDataFrame(
        geometry=[colecao.envelope], crs="EPSG:4326"
    )
    gdf_area.plot(
        ax=ax,
        facecolor="none",
        edgecolor="#FF0000",
        linewidth=1.5,
        zorder=5
    )

    # Ponto vermelho no centroide
    ax.plot(
        centroide.x, centroide.y,
        marker="*",
        color="#FF0000",
        markersize=10,
        zorder=6
    )

    ax.set_axis_off()
    ax.set_title("Localização no Estado", fontsize=7, pad=3, color="white",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a1a", edgecolor="none"))


def renderizar_mapa_municipio(geometrias: list, ax,
                               nome_municipio: str = "",
                               caminho_municipios: str = None):
    """
    Renderiza o mapa do município com a área de estudo destacada.
    Usado no painel de localização (canto inferior).
    """
    if caminho_municipios is None:
        caminho_municipios = str(CAMINHO_MUNICIPIOS)

    if not Path(caminho_municipios).exists():
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Municípios\nnão encontrados",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=8, color="gray")
        return

    gdf_municipios = gpd.read_file(caminho_municipios)

    # Filtra o município da área
    if nome_municipio:
        gdf_mun = gdf_municipios[
            gdf_municipios[CAMPO_MUNICIPIO].str.upper() == nome_municipio.upper()
        ]
    else:
        gdf_mun = gpd.GeoDataFrame()

    # Plota todos os municípios em verde claro (contexto regional)
    gdf_municipios.plot(
        ax=ax,
        facecolor="#c8e6c9",
        edgecolor="#555555",
        linewidth=0.4,
        zorder=1
    )

    # Destaca o município específico
    if not gdf_mun.empty:
        gdf_mun.plot(
            ax=ax,
            facecolor="#66bb6a",
            edgecolor="#222222",
            linewidth=1.0,
            zorder=2
        )

        # Zoom no município com buffer
        bounds = gdf_mun.total_bounds
        dx = (bounds[2] - bounds[0]) * 0.3
        dy = (bounds[3] - bounds[1]) * 0.3
        ax.set_xlim(bounds[0] - dx, bounds[2] + dx)
        ax.set_ylim(bounds[1] - dy, bounds[3] + dy)

    # Plota a área de estudo
    gdf_area = gpd.GeoDataFrame(geometry=geometrias, crs="EPSG:4326")
    gdf_area.plot(
        ax=ax,
        facecolor="none",
        edgecolor="#CC0000",
        linewidth=1.5,
        zorder=5
    )

    ax.set_axis_off()
    titulo = f"Município: {nome_municipio}" if nome_municipio else "Localização Municipal"
    ax.set_title(titulo, fontsize=7, pad=3, color="white",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#1a1a1a", edgecolor="none"))


# ─── Teste rápido ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from core.parser import carregar_arquivo

    if len(sys.argv) < 2:
        print("Uso: python localizacao.py <arquivo.geojson>")
        sys.exit(1)

    arquivo = sys.argv[1]
    geometrias, tipo, _ = carregar_arquivo(arquivo)

    print("Identificando município...")
    municipio = identificar_municipio(geometrias)
    print(f"Município identificado: {municipio or 'não identificado'}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5),
                                    facecolor="#1a1a1a")

    renderizar_mapa_estado(geometrias, ax1)
    renderizar_mapa_municipio(geometrias, ax2, municipio)

    plt.tight_layout()
    saida = "teste_localizacao.png"
    fig.savefig(saida, dpi=150, bbox_inches="tight", facecolor="#1a1a1a")
    plt.close()

    print(f"\n✓ Mapa de localização gerado: {saida}")
