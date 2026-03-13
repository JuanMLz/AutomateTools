import pandas as pd
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QScrollArea, QWidget, QMessageBox, QLineEdit, QCompleter
)
from PySide6.QtCore import Qt
from app.tasks.mapping_manager import mapping_manager
from app.tasks.epg_database_manager import epg_manager
from app.tasks.utils import slugify

class NewProgramDialog(QDialog):
    def __init__(self, initial_title="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cadastrar Novo Programa")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Título do Programa (idêntico à saída desejada):"))
        self.title_input = QLineEdit(initial_title)
        layout.addWidget(self.title_input)
        
        layout.addWidget(QLabel("Unique ID (Modifique se quiser um ID customizado):"))
        self.id_input = QLineEdit()
        layout.addWidget(self.id_input)
        
        self.title_input.textChanged.connect(self._on_title_changed)
        self._on_title_changed(initial_title)
        
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Salvar no Banco")
        self.btn_save.setStyleSheet("background-color: #2563eb; color: white; padding: 6px; border-radius: 4px; font-weight: bold;")
        self.btn_save.clicked.connect(self.validate_and_save)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)
        
        self.result_title = ""
        self.initial_title = initial_title

    def _on_title_changed(self, text):
        base_slug = slugify(text)
        if not base_slug: return
        slug = base_slug
        counter = 2
        while epg_manager.slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        self.id_input.setText(slug)

    def validate_and_save(self):
        t = self.title_input.text().strip()
        uid = self.id_input.text().strip()
        if not t or not uid:
            QMessageBox.warning(self, "Aviso", "Preencha título e ID.")
            return
            
        if epg_manager.slug_exists(uid):
            from app.tasks.epg_database_manager import _normalize
            existing_uid = epg_manager.get_title_to_id_map().get(_normalize(t))
            if existing_uid == uid:
                # O usuário está tentando re-cadastrar o MESMO programa Exato que já existe
                self.result_title = t
                self.accept()
                return
            else:
                QMessageBox.warning(self, "Conflito de ID", f"O ID '{uid}' já está em uso por outro programa.\nPor favor, modifique o ID inserindo '-2' no final, por exemplo.")
                return

        success = epg_manager.add_new_program(t, uid)
        if success:
            self.result_title = t
            # Salva também no DE-PARA: mapeia self.initial_title → t
            if self.initial_title and self.initial_title.strip() != t:
                from app.tasks.mapping_manager import mapping_manager
                import pandas as pd
                old_df, _ = mapping_manager.load_mapping_as_df()
                new_row = pd.DataFrame([[self.initial_title.strip(), t]], columns=["Nome_do_PDF", "Nome_Padronizado"])
                combined_df = pd.concat([old_df, new_row], ignore_index=True)
                combined_df.drop_duplicates(subset=['Nome_do_PDF'], keep='last', inplace=True)
                mapping_manager.save_mapping_from_df(combined_df)
            self.accept()
        else:
            QMessageBox.critical(self, "Erro", "Erro ao salvar no banco de dados. Verifique se o arquivo epg_database.xlsx está fechado no Excel.")


class BatchMappingDialog(QDialog):
    def __init__(self, unmapped_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Resolver Programas Desconhecidos")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        self.unmapped_list = unmapped_list
        self.rows = [] # Armazena ditos {"pdf_name": str, "combo": QComboBox}
        
        self.layout = QVBoxLayout(self)
        
        info = QLabel(f"Foram encontrados {len(unmapped_list)} programas no PDF sem mapeamento no DE-PARA.\nPor favor, indique o correspondente correto no banco EPG ou crie um novo.")
        info.setStyleSheet("font-size: 13px; margin-bottom: 10px;")
        self.layout.addWidget(info)
        
        # Área de Scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        all_titles = [""] + epg_manager.get_all_titles()
        
        for pdf_name in unmapped_list:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 5, 0, 5)
            
            lbl_pdf = QLabel(pdf_name)
            lbl_pdf.setMinimumWidth(250)
            lbl_pdf.setStyleSheet("font-weight: bold; color: #e2e8f0;")
            
            combo = QComboBox()
            combo.setEditable(True)
            combo.addItems(all_titles)
            combo.setMinimumWidth(250)
            
            completer = QCompleter(all_titles, combo)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            combo.setCompleter(completer)
            
            btn_new = QPushButton("Novo...")
            btn_new.setStyleSheet("padding: 4px; max-width: 60px;")
            # Closure to bind the combo to the button
            btn_new.clicked.connect(lambda checked=False, c=combo, n=pdf_name: self.create_new_program(c, n))
            
            row_l.addWidget(lbl_pdf)
            row_l.addWidget(QLabel(" → "))
            row_l.addWidget(combo)
            row_l.addWidget(btn_new)
            
            self.scroll_layout.addWidget(row_w)
            
            self.rows.append({"pdf_name": pdf_name, "combo": combo})
            
        self.scroll.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll)
        
        # Footer
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Salvar Mapeamentos e Continuar")
        self.btn_save.setStyleSheet("background-color: #22c55e; color: white; padding: 10px; border-radius: 4px; font-weight: bold; font-size: 14px;")
        self.btn_save.clicked.connect(self.save_all)
        
        btn_cancel = QPushButton("Cancelar Geração")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        self.layout.addLayout(btn_layout)

    def create_new_program(self, combo, pdf_name):
        dlg = NewProgramDialog(initial_title=pdf_name, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_title = dlg.result_title
            # Atualiza todas as combos da tela para incluir e selecionar o novo title
            for row in self.rows:
                c = row["combo"]
                if c.findText(new_title) == -1:
                    c.addItem(new_title)
            combo.setCurrentText(new_title)

    def save_all(self):
        # Validação
        mappings_to_add = []
        from app.tasks.epg_database_manager import _normalize
        title_map = epg_manager.get_title_to_id_map()
        
        for row in self.rows:
            pdf_name = row["pdf_name"]
            selected_title = row["combo"].currentText().strip()
            
            if not selected_title:
                QMessageBox.warning(self, "Validação", f"O programa '{pdf_name}' está sem correspondente. Resolva todos antes de continuar.")
                return
                
            if _normalize(selected_title) not in title_map:
                QMessageBox.warning(self, "Título Inválido", f"O título '{selected_title}' não existe no Banco EPG.\nPara programas desconhecidos, você DEVE clicar no botão 'Novo...' ao lado do campo para cadastrá-lo corretamente no banco antes de prosseguir.")
                return
                
            mappings_to_add.append((pdf_name, selected_title))
            
        # Salva no DE-PARA
        old_df, _ = mapping_manager.load_mapping_as_df()
        new_df = pd.DataFrame(mappings_to_add, columns=["Nome_do_PDF", "Nome_Padronizado"])
        
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
        combined_df.drop_duplicates(subset=['Nome_do_PDF'], keep='last', inplace=True)
        
        success, msg = mapping_manager.save_mapping_from_df(combined_df)
        if success:
            self.accept()
        else:
            QMessageBox.critical(self, "Erro ao Salvar", msg)
