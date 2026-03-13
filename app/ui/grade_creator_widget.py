# app/ui/grade_creator_widget.py

import pandas as pd
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QWidget, 
    QLabel, QLineEdit, QGroupBox, QMessageBox, QListWidget, QListView
)
from PySide6.QtCore import Qt

# Imports
from app.tasks.mapping_manager import mapping_manager
from app.tasks.schedule_processor import find_unmapped_programs
from app.workers import GradeExtractionWorker, GradeComparisonWorker, EpgGeneratorWorker

class GradeCreatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_pdf_files = []
        self.current_output_path = ""
        self.current_anterior_path = ""
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title_label = QLabel("Painel de Controle de Grades")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(title_label)

        # ============================================================
        # SEÇÃO: ENTRADAS
        # ============================================================
        entrada_label = QLabel("ENTRADAS")
        entrada_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        self.layout.addWidget(entrada_label)

        entradas_layout = QHBoxLayout()
        entradas_layout.setSpacing(15)

        # Card PDFs
        pdf_card = QWidget()
        pdf_card.setStyleSheet("QWidget { background-color: #2a2a3e; border-radius: 8px; }")
        pdf_layout = QVBoxLayout(pdf_card)
        
        lbl_pdf_title = QLabel("📄 PDFs da Semana")
        lbl_pdf_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        pdf_layout.addWidget(lbl_pdf_title)
        
        self.pdf_list = QListWidget()
        self.pdf_list.setFlow(QListView.Flow.LeftToRight)
        self.pdf_list.setWrapping(True)
        self.pdf_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.pdf_list.setSpacing(5)
        self.pdf_list.setMaximumHeight(80)
        self.pdf_list.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; }"
            "QListWidget::item { background: #3a3a4e; color: white; border-radius: 12px; padding: 4px 8px; }"
        )
        pdf_layout.addWidget(self.pdf_list)

        btn_sel_pdf = QPushButton("Selecionar PDFs")
        btn_sel_pdf.setStyleSheet("QPushButton { border: 1px solid #3b82f6; color: #3b82f6; border-radius: 4px; padding: 6px; background: transparent; } QPushButton:hover { background: rgba(59, 130, 246, 0.1); }")
        btn_sel_pdf.clicked.connect(self._select_pdfs)
        pdf_layout.addWidget(btn_sel_pdf)
        entradas_layout.addWidget(pdf_card)

        # Card Grade Anterior
        ant_card = QWidget()
        ant_card.setStyleSheet("QWidget { background-color: #2a2a3e; border-radius: 8px; }")
        ant_layout = QVBoxLayout(ant_card)
        
        lbl_ant_title = QLabel("📊 Grade Anterior")
        lbl_ant_title.setStyleSheet("color: white; font-weight: bold; font-size: 14px; background: transparent;")
        lbl_ant_sub = QLabel("(opcional — Grade Comparada)")
        lbl_ant_sub.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        ant_layout.addWidget(lbl_ant_title)
        ant_layout.addWidget(lbl_ant_sub)
        
        self.ant_list = QListWidget()
        self.ant_list.setFlow(QListView.Flow.LeftToRight)
        self.ant_list.setWrapping(True)
        self.ant_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.ant_list.setSpacing(5)
        self.ant_list.setMaximumHeight(80)
        self.ant_list.setStyleSheet(
            "QListWidget { background: transparent; border: none; outline: none; }"
            "QListWidget::item { background: #3a3a4e; color: white; border-radius: 12px; padding: 4px 8px; }"
        )
        ant_layout.addWidget(self.ant_list)

        btn_sel_ant = QPushButton("Selecionar Excel")
        btn_sel_ant.setStyleSheet("QPushButton { border: 1px solid #3b82f6; color: #3b82f6; border-radius: 4px; padding: 6px; background: transparent; } QPushButton:hover { background: rgba(59, 130, 246, 0.1); }")
        btn_sel_ant.clicked.connect(self._select_anterior)
        ant_layout.addWidget(btn_sel_ant)
        entradas_layout.addWidget(ant_card)

        self.layout.addLayout(entradas_layout)

        # Linha divisória
        div = QWidget()
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #444;")
        self.layout.addWidget(div)

        # ============================================================
        # SEÇÃO: GERAR
        # ============================================================
        gerar_label = QLabel("GERAR")
        gerar_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        self.layout.addWidget(gerar_label)

        gerar_layout = QHBoxLayout()
        gerar_layout.setSpacing(15)

        # Btn 1
        self.btn_simple = QPushButton("Planilha Simples\nRequer: PDFs")
        self.btn_simple.setFixedHeight(60)
        self.btn_simple.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; font-weight: bold; border-radius: 6px; }
            QPushButton:disabled { background-color: #4b5563; color: #9ca3af; }
        """)
        self.btn_simple.clicked.connect(self._run_simple_schedule)
        gerar_layout.addWidget(self.btn_simple)

        # Btn 2
        self.btn_compare = QPushButton("Grade Comparada\nRequer: PDFs + Grade Anterior")
        self.btn_compare.setFixedHeight(60)
        self.btn_compare.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; font-weight: bold; border-radius: 6px; }
            QPushButton:disabled { background-color: #4b5563; color: #9ca3af; }
        """)
        self.btn_compare.clicked.connect(self._run_comparison)
        gerar_layout.addWidget(self.btn_compare)

        # Btn 3
        self.btn_epg = QPushButton("Arquivo EPG\nRequer: PDFs")
        self.btn_epg.setFixedHeight(60)
        self.btn_epg.setStyleSheet("""
            QPushButton { background-color: #2563eb; color: white; font-weight: bold; border-radius: 6px; }
            QPushButton:disabled { background-color: #4b5563; color: #9ca3af; }
        """)
        self.btn_epg.clicked.connect(self._run_epg)
        gerar_layout.addWidget(self.btn_epg)

        self.layout.addLayout(gerar_layout)
        self.layout.addStretch()

        # ============================================================
        # RODAPÉ
        # ============================================================
        footer_layout = QHBoxLayout()
        
        self.btn_depara = QPushButton("Gerenciar DE-PARA")
        self.btn_depara.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_depara.setStyleSheet("color: #aaa; background: transparent; border: none; text-decoration: underline;")
        self.btn_depara.clicked.connect(self._open_mapping_manager)
        
        self.btn_sync_epg = QPushButton("Atualizar Banco EPG...")
        self.btn_sync_epg.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sync_epg.setStyleSheet("color: #aaa; background: transparent; border: none; text-decoration: underline;")
        self.btn_sync_epg.clicked.connect(self._sync_epg_from_file)

        lbl_dot = QLabel("•")
        lbl_dot.setStyleSheet("color: #888;")

        footer_layout.addWidget(self.btn_depara)
        footer_layout.addWidget(lbl_dot)
        footer_layout.addWidget(self.btn_sync_epg)
        footer_layout.addStretch()

        self.status_label = QLabel("Pronto para gerar.")
        self.status_label.setStyleSheet("color: #4ade80; font-weight: bold; font-size: 12px;")
        footer_layout.addWidget(self.status_label)

        self.layout.addLayout(footer_layout)

        self._update_button_states()

    def _update_button_states(self):
        has_pdf = len(self.selected_pdf_files) > 0
        has_ant = self.current_anterior_path is not None

        self.btn_simple.setEnabled(has_pdf)
        self.btn_epg.setEnabled(has_pdf)
        self.btn_compare.setEnabled(has_pdf and has_ant)

    # --- Funções Auxiliares de UI ---
    def _select_pdfs(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Selecione os PDFs", filter="Arquivos PDF (*.pdf)")
        if paths:
            self.selected_pdf_files = paths
            self.pdf_list.clear()
            for p in paths:
                self.pdf_list.addItem(f"📄 {os.path.basename(p)}")
            self._update_button_states()

    def _select_anterior(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecione a Grade Anterior", filter="Excel (*.xlsx *.xls)")
        if path:
            self.current_anterior_path = path
            self.ant_list.clear()
            self.ant_list.addItem(f"📊 {os.path.basename(path)}")
            self._update_button_states()

    def _open_mapping_manager(self):
        from app.ui.mapping_editor_widget import MappingEditorWidget 
        editor = MappingEditorWidget() 
        editor.exec()

    def _sync_epg_from_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecione o EPG preenchido", filter="Excel (*.xlsx)")
        if path:
            from app.tasks.epg_database_manager import epg_manager
            summary, error = epg_manager.preview_sync(path)
            if error:
                QMessageBox.critical(self, "Erro na leitura", error)
                return
            
            n_upd = len(summary['updated'])
            n_add = len(summary['added'])
            n_unc = len(summary['unchanged'])
            
            msg = f"Resumo da Atualização:\n\n"
            msg += f"Atualizados: {n_upd}\nAdicionados: {n_add}\nSem alteração: {n_unc}\n\n"
            msg += "Deseja aplicar estas alterações no banco de dados interno?"
            
            reply = QMessageBox.question(self, "Atualizar Banco EPG", msg)
            if reply == QMessageBox.StandardButton.Yes:
                success, msg_result = epg_manager.sync_from_epg_file(path)
                if success:
                    QMessageBox.information(self, "Sucesso", msg_result)
                else:
                    QMessageBox.critical(self, "Erro", msg_result)

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
            
            from app.ui.batch_mapping_dialog import BatchMappingDialog 
            editor = BatchMappingDialog(unmapped_list=unmapped)
            
            if editor.exec() == QDialog.DialogCode.Accepted:
                self.status_label.setText("Mapeamento atualizado. Reiniciando...")
                # Reinicia o fluxo sem pedir o caminho do arquivo de novo
                self._check_and_start_processing(run_mode)
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
        """Gera a planilha simples apenas com as colunas necessárias."""
        self._lock_ui("Gerando Planilha Simples...")
        try:
            # 1. Seleciona apenas as colunas que o usuário quer ver
            cols_to_keep = ['Data', 'Horario', 'Programa_Padronizado']
            
            # Verifica se as colunas existem antes de filtrar (segurança)
            existing_cols = [c for c in cols_to_keep if c in df.columns]
            df_final = df[existing_cols].copy()
            
            # 2. Renomeia 'Programa_Padronizado' para 'Programa'
            if 'Programa_Padronizado' in df_final.columns:
                df_final.rename(columns={'Programa_Padronizado': 'Programa'}, inplace=True)
            
            # 3. Salva
            df_final.to_excel(self.current_output_path, index=False, sheet_name="Grade Limpa")
            
            self.status_label.setText(f"Sucesso! Salvo em '{os.path.basename(self.current_output_path)}'")
        except Exception as e:
            self.status_label.setText(f"Erro: {e}")
        self._unlock_ui()

    def _run_comparison(self):
        if not self.current_anterior_path:
            self.status_label.setText("Erro: Selecione a Grade Anterior no Bloco 2.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Comparada...", filter="Excel (*.xlsx)")
        if path:
            self.current_output_path = path
            self._check_and_start_processing('comparison')

    def _start_comparison(self, df):
        self._lock_ui("Gerando Grade Comparada...")
        self.comp_worker = GradeComparisonWorker(df, self.current_anterior_path, self.current_output_path)
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