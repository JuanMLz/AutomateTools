# app/ui/consolidator_widget.py

import os # <-- Adicionamos a importação de 'os' para juntar os caminhos
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, QFileDialog,
    QRadioButton, QButtonGroup, QGroupBox
)
from PySide6.QtCore import Qt
from app.tasks.excel_consolidator import processar_logs_para_excel

class ConsolidatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.selected_log_files = []
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(20, 20, 20, 20)
        title_label = QLabel("Consolidator de Logs para Excel")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        self.layout.addWidget(title_label)
        
        logs_group = QGroupBox("Passo 1: Selecione os Arquivos de Entrada")
        logs_layout = QHBoxLayout()
        self.logs_selection_edit = QLineEdit("Nenhum arquivo selecionado")
        self.logs_selection_edit.setReadOnly(True)
        select_logs_button = QPushButton("Selecionar Arquivos de Log...")
        select_logs_button.clicked.connect(self._selecionar_arquivos_log)
        logs_layout.addWidget(select_logs_button)
        logs_layout.addWidget(self.logs_selection_edit)
        logs_group.setLayout(logs_layout)
        self.layout.addWidget(logs_group)

        output_group = QGroupBox("Passo 2: Configure o Arquivo de Saída")
        output_layout = QVBoxLayout()
        self.radio_existing = QRadioButton("Usar arquivo Excel existente")
        self.radio_new = QRadioButton("Criar um novo arquivo Excel")
        self.radio_existing.setChecked(True)
        self.output_mode_group = QButtonGroup()
        self.output_mode_group.addButton(self.radio_existing)
        self.output_mode_group.addButton(self.radio_new)
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.radio_existing)
        radio_layout.addWidget(self.radio_new)
        output_layout.addLayout(radio_layout)
        self.output_path_edit = QLineEdit("Nenhum arquivo/pasta de destino selecionado") # <-- Texto alterado
        self.output_path_edit.setReadOnly(True)
        self.select_output_button = QPushButton("Selecionar Arquivo Existente...")
        self.select_output_button.clicked.connect(self._selecionar_saida)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.select_output_button)
        path_layout.addWidget(self.output_path_edit)
        output_layout.addLayout(path_layout)
        
        # MUDANÇA: Renomeado para refletir a função dupla
        self.dynamic_input_layout = QHBoxLayout()
        self.dynamic_label = QLabel("Nome da Aba:")
        self.dynamic_input_edit = QLineEdit("Dados Consolidados")
        self.dynamic_input_layout.addWidget(self.dynamic_label)
        self.dynamic_input_layout.addWidget(self.dynamic_input_edit)
        output_layout.addLayout(self.dynamic_input_layout)
        output_group.setLayout(output_layout)
        self.layout.addWidget(output_group)

        # Conecta a mudança dos radio buttons a uma função que ATUALIZA TODA A UI
        self.radio_existing.toggled.connect(self._update_output_mode)
        
        process_button = QPushButton("GERAR RELATÓRIO")
        process_button.setStyleSheet("font-size: 14px; padding: 10px; margin-top: 10px;")
        process_button.clicked.connect(self._iniciar_processamento)
        self.layout.addWidget(process_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("Pronto para iniciar.")
        self.status_label.setStyleSheet("margin-top: 15px;")
        self.layout.addWidget(self.status_label)
        
        self._update_output_mode() # <-- Chama a função uma vez para configurar a UI inicial

    def _update_output_mode(self):
        """Atualiza a UI com base no modo de saída selecionado (novo vs. existente)."""
        if self.radio_existing.isChecked():
            self.select_output_button.setText("Selecionar Arquivo Existente...")
            self.dynamic_label.setText("Nome da Aba:")
            self.dynamic_input_edit.setText("Dados Consolidados")
            self.dynamic_input_edit.setPlaceholderText("")
        else: # Se "Criar novo" estiver selecionado
            self.select_output_button.setText("Selecionar Pasta de Destino...")
            self.dynamic_label.setText("Nome do Novo Arquivo:")
            self.dynamic_input_edit.setText("") # Limpa o campo
            self.dynamic_input_edit.setPlaceholderText("Ex: relatorio_final.xlsx")

    def _selecionar_arquivos_log(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Selecione os arquivos de log", filter="Arquivos de Texto (*.txt)")
        if paths:
            self.selected_log_files = paths
            self.logs_selection_edit.setText(f"{len(paths)} arquivos selecionados")

    def _selecionar_saida(self): # MUDANÇA: Renomeado para maior clareza
        """Abre o diálogo de arquivo/pasta apropriado com base no modo selecionado."""
        path = ""
        if self.radio_existing.isChecked():
            path, _ = QFileDialog.getOpenFileName(self, "Selecione um arquivo Excel existente", filter="Arquivos Excel (*.xlsx)")
        else: # Modo "Criar Novo" agora seleciona uma PASTA
            path = QFileDialog.getExistingDirectory(self, "Selecione a pasta onde o novo arquivo será salvo")
        
        if path:
            self.output_path_edit.setText(path)

    def _iniciar_processamento(self):
        lista_arquivos = self.selected_log_files
        
        # MUDANÇA: Lógica inteligente para construir o caminho do arquivo final
        caminho_final_excel = ""
        nome_aba = ""

        if self.radio_existing.isChecked():
            caminho_final_excel = self.output_path_edit.text()
            nome_aba = self.dynamic_input_edit.text()
        else: # Modo "Criar novo"
            pasta_destino = self.output_path_edit.text()
            nome_arquivo = self.dynamic_input_edit.text()
            
            # Validação
            if not nome_arquivo:
                self.status_label.setText("Erro: Por favor, digite um nome para o novo arquivo.")
                return
            if not nome_arquivo.endswith('.xlsx'):
                nome_arquivo += '.xlsx' # Garante a extensão correta
            
            caminho_final_excel = os.path.join(pasta_destino, nome_arquivo)
            nome_aba = "Dados Consolidados" # Usa um nome de aba padrão

        if not lista_arquivos or "Nenhum arquivo/pasta" in self.output_path_edit.text():
            self.status_label.setText("Erro: Selecione os arquivos de entrada e o destino.")
            return

        self.status_label.setText("Processando... Por favor, aguarde.")
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()

        resultado = processar_logs_para_excel(lista_arquivos, caminho_final_excel, nome_aba)
        self.status_label.setText(resultado)