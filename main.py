# main.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication # <-- Adicionar importação
from app.ui.main_window import MainWindow

def run():
    # =======================================================
    # == ADIÇÃO IMPORTANTE PARA APPDATA                    ==
    # =======================================================
    QCoreApplication.setOrganizationName("SuaOrganizacao") # Pode ser seu nome ou da empresa
    QCoreApplication.setApplicationName("AutomateTools")
    # =======================================================

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()