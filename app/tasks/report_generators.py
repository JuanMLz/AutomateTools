# app/tasks/report_generators.py
import pandas as pd
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Border, Side, Alignment
from .utils import clean_program_name, slugify, get_weekday_key # Importa Utils

def generate_epg_from_simple_schedule(simple_schedule_df, epg_output_path):
    try:
        from .epg_database_manager import epg_manager
        
        df = simple_schedule_df.copy()
        df['inicio'] = pd.to_datetime(df['Data'] + ' ' + df['Horario'], format='%d/%m/%Y %H:%M')
        # Usa slugify do utils
        df['titulo_slug'] = df['Programa_Padronizado'].apply(slugify)
        df = df.sort_values(by='inicio').reset_index(drop=True)
        
        # Atualiza DB
        unique_progs = df[['titulo_slug', 'Programa_Padronizado']].drop_duplicates()
        slugs = unique_progs['titulo_slug'].tolist()
        titles = unique_progs['Programa_Padronizado'].tolist()
        added_count = epg_manager.update_with_new_programs(slugs, titles)

        # Lógica visual EPG (Mantida e resumida para caber aqui)
        datas = sorted(df['inicio'].dt.date.unique())
        colunas_datas = [d.strftime('%d/%m/%Y') for d in datas]
        times_str = pd.date_range("00:00", "23:55", freq="5min").time.astype(str)
        indice_horarios = pd.to_datetime(times_str, format='%H:%M:%S')
        
        grade_df = pd.DataFrame(index=indice_horarios, columns=colunas_datas)
        grade_df.index.name = 'BRT'

        for _, row in df.iterrows():
            data_str = row['inicio'].strftime('%d/%m/%Y')
            h, m = row['inicio'].hour, row['inicio'].minute
            m_round = 5 * round(m / 5)
            if m_round == 60: h+=1; m_round=0; 
            if h==24: h=0
            time_str = f"{h:02}:{m_round:02}:00"
            idx_inicio = pd.to_datetime(time_str, format='%H:%M:%S')
            
            if data_str in grade_df.columns and idx_inicio in grade_df.index:
                grade_df.loc[idx_inicio, data_str] = row['titulo_slug']

        df_epg_db = epg_manager.load_db()

        with pd.ExcelWriter(epg_output_path, engine='xlsxwriter') as writer:
            grade_df.index = grade_df.index.strftime('%H:%M')
            grade_df.to_excel(writer, sheet_name='Schedule')
            wb = writer.book
            ws = writer.sheets['Schedule']
            merge_fmt = wb.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})
            ws.set_column('A:A', 10); ws.set_column('B:Z', 25)

            for col_num, _ in enumerate(grade_df.columns):
                excel_col = col_num + 1
                start_row = -1
                last_txt = None
                for row_num in range(len(grade_df)):
                    excel_row = row_num + 1
                    val = grade_df.iloc[row_num, col_num]
                    if pd.notna(val) and val != "":
                        if start_row != -1:
                            end_row = excel_row - 1
                            if end_row > start_row: ws.merge_range(start_row, excel_col, end_row, excel_col, last_txt, merge_fmt)
                            else: ws.write(start_row, excel_col, last_txt, merge_fmt)
                        start_row = excel_row; last_txt = val
                    if row_num == len(grade_df) - 1 and start_row != -1:
                        if excel_row > start_row: ws.merge_range(start_row, excel_col, excel_row, excel_col, last_txt, merge_fmt)
                        else: ws.write(start_row, excel_col, last_txt, merge_fmt)
            
            df_epg_db.to_excel(writer, sheet_name='EPG', index=False)

        return f"Sucesso! EPG salvo em '{epg_output_path}' (+{added_count} novos)"

    except Exception as e:
        import traceback
        return f"Erro EPG: {e} | {traceback.format_exc()}"

def generate_comparison_report(clean_schedule_df, excel_anterior_path, output_path):
    try:
        df_novo = clean_schedule_df.copy()

        # 1. Leitura do Antigo
        try:
            df_antigo = pd.read_excel(excel_anterior_path, header=0)
            if 'Data' not in df_antigo.columns: raise ValueError()
        except:
            df_antigo = pd.read_excel(excel_anterior_path, header=2)

        df_antigo = df_antigo.loc[:, ~df_antigo.columns.str.contains('^Unnamed')]
        df_antigo.columns = df_antigo.columns.str.strip()
        if 'Programa' in df_antigo.columns:
            df_antigo.rename(columns={'Programa': 'Programa_Padronizado'}, inplace=True)

        # === CORREÇÃO 3: Aplica a MESMA limpeza do Utils no arquivo antigo ===
        # Isso garante que se o Excel antigo tiver "Nome " (espaço no fim), ele limpa.
        if 'Programa_Padronizado' in df_antigo.columns:
            df_antigo['Programa_Padronizado'] = df_antigo['Programa_Padronizado'].apply(clean_program_name)

        df_antigo['Data'] = df_antigo['Data'].astype(str)
        # Normaliza Hora Antiga
        def _norm_time_old(val):
            if pd.isna(val): return "00:00"
            if hasattr(val, 'hour'): return f"{int(val.hour):02}:{int(val.minute):02}"
            s = str(val).strip()
            m = re.search(r'(\d{1,2}:\d{2})', s)
            return m.group(1) if m else s[:5]
        df_antigo['Horario'] = df_antigo['Horario'].apply(_norm_time_old)

        # Gera chaves (usa utils)
        df_novo['chave'] = df_novo.apply(lambda row: get_weekday_key(row), axis=1)
        df_antigo['chave'] = df_antigo.apply(lambda row: get_weekday_key(row), axis=1)

        mapa_antigo = df_antigo.drop_duplicates(subset=['chave'], keep='last').set_index('chave')['Programa_Padronizado'].to_dict()
        db_metadados = df_antigo.drop_duplicates(subset=['Programa_Padronizado'], keep='last').set_index('Programa_Padronizado').to_dict('index')

        colunas_principais = {'Data', 'Horario', 'Programa_Padronizado', 'chave', 'Status', 'Programa_Bruto'}
        colunas_extras = [c for c in df_antigo.columns if c not in colunas_principais]

        registros = []
        for _, row in df_novo.iterrows():
            chave = row['chave']
            # Limpeza garantida na comparação
            prog_novo = clean_program_name(row['Programa_Padronizado'])
            prog_antigo = mapa_antigo.get(chave)
            
            if not prog_antigo or str(prog_antigo) == 'nan': status = 'NOVO'
            elif prog_novo != prog_antigo: status = 'ALTERADO'
            else: status = 'SEM MUDANÇA'
            
            item = {'Data': row['Data'], 'Horario': row['Horario'], 'Programa': prog_novo, 'Status': status}
            meta = db_metadados.get(prog_novo, {})
            for col in colunas_extras: item[col] = meta.get(col, "") if pd.notna(meta.get(col)) else ""
            registros.append(item)

        # 3. Escrita (Mantida igual)
        wb = load_workbook(excel_anterior_path)
        ws = wb.active
        fill_green = PatternFill("solid", fgColor="C6EFCE")
        fill_yellow = PatternFill("solid", fgColor="FFFF00")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        align = Alignment(horizontal='left', vertical='center')

        ws.delete_rows(4, amount=(ws.max_row + 100))
        curr_row = 4
        last_date = None
        cols_order = ['Data', 'Horario', 'Programa'] + colunas_extras

        for reg in registros:
            if last_date and reg['Data'] != last_date:
                for c in range(2, len(cols_order) + 3):
                    cell = ws.cell(curr_row, c); cell.fill = fill_yellow; cell.border = border
                curr_row += 1
            last_date = reg['Data']
            is_changed = reg['Status'] in ['NOVO', 'ALTERADO']
            for i, col in enumerate(cols_order):
                cell = ws.cell(curr_row, i + 2); cell.value = reg.get(col, ""); cell.border = border; cell.alignment = align
                if is_changed: cell.fill = fill_green
            curr_row += 1

        wb.save(output_path)
        return f"Sucesso! Salvo em '{output_path}'"

    except Exception as e:
        import traceback
        return f"Erro Comparação: {e} | {traceback.format_exc()}"