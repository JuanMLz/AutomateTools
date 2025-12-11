# app/tasks/mapping_manager.py
# Gerenciador de mapeamento, com suporte a executável (PyInstaller) e Config customizada.

import os
import sys
import shutil
import pandas as pd
from PySide6.QtCore import QStandardPaths
import configparser

class MappingManager:
    def __init__(self, filename="mapeamento_programas.csv", config_filename="config.ini"):
        # Localização do arquivo de configuração (sempre no AppData do usuário)
        # Isso garante permissão de escrita sem precisar de Admin
        self.config_path_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.config_filepath = os.path.join(self.config_path_dir, config_filename)
        
        # --- Lógica de Configuração ---
        self.config = configparser.ConfigParser()
        self.config.read(self.config_filepath)
        
        # Procura por um caminho personalizado no config.ini
        if 'Paths' in self.config and 'mapping_file' in self.config['Paths']:
            self.filepath = self.config['Paths']['mapping_file']
        else:
            # Se não encontrar, usa o AppData como padrão (padrão seguro)
            self.filepath = os.path.join(self.config_path_dir, filename)

        # --- Lógica de Criação de Template (Blindada para .exe) ---
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        
        if not os.path.exists(self.filepath):
            # AQUI ESTÁ O SEGREDO: Descobre onde o programa está rodando
            if getattr(sys, 'frozen', False):
                # Se for executável (PyInstaller), usa a pasta temporária do MEIPASS
                base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
            else:
                # Se for rodando no VSCode/Python normal
                base_path = os.path.abspath(".")
            
            # Caminho absoluto para a pasta resources
            template_path = os.path.join(base_path, "resources", filename)

            if os.path.exists(template_path):
                shutil.copy(template_path, self.filepath)
            else:
                # Se não achar o template, cria um CSV vazio com cabeçalho
                pd.DataFrame(columns=["Nome_do_PDF", "Nome_Padronizado"]).to_csv(self.filepath, index=False)

    def get_mapping_filepath(self):
        """Retorna o caminho ATUAL do arquivo de mapeamento."""
        return self.filepath
    
    def set_mapping_filepath(self, new_path):
        """Define e salva um novo caminho personalizado para o arquivo de mapeamento."""
        if not self.config.has_section('Paths'):
            self.config.add_section('Paths')
        
        self.config.set('Paths', 'mapping_file', new_path)
        
        with open(self.config_filepath, 'w') as configfile:
            self.config.write(configfile)
        
        # Atualiza o caminho em tempo de execução
        self.filepath = new_path
        return True

    def load_mapping_as_dict(self):
        filepath_to_load = self.get_mapping_filepath()
        try:
            df = pd.read_csv(filepath_to_load)
            if "Nome_do_PDF" not in df.columns or "Nome_Padronizado" not in df.columns:
                 return None, "Erro: Arquivo de mapeamento mal formatado."
            df.dropna(subset=["Nome_do_PDF", "Nome_Padronizado"], inplace=True)
            mapping_dict = pd.Series(df.Nome_Padronizado.values, index=df.Nome_do_PDF).to_dict()
            return mapping_dict, None
        except FileNotFoundError:
             return None, f"Erro Crítico: O arquivo de mapeamento não foi encontrado em '{filepath_to_load}'."
        except pd.errors.EmptyDataError:
             return {}, None
        except Exception as e:
            return None, f"Erro ao ler o arquivo de mapeamento: {e}"

    def load_mapping_as_df(self):
        """
        Carrega o arquivo de mapeamento DO USUÁRIO e o retorna como um DataFrame do Pandas.
        """
        filepath_to_load = self.get_mapping_filepath()
        
        try:
            df = pd.read_csv(filepath_to_load)
            # Garante que as colunas existam, mesmo que o DF esteja vazio
            if "Nome_do_PDF" not in df.columns: df["Nome_do_PDF"] = ""
            if "Nome_Padronizado" not in df.columns: df["Nome_Padronizado"] = ""
            
            return df, None # Retorna o DataFrame e Nenhum erro
        except FileNotFoundError:
             return None, f"Erro Crítico: O arquivo de mapeamento não foi encontrado em '{filepath_to_load}'."
        except pd.errors.EmptyDataError:
             # Se o arquivo estiver vazio, retorna um DataFrame com as colunas corretas
             return pd.DataFrame(columns=["Nome_do_PDF", "Nome_Padronizado"]), None
        except Exception as e:
            return None, f"Erro ao ler o arquivo de mapeamento como DataFrame: {e}"

    def save_mapping_from_df(self, dataframe):
        try:
            # CORREÇÃO: Usava self.user_filepath que não existia. Corrigido para self.filepath
            dataframe.to_csv(self.filepath, index=False)
            return True, "Mapeamento salvo com sucesso."
        except Exception as e:
            return False, f"Erro ao salvar o mapeamento: {e}"

mapping_manager = MappingManager()