"""
GeoMapa Express - app.py (Revisão Diamante)
"""

import streamlit as st
import tempfile
import os
import sys
from pathlib import Path
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.parser import carregar_geodataframe, obter_centroide, carregar_arquivo
from core.localizacao import identificar_municipio
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

ferramenta = st.radio("", ["🚀 Gerador Completo (Prancha IMASUL/Poços)", "📍 Apenas Mapa de Localização (Básico)"], horizontal=True, label_visibility="collapsed")
st.markdown("<hr/>", unsafe_allow_html=True)

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
        
        # Inicialização segura
        for key in ["coord_entrada", "coord_sede", "last_click", "pdf_bytes", "ultimo_hash", "map_center", "map_zoom"]:
            if key not in st.session_state: st.session_state[key] = None

        lat_centro, lon_centro = -20.4428, -54.6460 # MS
        gdf_interativo = None
        
        if arquivo_area:
            bytes_arq = arquivo_area.getvalue()
            hash_arq = hashlib.md5(bytes_arq).hexdigest()
            
            # Se trocou o arquivo (verificado pelo Hash), zera as marcações antigas (Correção 2)
            if st.session_state["ultimo_hash"] != hash_arq:
                st.session_state["ultimo_hash"] = hash_arq
                st.session_state["coord_entrada"] = None
                st.session_state["coord_sede"] = None
                st.session_state["last_click"] = None
                st.session_state["pdf_bytes"] = None
                
                try:
                    gdf_temp, _, _ = ler_arquivo_em_cache(bytes_arq, arquivo_area.name)
                    lon_c, lat_c = obter_centroide(gdf_temp)
                    st.session_state["map_center"] = [lat_c, lon_c]
                    st.session_state["map_zoom"] = 13
                except:
                    pass

            try:
                gdf_interativo, _, _ = ler_arquivo_em_cache(bytes_arq, arquivo_area.name)
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
        else:
            st.session_state["map_center"] = [lat_centro, lon_centro]
            st.session_state["map_zoom"] = 6
            st.session_state["ultimo_hash"] = None

        st.markdown('<div class="secao"><h4>③ Coordenadas (Mapa Interativo)</h4>', unsafe_allow_html=True)
        modo_clique = st.radio("O que marcar no mapa?", ["📍 Entrada Principal", "🏡 Sede / Atividade"], horizontal=True)

        m = folium.Map(location=st.session_state["map_center"], zoom_start=st.session_state["map_zoom"])
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri', name='Satélite', max_zoom=18
        ).add_to(m)
        
        if gdf_interativo is not None:
            gdf_filtrado = gdf_interativo[gdf_interativo.geometry.notnull() & ~gdf_interativo.geometry.is_empty]
            if not gdf_filtrado.empty:
                folium.GeoJson(gdf_filtrado, style_function=lambda x: {'color': '#00ff00', 'fillOpacity': 0.1, 'weight': 3}).add_to(m)
            
        if st.session_state["coord_entrada"]:
            folium.Marker(st.session_state["coord_entrada"], tooltip="Entrada", icon=folium.Icon(color='green', icon='info-sign')).add_to(m)
        if st.session_state["coord_sede"]:
            folium.Marker(st.session_state["coord_sede"], tooltip="Sede/Atividade", icon=folium.Icon(color='blue', icon='home')).add_to(m)
            
        # Retirado zoom/center do return para o mapa parar de recarregar quando arrastar (Correção de Reruns)
        map_data = st_folium(m, height=400, returned_objects=["last_clicked"])
        
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

        def limpar_entrada(): st.session_state["coord_entrada"] = None
        def limpar_sede(): st.session_state["coord_sede"] = None

        # Campos reativados com botões de limpeza (Correção 3)
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1: in_lat_e = st.text_input("Lat. Entrada", value=str(st.session_state["coord_entrada"][0]) if st.session_state["coord_entrada"] else "")
        with c2: in_lon_e = st.text_input("Lon. Entrada", value=str(st.session_state["coord_entrada"][1]) if st.session_state["coord_entrada"] else "")
        with c3: st.button("Limpar", key="btn_limpa_e", on_click=limpar_entrada)

        c4, c5, c6 = st.columns([2, 2, 1])
        with c4: in_lat_s = st.text_input("Lat. Sede", value=str(st.session_state["coord_sede"][0]) if st.session_state["coord_sede"] else "")
        with c5: in_lon_s = st.text_input("Lon. Sede", value=str(st.session_state["coord_sede"][1]) if st.session_state["coord_sede"] else "")
        with c6: st.button("Limpar", key="btn_limpa_s", on_click=limpar_sede)
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
            st.session_state["pdf_bytes"] = None # Zera PDF de sucesso da fazenda anterior (Correção 1)
            
            if not arquivo_area or not endereco_partida:
                st.warning("⚠️ O Arquivo de Área e o Endereço de Partida são obrigatórios.")
            else:
                tmp_path = pdf_path = None # Inicialização segura (Correção do finally)
                try:
                    with st.spinner("⏳ Processando área, traçando rota e montando PDF..."):
                        sufixo = Path(arquivo_area.name).suffix.lower()
                        with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp_kml:
                            tmp_kml.write(arquivo_area.getvalue())
                            tmp_path = tmp_kml.name
                        
                        coord_e = None
                        if in_lat_e and in_lon_e:
                            try: coord_e = (float(in_lat_e.replace(",", ".")), float(in_lon_e.replace(",", ".")))
                            except: pass
                            
                        coord_s = None
                        if in_lat_s and in_lon_s:
                            try: coord_s = (float(in_lat_s.replace(",", ".")), float(in_lon_s.replace(",", ".")))
                            except: pass
                            
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
                            
                        criar_relatorio_unificado(tmp_path, endereco_partida, coord_e, coord_s, dados_projeto, pdf_path)
                        
                        with open(pdf_path, "rb") as f:
                            st.session_state["pdf_bytes"] = f.read()
                            
                except Exception as e:
                    # Ocultando caminhos do servidor e logando um erro bonito (Correção de Traceback)
                    st.error(f"❌ Erro na geração: Verifique se o arquivo anexo é válido e o endereço existe. \nDetalhe Técnico: {e}")
                finally:
                    if tmp_path and os.path.exists(tmp_path): os.unlink(tmp_path)
                    if pdf_path and os.path.exists(pdf_path): os.unlink(pdf_path)

        if st.session_state.get("pdf_bytes"):
            st.success("✅ Prancha de Localização e Acesso gerada e pronta!")
            st.download_button(
                label="⬇️ BAIXAR PRANCHA (PDF)",
                data=st.session_state["pdf_bytes"],
                file_name="Prancha_Acesso_Localizacao.pdf",
                mime="application/pdf",
                use_container_width=True
            )

elif ferramenta == "📍 Apenas Mapa de Localização (Básico)":
    
    col_form, col_preview = st.columns([1, 2], gap="large")

    with col_form:
        st.markdown('<div class="secao"><h4>① Área do Empreendimento</h4>', unsafe_allow_html=True)
        arquivo = st.file_uploader(
            "Importar arquivo geográfico",
            type=["kml", "kmz", "geojson", "json", "gpkg", "zip"],
            key="up_basico"
        )
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
            st.info("Faça o upload do arquivo para ver a prévia.")
            
        if arquivo:
            tmp_path = None
            try:
                sufixo = Path(arquivo.name).suffix.lower()
                with tempfile.NamedTemporaryFile(suffix=sufixo, delete=False) as tmp:
                    tmp.write(arquivo.read())
                    tmp_path = tmp.name

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

                        pdf_path = png_path = None
                        try:
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
                                st.image(png_path)

                            if os.path.exists(pdf_path):
                                with open(pdf_path, "rb") as f:
                                    pdf_bytes2 = f.read()
                                st.download_button(
                                    label="⬇️ BAIXAR PDF — MAPA DE LOCALIZAÇÃO",
                                    data=pdf_bytes2,
                                    file_name=f"mapa_localizacao.pdf",
                                    mime="application/pdf",
                                    use_container_width=True,
                                )
                        except Exception as e:
                            st.error(f"❌ Erro na montagem do layout: {e}")
                        finally:
                            if pdf_path and os.path.exists(pdf_path): os.unlink(pdf_path)
                            if png_path and os.path.exists(png_path): os.unlink(png_path)
            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path): os.unlink(tmp_path)
