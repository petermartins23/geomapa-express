"""
GeoMapa Express - rotas.py
Lógica de comunicação com a API do OSRM para traçar rotas e gerar o memorial.
"""

import requests
from geopy.geocoders import Nominatim
from dataclasses import dataclass
from typing import List, Optional

class ErroDeRota(Exception):
    """Exceção customizada para erros no cálculo de rota."""
    pass

@dataclass
class Partida:
    lon: float
    lat: float
    endereco: str

@dataclass
class Rota:
    coordenadas: List[list]  # lista de [lon, lat]
    distancia_km: float
    duracao_min: float
    passos: List[str]
    aviso: Optional[str] = None

# Dicionários de tradução do OSRM para o Português
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


def geocodificar(endereco: str) -> Partida:
    """Transforma um texto (Ex: 'Campo Grande, MS') em Coordenadas."""
    geolocator = Nominatim(user_agent="geomapa_express")
    loc = geolocator.geocode(endereco)
    if not loc:
        raise ErroDeRota(f"Endereço de partida não encontrado: {endereco}")
    return Partida(lon=loc.longitude, lat=loc.latitude, endereco=loc.address)


def calcular_rota(lon_a, lat_a, lon_b, lat_b) -> Rota:
    """Busca a rota no OSRM e gera o itinerário passo a passo."""
    url = f"http://router.project-osrm.org/route/v1/driving/{lon_a},{lat_a};{lon_b},{lat_b}?overview=full&geometries=geojson&steps=true"
    r = requests.get(url)
    
    if r.status_code != 200:
        raise ErroDeRota("Falha na comunicação com o servidor de rotas (OSRM).")
    
    data = r.json()
    if data.get("code") != "Ok":
        raise ErroDeRota("Não foi possível calcular o trajeto da rota.")
    
    route = data["routes"][0]
    coordenadas = route["geometry"]["coordinates"]
    distancia_km = route["distance"] / 1000.0
    duracao_min = route["duration"] / 60.0
    
    passos_texto = []
    dist_acumulada = 0.0
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
            
        texto += f" [Km acum: {dist_acumulada/1000:.1f}]"
        dist_acumulada += dist_m
            
        passos_texto.append(texto)
        
    aviso = None
    if distancia_km > 500:
        aviso = "A rota excede 500 km. Verifique se a partida e destino estão corretos."
        
    return Rota(
        coordenadas=coordenadas,
        distancia_km=distancia_km,
        duracao_min=duracao_min,
        passos=passos_texto,
        aviso=aviso
    )


def descrever_rota(rota: Rota, partida_endereco: str, destino_txt: str) -> str:
    """Gera o texto do memorial de acesso para a capa do PDF."""
    resumo = (
        f"Acesso partindo de {partida_endereco}, com destino final n{destino_txt}. "
        f"O trajeto possui uma distância total aproximada de {rota.distancia_km:.1f} km "
        f"e tempo estimado de viagem de {rota.duracao_min:.0f} minutos em condições normais de tráfego. "
        "O itinerário completo com as manobras e quilometragens encontra-se detalhado na próxima página."
    )
    return resumo
