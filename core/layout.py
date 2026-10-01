"""
GeoMapa Express - layout.py v5
Layout profissional padrão ABNT/licenciamento ambiental MS.
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D
import geopandas as gpd
from pathlib import Path
from datetime import datetime
from pyproj import Transformer
import contextily as ctx
from shapely.geometry import GeometryCollection
import numpy as np
import math
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.parser import carregar_arquivo
from core.localizacao import identificar_municipio

# ── PALETA ────────────────────────────────────────────────────────────────────
COR_CABECALHO  = "#1b3622"
COR_VERDE_MED  = "#2e7d32"
COR_BORDA      = "#2d4a30"
COR_TEXTO      = "#1a1a1a"
COR_TEXTO_CINZA = "#555555"
COR_DESTAQUE   = "#cc0000"
COR_FUNDO      = "#ffffff"
COR_LINHA      = "#b0bec5"

BASE_DIR        = Path(__file__).resolve().parent.parent
MUNICIPIOS_PATH = BASE_DIR / "dados" / "municipios_ms.geojson"
CAMPO_MUN       = "NM_MUN"


def montar_layout(
    geometrias: list,
    nome_empreendimento: str = "Área de Estudo",
    responsavel: str = "",
    municipio: str = "",
    observacoes: str = "",
    caminho_saida: str = "mapa_localizacao.pdf",
    basemap: str = "satelite",
):
    if not municipio:
        municipio = identificar_municipio(geometrias)

    fig = plt.figure(figsize=(16.54, 11.69), facecolor="white")

    # ── BORDA ÚNICA SIMPLES ───────────────────────────────────────────────────
    fig.add_artist(mpatches.FancyBboxPatch(
        (0.008, 0.008), 0.984, 0.984,
        boxstyle="square,pad=0", linewidth=2.0,
        edgecolor=COR_BORDA, facecolor="none",
        transform=fig.transFigure, zorder=10, clip_on=False,
    ))

    # ── GRID MASTER ───────────────────────────────────────────────────────────
    gs = gridspec.GridSpec(
        3, 1, figure=fig,
        height_ratios=[0.09, 0.845, 0.065],
        hspace=0.012,
        left=0.018, right=0.982,
        top=0.968, bottom=0.032,
    )

    # ── CABEÇALHO ─────────────────────────────────────────────────────────────
    ax_cab = fig.add_subplot(gs[0])
    ax_cab.set_facecolor(COR_CABECALHO)
    ax_cab.set_axis_off()

    # Barra lateral verde
    ax_cab.plot([0.006, 0.006], [0.08, 0.92], color="#4caf50", linewidth=6,
                transform=ax_cab.transAxes, clip_on=False)

    # Título principal
    ax_cab.text(0.025, 0.62,
        "MAPA DE LOCALIZAÇÃO DO EMPREENDIMENTO",
        transform=ax_cab.transAxes,
        ha="left", va="center",
        fontsize=17, fontweight="bold", color="white",
        fontfamily="DejaVu Sans")

    # Subtítulo
    ax_cab.text(0.025, 0.20,
        nome_empreendimento.upper(),
        transform=ax_cab.transAxes,
        ha="left", va="center",
        fontsize=11, color="#a5d6a7",
        fontfamily="DejaVu Sans")

    # Data no canto direito
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    ax_cab.text(0.988, 0.55,
        f"Emitido em\n{data_hoje}",
        transform=ax_cab.transAxes,
        ha="right", va="center",
        fontsize=9, color="#cccccc",
        linespacing=1.6)

    # ── CORPO ─────────────────────────────────────────────────────────────────
    gs_corpo = gridspec.GridSpecFromSubplotSpec(
        1, 2, subplot_spec=gs[1],
        width_ratios=[0.685, 0.315],
        wspace=0.015,
    )
    ax_mapa = fig.add_subplot(gs_corpo[0])

    gs_dir = gridspec.GridSpecFromSubplotSpec(
        3, 1, subplot_spec=gs_corpo[1],
        height_ratios=[0.40, 0.22, 0.38],
        hspace=0.018,
    )
    ax_loc  = fig.add_subplot(gs_dir[0])
    ax_leg  = fig.add_subplot(gs_dir[1])
    ax_info = fig.add_subplot(gs_dir[2])

    # ── MAPA PRINCIPAL ────────────────────────────────────────────────────────
    _mapa_principal(ax_mapa, geometrias, basemap)

    # ── MAPA DE LOCALIZAÇÃO ───────────────────────────────────────────────────
    _mapa_localizacao(ax_loc, geometrias, municipio)

    # ── LEGENDA ───────────────────────────────────────────────────────────────
    _legenda(ax_leg)

    # ── INFORMAÇÕES TÉCNICAS ──────────────────────────────────────────────────
    _quadro_info(ax_info, municipio, responsavel, observacoes, data_hoje)

    # ── RODAPÉ ────────────────────────────────────────────────────────────────
    ax_rod = fig.add_subplot(gs[2])
    ax_rod.set_facecolor(COR_CABECALHO)
    ax_rod.set_axis_off()
    ax_rod.text(0.012, 0.5,
        "SRC: SIRGAS 2000  |  Coordenadas Geográficas WGS84 (EPSG:4326)  |  "
        "Fontes: IBGE · IMASUL/SEMADESC · Esri World Imagery · OpenStreetMap",
        transform=ax_rod.transAxes,
        ha="left", va="center", fontsize=8, color="#b0bec5")
    ax_rod.text(0.988, 0.5,
        "GeoMapa Express",
        transform=ax_rod.transAxes,
        ha="right", va="center", fontsize=8, color="#b0bec5")

    # ── SALVAR ────────────────────────────────────────────────────────────────
    fig.savefig(caminho_saida, dpi=250, bbox_inches="tight",
                facecolor="white", format="pdf")
    png = caminho_saida.replace(".pdf", "_preview.png")
    fig.savefig(png, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"OK PDF: {caminho_saida}")
    print(f"OK PNG: {png}")
    return caminho_saida


# ── MAPA PRINCIPAL ────────────────────────────────────────────────────────────

def _mapa_principal(ax, geometrias, basemap):
    from core.mapa import calcular_extent_com_buffer, _bbox_para_poligono
    from matplotlib_scalebar.scalebar import ScaleBar

    gdf = gpd.GeoDataFrame(geometry=geometrias, crs="EPSG:4326")

    bbox   = GeometryCollection(geometrias).bounds
    bbox_b = calcular_extent_com_buffer(bbox, fator=0.22)
    minlon, minlat, maxlon, maxlat = bbox_b

    ax.set_xlim(minlon, maxlon)
    ax.set_ylim(minlat, maxlat)

    # Polígono
    gdf.plot(ax=ax, facecolor="none", edgecolor=COR_DESTAQUE,
             linewidth=2.5, zorder=5)

    # Basemap
    try:
        src = (ctx.providers.Esri.WorldImagery if basemap == "satelite"
               else ctx.providers.Esri.WorldStreetMap)
        ctx.add_basemap(ax, crs="EPSG:4326", source=src,
                        zoom="auto", attribution=False)
    except Exception as e:
        print(f"Basemap: {e}")

    # Grade de coordenadas
    _grade_coordenadas(ax, bbox_b)

    # Norte
    ax.annotate("", xy=(0.965, 0.962), xytext=(0.965, 0.900),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color="white",
                                lw=2.5, mutation_scale=18))
    ax.text(0.965, 0.972, "N", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=14, fontweight="bold",
            color="white",
            bbox=dict(boxstyle="round,pad=0.2", facecolor=COR_CABECALHO,
                      alpha=0.8, edgecolor="none"))

    # Escala em km (reprojetando para métrico usando buffer para evitar colisão em pontos)
    from shapely.geometry import box
    gdf_buffer = gpd.GeoDataFrame(geometry=[box(*bbox_b)], crs="EPSG:4326")
    bounds = gdf_buffer.to_crs(epsg=3857).total_bounds
    largura_m = bounds[2] - bounds[0]
    largura_graus = maxlon - minlon
    m_por_grau = largura_m / largura_graus if largura_graus > 0 else 111000

    _escala_grafica_km(ax, minlon, minlat, maxlon, maxlat, m_por_grau)

    _borda_ax(ax)


def _grade_coordenadas(ax, bbox):
    minlon, minlat, maxlon, maxlat = bbox
    span = max(maxlon - minlon, maxlat - minlat)

    if span > 2.0:   iv = 1.0
    elif span > 0.5: iv = 0.25
    elif span > 0.1: iv = 0.05
    else:            iv = 0.01

    lons = np.arange(math.ceil(minlon/iv)*iv, maxlon+iv, iv)
    lats = np.arange(math.ceil(minlat/iv)*iv, maxlat+iv, iv)

    lons_ok = [l for l in lons if minlon <= l <= maxlon]
    lats_ok = [l for l in lats if minlat <= l <= maxlat]

    ax.set_xticks(lons_ok)
    ax.set_yticks(lats_ok)
    ax.set_xticklabels([_gms(l, "lon") for l in lons_ok],
                       fontsize=8.5, color=COR_TEXTO, fontfamily="monospace")
    ax.set_yticklabels([_gms(l, "lat") for l in lats_ok],
                       fontsize=8.5, color=COR_TEXTO, fontfamily="monospace",
                       rotation=90, va="center")
    ax.tick_params(axis="both", direction="out", top=True, right=True,
                   colors=COR_BORDA, length=5, width=0.9, labelsize=8.5)
    ax.grid(True, color="white", linestyle="--", linewidth=0.5, alpha=0.5, zorder=4)
    for sp in ax.spines.values():
        sp.set_edgecolor(COR_BORDA)
        sp.set_linewidth(1.2)
        sp.set_visible(True)


def _escala_grafica_km(ax, minlon, minlat, maxlon, maxlat, m_por_grau):
    """Escala gráfica manual em km, posicionada no canto inferior esquerdo."""
    span_lon = maxlon - minlon
    span_lat = maxlat - minlat

    # Calcula distância representativa (~20% da largura)
    dist_alvo_m = span_lon * m_por_grau * 0.20

    # Arredonda para número bonito
    mag = 10 ** math.floor(math.log10(dist_alvo_m))
    for mult in [1, 2, 5, 10, 20, 25, 50, 100, 200, 500]:
        if mag * mult >= dist_alvo_m * 0.5:
            dist_km = mag * mult / 1000
            dist_graus = (mag * mult) / m_por_grau
            break
    else:
        dist_km = round(dist_alvo_m / 1000)
        dist_graus = dist_alvo_m / m_por_grau

    # Posição da escala
    x0 = minlon + span_lon * 0.04
    y0 = minlat + span_lat * 0.04
    x1 = x0 + dist_graus

    yb = y0 + span_lat * 0.012  # altura da barra

    # Barra bicolor (preto/branco alternado)
    ax.add_patch(Rectangle((x0, y0), dist_graus/2, yb-y0,
                 facecolor="black", edgecolor="black", linewidth=0.5, zorder=8))
    ax.add_patch(Rectangle((x0+dist_graus/2, y0), dist_graus/2, yb-y0,
                 facecolor="white", edgecolor="black", linewidth=0.5, zorder=8))

    # Fundo branco atrás dos textos
    pad_x = span_lon * 0.005
    pad_y = span_lat * 0.005
    ax.add_patch(Rectangle(
        (x0 - pad_x, y0 - span_lat*0.05),
        dist_graus + 2*pad_x, yb - y0 + span_lat*0.06,
        facecolor="white", alpha=0.6, edgecolor="none", zorder=7
    ))

    # Rótulos
    fs = 8
    ax.text(x0, y0 - span_lat*0.018, "0",
            ha="center", va="top", fontsize=fs, color="black",
            fontweight="bold", zorder=9)
    ax.text(x1, y0 - span_lat*0.018, f"{dist_km:.0f} km",
            ha="center", va="top", fontsize=fs, color="black",
            fontweight="bold", zorder=9)


# ── MAPA DE LOCALIZAÇÃO ───────────────────────────────────────────────────────

def _mapa_localizacao(ax, geometrias, municipio):
    """Mapa municipal com borda, norte, escala e legenda próprios."""
    ax.set_facecolor("#eef5ee")

    if not MUNICIPIOS_PATH.exists():
        ax.set_axis_off()
        ax.text(0.5, 0.5, "municipios_ms.geojson\nnão encontrado",
                ha="center", va="center", transform=ax.transAxes,
                fontsize=9, color="gray")
        return

    gdf_muns = gpd.read_file(MUNICIPIOS_PATH)

    # Todos os municípios
    gdf_muns.plot(ax=ax, facecolor="#d4e8d4", edgecolor="#888888",
                  linewidth=0.4, zorder=1)

    # Município destacado
    gdf_mun = gpd.GeoDataFrame()
    if municipio:
        gdf_mun = gdf_muns[gdf_muns[CAMPO_MUN].str.upper() == municipio.upper()]
        if not gdf_mun.empty:
            gdf_mun.plot(ax=ax, facecolor="#4caf50", edgecolor="#1b5e20",
                         linewidth=1.2, zorder=2)
            b = gdf_mun.total_bounds
            dx = (b[2]-b[0]) * 0.4
            dy = (b[3]-b[1]) * 0.4
            ax.set_xlim(b[0]-dx, b[2]+dx)
            ax.set_ylim(b[1]-dy, b[3]+dy)

    # Área de estudo
    gdf_area = gpd.GeoDataFrame(geometry=geometrias, crs="EPSG:4326")
    gdf_area.plot(ax=ax, facecolor="none", edgecolor=COR_DESTAQUE,
                  linewidth=2.0, zorder=5)

    ax.set_axis_off()

    # Título do painel
    ax.set_title("LOCALIZAÇÃO NO ESTADO — MATO GROSSO DO SUL",
                 fontsize=9, fontweight="bold", color=COR_CABECALHO,
                 pad=6, loc="left")

    # Borda do painel
    _borda_ax(ax)

    # Norte
    ax.annotate("", xy=(0.94, 0.96), xytext=(0.94, 0.87),
                xycoords="axes fraction", textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>", color=COR_CABECALHO,
                                lw=1.8, mutation_scale=13))
    ax.text(0.94, 0.97, "N", transform=ax.transAxes,
            ha="center", va="bottom", fontsize=10, fontweight="bold",
            color=COR_CABECALHO)

    # Escala simples no mapa de localização
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    span_x = xlim[1] - xlim[0]
    span_y = ylim[1] - ylim[0]

    # Barra de escala simples (50 km estimado)
    sc_graus = span_x * 0.25
    sc_km    = round(sc_graus * 111)
    x0s = xlim[0] + span_x * 0.05
    y0s = ylim[0] + span_y * 0.04
    ax.plot([x0s, x0s + sc_graus], [y0s, y0s],
            color=COR_CABECALHO, linewidth=2.5, zorder=6, solid_capstyle="butt")
    ax.plot([x0s, x0s], [y0s - span_y*0.01, y0s + span_y*0.01],
            color=COR_CABECALHO, linewidth=1.5, zorder=6)
    ax.plot([x0s+sc_graus, x0s+sc_graus],
            [y0s - span_y*0.01, y0s + span_y*0.01],
            color=COR_CABECALHO, linewidth=1.5, zorder=6)
    ax.text(x0s + sc_graus/2, y0s - span_y*0.035,
            f"≈ {sc_km} km",
            ha="center", va="top", fontsize=7, color=COR_CABECALHO,
            fontweight="bold", zorder=6)

    # Legenda do mapa de localização
    leg_x = xlim[0] + span_x * 0.04
    leg_y = ylim[0] + span_y * 0.18

    ax.add_patch(Rectangle(
        (leg_x, leg_y + span_y*0.04), span_x*0.07, span_y*0.045,
        facecolor="#4caf50", edgecolor="#1b5e20", linewidth=1.0, zorder=6
    ))
    ax.text(leg_x + span_x*0.09, leg_y + span_y*0.062,
            municipio or "Município", fontsize=7, va="center",
            color=COR_TEXTO, zorder=6)

    ax.plot([leg_x, leg_x + span_x*0.07],
            [leg_y + span_y*0.01, leg_y + span_y*0.01],
            color=COR_DESTAQUE, linewidth=2.0, zorder=6)
    ax.text(leg_x + span_x*0.09, leg_y + span_y*0.01,
            "Área de Estudo", fontsize=7, va="center",
            color=COR_TEXTO, zorder=6)


# ── LEGENDA PRINCIPAL ─────────────────────────────────────────────────────────

def _legenda(ax):
    ax.set_facecolor(COR_FUNDO)
    ax.set_axis_off()
    _borda_ax(ax)

    # Cabeçalho verde
    ax.add_patch(Rectangle((0, 0.72), 1, 0.28,
                 facecolor=COR_CABECALHO, transform=ax.transAxes,
                 clip_on=True, zorder=1))
    ax.text(0.04, 0.86, "LEGENDA", transform=ax.transAxes,
            fontsize=11, fontweight="bold", color="white", va="center", zorder=2)

    # Símbolo área de estudo
    rect = Rectangle((0.04, 0.36), 0.15, 0.24,
                     linewidth=2.5, edgecolor=COR_DESTAQUE,
                     facecolor="none", transform=ax.transAxes)
    ax.add_patch(rect)
    ax.text(0.24, 0.48, "Área de Estudo / Empreendimento",
            transform=ax.transAxes,
            fontsize=9.5, va="center", color=COR_TEXTO, fontweight="bold")

    # SRC
    ax.plot([0.03, 0.97], [0.26, 0.26], transform=ax.transAxes,
            color=COR_LINHA, linewidth=0.7, clip_on=False)
    ax.text(0.04, 0.20, "SRC:  SIRGAS 2000 / WGS84  (EPSG:4326)",
            transform=ax.transAxes,
            fontsize=8.5, color=COR_TEXTO_CINZA, va="center")

    # Fontes
    ax.plot([0.03, 0.97], [0.10, 0.10], transform=ax.transAxes,
            color=COR_LINHA, linewidth=0.7, clip_on=False)
    ax.text(0.04, 0.04, "Fontes: IMASUL/SEMADESC · IBGE · Esri · OSM",
            transform=ax.transAxes,
            fontsize=8, color=COR_TEXTO_CINZA, va="center", style="italic")


# ── QUADRO DE INFORMAÇÕES ─────────────────────────────────────────────────────

def _quadro_info(ax, municipio, responsavel, observacoes, data_hoje):
    ax.set_facecolor(COR_FUNDO)
    ax.set_axis_off()
    _borda_ax(ax)

    # Cabeçalho verde
    ax.add_patch(Rectangle((0, 0.88), 1, 0.12,
                 facecolor=COR_CABECALHO, transform=ax.transAxes,
                 clip_on=True, zorder=1))
    ax.text(0.04, 0.94, "INFORMAÇÕES TÉCNICAS",
            transform=ax.transAxes,
            fontsize=10, fontweight="bold", color="white", va="center", zorder=2)

    campos = [
        ("Município / UF",       f"{municipio} / MS" if municipio else "— / MS"),
        ("Estado",               "Mato Grosso do Sul"),
        ("Datum / Projeção",     "SIRGAS 2000 · Geog. WGS84"),
        ("Responsável Técnico",  responsavel or "—"),
        ("Data de Emissão",      data_hoje),
    ]
    if observacoes:
        campos.append(("Observações", observacoes))

    y = 0.83
    passo = 0.155
    for label, valor in campos:
        ax.text(0.04, y, label,
                transform=ax.transAxes,
                fontsize=8, color=COR_TEXTO_CINZA, va="top", fontweight="bold")
        ax.text(0.04, y - 0.065, valor,
                transform=ax.transAxes,
                fontsize=9.5, color=COR_TEXTO, va="top")
        ax.plot([0.03, 0.97], [y - passo + 0.01, y - passo + 0.01],
                transform=ax.transAxes,
                color="#e0e0e0", linewidth=0.6, clip_on=False)
        y -= passo


# ── UTILITÁRIOS ───────────────────────────────────────────────────────────────

def _gms(valor: float, tipo: str) -> str:
    neg = valor < 0
    v = abs(valor)
    g = int(v)
    md = (v - g) * 60
    m = int(md)
    s = round((md - m) * 60)
    if s == 60: s, m = 0, m + 1
    if m == 60: m, g = 0, g + 1
    h = ("S" if neg else "N") if tipo == "lat" else ("O" if neg else "L")
    return f"{g}°{m:02d}'{s:02d}\"{h}"


def _borda_ax(ax):
    for sp in ax.spines.values():
        sp.set_edgecolor(COR_BORDA)
        sp.set_linewidth(1.2)
        sp.set_visible(True)


# ── EXECUÇÃO ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python layout.py <arquivo.geojson>")
        sys.exit(1)

    geometrias, tipo, src = carregar_arquivo(sys.argv[1])
    montar_layout(
        geometrias=geometrias,
        nome_empreendimento="Limite Municipal — Bonito (MS)",
        responsavel="Peterson S.",
        observacoes="",
        caminho_saida="mapa_localizacao.pdf",
        basemap="osm",
    )
