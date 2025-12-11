# app/tasks/excel_consolidator.py

import os
import pandas as pd

# ATUALIZAÇÃO: Adicionado o parâmetro 'nome_da_aba'.
def processar_logs_para_excel(lista_de_arquivos, caminho_arquivo_excel, nome_da_aba="Dados Consolidados"):
    """
    Processa uma lista de arquivos de log e os consolida em uma aba específica de um arquivo Excel.
    """
    try:
        if not lista_de_arquivos:
            return "Erro: Nenhum arquivo de log foi selecionado."
        
        # Validação simples para o nome da aba
        if not nome_da_aba or len(nome_da_aba) > 31: # Limite de caracteres do Excel
             return "Erro: Nome da aba inválido ou muito longo."

        lista_de_dataframes = [pd.read_csv(f, delimiter=';', encoding='utf-8') for f in lista_de_arquivos]
        
        if not lista_de_dataframes:
            return "Erro: Falha ao ler os dados dos arquivos selecionados."

        df_final = pd.concat(lista_de_dataframes, ignore_index=True)
        
        mode = 'a' if os.path.exists(caminho_arquivo_excel) else 'w'
        if_sheet_exists = 'replace' if mode == 'a' else None

        with pd.ExcelWriter(
            caminho_arquivo_excel,
            engine='openpyxl',
            mode=mode,
            if_sheet_exists=if_sheet_exists
        ) as writer:
            # ATUALIZAÇÃO: Usa a variável 'nome_da_aba' ao salvar.
            df_final.to_excel(writer, sheet_name=nome_da_aba, index=False)
        
        return f"Sucesso! {len(lista_de_arquivos)} arquivos processados e {len(df_final)} linhas foram salvas na aba '{nome_da_aba}'."

    except Exception as e:
        # Tratamento de erro específico para permissão negada
        if isinstance(e, PermissionError):
            return f"Erro de Permissão: Feche o arquivo '{os.path.basename(caminho_arquivo_excel)}' antes de tentar salvá-lo."
        return f"Ocorreu um erro inesperado: {e}"