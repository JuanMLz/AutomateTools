# app/ui/mapping_editor_widget.py
# Janela de diálogo para gerenciar o arquivo de mapeamento DE-PARA.

import pandas as pd
import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableView, QAbstractItemView,
    QHeaderView, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, QAbstractTableModel
from app.tasks.mapping_manager import mapping_manager

# --- Modelo de Dados para a Tabela ---
class PandasModel(QAbstractTableModel):
    """Um modelo de tabela que exibe um DataFrame do Pandas."""
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid():
            if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def setData(self, index, value, role):
        if role == Qt.ItemDataRole.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            return True
        return False

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                return str(self._data.columns[section])
            if orientation == Qt.Orientation.Vertical:
                return str(self._data.index[section])
        return None
    
    def flags(self, index):
        return Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsEditable

class MappingEditorWidget(QDialog):
    def __init__(self, parent=None, new_unmapped_list=None):
        super().__init__(parent)
        
        self.new_unmapped_list = new_unmapped_list
        self.setMinimumSize(800, 600)

        self.layout = QVBoxLayout(self)

        if new_unmapped_list:
            self.setWindowTitle("Assistente de Mapeamento - Novos Programas Encontrados!")
            self.setup_learning_mode(new_unmapped_list)
        else:
            self.setWindowTitle("Gerenciador de Mapeamento DE-PARA")
            self.setup_editing_mode()

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.layout.addWidget(self.table_view)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Adicionar Linha")
        self.remove_button = QPushButton("Remover Linha Selecionada")
        self.save_button = QPushButton("Salvar e Fechar")
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.remove_button)

        self.change_path_button = QPushButton("Alterar Local do Arquivo...")
        # =======================================================
        # == MUDANÇA 1: Conexão do botão                     ==
        # =======================================================
        # A conexão agora aponta para a nova função que faz a pergunta inicial.
        self.change_path_button.clicked.connect(self._ask_change_path_intention)
        button_layout.addWidget(self.change_path_button)

        button_layout.addStretch()
        button_layout.addWidget(self.save_button)
        
        if new_unmapped_list:
            self.add_button.setEnabled(False)
            self.remove_button.setEnabled(False)
            self.save_button.setText("Confirmar Mapeamentos e Continuar")
        
        self.layout.addLayout(button_layout)

        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self.remove_row)
        self.save_button.clicked.connect(self.save_and_close)

    def setup_editing_mode(self):
        """Carrega o CSV completo para edição."""
        mapping_df, error = mapping_manager.load_mapping_as_df()
        if error:
            QMessageBox.critical(self, "Erro", error)
            mapping_df = pd.DataFrame(columns=["Nome_do_PDF", "Nome_Padronizado"])
        self.model = PandasModel(mapping_df)

    def setup_learning_mode(self, new_unmapped_list):
        """Cria um DF apenas com os novos programas para o usuário preencher."""
        data = {
            "Nome_do_PDF": new_unmapped_list,
            "Nome_Padronizado": [""] * len(new_unmapped_list)
        }
        self.model = PandasModel(pd.DataFrame(data))

    def save_and_close(self):
        """
        Salva as alterações no arquivo CSV e fecha a janela.
        """
        new_data_df = self.model._data

        if self.new_unmapped_list:
            old_data_df, error = mapping_manager.load_mapping_as_df()
            if error:
                QMessageBox.critical(self, "Erro Crítico", f"Não foi possível ler o arquivo de mapeamento existente para atualizá-lo.\n\n{error}")
                return
            combined_df = pd.concat([old_data_df, new_data_df], ignore_index=True)
            combined_df.drop_duplicates(subset=['Nome_do_PDF'], keep='last', inplace=True)
            combined_df.dropna(subset=['Nome_Padronizado'], inplace=True)
            combined_df = combined_df[combined_df['Nome_Padronizado'].str.strip() != '']
            df_to_save = combined_df
        else:
            df_to_save = new_data_df

        success, message = mapping_manager.save_mapping_from_df(df_to_save)
        
        if success:
            if not self.new_unmapped_list:
                QMessageBox.information(self, "Sucesso", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Erro ao Salvar", message)

    def add_row(self):
        """Adiciona uma nova linha em branco no final da tabela."""
        df = self.model._data
        new_row = pd.DataFrame([["", ""]], columns=df.columns)
        self.model._data = pd.concat([df, new_row], ignore_index=True)
        self.model.layoutChanged.emit()

    def remove_row(self):
        """Remove a(s) linha(s) selecionada(s)."""
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione uma linha para remover.")
            return
        
        for index in sorted(selected_indexes, reverse=True):
            self.model._data = self.model._data.drop(index.row())
        
        self.model._data.reset_index(drop=True, inplace=True)
        self.model.layoutChanged.emit()

    # =======================================================
    # == MUDANÇA 2: Método _change_mapping_path SUBSTITUÍDO  ==
    # == por 3 novos métodos para o fluxo aprimorado.      ==
    # =======================================================
    def _ask_change_path_intention(self):
        """
        Abre um pop-up que pergunta a intenção do usuário ANTES de abrir o diálogo de arquivo.
        """
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Alterar Local do Mapeamento")
        msg_box.setText("O que você deseja fazer com o arquivo de mapeamento?")
        msg_box.setInformativeText("Escolha 'Conectar' para usar um arquivo que já existe em uma pasta de rede. Escolha 'Mover' para criar um novo arquivo compartilhado a partir do seu mapeamento local.")
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        connect_button = msg_box.addButton("Conectar a um arquivo existente", QMessageBox.ButtonRole.ActionRole)
        move_button = msg_box.addButton("Mover para um novo local", QMessageBox.ButtonRole.ActionRole)
        cancel_button = msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)

        msg_box.exec()
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == connect_button:
            self._connect_to_existing_file()
        elif clicked_button == move_button:
            self._move_to_new_file()

    def _connect_to_existing_file(self):
        """Abre um diálogo para ABRIR um arquivo e atualiza a configuração."""
        current_path = mapping_manager.get_mapping_filepath()
        
        new_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecione o arquivo de mapeamento existente",
            os.path.dirname(current_path),
            "CSV (*.csv)"
        )
        
        if new_path:
            mapping_manager.set_mapping_filepath(new_path)
            QMessageBox.information(self, "Conectado com Sucesso",
                                  f"Configuração atualizada.\nO programa agora usará o arquivo:\n'{new_path}'.\n\n"
                                  "Por favor, reinicie a aplicação para que a mudança tenha efeito completo.")
            self.accept()

    def _move_to_new_file(self):
        """Abre um diálogo para SALVAR um novo arquivo, move os dados e atualiza a configuração."""
        current_path = mapping_manager.get_mapping_filepath()
        
        new_path, _ = QFileDialog.getSaveFileName(
            self,
            "Escolha o novo local para salvar o arquivo de mapeamento",
            os.path.dirname(current_path),
            "CSV (*.csv)"
        )
        
        if new_path:
            # Normaliza os caminhos para uma comparação segura
            if os.path.normpath(new_path) == os.path.normpath(current_path):
                QMessageBox.warning(self, "Aviso", "O novo local é o mesmo que o atual. Nenhuma alteração foi feita.")
                return

            try:
                shutil.move(current_path, new_path)
                msg = f"Mapeamento movido com sucesso para:\n'{new_path}'."
                mapping_manager.set_mapping_filepath(new_path)
            except Exception as e:
                msg = f"Não foi possível mover o arquivo ({e}). Nenhuma alteração foi feita."

            QMessageBox.information(self, "Operação Concluída", 
                                  f"{msg}\n\nPor favor, reinicie a aplicação para que a mudança tenha efeito completo.")
            self.accept()