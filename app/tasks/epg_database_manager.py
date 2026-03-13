# app/tasks/epg_database_manager.py
import os
import sys
import shutil
import unicodedata
import pandas as pd
from PySide6.QtCore import QStandardPaths


def _normalize(text):
    """Remove acentos e lowercase para comparações insensíveis."""
    nfkd = unicodedata.normalize('NFKD', str(text))
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


class EPGDatabaseManager:
    DB_FILENAME = "epg_database.xlsx"

    def __init__(self):
        # Em desenvolvimento: resources/ (junto ao projeto)
        # No .exe empacotado: AppData/Roaming/AutomateTools/
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
            self.is_packaged = True
        else:
            base_path = os.path.abspath(".")
            self.is_packaged = False

        self.resources_path = os.path.join(base_path, "resources", self.DB_FILENAME)

        # AppData path (sempre dentro de AutomateTools/)
        appdata_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.appdata_path = os.path.join(appdata_dir, "AutomateTools", self.DB_FILENAME)

        self.columns = [
            'Unique ID', 'Title', 'Type', 'Genre', 'TC IN', 'Duration',
            'SeriesId', 'EpisodeTitle', 'Short Description', 'Long Description',
            'SeasonNumber', 'EpisodeNo', 'Rating', 'Series Image',
            'Program Image', 'IsLive'
        ]

        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Garante que o arquivo de banco existe no local correto."""
        if self.is_packaged:
            # No .exe, usa AppData/AutomateTools/
            os.makedirs(os.path.dirname(self.appdata_path), exist_ok=True)
            if not os.path.exists(self.appdata_path):
                if os.path.exists(self.resources_path):
                    shutil.copy(self.resources_path, self.appdata_path)
                else:
                    pd.DataFrame(columns=self.columns).to_excel(
                        self.appdata_path, index=False, engine='openpyxl'
                    )
            self.filepath = self.appdata_path
        else:
            # Em desenvolvimento: usa resources/ diretamente
            os.makedirs(os.path.dirname(self.resources_path), exist_ok=True)
            if not os.path.exists(self.resources_path):
                pd.DataFrame(columns=self.columns).to_excel(
                    self.resources_path, index=False, engine='openpyxl'
                )
            self.filepath = self.resources_path

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def load_db(self):
        try:
            return pd.read_excel(self.filepath, engine='openpyxl')
        except Exception:
            return pd.DataFrame(columns=self.columns)

    def save_db(self, df):
        try:
            for col in self.columns:
                if col not in df.columns:
                    df[col] = ""
            df[self.columns].to_excel(self.filepath, index=False, engine='openpyxl')
            return True, None
        except PermissionError:
            return False, f"Arquivo bloqueado! Feche o arquivo '{os.path.basename(self.filepath)}' no Excel antes de salvar."
        except Exception as e:
            import traceback
            return False, f"Erro ao salvar banco EPG: {e}\n{traceback.format_exc()}"

    # ------------------------------------------------------------------
    # LOOKUPS
    # ------------------------------------------------------------------

    def get_title_to_id_map(self):
        """Retorna {title_normalizado: unique_id} para lookup no Schedule."""
        df = self.load_db()
        result = {}
        for _, row in df.iterrows():
            title = str(row.get('Title', '')).strip()
            uid = str(row.get('Unique ID', '')).strip()
            if title and title != 'nan' and uid and uid != 'nan':
                result[_normalize(title)] = uid
        return result

    def get_all_titles(self):
        """Retorna lista de Titles para autocomplete (ordenada)."""
        df = self.load_db()
        titles = df['Title'].dropna().astype(str).str.strip()
        return sorted(titles[titles != ''].tolist())

    def slug_exists(self, slug):
        """Verifica se um Unique ID já está em uso."""
        df = self.load_db()
        return slug.strip().lower() in df['Unique ID'].astype(str).str.lower().str.strip().values

    # ------------------------------------------------------------------
    # CADASTRO DE NOVO PROGRAMA
    # ------------------------------------------------------------------

    def add_new_program(self, title, unique_id):
        """
        Adiciona um novo programa ao banco.
        unique_id deve ser único (verificar com slug_exists antes).
        Preenche Series Image e Program Image automaticamente.
        """
        from .utils import slugify
        df = self.load_db()
        image = f"{unique_id}.png"
        new_row = {col: "" for col in self.columns}
        new_row['Unique ID'] = unique_id
        new_row['Title'] = title.strip()
        new_row['Type'] = "Media"
        new_row['Series Image'] = image
        new_row['Program Image'] = image
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        ok, err = self.save_db(df)
        if not ok:
            import traceback as _tb
            print("[EPGDatabaseManager.add_new_program] ERRO:", err)
        return ok

    # ------------------------------------------------------------------
    # SINCRONIZAÇÃO POR UPLOAD
    # ------------------------------------------------------------------

    def preview_sync(self, xlsx_path):
        """
        Lê a aba EPG do arquivo enviado e retorna um resumo do que será feito.
        Retorna: dict com 'updated', 'added', 'unchanged' como listas de títulos.
        """
        try:
            df_upload = pd.read_excel(xlsx_path, sheet_name='EPG', engine='openpyxl')
        except Exception as e:
            return None, f"Erro ao ler arquivo: {e}"

        df_db = self.load_db()
        db_by_id = {str(r['Unique ID']).strip(): r for _, r in df_db.iterrows()
                    if pd.notna(r.get('Unique ID'))}

        updated, added, unchanged = [], [], []
        for _, row in df_upload.iterrows():
            uid = str(row.get('Unique ID', '')).strip()
            title = str(row.get('Title', '')).strip()
            if not uid or uid == 'nan':
                continue
            if uid in db_by_id:
                # Checa se haveria alguma mudança
                existing = db_by_id[uid]
                has_change = any(
                    str(row.get(c, '')).strip() != str(existing.get(c, '')).strip()
                    for c in self.columns if c not in ('Unique ID',)
                )
                if has_change:
                    updated.append(title or uid)
                else:
                    unchanged.append(title or uid)
            else:
                added.append(title or uid)

        return {'updated': updated, 'added': added, 'unchanged': unchanged}, None

    def sync_from_epg_file(self, xlsx_path):
        """
        Realiza o merge do arquivo enviado no banco.
        O Unique ID do arquivo prevalece como chave.
        Campos do arquivo sobrescrevem o banco (analista decide).
        """
        try:
            df_upload = pd.read_excel(xlsx_path, sheet_name='EPG', engine='openpyxl')
        except Exception as e:
            return False, f"Erro ao ler arquivo: {e}"

        df_db = self.load_db()
        db_by_id = {str(r['Unique ID']).strip(): i
                    for i, r in df_db.iterrows() if pd.notna(r.get('Unique ID'))}

        for _, row in df_upload.iterrows():
            uid = str(row.get('Unique ID', '')).strip()
            if not uid or uid == 'nan':
                continue
            if uid in db_by_id:
                idx = db_by_id[uid]
                for col in self.columns:
                    val = row.get(col, '')
                    if pd.notna(val) and str(val).strip() not in ('', 'nan'):
                        df_db.at[idx, col] = str(val)
            else:
                new_row = {col: row.get(col, '') for col in self.columns}
                df_db = pd.concat([df_db, pd.DataFrame([new_row])], ignore_index=True)

        ok, err = self.save_db(df_db)
        if not ok:
            return False, f"Erro ao salvar banco: {err}"
        return True, "Banco atualizado com sucesso."

    def retro_fill_images(self):
        """Preenche Series/Program Image vazias baseado no Unique ID."""
        df = self.load_db()
        changed = False
        for idx, row in df.iterrows():
            slug = str(row.get('Unique ID', '')).strip()
            if not slug or slug == 'nan':
                continue
            expected = f"{slug}.png"
            if pd.isna(row.get('Series Image')) or str(row.get('Series Image')).strip() in ('', 'nan'):
                df.at[idx, 'Series Image'] = expected
                changed = True
            if pd.isna(row.get('Program Image')) or str(row.get('Program Image')).strip() in ('', 'nan'):
                df.at[idx, 'Program Image'] = expected
                changed = True
        if changed:
            self.save_db(df)


epg_manager = EPGDatabaseManager()