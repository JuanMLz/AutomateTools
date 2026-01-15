# app/tasks/pdf_extractor.py
import fitz # PyMuPDF
import pandas as pd
import re
from .mapping_manager import mapping_manager
from .utils import clean_program_name, get_weekday_key # Importa do nosso novo utils

def _extract_date_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            match = re.search(r'\d{2}/\d{2}/\d{4}', text)
            if match: return match.group(0)
        return ""
    except:
        return ""

def _extract_raw_data_from_pdfs(pdf_paths):
    all_schedule_data = []
    COLUMN_DIVIDER_X = 70.0 

    for pdf_path in pdf_paths:
        date = _extract_date_from_pdf(pdf_path)
        doc = fitz.open(pdf_path)
        page = doc[0]
        words = page.get_text("words")
        
        lines = {}
        for word in words:
            y0 = word[1]
            line_key = int(y0 // 10)
            if line_key not in lines: lines[line_key] = []
            lines[line_key].append(word)
        
        for line_key in sorted(lines.keys()):
            line_words = sorted(lines[line_key], key=lambda w: w[0])
            horario = ""
            programa_parts = []
            
            for word in line_words:
                if word[0] < COLUMN_DIVIDER_X:
                    horario = word[4]
                else:
                    programa_parts.append(word[4])
            
            if horario and horario[:1].isdigit():
                all_schedule_data.append({
                    'Data': date,
                    'Horario': horario,
                    'Programa_Bruto': " ".join(programa_parts)
                })
                
    return pd.DataFrame(all_schedule_data)

def extract_and_clean_from_pdfs(pdf_paths):
    """Extrai e gera o DataFrame base para tudo."""
    raw_mapping, error = mapping_manager.load_mapping_as_dict()
    if error: return None, error

    # === CORREÇÃO 1: Limpa as chaves do mapeamento usando a função central ===
    # Isso garante que se o mapeamento tiver "Nome " (com espaço), ele é limpo.
    mapping_dict = {clean_program_name(k): v for k, v in raw_mapping.items()}

    try:
        df_extracted = _extract_raw_data_from_pdfs(pdf_paths)
        if df_extracted.empty: return None, "Erro: PDFs vazios ou ilegíveis."

        # Ordenação
        df_extracted['temp_data'] = pd.to_datetime(df_extracted['Data'], format='%d/%m/%Y', errors='coerce')
        df_extracted['temp_hora_dt'] = pd.to_datetime(df_extracted['Horario'], format='%H:%M', errors='coerce')
        
        mask_na = df_extracted['temp_hora_dt'].isna()
        if mask_na.any():
            df_extracted.loc[mask_na, 'temp_hora_dt'] = pd.to_datetime(df_extracted.loc[mask_na, 'Horario'], format='%H:%M:%S', errors='coerce')

        df_extracted['temp_hora'] = df_extracted['temp_hora_dt'].dt.time
        df_extracted.sort_values(by=['temp_data', 'temp_hora'], inplace=True)
        
        df_extracted['Horario'] = df_extracted['temp_hora'].apply(lambda t: f"{t.hour:02}:{t.minute:02}" if pd.notna(t) else "")
        df_extracted.drop(columns=['temp_hora_dt', 'temp_hora', 'temp_data'], inplace=True, errors='ignore')

        # === CORREÇÃO 2: Limpa o nome bruto vindo do PDF usando a função central ===
        df_extracted['Programa_Bruto'] = df_extracted['Programa_Bruto'].apply(clean_program_name)

        # Aplica Mapeamento
        df_extracted['Programa_Padronizado'] = df_extracted['Programa_Bruto'].replace(mapping_dict)
        
        # Gera chave
        df_extracted['chave'] = df_extracted.apply(lambda row: get_weekday_key(row), axis=1)
        
        return df_extracted[['Data', 'Horario', 'Programa_Bruto', 'Programa_Padronizado', 'chave']], None
    except Exception as e:
        import traceback
        return None, f"Erro na extração: {e} | {traceback.format_exc()}"

def find_unmapped_programs(pdf_paths=None, df_extracted=None):
    mapping_dict, err = mapping_manager.load_mapping_as_dict()
    if err: return None, err

    try:
        if df_extracted is None:
            if not pdf_paths: return [], None
            # Chama a função principal para garantir que a limpeza (strip) seja aplicada
            # antes de checar se está mapeado.
            result = extract_and_clean_from_pdfs(pdf_paths)
            if result[0] is None: return [], None
            df_raw = result[0]
        else:
            df_raw = df_extracted.copy()

        if df_raw is None or df_raw.empty: return [], None

        # Normaliza chaves para comparação
        mapped_keys = {clean_program_name(k).lower() for k in mapping_dict.keys()}
        
        # Pega programas brutos e garante que estão limpos
        unique_raw = df_raw['Programa_Bruto'].apply(clean_program_name).unique()
        
        # Verifica quais não estão no mapa
        unmapped = [p for p in unique_raw if clean_program_name(p).lower() not in mapped_keys]
        
        return unmapped, None

    except Exception as e:
        return None, f"Erro check unmapped: {e}"