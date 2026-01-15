# app/workers.py
from PySide6.QtCore import QThread, Signal
import pandas as pd

# Importando a Lógica de Negócio (Tasks)
# Mantemos a organização: a inteligência fica em 'tasks', a execução paralela fica aqui.
from app.tasks.excel_consolidator import processar_logs_para_excel
from app.tasks.schedule_processor import (
    extract_and_clean_from_pdfs,
    generate_comparison_report,
    generate_epg_from_simple_schedule
)

# ============================================================================
# WORKER 1: Consolidador de Logs (Para a primeira ferramenta)
# ============================================================================
class ExcelConsolidatorWorker(QThread):
    finished = Signal(str) # Retorna a mensagem de sucesso ou erro

    def __init__(self, arquivos, saida, aba):
        super().__init__()
        self.arquivos = arquivos
        self.saida = saida
        self.aba = aba

    def run(self):
        try:
            # Chama a função original que está em app/tasks/excel_consolidator.py
            resultado = processar_logs_para_excel(self.arquivos, self.saida, self.aba)
            self.finished.emit(resultado)
        except Exception as e:
            self.finished.emit(f"Erro Crítico no Worker: {str(e)}")

# ============================================================================
# WORKER 2: Extração de PDF (Usado por Comparador e EPG)
# ============================================================================
class GradeExtractionWorker(QThread):
    # Retorna dois valores: O DataFrame (se der certo) e a Mensagem de Erro (se der errado)
    finished = Signal(object, str) 

    def __init__(self, pdf_paths):
        super().__init__()
        self.pdf_paths = pdf_paths

    def run(self):
        try:
            # Chama a função de extração e ordenação em app/tasks/schedule_processor.py
            df, erro = extract_and_clean_from_pdfs(self.pdf_paths)
            self.finished.emit(df, erro)
        except Exception as e:
            self.finished.emit(None, f"Erro inesperado na thread de extração: {e}")

# ============================================================================
# WORKER 3: Comparação de Grades (Pinta de Verde)
# ============================================================================
class GradeComparisonWorker(QThread):
    finished = Signal(str)

    def __init__(self, df_novo, path_anterior, path_saida):
        super().__init__()
        self.df_novo = df_novo
        self.path_anterior = path_anterior
        self.path_saida = path_saida

    def run(self):
        try:
            # Chama a função de comparação estética em app/tasks/schedule_processor.py
            resultado = generate_comparison_report(self.df_novo, self.path_anterior, self.path_saida)
            self.finished.emit(resultado)
        except Exception as e:
            self.finished.emit(f"Erro na thread de comparação: {e}")

# ============================================================================
# WORKER 4: Gerador de EPG (Visual de TV)
# ============================================================================
class EpgGeneratorWorker(QThread):
    finished = Signal(str)

    def __init__(self, df_grade, path_saida):
        super().__init__()
        self.df_grade = df_grade
        self.path_saida = path_saida

    def run(self):
        try:
            # Chama a função de EPG em app/tasks/schedule_processor.py
            resultado = generate_epg_from_simple_schedule(self.df_grade, self.path_saida)
            self.finished.emit(resultado)
        except Exception as e:
            self.finished.emit(f"Erro na thread de EPG: {e}")


# ============================================================================
# WORKER 5: Dashboard de Antenas (Monitor de cidades fora do ar)
# ============================================================================
class AntennaDashboardWorker(QThread):
    # Retorna (success: bool, message: str)
    finished = Signal(bool, str)

    def __init__(self, xlsx_paths, output_path):
        super().__init__()
        # Aceita tanto string única quanto lista de arquivos
        if isinstance(xlsx_paths, str):
            self.xlsx_paths = [xlsx_paths]
        else:
            self.xlsx_paths = xlsx_paths
        self.output_path = output_path

    def run(self):
        try:
            from app.tasks.antenna_data_manager import antenna_manager
            from app.tasks.dashboard_generator import generate_dashboard_pdf
            
            # 1. Carrega todas as planilhas organizadas por data
            reports_by_date, error = antenna_manager.load_multiple_reports(self.xlsx_paths)
            if error:
                self.finished.emit(False, error)
                return
            
            if not reports_by_date:
                self.finished.emit(False, "Nenhum relatório carregado")
                return
            
            # 2. Carrega base de cidades (opcional, para regiões)
            df_database, _ = antenna_manager.load_cities_database()
            
            # 3. Processa dados da semana e calcula métricas
            metrics, error = antenna_manager.process_weekly_data(reports_by_date, df_database)
            if error:
                self.finished.emit(False, error)
                return
            
            # 4. Gera PDF com 3 páginas
            success, message = generate_dashboard_pdf(metrics, self.output_path)
            
            self.finished.emit(success, message)
            
        except Exception as e:
            import traceback
            self.finished.emit(False, f"Erro no worker: {e}\n{traceback.format_exc()}")