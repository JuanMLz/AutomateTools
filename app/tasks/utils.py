# app/tasks/utils.py
import re
import unicodedata
import pandas as pd

def clean_program_name(text):
    """
    Função CENTRAL de limpeza.
    Remove espaços das pontas e espaços duplos no meio.
    Garante que "Jornal  X " vire "Jornal X" em todo o sistema.
    """
    if pd.isna(text) or text == "":
        return ""
    # Converte para string, remove espaços das pontas
    text = str(text).strip()
    # Remove múltiplos espaços internos (ex: "  " vira " ")
    text = re.sub(r'\s+', ' ', text)
    return text

def slugify(text):
    """Converte texto para formato URL amigável."""
    if not text: return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text

def get_weekday_key(row):
    """Gera chave DiaSemana_HH:MM (0_09:00)."""
    try:
        # Tenta pegar Horario
        horario_raw = row.get('Horario', "")
        
        # Se já for objeto time/datetime
        if hasattr(horario_raw, 'hour'):
            time_str = f"{int(horario_raw.hour):02}:{int(horario_raw.minute):02}"
        else:
            # Se for string
            s = str(horario_raw).strip()
            m = re.search(r'(\d{1,2}:\d{2})', s)
            time_str = m.group(1) if m else s[:5]
        
        # Tenta pegar Data
        data_raw = row.get('Data', '')
        if isinstance(data_raw, str):
            # Tenta DD/MM/YYYY
            try:
                data_obj = pd.to_datetime(data_raw, format='%d/%m/%Y')
            except:
                data_obj = pd.to_datetime(data_raw)
        else:
            data_obj = pd.to_datetime(data_raw)
        
        weekday = data_obj.weekday() # 0=seg...6=dom
        return f"{weekday}_{time_str}"
    except Exception:
        # Fallback seguro para não travar
        return f"ERR_{str(row.get('Data', ''))}_{str(row.get('Horario', ''))}"