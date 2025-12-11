# app/ui/main_window.py
# Módulo que define a janela principal da aplicação, agora com a nova ferramenta.

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar, QLabel
from PySide6.QtGui import QAction, QIcon, QPixmap, QPainter, QActionGroup
from PySide6.QtCore import Qt, QSize
from app.ui.consolidator_widget import ConsolidatorWidget
from app.ui.grade_creator_widget import GradeCreatorWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AutomateTools - Sua Caixa de Ferramentas de Automação")
        self.resize(850, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # Página 0: Boas-vindas
        welcome_label = QLabel("Bem-vindo ao AutomateTools!\nSelecione uma ferramenta na barra lateral para começar.")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stacked_widget.addWidget(welcome_label)

        # Página 1: Ferramenta de Consolidação de Logs (Existente)
        self.consolidator_page = ConsolidatorWidget()
        self.stacked_widget.addWidget(self.consolidator_page)

        # =======================================================
        # == NOVO: Adicionando a nova página "Criador de Grade" ==
        # =======================================================
        # Página 2: Nova ferramenta Criador de Grade
        self.grade_creator_page = GradeCreatorWidget()
        self.stacked_widget.addWidget(self.grade_creator_page)

        self.toolbar = QToolBar("Ferramentas")
        self.toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.toolbar)
        self.toolbar.setMovable(False)
        
        self.toolbar.setStyleSheet("""
            QToolBar { background-color: #333; border: none; }
            QToolButton { color: #FFF; padding: 10px; margin: 2px; border-radius: 4px; }
            QToolButton:hover { background-color: #555; }
            QToolButton:checked { background-color: #0078d4; }
        """)

        action_group = QActionGroup(self)
        action_group.setExclusive(True)

        # Ação Home (Existente)
        home_icon = self._create_color_icon(Qt.GlobalColor.gray)
        action_home = QAction(home_icon, "Página Inicial", self)
        action_home.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        action_home.setCheckable(True)
        action_group.addAction(action_home)
        self.toolbar.addAction(action_home)

        self.toolbar.addSeparator()

        # Ação Consolidador de Logs (Existente)
        green_square_icon = self._create_color_icon(Qt.GlobalColor.darkGreen)
        action_consolidator = QAction(green_square_icon, "Consolidar Logs", self)
        action_consolidator.setStatusTip("Junta múltiplos arquivos de log em uma única planilha Excel.")
        action_consolidator.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        action_consolidator.setCheckable(True)
        action_group.addAction(action_consolidator)
        self.toolbar.addAction(action_consolidator)
        
        # =======================================================
        # == NOVO: Adicionando o botão para a nova ferramenta  ==
        # =======================================================
        # Ação Criador de Grade
        blue_square_icon = self._create_color_icon(Qt.GlobalColor.darkBlue)
        action_grade_creator = QAction(blue_square_icon, "Criador de Grade", self)
        action_grade_creator.setStatusTip("Extrai e processa grades de programação a partir de PDFs.")
        action_grade_creator.triggered.connect(lambda: self.stacked_widget.setCurrentIndex(2)) # Aponta para a página 2
        action_grade_creator.setCheckable(True)
        action_group.addAction(action_grade_creator)
        self.toolbar.addAction(action_grade_creator)
        # =======================================================

        # Inicia na página inicial
        action_home.setChecked(True)
        self.stacked_widget.setCurrentIndex(0)

    def _create_color_icon(self, color):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(color)
        painter.setPen(Qt.GlobalColor.transparent)
        painter.drawRect(4, 4, 24, 24)
        painter.end()
        return QIcon(pixmap)