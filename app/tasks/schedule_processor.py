# app/tasks/schedule_processor.py

# =========================================================
# == ARQUIVO PONTE (FACADE)                              ==
# == Este arquivo redireciona as chamadas antigas para   ==
# == os novos módulos organizados.                       ==
# =========================================================

# Importa as funções dos novos arquivos
from .utils import slugify, get_weekday_key
from .pdf_extractor import (
    extract_and_clean_from_pdfs, 
    find_unmapped_programs,
    _extract_raw_data_from_pdfs # Caso alguém chame direto
)
from .report_generators import (
    generate_epg_from_simple_schedule, 
    generate_comparison_report
)

# Se precisar expor o mapping_manager aqui também (compatibilidade)
from .mapping_manager import mapping_manager

# =========================================================
# FIM DO ARQUIVO
# Agora o resto do seu programa (UI, Workers) pode continuar
# importando "app.tasks.schedule_processor" e tudo funcionará.
# =========================================================