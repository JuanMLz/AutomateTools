# Ferramenta local: analisa duas planilhas (nova vs anterior) e gera relatório
import sys
import os
import unicodedata
import re
import pandas as pd
from datetime import datetime

def norm(s):
    if pd.isna(s): return ""
    s = str(s).strip()
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')
    s = re.sub(r'\s+', ' ', s)
    return s.lower()

def try_read_excel(path):
    # tenta header=0 e header=2 (mesma heurística do projeto)
    tried = []
    for header in (0, 2):
        try:
            df = pd.read_excel(path, header=header)
            # limpa colunas unnamed e strip
            df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
            df.columns = df.columns.str.strip()
            # verifica se tem colunas mínimas
            if 'Data' in df.columns and 'Horario' in df.columns:
                print(f"Leitura bem sucedida: header={header} para '{path}'")
                return df
            tried.append((header, list(df.columns)))
        except Exception as e:
            tried.append((header, f"erro:{e}"))
    # Se não encontrou 'Data'/'Horario', devolve o último df lido (ou levanta)
    print(f"Atenção: não foi possível detectar 'Data'/'Horario' com header 0/2. Tentativas: {tried}")
    # Tentar abrir com header=0 mesmo assim para mostrar colunas/erro
    df = pd.read_excel(path, header=0)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = df.columns.str.strip()
    return df

def detect_program_column(df):
    # candidatos explícitos
    candidates = [
        'Programa_Padronizado', 'Programa_Bruto', 'Programa', 'Programa Original',
        'Programa Original Padronizado', 'Nome_do_PDF', 'Nome_Padronizado'
    ]
    for c in candidates:
        if c in df.columns:
            return c
    # fallback: procura coluna cujo nome contenha 'program' (ignorando acentos e case)
    def strip_acc(s):
        s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('utf-8')
        return s.lower()
    for c in df.columns:
        if 'program' in strip_acc(c) or 'programa' in strip_acc(c) or 'nome' in strip_acc(c):
            return c
    return None

def _normalize_time_to_hhmm(value):
    """Retorna string 'HH:MM' a partir de vários formatos (str, time, Timestamp)."""
    if pd.isna(value):
        return "00:00"
    # se vier como objeto com hour/minute (p.ex. python datetime.time ou pandas Timestamp)
    try:
        if hasattr(value, 'hour') and hasattr(value, 'minute'):
            h = int(value.hour)
            m = int(value.minute)
            return f"{h:02}:{m:02}"
    except Exception:
        pass
    s = str(value).strip()
    # procura HH:MM dentro da string (aceita HH:MM(:SS) também)
    m = re.search(r'(\d{1,2}:\d{2})', s)
    if m:
        hhmm = m.group(1)
        # normaliza padding (ex: '7:5' -> '07:05' não esperado, mas tratar)
        parts = hhmm.split(':')
        h = int(parts[0]); mm = int(parts[1])
        return f"{h:02}:{mm:02}"
    # fallback: tenta converter com pandas e extrair hora/min
    try:
        ts = pd.to_datetime(s, errors='coerce', dayfirst=True)
        if not pd.isna(ts):
            return f"{ts.hour:02}:{ts.minute:02}"
    except Exception:
        pass
    # último recurso: pega primeiros 5 caracteres (ruim, mas evita crash)
    return (s + "00000")[:5]

def get_weekday_key(row, day_index_map=None):
    """
    Gera chave baseada em Índice Sequencial de Dia (0-6: sábado-sexta) + HH:MM.
    Aceita 'Data' como string/objeto e 'Horario' em vários formatos.
    Se day_index_map for fornecido, usa o mapa para converter Data → índice.
    """
    try:
        data_str = str(row.get('Data', ''))
        if day_index_map and data_str in day_index_map:
            day_index = day_index_map[data_str]
        else:
            # fallback: não temos mapa, assume índice 0
            day_index = 0
        
        time_str = _normalize_time_to_hhmm(row.get('Horario', ""))
        return f"{day_index}_{time_str}"
    except Exception:
        return f"ERR_{row.get('Data')}_{row.get('Horario')}"

def analyze(nova_path, antiga_path, out_path="grade_diff_report.xlsx", sample_limit=20):
    print("cwd:", os.getcwd())
    print("nova_path:", nova_path)
    print("antiga_path:", antiga_path)
    print("out_path:", os.path.abspath(out_path))

    df_novo = try_read_excel(nova_path)
    df_antigo = try_read_excel(antiga_path)

    print("Colunas detectadas em nova:", list(df_novo.columns)[:50])
    print("Colunas detectadas em antiga:", list(df_antigo.columns)[:50])

    # Detectar colunas de programa em cada planilha
    prog_col_antiga = detect_program_column(df_antigo)
    prog_col_nova = detect_program_column(df_novo)

    # Para a antiga normalizamos para 'Programa_Padronizado' (se possível)
    if prog_col_antiga and prog_col_antiga != 'Programa_Padronizado':
        df_antigo = df_antigo.rename(columns={prog_col_antiga: 'Programa_Padronizado'})
        prog_col_antiga = 'Programa_Padronizado'

    if not prog_col_antiga:
        print("Aviso: não foi possível detectar coluna de programa na planilha 'antiga'. Colunas:", list(df_antigo.columns))
    if not prog_col_nova:
        print("Aviso: não foi possível detectar coluna de programa na planilha 'nova'. Colunas:", list(df_novo.columns))

    # Garante colunas mínimas
    for df, name in ((df_novo, 'nova'), (df_antigo, 'antiga')):
        if 'Data' not in df.columns or 'Horario' not in df.columns:
            raise SystemExit(f"Arquivo '{name}' parece não ter colunas 'Data' e 'Horario' (colunas: {list(df.columns)})")

    # Normaliza Data para string para favorecer legibilidade (chave usa pd.to_datetime novamente)
    df_novo['Data'] = df_novo['Data'].astype(str)
    df_antigo['Data'] = df_antigo['Data'].astype(str)

    # Cria mapas de índice de dia (0-6: sábado-sexta) baseado na ordem de aparição das datas
    unique_dates_novo = df_novo['Data'].unique()
    day_index_map_novo = {date_str: idx for idx, date_str in enumerate(unique_dates_novo)}
    
    unique_dates_antigo = df_antigo['Data'].unique()
    day_index_map_antigo = {date_str: idx for idx, date_str in enumerate(unique_dates_antigo)}

    # Normaliza Horario na própria tabela para consistência
    df_novo['Horario_norm'] = df_novo['Horario'].apply(_normalize_time_to_hhmm)
    df_antigo['Horario_norm'] = df_antigo['Horario'].apply(_normalize_time_to_hhmm)
    # redefine a coluna Horario usada para chave (manter o original também)
    df_novo['Horario'] = df_novo['Horario_norm']
    df_antigo['Horario'] = df_antigo['Horario_norm']

    # Gera chaves com mapa de índices de dia
    df_novo['chave'] = df_novo.apply(lambda row: get_weekday_key(row, day_index_map_novo), axis=1)
    df_antigo['chave'] = df_antigo.apply(lambda row: get_weekday_key(row, day_index_map_antigo), axis=1)

    # Normaliza programas padronizados (do antigo) e novos
    if 'Programa_Padronizado' in df_antigo.columns:
        df_antigo['prog_norm'] = df_antigo['Programa_Padronizado'].astype(str).apply(norm)
    else:
        # fallback: use detected coluna se existir
        if prog_col_antiga:
            df_antigo['prog_norm'] = df_antigo[prog_col_antiga].astype(str).apply(norm)
        else:
            df_antigo['prog_norm'] = pd.Series([""] * len(df_antigo))

    # No novo tentamos pegar colunas comuns
    if 'Programa_Padronizado' in df_novo.columns:
        col_novo = 'Programa_Padronizado'
    elif 'Programa_Bruto' in df_novo.columns:
        col_novo = 'Programa_Bruto'
    elif prog_col_nova:
        col_novo = prog_col_nova
    else:
        raise SystemExit(f"Não foi possível localizar coluna de programa na planilha nova. Colunas: {list(df_novo.columns)}")

    df_novo['prog_norm'] = df_novo[col_novo].astype(str).apply(norm)

    # Mapa antigo: chave -> programa (usa última ocorrência)
    mapa_antigo = df_antigo.drop_duplicates(subset=['chave'], keep='last').set_index('chave')['prog_norm'].to_dict()

    registros = []
    for _, row in df_novo.iterrows():
        chave = row['chave']
        novo = row['prog_norm']
        antigo = mapa_antigo.get(chave, None)
        status = 'SEM MUDANÇA'
        if antigo is None or antigo == "":
            status = 'NOVO'
        elif antigo != novo:
            status = 'ALTERADO'
        registros.append({
            'Data': row['Data'],
            'Horario': row['Horario'],
            'Programa_Original': row.get(col_novo, ''),
            'Programa_Normalizado': novo,
            'Chave': chave,
            'Antigo_Normalizado': antigo if antigo is not None else '',
            'Status': status
        })

    df_reg = pd.DataFrame(registros)
    counts = df_reg['Status'].value_counts().to_dict()

    # Resumo no console
    print("=== Resumo ===")
    print(counts)
    print()
    print("Exemplos de mudanças (até {}):".format(sample_limit))
    print(df_reg[df_reg['Status'] != 'SEM MUDANÇA'][['Data','Horario','Programa_Original','Antigo_Normalizado','Status']].head(sample_limit).to_string(index=False))

    # Salva Excel com abas: resumo + tabelão
    out_abspath = os.path.abspath(out_path)
    with pd.ExcelWriter(out_abspath, engine='xlsxwriter') as writer:
        df_reg.to_excel(writer, sheet_name='diff_rows', index=False)
        summary = pd.DataFrame([counts], index=['counts']).T.reset_index().rename(columns={'index':'Status',0:'Count'})
        summary.to_excel(writer, sheet_name='summary', index=False)
    print(f"\nRelatório salvo em: {out_abspath}")

if __name__ == '__main__':
    # aceitar argumentos via CLI ou usar os caminhos padrão abaixo
    if len(sys.argv) >= 3:
        nova = sys.argv[1]
        antiga = sys.argv[2]
        out = sys.argv[3] if len(sys.argv) > 3 else "grade_diff_report.xlsx"
    else:
        # caminhos de exemplo (substitua se desejar)
        nova = r"C:\Users\juan.lopes\Downloads\01_11_2025_ate_07_11_2025_grade (2).xlsx"
        antiga = r"C:\Users\juan.lopes\Downloads\teste21.xlsx"
        out = "grade_diff_report.xlsx"
    analyze(nova, antiga, out)