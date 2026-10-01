"""
GeoMapa Express - pdf_utils.py
Utilitários para formatação de texto e coordenadas no PDF.
"""

def coordenada_gms(valor: float, tipo: str = 'lat') -> str:
    """Converte valor decimal para Graus Minutos Segundos."""
    is_negative = valor < 0
    val_abs = abs(valor)
    graus = int(val_abs)
    minutos_float = (val_abs - graus) * 60
    minutos = int(minutos_float)
    segundos = (minutos_float - minutos) * 60
    
    if tipo == 'lat':
        letra = 'S' if is_negative else 'N'
    else:
        letra = 'O' if is_negative else 'L'
        
    return f"{graus}°{minutos}'{segundos:.2f}\"{letra}"


def registrar_fonte_unicode(pdf):
    """
    Retorna a família da fonte padrão.
    O FPDF2 já suporta a maioria dos acentos nativamente.
    """
    return "Helvetica"


def texto_seguro(texto, familia="Helvetica"):
    """
    Limpa caracteres especiais (como travessões longos ou aspas tortas do Word)
    que costumam quebrar as fontes padrão do PDF.
    """
    if not texto:
        return ""
    
    s = str(texto)
    s = s.replace("—", "-").replace("–", "-")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace("‘", "'").replace("’", "'")
    s = s.replace("•", "-")
    
    return s
