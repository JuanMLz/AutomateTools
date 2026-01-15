# app/tasks/mapping_manager.py
import os
import sys
import shutil
import pandas as pd
import configparser
from PySide6.QtCore import QStandardPaths

class MappingManager:
    def __init__(self, filename="mapeamento_programas.csv", config_filename="config.ini"):
        # 1. Define a pasta padrão organizada (AppData/Local/AutomateTools)
        # Isso garante que todos os arquivos de configuração fiquem juntos
        app_data_root = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.app_dir = os.path.join(app_data_root, "AutomateTools")
        
        # Cria a pasta se não existir
        os.makedirs(self.app_dir, exist_ok=True)

        # O config.ini também fica dentro dessa pasta organizada
        self.config_filepath = os.path.join(self.app_dir, config_filename)
        
        # --- Lógica de Configuração ---
        self.config = configparser.ConfigParser()
        self.config.read(self.config_filepath)
        
        # Verifica se o usuário mudou o local do arquivo CSV no config.ini
        if 'Paths' in self.config and 'mapping_file' in self.config['Paths']:
            self.filepath = self.config['Paths']['mapping_file']
        else:
            # Se não, usa o padrão DENTRO da pasta AutomateTools
            self.filepath = os.path.join(self.app_dir, filename)

        # --- Lógica de Criação de Template (Blindada para .exe) ---
        # Só copia se o arquivo NÃO existir no destino
        if not os.path.exists(self.filepath):
            # Descobre onde o programa está rodando (se é .exe ou .py)
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(sys.executable)
            else:
                base_path = os.path.abspath(".")
            
            # Caminho do template na pasta resources do projeto
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
            # Tenta ler com vírgula (padrão)
            df = pd.read_csv(filepath_to_load)
            
            # Se parecer errado (1 coluna), tenta ponto e vírgula (Excel BR)
            if df.shape[1] < 2:
                df = pd.read_csv(filepath_to_load, sep=';')

            if "Nome_do_PDF" not in df.columns or "Nome_Padronizado" not in df.columns:
                 return {}, None # Retorna vazio se mal formatado, mas não crasha
            
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
            # Tenta separador alternativo se necessário
            if df.shape[1] < 2:
                df = pd.read_csv(filepath_to_load, sep=';')
            
            # Garante que as colunas existam
            if "Nome_do_PDF" not in df.columns: df["Nome_do_PDF"] = ""
            if "Nome_Padronizado" not in df.columns: df["Nome_Padronizado"] = ""
            
            return df, None 
        except FileNotFoundError:
             return None, f"Erro Crítico: O arquivo de mapeamento não foi encontrado em '{filepath_to_load}'."
        except pd.errors.EmptyDataError:
             return pd.DataFrame(columns=["Nome_do_PDF", "Nome_Padronizado"]), None
        except Exception as e:
            return None, f"Erro ao ler o arquivo de mapeamento como DataFrame: {e}"

    def save_mapping_from_df(self, dataframe):
        try:
            # Sempre salva com vírgula para manter padrão
            dataframe.to_csv(self.filepath, index=False)
            return True, "Mapeamento salvo com sucesso."
        except Exception as e:
            return False, f"Erro ao salvar o mapeamento: {e}"

mapping_manager = MappingManager()