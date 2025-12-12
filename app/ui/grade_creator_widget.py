# app/ui/grade_creator_widget.py

import pandas as pd
import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QAbstractItemView,
    QHeaderView, QMessageBox, QFileDialog, QWidget, QLabel, QLineEdit, QGroupBox, QApplication
)
from PySide6.QtCore import Qt, QAbstractTableModel
from app.tasks.schedule_processor import find_unmapped_programs

# Importa o Gerenciador de Mapeamento e a Janela de Edição (se estiver no mesmo arquivo ou separado)
from app.tasks.mapping_manager import mapping_manager
# Se o MappingEditor estiver em outro arquivo, importe de lá. Se estiver aqui, mantenha a classe abaixo.

# IMPORTANTE: Importa os Workers que criamos
from app.workers import GradeExtractionWorker, GradeComparisonWorker, EpgGeneratorWorker

# =======================================================
# == CLASSES AUXILIARES (MODEL E EDITOR)               ==
# =======================================================

class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data
    def rowCount(self, parent=None): return self._data.shape[0]
    def columnCount(self, parent=None): return self._data.shape[1]
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and (role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole):
            return str(self._data.iloc[index.row(), index.column()])
        return None
    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole: self._data.iloc[index.row(), index.column()] = value; return True
        return False
    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal: return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical: return str(self._data.index[section])
        return None
    def flags(self, index): return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

# (Estou assumindo que a classe MappingEditorWidget está importada ou definida aqui. 
# Se você já tem ela em outro arquivo, importe-a. Se não, mantenha o código dela aqui.)
# Vou importar do arquivo mapping_editor_widget.py para manter limpo, ou você pode colar a classe aqui de volta.
# from app.ui.mapping_editor_widget import MappingEditorWidget 
# CASO A CLASSE ESTEJA AQUI MESMO NO SEU ARQUIVO ORIGINAL, MANTENHA-A.
# ABAIXO, VOU MANTER O ESPAÇO RESERVADO PARA ELA:

class MappingEditorWidget(QDialog):
    # ... (MANTENHA SEU CÓDIGO DA CLASSE MappingEditorWidget AQUI SE ELA NÃO ESTIVER EM ARQUIVO SEPARADO) ...
    # Como você me mandou um "pass" no exemplo anterior, vou assumir que você sabe onde ela está.
    # Se precisar que eu cole ela inteira de novo, me avise. 
    # Por segurança, vou deixar importada do arquivo separado se você tiver criado, senão, cole ela aqui.
    pass 

# =======================================================
# == WIDGET PRINCIPAL DA FERRAMENTA "CRIADOR DE GRADE" ==
# =======================================================

class GradeCreatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_pdf_files = []
        
        # Variáveis de estado para guardar caminhos antes da verificação de mapeamento
        self.current_output_path = None
        self.current_anterior_path = None
        
        # Layout Principal (restante do __init__ continua igual)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Título e Botão de Gerenciamento ---
        # ... (Mantido igual)
        title_layout = QHBoxLayout()
        title_label = QLabel("Painel de Controle de Grades")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.settings_button = QPushButton("Gerenciar DE-PARA")
        self.settings_button.setFixedSize(150, 30)
        self.settings_button.clicked.connect(self._open_mapping_manager)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.settings_button)
        self.layout.addLayout(title_layout)

        # --- Entradas ---
        # ... (Mantido igual)
        inputs_group = QGroupBox("Entradas")
        inputs_layout = QVBoxLayout()
        # PDFs
        self.pdf_path_edit = QLineEdit("Nenhum PDF selecionado")
        self.pdf_path_edit.setReadOnly(True)
        select_pdf_button = QPushButton("1. Selecionar PDFs da Nova Grade...")
        select_pdf_button.clicked.connect(self._select_pdfs)
        inputs_layout.addWidget(select_pdf_button)
        inputs_layout.addWidget(self.pdf_path_edit)
        # Grade Anterior
        self.anterior_path_edit = QLineEdit("Nenhum arquivo selecionado (opcional)")
        self.anterior_path_edit.setReadOnly(True)
        select_anterior_button = QPushButton("2. Selecionar Grade Anterior (Excel)...")
        select_anterior_button.clicked.connect(self._select_anterior)
        inputs_layout.addWidget(select_anterior_button)
        inputs_layout.addWidget(self.anterior_path_edit)
        inputs_group.setLayout(inputs_layout)
        self.layout.addWidget(inputs_group)
        
        # --- Ações de Saída ---
        actions_group = QGroupBox("Ações de Saída")
        actions_layout = QVBoxLayout()
        
        # Ação 1: Simples
        self.simple_schedule_button = QPushButton("Gerar Planilha Simples")
        self.simple_schedule_button.clicked.connect(self._run_simple_schedule)
        actions_layout.addWidget(self.simple_schedule_button)
        
        # Ação 2: Comparada
        self.comparison_button = QPushButton("Gerar Grade Comparada")
        self.comparison_button.clicked.connect(self._run_comparison)
        actions_layout.addWidget(self.comparison_button)
        
        # Ação 3: EPG
        self.epg_button = QPushButton("Gerar Grade EPG")
        self.epg_button.setEnabled(True) 
        self.epg_button.clicked.connect(self._run_epg) 
        actions_layout.addWidget(self.epg_button)
        
        actions_group.setLayout(actions_layout)
        self.layout.addWidget(actions_group)

        self.status_label = QLabel("Pronto.")
        self.status_label.setStyleSheet("margin-top: 15px;")
        self.layout.addWidget(self.status_label)
        self.layout.addStretch()

    # --- Funções de Seleção de Arquivo ---
    def _select_pdfs(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Selecione os PDFs", filter="Arquivos PDF (*.pdf)")
        if paths:
            self.selected_pdf_files = paths
            self.pdf_path_edit.setText(f"{len(paths)} arquivos selecionados")

    def _select_anterior(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecione a Grade Anterior", filter="Excel (*.xlsx *.xls)")
        if path:
            self.anterior_path_edit.setText(path)

    def _open_mapping_manager(self):
        # Importe aqui se a classe estiver em outro arquivo para evitar erro circular
        from app.ui.mapping_editor_widget import MappingEditorWidget 
        editor = MappingEditorWidget(self)
        editor.exec()

    # ===================================================================
    # == NOVO: FUNÇÕES DE CONTROLE DE FLUXO (VALIDAÇÃO DE MAPA)        ==
    # ===================================================================

    def _check_and_start_processing(self, run_mode):
        """
        Gatilho central. 
        1. Inicia a extração em background.
        2. Quando termina, a função _handle_mapping_check_result assume.
        """
        if not self.selected_pdf_files:
            self.status_label.setText("Erro: Selecione os PDFs da Nova Grade.")
            self.current_output_path = None # Limpa caminhos em caso de erro
            return

        self._lock_ui("Fase 1/2: Extraindo dados e verificando mapeamento pendente...")
        
        # Inicia Worker de Extração (roda a lógica pesada em outra thread)
        self.extraction_worker = GradeExtractionWorker(self.selected_pdf_files)
        
        # Quando terminar, chama a próxima etapa, passando o modo
        self.extraction_worker.finished.connect(
            lambda df, error: self._handle_mapping_check_result(df, error, run_mode)
        )
        self.extraction_worker.start()

    def _handle_mapping_check_result(self, df_extracted, error, run_mode):
        """
        Processa o resultado da extração e decide se abre o pop-up de mapeamento.
        """
        
        if error:
            self._unlock_ui()
            self.status_label.setText(error)
            return

        # Busca a lista de programas não mapeados
        # Nota: Essa função find_unmapped_programs já está otimizada para ser rápida.
        unmapped_programs, map_error = find_unmapped_programs(df_extracted=df_extracted)

        if map_error:
            self._unlock_ui()
            self.status_label.setText(f"Erro ao verificar mapeamento: {map_error}")
            return
        
        if unmapped_programs:
            # === GATILHO DO POP-UP ===
            self.status_label.setText(f"ATENÇÃO: {len(unmapped_programs)} programas novos. Abrindo editor...")
            self._unlock_ui() # Destrava para que a janela modal do editor funcione

            from app.ui.mapping_editor_widget import MappingEditorWidget
            editor = MappingEditorWidget(new_unmapped_list=unmapped_programs)
            
            # Executa a janela modal. Se retornar Accepted (salvou e fechou):
            if editor.exec() == QDialog.DialogCode.Accepted:
                self.status_label.setText("Mapeamento salvo com sucesso. Reiniciando processo...")
                # Reinicia o fluxo para a tarefa original
                if run_mode == 'simple': self._run_simple_schedule()
                elif run_mode == 'comparison': self._run_comparison()
                elif run_mode == 'epg': self._run_epg()
            else:
                self.status_label.setText("Mapeamento cancelado. Ação abortada.")
        
        else:
            # NENHUM NOVO PROGRAMA. Continua o fluxo normalmente.
            self.status_label.setText("Mapeamento OK. Iniciando processamento final...")
            
            if run_mode == 'simple': self._start_simple_schedule_phase_2(df_extracted)
            elif run_mode == 'comparison': self._start_comparison_phase_2(df_extracted, self.current_anterior_path, self.current_output_path)
            elif run_mode == 'epg': self._start_epg_phase_2(df_extracted, self.current_output_path)

    # ===================================================================
    # == RE-MAPEANDO AS FUNÇÕES DE BOTÃO PARA O NOVO FLUXO             ==
    # ===================================================================

    def _run_simple_schedule(self):
        """Prepara caminhos e inicia o checkup de mapeamento."""
        output_path, _ = QFileDialog.getSaveFileName(self, "Salvar Planilha Simples Como...", filter="Arquivos Excel (*.xlsx)")
        if not output_path: return
        self.current_output_path = output_path # Guarda o caminho
        
        self._check_and_start_processing('simple')
        
    def _start_simple_schedule_phase_2(self, df):
        """Continuação APÓS checkup de mapeamento (agora com dados limpos)."""
        output_path = self.current_output_path
        self._lock_ui("Gerando planilha simples...")
        try:
            df.to_excel(output_path, index=False, sheet_name="Grade Limpa")
            self.status_label.setText(f"Sucesso! Planilha simples salva em '{output_path}'")
        except Exception as e:
            self.status_label.setText(f"Erro ao salvar o Excel: {e}")
        self._unlock_ui()


    def _run_comparison(self):
        """Prepara caminhos e inicia o checkup de mapeamento."""
        anterior_path = self.anterior_path_edit.text()
        if "Nenhum arquivo" in anterior_path:
            self.status_label.setText("Erro: Para comparar, selecione a Grade Anterior (Excel).")
            return
        
        output_path, _ = QFileDialog.getSaveFileName(self, "Salvar Grade Comparada Como...", filter="Arquivos Excel (*.xlsx)")
        if not output_path: return
        
        self.current_output_path = output_path
        self.current_anterior_path = anterior_path
        self._check_and_start_processing('comparison')

    def _start_comparison_phase_2(self, df_novo, anterior_path, output_path):
        """Continuação APÓS checkup de mapeamento (agora com dados limpos)."""
        output_path = self.current_output_path
        anterior_path = self.current_anterior_path
        
        self._lock_ui("Fase 2/2: Comparando e formatando Excel...")
        
        # Inicia Worker de Comparação
        self.comparison_worker = GradeComparisonWorker(df_novo, anterior_path, output_path)
        self.comparison_worker.finished.connect(self._finish_generic_task)
        self.comparison_worker.start()

    def _run_epg(self):
        """Prepara caminhos e inicia o checkup de mapeamento."""
        output_path, _ = QFileDialog.getSaveFileName(self, "Salvar EPG...", filter="Arquivos Excel (*.xlsx)")
        if not output_path: return
        self.current_output_path = output_path
        self._check_and_start_processing('epg')

    def _start_epg_phase_2(self, df_grade, output_path):
        """Continuação APÓS checkup de mapeamento (agora com dados limpos)."""
        output_path = self.current_output_path

        self._lock_ui("Fase 2/2: Gerando visual EPG...")

        # Inicia Worker de EPG
        self.epg_worker = EpgGeneratorWorker(df_grade, output_path)
        self.epg_worker.finished.connect(self._finish_generic_task)
        self.epg_worker.start()

    # --- Funções Genéricas de UI ---
    def _finish_generic_task(self, resultado):
        self._unlock_ui()
        self.status_label.setText(resultado)

    def _lock_ui(self, message):
        self.status_label.setText(f"{message} (Pode continuar usando o PC)")
        self.simple_schedule_button.setEnabled(False)
        self.comparison_button.setEnabled(False)
        self.epg_button.setEnabled(False)

    def _unlock_ui(self):
        self.simple_schedule_button.setEnabled(True)
        self.comparison_button.setEnabled(True)
        self.epg_button.setEnabled(True)