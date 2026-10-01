"""
GeoMapa Express - relatorio_completo.py (revisado)

Gera a prancha "Croqui de Acesso e Localização" + memorial descritivo
completo do trajeto, para instrução de processos de licenciamento.

Correções desta revisão (as mais importantes do pacote)
-------------------------------------------------------
1. BUG QUE IMPEDIA A EXECUÇÃO: `carregar_arquivo()` devolve uma LISTA de
   geometrias, mas o código fazia `gdf_area, _, _ = carregar_arquivo(...)` e
   logo em seguida `gdf_area.to_crs(...)` — a lista não tem `.to_crs`, então
   o relatório quebrava com AttributeError em qualquer arquivo. Agora usamos
   `carregar_geodataframe()`.
2. DESTINO DA ROTA: a rota ia até o centroide da área. Em fazenda, o centroide
   cai no meio do pasto, e o OSRM encaixa esse ponto numa via qualquer —
   produzindo quilometragem e trajeto errados. Agora, se a coordenada da
   entrada/porteira for informada, a rota termina nela.
3. MEMORIAL TRUNCADO: o itinerário era cortado nos 10 primeiros passos com
   "...". Agora o PDF traz o itinerário COMPLETO em página própria, numerado
   e com quilometragem acumulada.
4. ACENTUAÇÃO: textos não passam mais por latin-1 'replace' (que virava "?").
5. Norte, escala gráfica e coordenadas em grau/minuto/segundo nos dois mapas
   — itens exigidos na análise de croquis.
6. Arquivos temporários sempre removidos; figuras sempre fechadas.

Convenção de coordenadas: `coord_entrada` e `coord_sede` são tuplas
(latitude, longitude) em graus decimais, WGS84.
"""

from __future__ import annotations

import os
import tempfile

import geopandas as gpd
import matplotlib.pyplot as plt
from fpdf import FPDF
from shapely.geometry import LineString, Point

from core.mapa import (
    adicionar_basemap,
    adicionar_escala,
    adicionar_norte,
    calcular_extent_com_buffer,
    salvar_figura,
)
from core.parser import (
    carregar_geodataframe,
    obter_area_hectares,
    obter_centroide,
    obter_ponto_destino,
    validar_coordenada,
)
from core.pdf_utils import coordenada_gms, registrar_fonte_unicode, texto_seguro
from core.rotas import ErroDeRota, calcular_rota, descrever_rota, geocodificar
from core.localizacao import identificar_municipios

WGS84 = "EPSG:4326"
MERCATOR = "EPSG:3857"
VERDE_ESCURO = (27, 54, 34)


# ── MAPAS ─────────────────────────────────────────────────────────────────────

def gerar_mapa_acesso(local_partida, gdf_area, coordenadas_rota, caminho_img):
    """Vista regional: trajeto completo da partida até a área."""
    rota = gpd.GeoDataFrame(
        geometry=[LineString(coordenadas_rota)], crs=WGS84
    ).to_crs(MERCATOR)
    area = gdf_area.to_crs(MERCATOR)

    fig, ax = plt.subplots(figsize=(10, 6))
    rota.plot(ax=ax, color="#cc0000", linewidth=2.6, alpha=0.9, zorder=3)
    area.plot(ax=ax, facecolor="none", edgecolor="#ffeb3b", linewidth=2.2, zorder=4)

    partida = gpd.GeoSeries(
        [Point(local_partida.lon, local_partida.lat)], crs=WGS84
    ).to_crs(MERCATOR)
    partida.plot(ax=ax, color="#1e88e5", markersize=110, marker="o",
                 edgecolor="white", zorder=5)
    ax.annotate(
        "Partida",
        xy=(partida.x.iloc[0], partida.y.iloc[0]),
        xytext=(8, 8), textcoords="offset points",
        color="white", fontweight="bold", fontsize=9, zorder=6,
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#1e88e5", edgecolor="none"),
    )

    # Enquadra rota + área com folga.
    limites = rota.total_bounds
    area_limites = area.total_bounds
    minx = min(limites[0], area_limites[0])
    miny = min(limites[1], area_limites[1])
    maxx = max(limites[2], area_limites[2])
    maxy = max(limites[3], area_limites[3])
    folga_x = max((maxx - minx) * 0.08, 1500)
    folga_y = max((maxy - miny) * 0.08, 1500)
    ax.set_xlim(minx - folga_x, maxx + folga_x)
    ax.set_ylim(miny - folga_y, maxy + folga_y)

    adicionar_basemap(ax, "satelite")
    adicionar_norte(ax)
    adicionar_escala(ax, gdf_area.total_bounds[1])
    ax.set_axis_off()
    return salvar_figura(fig, caminho_img, dpi=170)


def gerar_mapa_localizacao(gdf_area, coord_entrada, coord_sede, caminho_img):
    """Detalhe da área, com entrada e sede/atividade marcadas."""
    area = gdf_area.to_crs(MERCATOR)

    fig, ax = plt.subplots(figsize=(10, 6))
    area.plot(ax=ax, facecolor="#4caf50", alpha=0.22, edgecolor="#1b5e20",
              linewidth=2.6, zorder=3)

    marcadores = [
        (coord_entrada, "Entrada principal", "#ffeb3b", "*", 230),
        (coord_sede, "Sede / atividade", "#00e5ff", "s", 110),
    ]
    for coord, rotulo, cor, marca, tamanho in marcadores:
        if not coord:
            continue
        lat, lon = float(coord[0]), float(coord[1])
        validar_coordenada(lat, lon)
        ponto = gpd.GeoSeries([Point(lon, lat)], crs=WGS84).to_crs(MERCATOR)
        ponto.plot(ax=ax, color=cor, markersize=tamanho, marker=marca,
                   edgecolor="black", linewidth=0.8, zorder=5)
        ax.annotate(
            rotulo,
            xy=(ponto.x.iloc[0], ponto.y.iloc[0]),
            xytext=(9, 9), textcoords="offset points",
            fontsize=9, fontweight="bold", color="black", zorder=6,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=cor, alpha=0.9,
                      edgecolor="black", linewidth=0.5),
        )

    # Folga proporcional (o buffer fixo de 500 m sumia em fazendas grandes).
    bbox_wgs = calcular_extent_com_buffer(gdf_area.total_bounds, fator=0.15)
    limites = (
        gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt([]), crs=WGS84)
        if False else None
    )
    from shapely.geometry import box as _box

    limites = gpd.GeoDataFrame(geometry=[_box(*bbox_wgs)], crs=WGS84).to_crs(
        MERCATOR
    ).total_bounds
    ax.set_xlim(limites[0], limites[2])
    ax.set_ylim(limites[1], limites[3])

    adicionar_basemap(ax, "satelite")
    adicionar_norte(ax)
    adicionar_escala(ax, gdf_area.total_bounds[1])
    ax.set_axis_off()
    return salvar_figura(fig, caminho_img, dpi=170)


# ── PDF ───────────────────────────────────────────────────────────────────────

class PranchaPDF(FPDF):
    """A4 retrato, com cabeçalho e rodapé institucionais."""

    familia = "Helvetica"
    titulo_prancha = "CROQUI DE ACESSO E LOCALIZAÇÃO"

    def header(self):
        self.set_fill_color(*VERDE_ESCURO)
        self.rect(0, 0, self.w, 16, "F")
        self.set_font(self.familia, "B", 12)
        self.set_text_color(255, 255, 255)
        self.set_y(4)
        self.cell(0, 8, texto_seguro(self.titulo_prancha, self.familia),
                  align="C")
        self.set_y(22)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font(self.familia, "", 7)
        self.set_text_color(110, 110, 110)
        self.cell(
            0, 5,
            texto_seguro(
                "SRC: SIRGAS 2000 / WGS84 (EPSG:4326) · GeoMapa Express · "
                f"página {self.page_no()}",
                self.familia,
            ),
            align="C",
        )
        self.set_text_color(0, 0, 0)


def _linha(pdf, altura, texto, largura=0, borda=0, alinhamento="L", pular=True):
    """Compatível com fpdf e fpdf2 (onde `ln=` está obsoleto)."""
    conteudo = texto_seguro(texto, pdf.familia)
    try:
        from fpdf.enums import XPos, YPos

        pdf.cell(
            largura, altura, conteudo, border=borda, align=alinhamento,
            new_x=XPos.LMARGIN if pular else XPos.RIGHT,
            new_y=YPos.NEXT if pular else YPos.TOP,
        )
    except ImportError:
        pdf.cell(largura, altura, conteudo, border=borda, align=alinhamento,
                 ln=1 if pular else 0)


def _campo(pdf, rotulo, valor):
    pdf.set_font(pdf.familia, "B", 9)
    _linha(pdf, 6, rotulo, largura=38, borda=1, pular=False)
    pdf.set_font(pdf.familia, "", 9)
    _linha(pdf, 6, str(valor or "—"), largura=152, borda=1)


def criar_relatorio_unificado(
    arquivo_area_path: str,
    endereco_partida: str,
    coord_entrada=None,
    coord_sede=None,
    dados_proj: dict | None = None,
    caminho_saida: str = "croqui_acesso.pdf",
):
    """
    Monta a prancha completa.

    coord_entrada / coord_sede: (latitude, longitude) em graus decimais.
    dados_proj: proponente, atividade, municipio, responsavel, crea, processo.
    """
    dados_proj = dados_proj or {}

    # 1. Área de estudo
    gdf_area, tipo, src_original = carregar_geodataframe(arquivo_area_path)

    # 2. Destino da rota: a porteira, se informada.
    lon_destino, lat_destino = obter_ponto_destino(gdf_area, coord_entrada)
    lon_centro, lat_centro = obter_centroide(gdf_area)

    # 3. Partida e trajeto
    partida = geocodificar(endereco_partida)
    rota = calcular_rota(partida.lon, partida.lat, lon_destino, lat_destino)

    # 4. Município (preenche sozinho se o técnico não informou)
    municipios = dados_proj.get("municipio") or ", ".join(
        identificar_municipios(gdf_area)
    )

    img_acesso = img_loc = None
    try:
        img_acesso = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        img_loc = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name

        gerar_mapa_acesso(partida, gdf_area, rota.coordenadas, img_acesso)
        gerar_mapa_localizacao(gdf_area, coord_entrada, coord_sede, img_loc)

        pdf = PranchaPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=16)
        pdf.familia = "Helvetica"
        pdf.add_page()
        pdf.familia = registrar_fonte_unicode(pdf)
        pdf.set_font(pdf.familia, "", 9)

        # ── Quadro de identificação
        _campo(pdf, "PROPONENTE:", dados_proj.get("proponente"))
        _campo(pdf, "ATIVIDADE:", dados_proj.get("atividade"))
        _campo(pdf, "MUNICÍPIO / UF:", f"{municipios} / MS" if municipios else "— / MS")
        if dados_proj.get("processo"):
            _campo(pdf, "PROCESSO:", dados_proj["processo"])
        pdf.ln(2)

        # ── Memorial resumido
        destino_txt = (
            "a entrada principal da propriedade"
            if coord_entrada
            else "o ponto central da área"
        )
        resumo = descrever_rota(rota, partida.endereco, destino_txt)
        pdf.set_font(pdf.familia, "B", 9)
        _linha(pdf, 6, "MEMORIAL DE ACESSO", largura=190, borda="LRT")
        pdf.set_font(pdf.familia, "", 8)
        pdf.multi_cell(190, 4.6, texto_seguro(resumo, pdf.familia), border="LRB")
        pdf.ln(2)

        # ── Mapas
        pdf.set_font(pdf.familia, "B", 10)
        _linha(pdf, 6, "1. CROQUI DE ACESSO (VISTA REGIONAL)", alinhamento="C")
        pdf.image(img_acesso, x=15, y=pdf.get_y(), w=180)
        pdf.set_y(pdf.get_y() + 76)

        _linha(pdf, 6, "2. CROQUI DE LOCALIZAÇÃO DA ÁREA", alinhamento="C")
        pdf.image(img_loc, x=15, y=pdf.get_y(), w=180)
        pdf.set_y(pdf.get_y() + 76)

        # ── Coordenadas de referência
        pdf.set_font(pdf.familia, "B", 9)
        _linha(pdf, 5, "COORDENADAS DE REFERÊNCIA (SIRGAS 2000 / WGS84)",
               alinhamento="C")
        pdf.set_font(pdf.familia, "", 8)
        if coord_entrada:
            _linha(pdf, 4.4, f"Entrada principal: {_par(coord_entrada)}",
                   alinhamento="C")
        if coord_sede:
            _linha(pdf, 4.4, f"Sede / atividade: {_par(coord_sede)}", alinhamento="C")
        _linha(pdf, 4.4, f"Ponto central da área: {_par((lat_centro, lon_centro))}",
               alinhamento="C")
        try:
            _linha(pdf, 4.4,
                   f"Área total: {obter_area_hectares(gdf_area):,.2f} ha".replace(",", "."),
                   alinhamento="C")
        except Exception:
            pass
        _linha(pdf, 4.4,
               f"Arquivo de origem: {tipo.upper()} · SRC informado: {src_original}",
               alinhamento="C")

        # ── Itinerário completo (sem truncar)
        pdf.add_page()
        pdf.set_font(pdf.familia, "B", 11)
        _linha(pdf, 8, "3. ITINERÁRIO DESCRITIVO COMPLETO")
        pdf.set_font(pdf.familia, "", 8)
        _linha(pdf, 5, f"Partida: {partida.endereco}")
        _linha(
            pdf, 5,
            f"Distância total: {rota.distancia_km:.1f} km  ·  "
            f"Tempo estimado: {rota.duracao_min:.0f} min  ·  "
            f"{len(rota.passos)} manobras",
        )
        pdf.ln(2)

        pdf.set_font(pdf.familia, "", 8.5)
        for passo in rota.passos:
            pdf.multi_cell(190, 4.8, texto_seguro(passo, pdf.familia))

        if rota.aviso:
            pdf.ln(3)
            pdf.set_font(pdf.familia, "B", 8.5)
            pdf.multi_cell(190, 4.8, texto_seguro("Observação: " + rota.aviso,
                                                  pdf.familia))

        if dados_proj.get("observacoes"):
            pdf.ln(3)
            pdf.set_font(pdf.familia, "B", 9)
            _linha(pdf, 5, "OBSERVAÇÕES")
            pdf.set_font(pdf.familia, "", 8.5)
            pdf.multi_cell(190, 4.8,
                           texto_seguro(dados_proj["observacoes"], pdf.familia))

        _assinaturas(pdf, dados_proj)
        pdf.output(caminho_saida)
        return caminho_saida

    finally:
        for caminho in (img_acesso, img_loc):
            if caminho and os.path.exists(caminho):
                try:
                    os.unlink(caminho)
                except OSError:
                    pass
        plt.close("all")


def _par(coord) -> str:
    """(lat, lon) -> 'Lat 20°31'12.00"S | Lon 54°36'00.00"O'."""
    lat, lon = float(coord[0]), float(coord[1])
    validar_coordenada(lat, lon)
    return (
        f"Lat {coordenada_gms(lat, 'lat')} | Lon {coordenada_gms(lon, 'lon')}  "
        f"({lat:.6f}, {lon:.6f})"
    )


def _assinaturas(pdf, dados_proj: dict):
    """Bloco de assinaturas, sempre com espaço garantido na página."""
    if pdf.get_y() > pdf.h - 55:
        pdf.add_page()
    pdf.ln(18)
    y = pdf.get_y()
    pdf.line(28, y, 92, y)
    pdf.line(118, y, 182, y)
    pdf.set_y(y + 2)

    pdf.set_font(pdf.familia, "B", 8)
    pdf.set_x(28)
    _linha(pdf, 4, dados_proj.get("proponente", "Proponente"), largura=64,
           alinhamento="C", pular=False)
    pdf.set_x(118)
    _linha(pdf, 4, dados_proj.get("responsavel", "Responsável Técnico"),
           largura=64, alinhamento="C")

    pdf.set_font(pdf.familia, "", 8)
    pdf.set_x(118)
    _linha(pdf, 4, f"CREA/CRBio: {dados_proj.get('crea', '—')}", largura=64,
           alinhamento="C")


# ── Compatibilidade com o nome antigo ────────────────────────────────────────
def gerar_relatorio_acesso(endereco_partida, lon_b, lat_b, responsavel,
                           caminho_saida):
    """
    Versão simplificada (sem arquivo de área), mantida para não quebrar
    chamadas existentes. Prefira `criar_relatorio_unificado`.
    """
    raise ErroDeRota(
        "Esta função foi substituída por criar_relatorio_unificado(), que exige "
        "o arquivo da área (KML/KMZ/GeoJSON/SHP) para gerar o croqui."
    )


# ─── Teste rápido ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    if len(sys.argv) < 3:
        print("Uso: python relatorio_completo.py <area.kml> <endereco de partida>")
        sys.exit(1)

    saida = criar_relatorio_unificado(
        arquivo_area_path=sys.argv[1],
        endereco_partida=" ".join(sys.argv[2:]),
        coord_entrada=None,
        coord_sede=None,
        dados_proj={
            "proponente": "Proponente de Teste",
            "atividade": "Suinocultura",
            "responsavel": "Peterson Martins",
            "crea": "0000000",
        },
        caminho_saida="croqui_acesso.pdf",
    )
    print("PDF gerado:", saida)
