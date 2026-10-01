import requests
from geopy.geocoders import Nominatim
import geopandas as gpd
from shapely.geometry import LineString, Point
import matplotlib.pyplot as plt
import contextily as ctx
import math
from pathlib import Path
from fpdf import FPDF
import tempfile
import os

# Dicionários de tradução
dicionario_manobra = {
    "depart": "Siga", "turn": "Vire", "continue": "Continue", "new name": "Siga pela",
    "merge": "Entre", "on ramp": "Pegue o acesso", "off ramp": "Saia", "fork": "Mantenha-se",
    "end of road": "Fim da via", "use lane": "Use a faixa", "roundabout": "Na rotatória",
    "roundabout turn": "Na rotatória, vire", "arrive": "Chegada ao destino",
    "exit roundabout": "Saia da rotatória", "exit rotary": "Saia da rotatória"
}
dicionario_modificador = {
    "uturn": "faça um retorno", "sharp right": "à direita acentuada", "right": "à direita",
    "slight right": "levemente à direita", "straight": "em frente", "slight left": "levemente à esquerda",
    "left": "à esquerda", "sharp left": "à esquerda acentuada"
}

def geocodificar_endereco(endereco: str):
    geolocator = Nominatim(user_agent="geomapa_express")
    loc = geolocator.geocode(endereco)
    if not loc:
        raise ValueError(f"Endereço não encontrado: {endereco}")
    return loc.longitude, loc.latitude, loc.address

def calcular_rota(lon_a, lat_a, lon_b, lat_b):
    url = f"http://router.project-osrm.org/route/v1/driving/{lon_a},{lat_a};{lon_b},{lat_b}?overview=full&geometries=geojson&steps=true"
    r = requests.get(url)
    data = r.json()
    if data.get("code") != "Ok":
        raise ValueError("Não foi possível calcular a rota pelo OSRM.")
    return data["routes"][0]

def gerar_texto_passos(route):
    passos_texto = []
    steps = route["legs"][0]["steps"]
    for i, step in enumerate(steps):
        maneuver = step["maneuver"]
        tipo = maneuver.get("type", "")
        modificador = maneuver.get("modifier", "")
        nome_via = step.get("name", "")
        dist_m = step["distance"]
        
        acao = dicionario_manobra.get(tipo, tipo.capitalize())
        direcao = dicionario_modificador.get(modificador, modificador)
        
        texto = f"{i+1}. {acao}"
        if direcao: texto += f" {direcao}"
        if nome_via: texto += f" na via '{nome_via}'"
        else:
            if tipo != "arrive": texto += " na via sem nome"
        
        if dist_m > 0:
            if dist_m >= 1000: texto += f" (siga por {dist_m/1000:.1f} km)"
            else: texto += f" (siga por {dist_m:.0f} m)"
        passos_texto.append(texto)
    return passos_texto

def gerar_mapa_rota(lon_a, lat_a, lon_b, lat_b, geometry_coords, caminho_img):
    linha = LineString(geometry_coords)
    gdf = gpd.GeoDataFrame(geometry=[linha], crs="EPSG:4326")
    gdf_merc = gdf.to_crs(epsg=3857)
    
    fig, ax = plt.subplots(figsize=(10, 8))
    gdf_merc.plot(ax=ax, color='#1b3622', linewidth=3, alpha=0.8, zorder=3)
    
    pt_a = gpd.GeoSeries([Point(lon_a, lat_a)], crs="EPSG:4326").to_crs(epsg=3857)
    pt_b = gpd.GeoSeries([Point(lon_b, lat_b)], crs="EPSG:4326").to_crs(epsg=3857)
    
    pt_a.plot(ax=ax, color='#2e7d32', markersize=120, marker='o', zorder=4)
    pt_b.plot(ax=ax, color='#cc0000', markersize=150, marker='X', zorder=4)
    
    ax.text(pt_a.x.iloc[0], pt_a.y.iloc[0], " Partida", color="#1b3622", fontweight="bold", fontsize=10, zorder=5)
    ax.text(pt_b.x.iloc[0], pt_b.y.iloc[0], " Destino", color="#cc0000", fontweight="bold", fontsize=10, zorder=5)
    
    try:
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldStreetMap, attribution=False)
    except:
        pass
        
    ax.set_axis_off()
    fig.savefig(caminho_img, dpi=200, bbox_inches="tight")
    plt.close()

class PDFCroqui(FPDF):
    def header(self):
        self.set_fill_color(27, 54, 34)
        self.rect(0, 0, 210, 20, 'F')
        self.set_font('Arial', 'B', 14)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'CROQUI E MEMORIAL DE ACESSO', 0, 1, 'C')
        self.ln(5)

def gerar_relatorio_acesso(endereco_partida, lon_b, lat_b, responsavel, caminho_saida):
    lon_a, lat_a, endereco_formatado = geocodificar_endereco(endereco_partida)
    rota = calcular_rota(lon_a, lat_a, lon_b, lat_b)
    passos = gerar_texto_passos(rota)
    
    dist_total = rota["distance"] / 1000
    tempo_total = rota["duration"] / 60
    
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
        mapa_img = tmp_img.name
        
    gerar_mapa_rota(lon_a, lat_a, lon_b, lat_b, rota["geometry"]["coordinates"], mapa_img)
    
    pdf = PDFCroqui()
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Partida: {endereco_formatado}", 0, 1)
    pdf.cell(0, 8, f"Destino: Lat {lat_b:.5f}, Lon {lon_b:.5f}", 0, 1)
    pdf.cell(0, 8, f"Distancia Total: {dist_total:.1f} km | Tempo Estimado: {tempo_total:.0f} min", 0, 1)
    if responsavel:
        pdf.cell(0, 8, f"Responsavel: {responsavel}", 0, 1)
        
    pdf.image(mapa_img, x=15, y=55, w=180)
    
    pdf.add_page()
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "ITINERARIO PASSO A PASSO", 0, 1)
    pdf.ln(2)
    
    pdf.set_font('Arial', '', 10)
    for p in passos:
        # Pular caracteres nao latinos
        p_safe = p.encode('latin-1', 'replace').decode('latin-1')
        pdf.write(6, p_safe + '\n')
        
    pdf.output(caminho_saida)
    
    try:
        os.unlink(mapa_img)
    except:
        pass
