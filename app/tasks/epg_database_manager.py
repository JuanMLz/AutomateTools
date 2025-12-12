# app/tasks/epg_database_manager.py
import os
import sys
import shutil
import pandas as pd
from PySide6.QtCore import QStandardPaths

class EPGDatabaseManager:
    def __init__(self, filename="epg_database.csv"):
        self.config_path_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.filepath = os.path.join(self.config_path_dir, filename)
        
        self.columns = [
            'Unique ID', 'Title', 'Type', 'Genre', 'TC IN', 'Duration', 
            'SeriesId', 'EpisodeTitle', 'Short Description', 'Long Description', 
            'SeasonNumber', 'EpisodeNo', 'Rating', 'Series Image', 
            'Program Image', 'IsLive'
        ]

        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        if not os.path.exists(self.filepath):
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
            else:
                base_path = os.path.abspath(".")
            
            template_path = os.path.join(base_path, "resources", filename)

            if os.path.exists(template_path):
                shutil.copy(template_path, self.filepath)
            else:
                pd.DataFrame(columns=self.columns).to_csv(self.filepath, index=False)

    def load_db(self):
        try:
            return pd.read_csv(self.filepath)
        except Exception:
            return pd.DataFrame(columns=self.columns)

    def save_db(self, df):
        try:
            for col in self.columns:
                if col not in df.columns:
                    df[col] = ""
            df.to_csv(self.filepath, index=False)
            return True
        except Exception:
            return False

    def update_with_new_programs(self, list_of_slugs, list_of_titles):
        """
        Verifica se o TÍTULO já existe no banco. Se não, adiciona.
        """
        df_db = self.load_db()
        
        # Cria conjunto de títulos existentes para comparação rápida
        # Normaliza para string e remove espaços
        existing_titles = set(df_db['Title'].astype(str).str.strip().unique())
        
        new_rows = []
        # Itera sobre o zip para ter slug e título alinhados
        for slug, title in zip(list_of_slugs, list_of_titles):
            title_clean = str(title).strip()
            
            if title_clean not in existing_titles:
                new_row = {col: "" for col in self.columns}
                new_row['Unique ID'] = slug
                new_row['Title'] = title_clean # Salva o nome bonito
                new_row['Type'] = "Media"
                new_rows.append(new_row)
                existing_titles.add(title_clean) # Evita adicionar 2x na mesma rodada
        
        if new_rows:
            df_new = pd.DataFrame(new_rows)
            df_final = pd.concat([df_db, df_new], ignore_index=True)
            self.save_db(df_final)
            return len(new_rows)
        
        return 0

epg_manager = EPGDatabaseManager()