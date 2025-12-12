# app/ui/grade_creator_widget.py

import pandas as pd
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QWidget, 
    QLabel, QLineEdit, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt

# Imports
from app.tasks.mapping_manager import mapping_manager
from app.tasks.schedule_processor import find_unmapped_programs
from app.workers import GradeExtractionWorker, GradeComparisonWorker, EpgGeneratorWorker
# Importe sua classe MappingEditorWidget do local correto (se for arquivo separado)
# from app.ui.mapping_editor_widget import MappingEditorWidget 

# Se a classe MappingEditorWidget estiver neste arquivo ou colada abaixo, mantenha.
# Vou assumir que ela está em arquivo separado conforme boas práticas, 
# mas se não estiver, cole-a aqui antes da classe GradeCreatorWidget.

class GradeCreatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_pdf_files = []
        
        # Variáveis de estado
        self.current_output_path = None
        self.current_anterior_path = None
        
        # Layout Principal
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Cabeçalho ---
        header_layout = QHBoxLayout()
        title_label = QLabel("Painel de Controle de Grades")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        
        self.settings_button = QPushButton("Gerenciar DE-PARA")
        self.settings_button.setFixedSize(150, 30)
        self.settings_button.clicked.connect(self._open_mapping_manager)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.settings_button)
        self.layout.addLayout(header_layout)

        # ============================================================
        # BLOCO 1: EXTRAÇÃO & BASE (A Fonte da Verdade)
        # ============================================================
        group1 = QGroupBox("1. Extração de Dados (Base)")
        group1.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #aaa; margin-top: 10px; padding-top: 15px; } QGroupBox::title { top: -8px; left: 10px; }")
        layout1 = QVBoxLayout()
        
        # Input PDF
        pdf_layout = QHBoxLayout()
        self.pdf_path_edit = QLineEdit("Nenhum PDF selecionado")
        self.pdf_path_edit.setReadOnly(True)
        select_pdf_btn = QPushButton("Selecionar PDFs da Semana...")
        select_pdf_btn.clicked.connect(self._select_pdfs)
        pdf_layout.addWidget(select_pdf_btn)
        pdf_layout.addWidget(self.pdf_path_edit)
        layout1.addLayout(pdf_layout)
        
        # Action 1
        self.btn_simple = QPushButton("Gerar Planilha Simples")
        self.btn_simple.setStyleSheet("padding: 6px; font-weight: bold;")
        self.btn_simple.clicked.connect(self._run_simple_schedule)
        layout1.addWidget(self.btn_simple)
        
        group1.setLayout(layout1)
        self.layout.addWidget(group1)

        # ============================================================
        # BLOCO 2: GRADE COMPARADA (Operacional)
        # ============================================================
        group2 = QGroupBox("2. Grade Comparada (Visual)")
        group2.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #aaa; margin-top: 10px; padding-top: 15px; } QGroupBox::title { top: -8px; left: 10px; }")
        layout2 = QVBoxLayout()
        
        # Input Grade Anterior
        ant_layout = QHBoxLayout()
        self.anterior_path_edit = QLineEdit("Nenhuma grade anterior selecionada")
        self.anterior_path_edit.setReadOnly(True)
        select_ant_btn = QPushButton("Selecionar Grade Anterior (Template)...")
        select_ant_btn.clicked.connect(self._select_anterior)
        ant_layout.addWidget(select_ant_btn)
        ant_layout.addWidget(self.anterior_path_edit)
        layout2.addLayout(ant_layout)
        
        # Action 2
        self.btn_compare = QPushButton("Criar Nova Grade Comparada")
        self.btn_compare.setStyleSheet("padding: 6px; font-weight: bold;")
        self.btn_compare.clicked.connect(self._run_comparison)
        layout2.addWidget(self.btn_compare)
        
        group2.setLayout(layout2)
        self.layout.addWidget(group2)

        # ============================================================
        # BLOCO 3: EPG & DATABASE (Sistema)
        # ============================================================
        group3 = QGroupBox("3. EPG & Database")
        group3.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #aaa; margin-top: 10px; padding-top: 15px; } QGroupBox::title { top: -8px; left: 10px; }")
        layout3 = QVBoxLayout()
        
        info_label = QLabel("Este processo utiliza o Banco de Dados interno (epg_database.csv) para preencher as informações.")
        info_label.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 5px; font-style: italic;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout3.addWidget(info_label)
        
        # Action 3
        self.btn_epg = QPushButton("Criar Novo Arquivo EPG")
        self.btn_epg.setStyleSheet("padding: 6px; font-weight: bold;")
        self.btn_epg.clicked.connect(self._run_epg)
        layout3.addWidget(self.btn_epg)
        
        group3.setLayout(layout3)
        self.layout.addWidget(group3)

        # --- Status ---
        self.status_label = QLabel("Pronto.")
        self.status_label.setStyleSheet("margin-top: 15px; font-size: 12px; color: green; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.status_label)
        self.layout.addStretch()

    # --- Funções Auxiliares de UI ---
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
        # Importe aqui ou no topo
        from app.ui.mapping_editor_widget import MappingEditorWidget 
        editor = MappingEditorWidget() 
        editor.exec()

    # ===================================================================
    # == FLUXO DE CONTROLE (Check de Mapeamento -> Execução)           ==
    # ===================================================================

    def _check_and_start_processing(self, run_mode):
        if not self.selected_pdf_files:
            self.status_label.setText("Erro: Selecione os PDFs no Bloco 1.")
            return

        self._lock_ui("Verificando mapeamento...")
        self.extraction_worker = GradeExtractionWorker(self.selected_pdf_files)
        self.extraction_worker.finished.connect(
            lambda df, error: self._handle_mapping_check(df, error, run_mode)
        )
        self.extraction_worker.start()

    def _handle_mapping_check(self, df_extracted, error, run_mode):
        if error:
            self._unlock_ui(); self.status_label.setText(error); return

        unmapped, map_error = find_unmapped_programs(df_extracted=df_extracted)
        
        if unmapped:
            self._unlock_ui()
            self.status_label.setText(f"Atenção: {len(unmapped)} novos programas.")
            
            from app.ui.mapping_editor_widget import MappingEditorWidget 
            editor = MappingEditorWidget(new_unmapped_list=unmapped)
            
            if editor.exec() == QDialog.DialogCode.Accepted:
                self.status_label.setText("Mapeamento atualizado. Reiniciando...")
                # Reinicia o fluxo
                if run_mode == 'simple': self._run_simple_schedule()
                elif run_mode == 'comparison': self._run_comparison()
                elif run_mode == 'epg': self._run_epg()
            else:
                self.status_label.setText("Mapeamento cancelado.")
        else:
            # Tudo ok, segue o baile
            if run_mode == 'simple': self._start_simple(df_extracted)
            elif run_mode == 'comparison': self._start_comparison(df_extracted)
            elif run_mode == 'epg': self._start_epg(df_extracted)

    # --- Runners ---
    def _run_simple_schedule(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Simples...", filter="Excel (*.xlsx)")
        if path:
            self.current_output_path = path
            self._check_and_start_processing('simple')

    def _start_simple(self, df):
        self._lock_ui("Gerando Planilha Simples...")
        try:
            df.to_excel(self.current_output_path, index=False, sheet_name="Grade Limpa")
            self.status_label.setText(f"Sucesso! Salvo em '{os.path.basename(self.current_output_path)}'")
        except Exception as e:
            self.status_label.setText(f"Erro: {e}")
        self._unlock_ui()

    def _run_comparison(self):
        if "Nenhuma" in self.anterior_path_edit.text():
            self.status_label.setText("Erro: Selecione a Grade Anterior no Bloco 2.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Comparada...", filter="Excel (*.xlsx)")
        if path:
            self.current_output_path = path
            self._check_and_start_processing('comparison')

    def _start_comparison(self, df):
        self._lock_ui("Gerando Grade Comparada...")
        self.comp_worker = GradeComparisonWorker(df, self.anterior_path_edit.text(), self.current_output_path)
        self.comp_worker.finished.connect(self._finish_task)
        self.comp_worker.start()

    def _run_epg(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar EPG...", filter="Excel (*.xlsx)")
        if path:
            self.current_output_path = path
            self._check_and_start_processing('epg')

    def _start_epg(self, df):
        self._lock_ui("Gerando EPG e Atualizando Banco de Dados...")
        self.epg_worker = EpgGeneratorWorker(df, self.current_output_path)
        self.epg_worker.finished.connect(self._finish_task)
        self.epg_worker.start()

    def _finish_task(self, msg):
        self._unlock_ui()
        self.status_label.setText(msg)

    def _lock_ui(self, msg):
        self.status_label.setText(msg)
        self.btn_simple.setEnabled(False)
        self.btn_compare.setEnabled(False)
        self.btn_epg.setEnabled(False)

    def _unlock_ui(self):
        self.btn_simple.setEnabled(True)
        self.btn_compare.setEnabled(True)
        self.btn_epg.setEnabled(True)