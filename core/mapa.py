"""
GeoMapa Express - app.py (Revisão Ouro)
"""

import streamlit as st
import tempfile
import os
import sys
from pathlib import Path
import folium
from streamlit_folium import st_folium
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.parser import carregar_geodataframe, obter_centroide
from core.localizacao import identificar_municipios
from core.relatorio_completo import criar_relatorio_unificado

st.set_page_config(page_title="GeoMapa Express", page_icon="🗺️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .main { background-color: #f4f6f4; }
    .header-box { background: linear-gradient(135deg, #1b3622 0%, #2e7d32 100%); padding: 22px 28px; border-radius: 10px; margin-bottom: 22px; text-align: center; }
    .header-box h1 { color: white; font-size: 1.9rem; margin: 0; font-weight: 800; }
    .header-box p  { color: #a5d6a7; font-size: 1rem; margin: 5px 0 0 0; }
    .secao { background: white; border: 1px solid #dde8dd; border-left: 5px solid #1b3622; border-radius: 8px; padding: 18px 20px 10px 20px; margin-bottom: 14px; }
    .secao h4 { color: #1b3622; font-size: 0.92rem; font-weight: 800; letter-spacing: 1.2px; text-transform: uppercase; margin: 0 0 14px 0; }
    .stButton > button { background-color: #1b3622 !important; color: white !important; font-weight: 800 !important; font-size: 1.1rem !important; border-radius: 8px !important; padding: 16px !important; width: 100% !important; margin-top: 8px !important; }
    .stDownloadButton > button { background-color: #2e7d32 !important; color: white !important; font-weight: 700 !important; border-radius: 8px !important; padding: 14px !important; width: 100% !important; margin-top: 10px !important; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="header-box"><h1>🗺️ GeoMapa Express</h1><p>Geração de Pranchas Ambientais Oficiais</p></div>', unsafe_allow_html=True)

ferramenta = st.radio("", ["🚀 Gerador Completo (Prancha IMASUL/Poços)"], horizontal=True, label_visibility="collapsed")
st.markdown("<hr/>", unsafe_allow_html=True)

# Memória Cache (Solução do Apontamento 5: Evita o site engasgar relendo o arquivo)
@st.cache_data(show_spinner=False)
def ler_arquivo_em_cache(bytes_arquivo, nome_arquivo):
    sufixo = Path(nome_arquivo).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
        tmp.write(bytes_arquivo)
        tmp_path = tmp.name
    try:
        return carregar_geodataframe(tmp_path)
    finally:
        if os.path.exists(tmp_path): os.unlink(tmp_path)

if ferramenta == "🚀 Gerador Completo (Prancha IMASUL/Poços)":
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="secao"><h4>① Arquivo da Fazenda / Propriedade</h4>', unsafe_allow_html=True)
        arquivo_area = st.file_uploader("KML / GeoJSON / KMZ / ZIP", type=["kml", "geojson", "json", "zip", "kmz", "gpkg"])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="secao"><h4>② Rota de Acesso</h4>', unsafe_allow_html=True)
        endereco_partida = st.text_input("Endereço de Partida da Rota", placeholder="Ex: Campo Grande, MS")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Guardar Variáveis na Memória (Solução do Apontamento 3: Botão PDF não sumir)
        for key in ["coord_entrada", "coord_sede", "last_click", "pdf_bytes"]:
            if key not in st.session_state: st.session_state[key] = None

        st.markdown('<div class="secao"><h4>③ Coordenadas (Mapa Interativo)</h4>', unsafe_allow_html=True)
        st.caption("Suba o arquivo acima e clique no mapa para capturar a coordenada exata.")
        modo_clique = st.radio("O que marcar com o dedo no mapa?", ["📍 Entrada Principal", "🏡 Sede / Atividade"], horizontal=True)

        lat_centro, lon_centro = -20.4428, -54.6460 # MS
        gdf_interativo = None
        zoom = 6
        
        if arquivo_area:
            try:
                gdf_interativo, _, _ = ler_arquivo_em_cache(arquivo_area.getvalue(), arquivo_area.name)
                lon_centro, lat_centro = obter_centroide(gdf_interativo)
                zoom = 13
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")

        # Guardar Localização do Mapa (Solução do Apontamento 4: O mapa não pula mais pro centro a cada clique)
        if "map_center" not in st.session_state: st.session_state["map_center"] = [lat_centro, lon_centro]
        if "map_zoom" not in st.session_state: st.session_state["map_zoom"] = zoom
        
        if "ultimo_arquivo" not in st.session_state or st.session_state["ultimo_arquivo"] != (arquivo_area.name if arquivo_area else None):
            st.session_state["map_center"] = [lat_centro, lon_centro]
            st.session_state["map_zoom"] = zoom
            st.session_state["ultimo_arquivo"] = arquivo_area.name if arquivo_area else None

        m = folium.Map(location=st.session_state["map_center"], zoom_start=st.session_state["map_zoom"])
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satélite', max_zoom=18
        ).add_to(m)
        
        if gdf_interativo is not None:
            # Filtro das geometrias vazias (Solução do Apontamento 1)
            gdf_filtrado = gdf_interativo[gdf_interativo.geometry.notnull() & ~gdf_interativo.geometry.is_empty]
            if not gdf_filtrado.empty:
                folium.GeoJson(gdf_filtrado, style_function=lambda x: {'color': '#00ff00', 'fillOpacity': 0.1, 'weight': 3}).add_to(m)
            
        if st.session_state["coord_entrada"]:
            folium.Marker(st.session_state["coord_entrada"], tooltip="Entrada", icon=folium.Icon(color='green', icon='info-sign')).add_to(m)
        if st.session_state["coord_sede"]:
            folium.Marker(st.session_state["coord_sede"], tooltip="Sede/Atividade", icon=folium.Icon(color='blue', icon='home')).add_to(m)
            
        map_data = st_folium(m, center=st.session_state["map_center"], zoom=st.session_state["map_zoom"], height=400, returned_objects=["last_clicked", "center", "zoom"])
        
        if map_data:
            if map_data.get("center"): st.session_state["map_center"] = [map_data["center"]["lat"], map_data["center"]["lng"]]
            if map_data.get("zoom"): st.session_state["map_zoom"] = map_data["zoom"]
            
            if map_data.get("last_clicked"):
                lat = map_data["last_clicked"]["lat"]
                lng = map_data["last_clicked"]["lng"]
                if st.session_state["last_click"] != (lat, lng):
                    st.session_state["last_click"] = (lat, lng)
                    if modo_clique == "📍 Entrada Principal":
                        st.session_state["coord_entrada"] = (lat, lng)
                    else:
                        st.session_state["coord_sede"] = (lat, lng)
                    st.rerun()

        c_lat1, c_lon1 = st.columns(2)
        with c_lat1: st.text_input("Lat. Entrada", value=str(st.session_state["coord_entrada"][0]) if st.session_state["coord_entrada"] else "", disabled=True)
        with c_lon1: st.text_input("Lon. Entrada", value=str(st.session_state["coord_entrada"][1]) if st.session_state["coord_entrada"] else "", disabled=True)
        
        c_lat2, c_lon2 = st.columns(2)
        with c_lat2: st.text_input("Lat. Sede", value=str(st.session_state["coord_sede"][0]) if st.session_state["coord_sede"] else "", disabled=True)
        with c_lon2: st.text_input("Lon. Sede", value=str(st.session_state["coord_sede"][1]) if st.session_state["coord_sede"] else "", disabled=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="secao"><h4>④ Cabeçalho do Relatório</h4>', unsafe_allow_html=True)
        prop_nome = st.text_input("Proponente / Fazenda", placeholder="Ex: João da Silva")
        atividade = st.text_input("Atividade", placeholder="Ex: Licenciamento de Poço")
        municipio = st.text_input("Município (Deixe vazio para autodetectar)", placeholder="")
        resp_tecnico = st.text_input("Responsável Técnico")
        crea_tecnico = st.text_input("Registro CREA / CRBio")
        num_processo = st.text_input("Nº Processo (Opcional)")
        obs = st.text_area("Observações (Opcional)")
        st.markdown('</div>', unsafe_allow_html=True)
        
        gerar_completo = st.button("🗺️ GERAR PRANCHA COMPLETA EM PDF", use_container_width=True)

    with col2:
        if gerar_completo:
            if not arquivo_area or not endereco_partida:
                st.warning("⚠️ O Arquivo de Área e o Endereço de Partida são obrigatórios.")
            else:
                try:
                    with st.spinner("⏳ Processando área, traçando rota e montando PDF..."):
                        sufixo = Path(arquivo_area.name).suffix.lower()
                        with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp_kml:
                            tmp_kml.write(arquivo_area.getvalue())
                            tmp_path = tmp_kml.name
                        
                        dados_projeto = {
                            "proponente": prop_nome,
                            "atividade": atividade,
                            "municipio": municipio,
                            "responsavel": resp_tecnico,
                            "crea": crea_tecnico,
                            "processo": num_processo,
                            "observacoes": obs
                        }
                        
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                            pdf_path = tmp_pdf.name
                            
                        criar_relatorio_unificado(tmp_path, endereco_partida, st.session_state["coord_entrada"], st.session_state["coord_sede"], dados_projeto, pdf_path)
                        
                        with open(pdf_path, "rb") as f:
                            st.session_state["pdf_bytes"] = f.read()
                            
                except Exception as e:
                    import traceback
                    st.error(f"❌ Erro na geração: {e}")
                    st.code(traceback.format_exc())
                finally:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path): os.unlink(tmp_path)
                    if 'pdf_path' in locals() and os.path.exists(pdf_path): os.unlink(pdf_path)

        if st.session_state["pdf_bytes"]:
            st.success("✅ Prancha de Localização e Acesso gerada e pronta!")
            st.download_button(
                label="⬇️ BAIXAR PRANCHA (PDF)",
                data=st.session_state["pdf_bytes"],
                file_name="Prancha_Acesso_Localizacao.pdf",
                mime="application/pdf",
                use_container_width=True
            )
