# app/ui/antenna_dashboard_widget.py
"""
Widget para geração de dashboard de antenas/cidades fora do ar.
Interface: carregar múltiplas planilhas → gerar PDF com análise semanal.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QFileDialog, QGroupBox, QMessageBox
)
from PySide6.QtCore import Qt

from app.workers import AntennaDashboardWorker


class AntennaDashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.selected_xlsx_paths = []  # Lista de arquivos
        self.worker = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Configura a interface do widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # --- Cabeçalho ---
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📡 Monitor de Antenas")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        
        self.settings_button = QPushButton("Configurar Base de Cidades")
        self.settings_button.setFixedSize(180, 30)
        self.settings_button.clicked.connect(self._open_database_settings)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.settings_button)
        layout.addLayout(header_layout)
        
        # --- Descrição ---
        desc_label = QLabel(
            "Esta ferramenta gera um relatório visual (PDF) de acompanhamento das cidades/antenas fora do ar.\n"
            "Selecione os arquivos do período (ex: 7 dias) para análise de tendências e histórico."
        )
        desc_label.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 15px;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # --- Bloco 1: Entrada ---
        group_input = QGroupBox("1. Dados de Entrada (Múltiplos Arquivos)")
        group_input.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #aaa; 
                margin-top: 10px; 
                padding-top: 15px; 
            } 
            QGroupBox::title { 
                top: -8px; 
                left: 10px; 
            }
        """)
        input_layout = QVBoxLayout()
        
        # Nota sobre formato
        format_label = QLabel("📁 Formato esperado: call_center_DD-MM-YYYY.xlsx")
        format_label.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        input_layout.addWidget(format_label)
        
        # Seleção de arquivos
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit("Nenhum arquivo selecionado")
        self.file_path_edit.setReadOnly(True)
        
        select_file_btn = QPushButton("Selecionar Planilhas...")
        select_file_btn.clicked.connect(self._select_xlsx_files)
        
        file_layout.addWidget(select_file_btn)
        file_layout.addWidget(self.file_path_edit)
        input_layout.addLayout(file_layout)
        
        group_input.setLayout(input_layout)
        layout.addWidget(group_input)
        
        # --- Bloco 2: Geração ---
        group_output = QGroupBox("2. Gerar Relatório")
        group_output.setStyleSheet("""
            QGroupBox { 
                font-weight: bold; 
                border: 1px solid #aaa; 
                margin-top: 10px; 
                padding-top: 15px; 
            } 
            QGroupBox::title { 
                top: -8px; 
                left: 10px; 
            }
        """)
        output_layout = QVBoxLayout()
        
        info_label = QLabel(
            "O dashboard será gerado em PDF com 3 páginas:\n"
            "📄 Página 1: Resumo do período (KPIs, distribuição por estado/motivo/região)\n"
            "📄 Página 2: Análise de tendência (evolução diária, tempo médio por categoria)\n"
            "📄 Página 3: Histórico (Top 10 críticas, resolvidas, comparativo)"
        )
        info_label.setStyleSheet("color: #555; font-size: 10px; margin-bottom: 10px;")
        output_layout.addWidget(info_label)
        
        self.btn_generate = QPushButton("📊 Gerar Dashboard PDF")
        self.btn_generate.setStyleSheet("""
            QPushButton {
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """)
        self.btn_generate.clicked.connect(self._generate_dashboard)
        output_layout.addWidget(self.btn_generate)
        
        group_output.setLayout(output_layout)
        layout.addWidget(group_output)
        
        # --- Status ---
        self.status_label = QLabel("Pronto.")
        self.status_label.setStyleSheet("""
            margin-top: 15px; 
            font-size: 12px; 
            color: green; 
            font-weight: bold;
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
    
    def _select_xlsx_files(self):
        """Abre diálogo para selecionar múltiplos arquivos Excel."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Selecione as Planilhas do Período",
            "",
            "Excel (*.xlsx *.xls)"
        )
        if paths:
            self.selected_xlsx_paths = paths
            self.file_path_edit.setText(f"{len(paths)} arquivos selecionados")
            self.status_label.setText(f"✅ {len(paths)} arquivos carregados. Pronto para gerar.")
            self.status_label.setStyleSheet("margin-top: 15px; font-size: 12px; color: green; font-weight: bold;")
    
    def _generate_dashboard(self):
        """Inicia a geração do dashboard."""
        if not self.selected_xlsx_paths:
            self.status_label.setText("❌ Erro: Selecione pelo menos uma planilha.")
            self.status_label.setStyleSheet("margin-top: 15px; font-size: 12px; color: red; font-weight: bold;")
            return
        
        # Pede local para salvar
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar Dashboard PDF",
            "dashboard_antenas.pdf",
            "PDF (*.pdf)"
        )
        
        if not output_path:
            return
        
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'
        
        self._lock_ui("⏳ Processando planilhas e gerando dashboard...")
        
        # Inicia worker
        self.worker = AntennaDashboardWorker(self.selected_xlsx_paths, output_path)
        self.worker.finished.connect(self._on_generation_finished)
        self.worker.start()
    
    def _on_generation_finished(self, success, message):
        """Callback quando a geração termina."""
        self._unlock_ui()
        
        if success:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("margin-top: 15px; font-size: 12px; color: green; font-weight: bold;")
            
            QMessageBox.information(
                self,
                "Sucesso",
                f"Dashboard gerado com sucesso!\n\n{message}"
            )
        else:
            self.status_label.setText(f"❌ Erro na geração")
            self.status_label.setStyleSheet("margin-top: 15px; font-size: 12px; color: red; font-weight: bold;")
            
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao gerar dashboard:\n\n{message}"
            )
    
    def _open_database_settings(self):
        """Abre diálogo para configurar base de cidades."""
        from app.tasks.antenna_data_manager import antenna_manager
        
        db_path = antenna_manager.get_db_filepath()
        history_path = antenna_manager.get_history_filepath()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Configurações")
        msg.setText("Arquivos de Dados")
        msg.setInformativeText(
            f"📁 Base de Cidades:\n{db_path}\n\n"
            f"📁 Histórico de Ocorrências:\n{history_path}\n\n"
            "A base de cidades permite calcular percentuais e agrupar por região.\n"
            "O histórico armazena todas as ocorrências para análise de tendências.\n\n"
            "Formato da base: CSV com colunas CIDADE, ESTADO, REGIAO"
        )
        
        btn_open_db = msg.addButton("Abrir Pasta", QMessageBox.ButtonRole.ActionRole)
        btn_replace_db = msg.addButton("Substituir Base...", QMessageBox.ButtonRole.ActionRole)
        btn_clear_history = msg.addButton("Limpar Histórico", QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(QMessageBox.StandardButton.Close)
        
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == btn_open_db:
            folder = os.path.dirname(db_path)
            os.startfile(folder)
        
        elif clicked == btn_replace_db:
            new_path, _ = QFileDialog.getOpenFileName(
                self, "Selecionar Base de Cidades", "", "CSV (*.csv)"
            )
            if new_path:
                import shutil
                try:
                    shutil.copy(new_path, db_path)
                    QMessageBox.information(self, "Sucesso", 
                                            f"Base de cidades atualizada!\n\n{db_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao copiar arquivo:\n{e}")
        
        elif clicked == btn_clear_history:
            confirm = QMessageBox.question(
                self, "Confirmar",
                "Tem certeza que deseja limpar todo o histórico?\n\nEsta ação não pode ser desfeita.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    import pandas as pd
                    columns = ["CIDADE", "ESTADO", "REGIAO", "MOTIVO", "DATA_ENTRADA", "DATA_SAIDA", "DIAS_FORA", "STATUS"]
                    pd.DataFrame(columns=columns).to_csv(history_path, index=False)
                    QMessageBox.information(self, "Sucesso", "Histórico limpo com sucesso!")
                except Exception as e:
                    QMessageBox.critical(self, "Erro", f"Erro ao limpar histórico:\n{e}")
    
    def _lock_ui(self, message):
        """Bloqueia UI durante processamento."""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("margin-top: 15px; font-size: 12px; color: #F39C12; font-weight: bold;")
        self.btn_generate.setEnabled(False)
    
    def _unlock_ui(self):
        """Desbloqueia UI após processamento."""
        self.btn_generate.setEnabled(True)
