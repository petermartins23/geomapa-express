"""
GeoMapa Express - app.py (Index Unificado)
Interface Streamlit. Toda a lógica geoespacial está no core/.
"""

import streamlit as st
import tempfile
import os
import sys
from pathlib import Path
import folium
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.parser import carregar_arquivo, obter_centroide
from core.localizacao import identificar_municipio
from core.rotas import gerar_relatorio_acesso, geocodificar_endereco

st.set_page_config(
    page_title="GeoMapa Express",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .main { background-color: #f4f6f4; }
    .header-box {
        background: linear-gradient(135deg, #1b3622 0%, #2e7d32 100%);
        padding: 22px 28px; border-radius: 10px; margin-bottom: 22px;
        text-align: center;
    }
    .header-box h1 { color: white; font-size: 1.9rem; margin: 0; font-weight: 800; }
    .header-box p  { color: #a5d6a7; font-size: 1rem; margin: 5px 0 0 0; }
    .secao {
        background: white; border: 1px solid #dde8dd;
        border-left: 5px solid #1b3622; border-radius: 8px;
        padding: 18px 20px 10px 20px; margin-bottom: 14px;
    }
    .secao h4 {
        color: #1b3622; font-size: 0.92rem; font-weight: 800;
        letter-spacing: 1.2px; text-transform: uppercase; margin: 0 0 14px 0;
    }
    .stTextInput label, .stTextArea label,
    .stRadio label, .stFileUploader label {
        font-size: 1rem !important; font-weight: 600 !important; color: #333 !important;
    }
    .stTextInput input, .stTextArea textarea {
        font-size: 1rem !important; padding: 10px 12px !important;
    }
    .stButton > button {
        background-color: #1b3622 !important; color: white !important;
        font-weight: 800 !important; font-size: 1.1rem !important;
        border-radius: 8px !important; border: none !important;
        padding: 16px !important; width: 100% !important;
        letter-spacing: 0.8px !important; margin-top: 8px !important;
    }
    .stButton > button:hover { background-color: #2e7d32 !important; }
    .stDownloadButton > button {
        background-color: #2e7d32 !important; color: white !important;
        font-weight: 700 !important; font-size: 1rem !important;
        border-radius: 8px !important; border: none !important;
        padding: 14px !important; width: 100% !important; margin-top: 10px !important;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h1>🗺️ GeoMapa Express</h1>
    <p>O que você deseja gerar hoje?</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; color: #1b3622;'>Selecione a Ferramenta:</h3>", unsafe_allow_html=True)

# Opções principais 
ferramenta = st.radio(
    "",
    ["🚀 Gerador Completo (Prancha IMASUL/Poços)", "📍 Apenas Mapa de Localização (Básico)"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("<hr/>", unsafe_allow_html=True)

# ==============================================================================
# FERRAMENTA 1: GERADOR COMPLETO (CROQUI + LOCALIZAÇÃO)
# ==============================================================================
if ferramenta == "🚀 Gerador Completo (Prancha IMASUL/Poços)":
    st.markdown("Cria a prancha padrão em PDF contendo o Cabeçalho, Memorial de Acesso, Mapa Regional e Mapa Local detalhado.")
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="secao"><h4>① Arquivo da Fazenda / Propriedade</h4>', unsafe_allow_html=True)
        arquivo_area = st.file_uploader("KML / GeoJSON do Limite do Imóvel", type=["kml", "geojson", "zip"])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="secao"><h4>② Rota de Acesso</h4>', unsafe_allow_html=True)
        endereco_partida = st.text_input("Endereço de Partida da Rota", placeholder="Ex: Campo Grande, MS")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if "coord_entrada" not in st.session_state: st.session_state["coord_entrada"] = None
        if "coord_sede" not in st.session_state: st.session_state["coord_sede"] = None
        if "last_click" not in st.session_state: st.session_state["last_click"] = None

        st.markdown('<div class="secao"><h4>③ Coordenadas Geográficas (Mapa Interativo)</h4>', unsafe_allow_html=True)
        st.caption("Faça o upload do KML acima e **clique no mapa** para preencher as coordenadas automaticamente.")
        
        modo_clique = st.radio("O que você vai marcar com o dedo no mapa agora?", ["📍 Entrada Principal", "🏡 Sede / Atividade"], horizontal=True)

        lat_centro, lon_centro = -20.4428, -54.6460 # MS Default
        gdf_interativo = None
        
        if arquivo_area:
            sufixo = Path(arquivo_area.name).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp_kml2:
                tmp_kml2.write(arquivo_area.getvalue())
                tmp_kml2_path = tmp_kml2.name
            try:
                gdf_interativo, _, _ = carregar_arquivo(tmp_kml2_path)
                lon_centro, lat_centro = obter_centroide(gdf_interativo)
            except:
                pass
            finally:
                if os.path.exists(tmp_kml2_path): os.unlink(tmp_kml2_path)
                
        m = folium.Map(location=[lat_centro, lon_centro], zoom_start=13 if arquivo_area else 6)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Satélite Esri',
            max_zoom=18
        ).add_to(m)
        
        if gdf_interativo is not None:
            gdf_interativo = gdf_interativo[gdf_interativo.geometry.notnull() & ~gdf_interativo.geometry.is_empty]
            if not gdf_interativo.empty:
                folium.GeoJson(gdf_interativo, style_function=lambda x: {'color': '#00ff00', 'fillOpacity': 0.1, 'weight': 3}).add_to(m)
            
        if st.session_state["coord_entrada"]:
            folium.Marker(st.session_state["coord_entrada"], tooltip="Entrada", icon=folium.Icon(color='green', icon='info-sign')).add_to(m)
        if st.session_state["coord_sede"]:
            folium.Marker(st.session_state["coord_sede"], tooltip="Sede/Atividade", icon=folium.Icon(color='blue', icon='home')).add_to(m)
            
        map_data = st_folium(m, height=400, use_container_width=True, returned_objects=["last_clicked"])
        
        if map_data and map_data.get("last_clicked"):
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
        with c_lat1: lat_entrada = st.text_input("Lat. Entrada Principal", value=str(st.session_state["coord_entrada"][0]) if st.session_state["coord_entrada"] else "")
        with c_lon1: lon_entrada = st.text_input("Lon. Entrada Principal", value=str(st.session_state["coord_entrada"][1]) if st.session_state["coord_entrada"] else "")
        
        c_lat2, c_lon2 = st.columns(2)
        with c_lat2: lat_sede = st.text_input("Lat. Sede / Atividade", value=str(st.session_state["coord_sede"][0]) if st.session_state["coord_sede"] else "")
        with c_lon2: lon_sede = st.text_input("Lon. Sede / Atividade", value=str(st.session_state["coord_sede"][1]) if st.session_state["coord_sede"] else "")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="secao"><h4>④ Cabeçalho do Relatório</h4>', unsafe_allow_html=True)
        prop_nome = st.text_input("Nome do Proponente / Fazenda", placeholder="Ex: João da Silva")
        atividade = st.text_input("Atividade", placeholder="Ex: Licenciamento Ambiental de Poço")
        municipio = st.text_input("Município", placeholder="Ex: Bonito - MS")
        resp_tecnico = st.text_input("Responsável Técnico", placeholder="Nome do Técnico")
        crea_tecnico = st.text_input("Registro CREA / CRBio", placeholder="Número do Conselho")
        st.markdown('</div>', unsafe_allow_html=True)
        
        gerar_completo = st.button("🗺️ GERAR PRANCHA COMPLETA EM PDF", use_container_width=True)

    with col2:
        if gerar_completo:
            if not arquivo_area or not endereco_partida:
                st.warning("⚠️ O KML da fazenda e o Endereço de Partida são obrigatórios.")
            else:
                try:
                    with st.spinner("⏳ Processando área, traçando rota e montando a prancha PDF..."):
                        sufixo = Path(arquivo_area.name).suffix.lower()
                        with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp_kml:
                            tmp_kml.write(arquivo_area.read())
                            tmp_path = tmp_kml.name
                        
                        coord_entrada = None
                        if lat_entrada.strip() and lon_entrada.strip():
                            coord_entrada = (float(lat_entrada.replace(",", ".")), float(lon_entrada.replace(",", ".")))
                            
                        coord_sede = None
                        if lat_sede.strip() and lon_sede.strip():
                            coord_sede = (float(lat_sede.replace(",", ".")), float(lon_sede.replace(",", ".")))
                            
                        dados_projeto = {
                            "proponente": prop_nome,
                            "atividade": atividade,
                            "municipio": municipio,
                            "responsavel": resp_tecnico,
                            "crea": crea_tecnico
                        }
                        
                        from core.relatorio_completo import criar_relatorio_unificado
                        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                            pdf_path = tmp_pdf.name
                            
                        criar_relatorio_unificado(tmp_path, endereco_partida, coord_entrada, coord_sede, dados_projeto, pdf_path)
                        
                        with open(pdf_path, "rb") as f:
                            pdf_bytes = f.read()
                            
                        st.success("✅ Prancha de Localização e Acesso gerada!")
                        st.download_button(
                            label="⬇️ BAIXAR PRANCHA (PDF)",
                            data=pdf_bytes,
                            file_name="Prancha_Acesso_Localizacao.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    st.error(f"❌ Erro na geração: {e}")
                finally:
                    try:
                        if 'tmp_path' in locals() and os.path.exists(tmp_path): os.unlink(tmp_path)
                        if 'pdf_path' in locals() and os.path.exists(pdf_path): os.unlink(pdf_path)
                    except:
                        pass
        else:
            st.info("👈 Preencha os campos e anexe o limite da propriedade.")

# ==============================================================================
# FERRAMENTA 2: MAPA DE LOCALIZAÇÃO (ANTIGO)
# ==============================================================================
elif ferramenta == "📍 Apenas Mapa de Localização (Básico)":
    
    col_form, col_preview = st.columns([1, 2], gap="large")

    with col_form:
        st.markdown('<div class="secao"><h4>① Área do Empreendimento</h4>', unsafe_allow_html=True)
        arquivo = st.file_uploader(
            "Importar arquivo geográfico",
            type=["kml", "kmz", "geojson", "json", "gpkg", "zip"],
        )
        st.caption("KML · KMZ · GeoJSON · GeoPackage · Shapefile (.zip)")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="secao"><h4>② Dados do Empreendimento</h4>', unsafe_allow_html=True)
        nome_empreendimento = st.text_input("Nome", placeholder="Ex: Fazenda Santa Maria")
        municipio_manual    = st.text_input("Município", placeholder="Opcional")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="secao"><h4>③ Responsável Técnico</h4>', unsafe_allow_html=True)
        responsavel = st.text_input("Nome / Cargo", placeholder="Ex: João Silva – Eng. Ambiental")
        crea = st.text_input("CREA / CRBio", placeholder="Opcional")
        num_processo = st.text_input("Nº Processo", placeholder="Opcional")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="secao"><h4>④ Configurações</h4>', unsafe_allow_html=True)
        basemap = st.radio("Fundo", ["satelite", "osm"], horizontal=True)
        observacoes = st.text_area("Observações impressas no mapa", height=60)
        st.markdown('</div>', unsafe_allow_html=True)

        gerar_mapa = st.button("🗺️ GERAR MAPA DE LOCALIZAÇÃO (PDF)", use_container_width=True)

    with col_preview:
        if not arquivo:
            st.info("Faça o upload do arquivo KML/GeoJSON para ver a prévia.")
            
        if arquivo:
            sufixo = Path(arquivo.name).suffix.lower()
            with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
                tmp.write(arquivo.read())
                tmp_path = tmp.name

            try:
                geometrias, tipo, src_original = carregar_arquivo(tmp_path)
                municipio_auto  = identificar_municipio(geometrias)
                municipio_final = municipio_manual.strip() or municipio_auto

                st.success("✅ Arquivo processado e pronto para impressão.")

                if gerar_mapa:
                    if not nome_empreendimento.strip():
                        st.warning("⚠️ Informe o nome do empreendimento.")
                    else:
                        resp_completo = responsavel
                        if crea: resp_completo += f"  |  {crea}"
                        obs_final = observacoes
                        if num_processo: obs_final = f"Nº Processo: {num_processo} — {observacoes}"

                        with st.spinner("⏳ Gerando mapa detalhado..."):
                            from core.layout import montar_layout

                            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_tmp:
                                pdf_path = pdf_tmp.name

                            montar_layout(
                                geometrias=geometrias,
                                nome_empreendimento=nome_empreendimento,
                                responsavel=resp_completo,
                                municipio=municipio_final,
                                observacoes=obs_final,
                                caminho_saida=pdf_path,
                                basemap=basemap,
                            )
                            png_path = pdf_path.replace(".pdf", "_preview.png")

                        if os.path.exists(png_path):
                            st.image(png_path, use_column_width=True)

                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as f:
                                pdf_bytes = f.read()
                            st.download_button(
                                label="⬇️ BAIXAR PDF — MAPA DE LOCALIZAÇÃO",
                                data=pdf_bytes,
                                file_name=f"mapa_localizacao.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {e}")
            finally:
                try:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path): os.unlink(tmp_path)
                    if 'pdf_path' in locals() and os.path.exists(pdf_path): os.unlink(pdf_path)
                    if 'png_path' in locals() and os.path.exists(png_path): os.unlink(png_path)
                except:
                    pass
