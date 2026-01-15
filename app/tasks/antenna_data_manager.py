# app/tasks/antenna_data_manager.py
"""
Gerenciador de dados de antenas/cidades fora do ar.
Processa múltiplas planilhas, calcula métricas e mantém histórico.
"""

import os
import sys
import re
import shutil
import pandas as pd
from PySide6.QtCore import QStandardPaths
from datetime import datetime, timedelta


class AntennaDataManager:
    def __init__(self, db_filename="cidades_base.csv", history_filename="historico_antenas.csv"):
        """Inicializa o gerenciador com o banco de cidades e histórico."""
        # Define pasta de dados no AppData
        app_data_root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.app_dir = os.path.join(app_data_root, "AutomateTools")
        os.makedirs(self.app_dir, exist_ok=True)
        
        # Caminho do banco de cidades
        self.db_filepath = os.path.join(self.app_dir, db_filename)
        
        # Caminho do histórico
        self.history_filepath = os.path.join(self.app_dir, history_filename)
        
        # Copia templates se não existirem
        if not os.path.exists(self.db_filepath):
            self._copy_template(db_filename)
        
        if not os.path.exists(self.history_filepath):
            self._create_empty_history()
    
    def _copy_template(self, filename):
        """Copia template da pasta resources para AppData."""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
        else:
            base_path = os.path.abspath(".")
        
        template_path = os.path.join(base_path, "resources", filename)
        
        if os.path.exists(template_path):
            shutil.copy(template_path, self.db_filepath)
        else:
            pd.DataFrame(columns=["CIDADE", "ESTADO", "REGIAO"]).to_csv(self.db_filepath, index=False)
    
    def _create_empty_history(self):
        """Cria arquivo de histórico vazio."""
        columns = ["CIDADE", "ESTADO", "REGIAO", "MOTIVO", "DATA_ENTRADA", "DATA_SAIDA", "DIAS_FORA", "STATUS"]
        pd.DataFrame(columns=columns).to_csv(self.history_filepath, index=False)
    
    def get_db_filepath(self):
        """Retorna caminho do banco de cidades."""
        return self.db_filepath
    
    def get_history_filepath(self):
        """Retorna caminho do histórico."""
        return self.history_filepath
    
    def load_cities_database(self):
        """Carrega o banco de dados de cidades."""
        try:
            if not os.path.exists(self.db_filepath):
                return None, f"Banco de cidades não encontrado: {self.db_filepath}"
            
            df = pd.read_csv(self.db_filepath)
            if df.shape[1] < 2:
                df = pd.read_csv(self.db_filepath, sep=';')
            
            # Normaliza nomes das colunas
            df.columns = df.columns.str.strip().str.upper()
            
            return df, None
        except Exception as e:
            return None, f"Erro ao carregar banco de cidades: {e}"
    
    def load_history(self):
        """Carrega o histórico de ocorrências."""
        try:
            if not os.path.exists(self.history_filepath):
                self._create_empty_history()
            
            df = pd.read_csv(self.history_filepath)
            return df, None
        except Exception as e:
            return None, f"Erro ao carregar histórico: {e}"
    
    def save_history(self, df_history):
        """Salva o histórico de ocorrências."""
        try:
            df_history.to_csv(self.history_filepath, index=False)
            return True, None
        except Exception as e:
            return False, f"Erro ao salvar histórico: {e}"
    
    def extract_date_from_filename(self, filepath):
        """
        Extrai a data do nome do arquivo.
        Formato esperado: call_center_DD-MM-YYYY.xlsx
        """
        filename = os.path.basename(filepath)
        
        # Tenta encontrar padrão DD-MM-YYYY
        match = re.search(r'(\d{2})-(\d{2})-(\d{4})', filename)
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except:
                pass
        
        # Tenta padrão YYYY-MM-DD
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            year, month, day = match.groups()
            try:
                return datetime(int(year), int(month), int(day))
            except:
                pass
        
        return None
    
    def load_antenna_report(self, excel_path):
        """Carrega uma planilha de antenas fora do ar."""
        try:
            df = pd.read_excel(excel_path)
            df.columns = df.columns.str.strip().str.upper()
            
            # Verifica colunas esperadas
            required_cols = ['CIDADE', 'ESTADO', 'STATUS ATUAL']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                return None, f"Colunas faltando: {missing}"
            
            df['CIDADE'] = df['CIDADE'].astype(str).str.strip().str.upper()
            df['ESTADO'] = df['ESTADO'].astype(str).str.strip().str.upper()
            
            return df, None
        except Exception as e:
            return None, f"Erro ao ler planilha: {e}"
    
    def load_multiple_reports(self, excel_paths):
        """
        Carrega múltiplas planilhas e retorna um dict organizado por data.
        Returns: ({data: DataFrame}, error)
        """
        reports = {}
        
        for path in excel_paths:
            date = self.extract_date_from_filename(path)
            if date is None:
                return None, f"Não foi possível extrair data do arquivo: {os.path.basename(path)}"
            
            df, error = self.load_antenna_report(path)
            if error:
                return None, error
            
            reports[date] = df
        
        # Ordena por data
        reports = dict(sorted(reports.items()))
        
        return reports, None
    
    def process_weekly_data(self, reports_by_date, df_database=None):
        """
        Processa os relatórios da semana e calcula todas as métricas.
        
        Args:
            reports_by_date: dict {datetime: DataFrame}
            df_database: DataFrame com banco de cidades (opcional)
        
        Returns: dict com todas as métricas
        """
        if not reports_by_date:
            return None, "Nenhum relatório para processar"
        
        dates = sorted(reports_by_date.keys())
        first_date = dates[0]
        last_date = dates[-1]
        
        # Carrega histórico existente
        df_history, _ = self.load_history()
        if df_history is None:
            df_history = pd.DataFrame(columns=["CIDADE", "ESTADO", "REGIAO", "MOTIVO", "DATA_ENTRADA", "DATA_SAIDA", "DIAS_FORA", "STATUS"])
        
        # Prepara banco de cidades para lookup de região
        region_map = {}
        if df_database is not None and not df_database.empty:
            df_database['CIDADE'] = df_database['CIDADE'].astype(str).str.strip().str.upper()
            df_database['ESTADO'] = df_database['ESTADO'].astype(str).str.strip().str.upper()
            for _, row in df_database.iterrows():
                key = f"{row['CIDADE']}|{row['ESTADO']}"
                region_map[key] = row.get('REGIAO', '')
        
        # Rastreia todas as cidades ao longo da semana
        all_cities_seen = {}  # {cidade|estado: {first_seen, last_seen, motivo, appearances}}
        
        for date, df_report in reports_by_date.items():
            # Encontra coluna de motivo
            motivo_col = None
            for col in df_report.columns:
                if 'MOTIVO' in col.upper():
                    motivo_col = col
                    break
            
            for _, row in df_report.iterrows():
                cidade = row.get('CIDADE', '')
                estado = row.get('ESTADO', '')
                motivo = row.get(motivo_col, '') if motivo_col else ''
                key = f"{cidade}|{estado}"
                
                if key not in all_cities_seen:
                    all_cities_seen[key] = {
                        'cidade': cidade,
                        'estado': estado,
                        'regiao': region_map.get(key, ''),
                        'motivo': motivo,
                        'first_seen': date,
                        'last_seen': date,
                        'appearances': [date]
                    }
                else:
                    all_cities_seen[key]['last_seen'] = date
                    all_cities_seen[key]['appearances'].append(date)
                    if motivo:
                        all_cities_seen[key]['motivo'] = motivo
        
        # Analisa status de cada cidade
        cidades_atuais = []  # Ainda fora do ar (aparece na última planilha)
        cidades_resolvidas = []  # Saiu durante a semana
        cidades_novas = []  # Entrou durante a semana
        
        last_report_cities = set()
        if last_date in reports_by_date:
            for _, row in reports_by_date[last_date].iterrows():
                last_report_cities.add(f"{row['CIDADE']}|{row['ESTADO']}")
        
        first_report_cities = set()
        if first_date in reports_by_date:
            for _, row in reports_by_date[first_date].iterrows():
                first_report_cities.add(f"{row['CIDADE']}|{row['ESTADO']}")
        
        for key, info in all_cities_seen.items():
            cidade_data = {
                'cidade': info['cidade'],
                'estado': info['estado'],
                'regiao': info['regiao'],
                'motivo': info['motivo'],
                'first_seen': info['first_seen'],
                'last_seen': info['last_seen'],
            }
            
            if key in last_report_cities:
                # Ainda fora do ar
                cidades_atuais.append(cidade_data)
                
                if key not in first_report_cities:
                    # Nova na semana (não estava na primeira planilha)
                    cidades_novas.append(cidade_data)
            else:
                # Não está na última planilha = resolvida
                cidade_data['data_resolucao'] = info['last_seen']
                cidades_resolvidas.append(cidade_data)
        
        # Atualiza histórico
        df_history = self._update_history(df_history, all_cities_seen, last_report_cities, last_date)
        self.save_history(df_history)
        
        # Calcula métricas
        metrics = self._calculate_metrics(
            reports_by_date=reports_by_date,
            cidades_atuais=cidades_atuais,
            cidades_resolvidas=cidades_resolvidas,
            cidades_novas=cidades_novas,
            df_history=df_history,
            df_database=df_database,
            first_date=first_date,
            last_date=last_date
        )
        
        return metrics, None
    
    def _update_history(self, df_history, all_cities_seen, last_report_cities, last_date):
        """Atualiza o histórico com os dados da semana."""
        
        # Converte para lista de dicts para facilitar manipulação
        history_records = df_history.to_dict('records') if not df_history.empty else []
        
        # Cria índice de registros ativos (STATUS = FORA DO AR)
        active_records = {}
        for i, record in enumerate(history_records):
            if record.get('STATUS') == 'FORA DO AR':
                key = f"{record['CIDADE']}|{record['ESTADO']}"
                active_records[key] = i
        
        for key, info in all_cities_seen.items():
            cidade = info['cidade']
            estado = info['estado']
            
            if key in last_report_cities:
                # Cidade ainda fora do ar
                if key in active_records:
                    # Atualiza registro existente
                    idx = active_records[key]
                    history_records[idx]['MOTIVO'] = info['motivo'] or history_records[idx].get('MOTIVO', '')
                else:
                    # Novo registro
                    new_record = {
                        'CIDADE': cidade,
                        'ESTADO': estado,
                        'REGIAO': info['regiao'],
                        'MOTIVO': info['motivo'],
                        'DATA_ENTRADA': info['first_seen'].strftime('%Y-%m-%d'),
                        'DATA_SAIDA': '',
                        'DIAS_FORA': (last_date - info['first_seen']).days + 1,
                        'STATUS': 'FORA DO AR'
                    }
                    history_records.append(new_record)
            else:
                # Cidade resolvida
                if key in active_records:
                    idx = active_records[key]
                    data_entrada = pd.to_datetime(history_records[idx]['DATA_ENTRADA'])
                    data_saida = info['last_seen']
                    dias_fora = (data_saida - data_entrada).days + 1
                    
                    history_records[idx]['DATA_SAIDA'] = data_saida.strftime('%Y-%m-%d')
                    history_records[idx]['DIAS_FORA'] = dias_fora
                    history_records[idx]['STATUS'] = 'RESOLVIDO'
        
        # Atualiza DIAS_FORA para registros ainda ativos
        for record in history_records:
            if record.get('STATUS') == 'FORA DO AR' and record.get('DATA_ENTRADA'):
                try:
                    data_entrada = pd.to_datetime(record['DATA_ENTRADA'])
                    record['DIAS_FORA'] = (last_date - data_entrada).days + 1
                except:
                    pass
        
        return pd.DataFrame(history_records)
    
    def _calculate_metrics(self, reports_by_date, cidades_atuais, cidades_resolvidas, 
                          cidades_novas, df_history, df_database, first_date, last_date):
        """Calcula todas as métricas para o dashboard."""
        
        metrics = {}
        
        # === PÁGINA 1: Resumo da Semana ===
        metrics['periodo'] = {
            'inicio': first_date.strftime('%d/%m/%Y'),
            'fim': last_date.strftime('%d/%m/%Y')
        }
        
        metrics['total_fora_atual'] = len(cidades_atuais)
        metrics['total_resolvidas_semana'] = len(cidades_resolvidas)
        metrics['total_novas_semana'] = len(cidades_novas)
        
        # Total de cidades no banco
        if df_database is not None and not df_database.empty:
            metrics['total_cidades_base'] = len(df_database)
            metrics['percentual_fora'] = round((len(cidades_atuais) / len(df_database)) * 100, 2)
        else:
            metrics['total_cidades_base'] = None
            metrics['percentual_fora'] = None
        
        # Tempo médio de resolução (das resolvidas na semana)
        if cidades_resolvidas:
            tempos = []
            for c in cidades_resolvidas:
                if c.get('first_seen') and c.get('data_resolucao'):
                    dias = (c['data_resolucao'] - c['first_seen']).days + 1
                    tempos.append(dias)
            metrics['tempo_medio_resolucao'] = round(sum(tempos) / len(tempos), 1) if tempos else 0
        else:
            metrics['tempo_medio_resolucao'] = 0
        
        # Taxa de resolução
        total_periodo = len(cidades_atuais) + len(cidades_resolvidas)
        if total_periodo > 0:
            metrics['taxa_resolucao'] = round((len(cidades_resolvidas) / total_periodo) * 100, 1)
        else:
            metrics['taxa_resolucao'] = 0
        
        # Por Estado (atual)
        por_estado = {}
        for c in cidades_atuais:
            estado = c.get('estado', 'N/D')
            por_estado[estado] = por_estado.get(estado, 0) + 1
        metrics['por_estado'] = dict(sorted(por_estado.items(), key=lambda x: x[1], reverse=True))
        
        # Por Motivo (atual)
        por_motivo = {}
        for c in cidades_atuais:
            motivo = c.get('motivo', 'N/D') or 'N/D'
            por_motivo[motivo] = por_motivo.get(motivo, 0) + 1
        metrics['por_motivo'] = dict(sorted(por_motivo.items(), key=lambda x: x[1], reverse=True))
        
        # Por Região (atual)
        por_regiao = {}
        for c in cidades_atuais:
            regiao = c.get('regiao', 'N/D') or 'N/D'
            por_regiao[regiao] = por_regiao.get(regiao, 0) + 1
        metrics['por_regiao'] = dict(sorted(por_regiao.items(), key=lambda x: x[1], reverse=True))
        
        # === PÁGINA 2: Tendência ===
        
        # Evolução diária
        evolucao_diaria = []
        for date in sorted(reports_by_date.keys()):
            df = reports_by_date[date]
            evolucao_diaria.append({
                'data': date,
                'data_str': date.strftime('%d/%m'),
                'quantidade': len(df)
            })
        metrics['evolucao_diaria'] = evolucao_diaria
        
        # Indicador de tendência
        if len(evolucao_diaria) >= 2:
            diff = evolucao_diaria[-1]['quantidade'] - evolucao_diaria[0]['quantidade']
            if diff < 0:
                metrics['tendencia'] = {'status': 'MELHORANDO', 'diff': diff}
            elif diff > 0:
                metrics['tendencia'] = {'status': 'PIORANDO', 'diff': f"+{diff}"}
            else:
                metrics['tendencia'] = {'status': 'ESTÁVEL', 'diff': 0}
        else:
            metrics['tendencia'] = {'status': 'N/D', 'diff': 0}
        
        # Tempo médio por categoria (do histórico)
        tempo_por_motivo = {}
        tempo_por_regiao = {}
        
        if not df_history.empty:
            df_resolvidos = df_history[df_history['STATUS'] == 'RESOLVIDO'].copy()
            if not df_resolvidos.empty:
                df_resolvidos['DIAS_FORA'] = pd.to_numeric(df_resolvidos['DIAS_FORA'], errors='coerce')
                
                # Por motivo
                for motivo in df_resolvidos['MOTIVO'].dropna().unique():
                    dias = df_resolvidos[df_resolvidos['MOTIVO'] == motivo]['DIAS_FORA'].mean()
                    if pd.notna(dias):
                        tempo_por_motivo[motivo] = round(dias, 1)
                
                # Por região
                for regiao in df_resolvidos['REGIAO'].dropna().unique():
                    dias = df_resolvidos[df_resolvidos['REGIAO'] == regiao]['DIAS_FORA'].mean()
                    if pd.notna(dias):
                        tempo_por_regiao[regiao] = round(dias, 1)
        
        metrics['tempo_medio_por_motivo'] = dict(sorted(tempo_por_motivo.items(), key=lambda x: x[1]))
        metrics['tempo_medio_por_regiao'] = dict(sorted(tempo_por_regiao.items(), key=lambda x: x[1]))
        
        # === PÁGINA 3: Histórico ===
        
        # Top 10 há mais tempo fora do ar
        top_criticas = []
        if not df_history.empty:
            df_ativos = df_history[df_history['STATUS'] == 'FORA DO AR'].copy()
            df_ativos['DIAS_FORA'] = pd.to_numeric(df_ativos['DIAS_FORA'], errors='coerce')
            df_ativos = df_ativos.sort_values('DIAS_FORA', ascending=False).head(10)
            
            for _, row in df_ativos.iterrows():
                top_criticas.append({
                    'cidade': row['CIDADE'],
                    'estado': row['ESTADO'],
                    'dias': int(row['DIAS_FORA']) if pd.notna(row['DIAS_FORA']) else 0,
                    'motivo': row.get('MOTIVO', '')
                })
        
        metrics['top_criticas'] = top_criticas
        
        # Lista de resolvidas na semana
        metrics['lista_resolvidas'] = [
            {
                'cidade': c['cidade'],
                'estado': c['estado'],
                'motivo': c.get('motivo', ''),
                'dias': (c['data_resolucao'] - c['first_seen']).days + 1 if c.get('data_resolucao') and c.get('first_seen') else 0
            }
            for c in cidades_resolvidas[:10]
        ]
        
        # Lista de atuais (para página detalhada)
        metrics['lista_atuais'] = [
            {
                'cidade': c['cidade'],
                'estado': c['estado'],
                'regiao': c.get('regiao', ''),
                'motivo': c.get('motivo', '')
            }
            for c in cidades_atuais
        ]
        
        metrics['data_geracao'] = datetime.now().strftime('%d/%m/%Y às %H:%M')
        
        return metrics


# Singleton para uso global
antenna_manager = AntennaDataManager()
