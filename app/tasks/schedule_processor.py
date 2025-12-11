# app/tasks/schedule_processor.py
"""
Módulo responsável por toda a lógica de processamento de grades:
1. Extração de dados de PDFs.
2. Limpeza e Padronização.
3. Geração de EPG Visual.
4. Geração de Relatórios Comparativos (Excel Template).
"""

import re
import unicodedata
import fitz  # PyMuPDF
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from .mapping_manager import mapping_manager

# ======================================================================
# == 1. FUNÇÕES AUXILIARES (Internas)                                 ==
# ======================================================================

def _slugify(text):
    """Converte texto para formato URL amigável (ex: 'Mãe Maria' -> 'mae-maria')."""
    if not text: return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('utf-8')
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text

def _extract_date_from_pdf(pdf_path):
    """Procura a primeira data no formato DD/MM/AAAA dentro do PDF."""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            match = re.search(r'\d{2}/\d{2}/\d{4}', text)
            if match: return match.group(0)
        return ""
    except Exception:
        return ""

def _get_weekday_key(row):
    """
    Gera uma chave única para comparação baseada no Dia da Semana e Horário.
    Ex: '09/12/2025' (Segunda) às '00:00:00' -> Retorna '0_00:00'.
    Isso permite comparar semanas diferentes (Segunda com Segunda).
    """
    try:
        dt = pd.to_datetime(row['Data'], dayfirst=True)
        weekday = dt.weekday() # 0 = Segunda, 6 = Domingo
        
        # Pega apenas HH:MM para evitar erros com segundos (00:00:00 vs 00:00)
        raw_time = str(row['Horario']).strip()
        time_str = raw_time[:5] 
        
        return f"{weekday}_{time_str}"
    except Exception:
        return f"ERR_{row['Data']}_{row['Horario']}"

def _extract_raw_data_from_pdfs(pdf_paths):
    """Lê as coordenadas X/Y do PDF para separar Horário de Programa."""
    all_schedule_data = []
    COLUMN_DIVIDER_X = 70.0 # Divisor visual entre coluna de hora e nome

    for pdf_path in pdf_paths:
        date = _extract_date_from_pdf(pdf_path)
        doc = fitz.open(pdf_path)
        page = doc[0] # Assume que a grade está na primeira página
        words = page.get_text("words")
        
        # Agrupa palavras por linha (eixo Y)
        lines = {}
        for word in words:
            y0 = word[1]
            line_key = int(y0 // 10) # Agrupamento aproximado
            if line_key not in lines: lines[line_key] = []
            lines[line_key].append(word)
        
        # Processa cada linha
        for line_key in sorted(lines.keys()):
            line_words = sorted(lines[line_key], key=lambda w: w[0])
            horario = ""
            programa_parts = []
            
            for word in line_words:
                if word[0] < COLUMN_DIVIDER_X:
                    horario = word[4]
                else:
                    programa_parts.append(word[4])
            
            # Só adiciona se tiver horário válido
            if horario and horario[:1].isdigit():
                all_schedule_data.append({
                    'Data': date,
                    'Horario': horario,
                    'Programa_Bruto': " ".join(programa_parts)
                })
                
    return pd.DataFrame(all_schedule_data)

# ======================================================================
# == 2. FUNÇÕES PRINCIPAIS (Tasks)                                    ==
# ======================================================================

def extract_and_clean_from_pdfs(pdf_paths):
    """Extrai dados, ordena cronologicamente e aplica o De-Para."""
    mapping_dict, error = mapping_manager.load_mapping_as_dict()
    if error: return None, error

    try:
        df_extracted = _extract_raw_data_from_pdfs(pdf_paths)
        if df_extracted.empty: return None, "Erro: PDFs vazios ou ilegíveis."

        # Ordenação Cronológica Rigorosa
        df_extracted['temp_data'] = pd.to_datetime(df_extracted['Data'], format='%d/%m/%Y', errors='coerce')
        df_extracted['temp_hora'] = pd.to_datetime(df_extracted['Horario'], format='%H:%M', errors='coerce').dt.time
        df_extracted.sort_values(by=['temp_data', 'temp_hora'], inplace=True)
        df_extracted.drop(columns=['temp_data', 'temp_hora'], inplace=True)

        # Aplica Mapeamento
        df_extracted['Programa_Padronizado'] = df_extracted['Programa_Bruto'].replace(mapping_dict)
        
        # Retorna apenas colunas úteis
        return df_extracted[['Data', 'Horario', 'Programa_Padronizado']], None
    except Exception as e:
        return None, f"Erro na extração: {e}"

def generate_epg_from_simple_schedule(simple_schedule_df, epg_output_path):
    """Gera o Excel Visual (EPG) com células mescladas."""
    try:
        df = simple_schedule_df.copy()
        
        # Preparação de Datas e Horários
        df['inicio'] = pd.to_datetime(df['Data'] + ' ' + df['Horario'], format='%d/%m/%Y %H:%M')
        df['titulo_slug'] = df['Programa_Padronizado'].apply(_slugify)
        df = df.sort_values(by='inicio').reset_index(drop=True)
        
        datas = sorted(df['inicio'].dt.date.unique())
        colunas_datas = [d.strftime('%d/%m/%Y') for d in datas]
        
        # Cria índice de horários (00:00 a 23:55)
        times_str = pd.date_range("00:00", "23:55", freq="5min").time.astype(str)
        indice_horarios = pd.to_datetime(times_str, format='%H:%M:%S')
        
        grade_df = pd.DataFrame(index=indice_horarios, columns=colunas_datas)
        grade_df.index.name = 'BRT'

        # Preenche a Grade
        for _, row in df.iterrows():
            data_str = row['inicio'].strftime('%d/%m/%Y')
            
            # Arredondamento para 5 min
            h, m = row['inicio'].hour, row['inicio'].minute
            m_round = 5 * round(m / 5)
            if m_round == 60:
                h += 1; m_round = 0
                if h == 24: h = 0
            
            time_str = f"{h:02}:{m_round:02}:00"
            idx_inicio = pd.to_datetime(time_str, format='%H:%M:%S')
            
            if data_str in grade_df.columns and idx_inicio in grade_df.index:
                grade_df.loc[idx_inicio, data_str] = row['titulo_slug']

        # Escrita com XlsxWriter
        with pd.ExcelWriter(epg_output_path, engine='xlsxwriter') as writer:
            grade_df.index = grade_df.index.strftime('%H:%M')
            grade_df.to_excel(writer, sheet_name='Schedule')
            
            wb = writer.book
            ws = writer.sheets['Schedule']
            merge_fmt = wb.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})
            
            ws.set_column('A:A', 10)
            ws.set_column('B:Z', 25)

            # Algoritmo de Mesclagem
            for col_num, _ in enumerate(grade_df.columns):
                excel_col = col_num + 1
                start_row = -1
                last_txt = None
                
                for row_num in range(len(grade_df)):
                    excel_row = row_num + 1
                    val = grade_df.iloc[row_num, col_num]
                    
                    if pd.notna(val) and val != "":
                        # Fecha bloco anterior
                        if start_row != -1:
                            end_row = excel_row - 1
                            if end_row > start_row:
                                ws.merge_range(start_row, excel_col, end_row, excel_col, last_txt, merge_fmt)
                            else:
                                ws.write(start_row, excel_col, last_txt, merge_fmt)
                        
                        start_row = excel_row
                        last_txt = val
                    
                    # Fecha último bloco do dia
                    if row_num == len(grade_df) - 1 and start_row != -1:
                        if excel_row > start_row:
                            ws.merge_range(start_row, excel_col, excel_row, excel_col, last_txt, merge_fmt)
                        else:
                            ws.write(start_row, excel_col, last_txt, merge_fmt)
                            
        return f"Sucesso! EPG salvo em '{epg_output_path}'"
    except Exception as e:
        return f"Erro EPG: {e}"

def generate_comparison_report(clean_schedule_df, excel_anterior_path, output_path):
    """Gera relatório comparativo usando a planilha anterior como Template."""
    try:
        df_novo = clean_schedule_df.copy()

        # 1. Tenta ler o Template
        try:
            df_antigo = pd.read_excel(excel_anterior_path, header=0)
            if 'Data' not in df_antigo.columns: raise ValueError()
        except:
            df_antigo = pd.read_excel(excel_anterior_path, header=2)

        # Limpeza de colunas do Template
        df_antigo = df_antigo.loc[:, ~df_antigo.columns.str.contains('^Unnamed')]
        df_antigo.columns = df_antigo.columns.str.strip()
        
        if 'Programa' in df_antigo.columns:
            df_antigo.rename(columns={'Programa': 'Programa_Padronizado'}, inplace=True)

        # 2. Configura Chaves de Comparação
        df_novo['Data'] = df_novo['Data'].astype(str)
        df_novo['chave'] = df_novo.apply(_get_weekday_key, axis=1)
        
        df_antigo['Data'] = df_antigo['Data'].astype(str)
        df_antigo['chave'] = df_antigo.apply(_get_weekday_key, axis=1)

        # 3. Biblioteca de Metadados (Sinopses antigas)
        db_sinopses = df_antigo.drop_duplicates(subset=['Programa_Padronizado'], keep='last')
        mapa_antigo = pd.Series(df_antigo.Programa_Padronizado.values, index=df_antigo.chave).to_dict()

        colunas_extras = [c for c in df_antigo.columns if c not in ['Data', 'Horario', 'Programa_Padronizado', 'chave', 'Status']]
        
        # 4. Processamento dos Registros
        registros = []
        for _, row in df_novo.iterrows():
            item = {
                'Data': row['Data'], 'Horario': row['Horario'], 'Programa': row['Programa_Padronizado'],
                'Status': 'SEM MUDANÇA'
            }
            
            # Recupera dados extras (Sinopse, etc)
            dados = db_sinopses[db_sinopses['Programa_Padronizado'] == item['Programa']]
            for col in colunas_extras:
                val = dados.iloc[0][col] if not dados.empty else ""
                item[col] = val if pd.notna(val) else ""

            # Verifica Mudanças
            prog_antigo = mapa_antigo.get(row['chave'])
            if not prog_antigo: item['Status'] = 'NOVO'
            elif item['Programa'] != prog_antigo: item['Status'] = 'ALTERADO'
            
            registros.append(item)

        # 5. Escrita Cirúrgica (OpenPyXL)
        wb = load_workbook(excel_anterior_path)
        ws = wb.active
        
        fill_green = PatternFill("solid", fgColor="C6EFCE")
        fill_yellow = PatternFill("solid", fgColor="FFFF00")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        align = Alignment(horizontal='left', vertical='center')

        start_row = 4
        ws.delete_rows(start_row, amount=(ws.max_row + 100)) # Limpa dados antigos

        curr_row = start_row
        last_date = None
        cols_order = ['Data', 'Horario', 'Programa'] + colunas_extras

        for reg in registros:
            # Linha Amarela (Separador de Dia)
            if last_date and reg['Data'] != last_date:
                for c in range(2, len(cols_order) + 3): # Col B até fim
                    cell = ws.cell(curr_row, c)
                    cell.fill = fill_yellow
                    cell.border = border
                ws.row_dimensions[curr_row].height = 15
                curr_row += 1
            
            last_date = reg['Data']
            is_changed = reg['Status'] in ['NOVO', 'ALTERADO']

            # Escreve Dados
            for i, col in enumerate(cols_order):
                cell = ws.cell(curr_row, i + 2) # +2 offset (Col A vazia)
                cell.value = reg.get(col, "")
                cell.border = border
                cell.alignment = align
                if is_changed: cell.fill = fill_green
            
            curr_row += 1

        wb.save(output_path)
        return f"Sucesso! Salvo em '{output_path}'"

    except Exception as e:
        import traceback
        return f"Erro Comparação: {e} | {traceback.format_exc()}"