# AutomateTools - AI Coding Agent Instructions

## Project Overview
**AutomateTools** é uma aplicação desktop (PySide6) que automatiza processamento de grades de programação de TV (PDFs) para uma emissora religiosa. O projeto é estruturado em três camadas: **UI** (PySide6), **Workers** (QThread), e **Tasks** (lógica de negócio).

### Core Purpose
- Extrair programas de PDFs de grades usando OCR (PyMuPDF).
- Mapear nomes brutos para nomes padronizados usando um arquivo CSV de DE-PARA.
- Gerar três tipos de saída: (1) Planilhas simples, (2) Relatórios comparativos com pintura Excel, (3) EPG visual.

---

## Architecture & Data Flow

### Layer 1: UI (PySide6) - `app/ui/`
**Key Files:** `main_window.py`, `grade_creator_widget.py`, `mapping_editor_widget.py`, `consolidator_widget.py`

- **MainWindow:** Janela principal com toolbar (StackedWidget alternando ferramentas).
- **GradeCreatorWidget:** Interface para seleção de PDFs, saídas e acionamento de processamento.
  - Fluxo: Seleciona PDFs → Verifica mapeamentos não-mapeados → Abre editor se necessário → Dispara Worker.
- **MappingEditorWidget:** Editor tabelado (QTableView + PandasModel) para gerenciar arquivo `mapeamento_programas.csv`.
  - Operações: add_row, remove_row, save_and_close (com merge de dados antigos se aplicável).
- **ConsolidatorWidget:** Consolidação de logs em Excel (funcionalidade separada).

**Pattern:** Widgets usam QThread workers para operações longas; signals/slots para comunicação.

### Layer 2: Workers (QThread) - `app/workers.py`
Cada worker é uma `QThread` que executa lógica de negócio em thread separada:
- **GradeExtractionWorker:** Chama `extract_and_clean_from_pdfs`, retorna DataFrame + erro via signal.
- **GradeComparisonWorker:** Chama `generate_comparison_report`, pinta Excel com status.
- **EpgGeneratorWorker:** Chama `generate_epg_from_simple_schedule`, gera EPG visual.

**Convention:** Worker `run()` sempre chama `finished.emit(result, error_msg)` com dois argumentos (result pode ser DataFrame, string ou None).

### Layer 3: Tasks (Business Logic) - `app/tasks/`
**Key Files:** `schedule_processor.py`, `mapping_manager.py`, `excel_consolidator.py`

#### schedule_processor.py
Core functions (3 fases):
1. **_extract_raw_data_from_pdfs(pdf_paths)** → Lê PDF com PyMuPDF, agrupa palavras por Y, separa Horário (<70px) de Programa (>70px).
2. **extract_and_clean_from_pdfs(pdf_paths)** → Aplica mapeamento, ordena cronologicamente, retorna `df[Data, Horario, Programa_Bruto, Programa_Padronizado]`.
3. **generate_comparison_report(df_novo, path_anterior, path_saida)** → Compara com planilha anterior, pinta verde (SEM MUDANÇA) / vermelho (NOVO/ALTERADO) usando openpyxl.
4. **generate_epg_from_simple_schedule(df)** → Cria layout visual tipo TV guide.

**Helper Functions:**
- `_get_weekday_key(row)` → Gera chave `"{weekday}_{HH:MM}"` para juntar registros (normalizando segundos).
- `_normalize_text_for_compare(value)` → Strip + collapse espaços + remove acentos + lower (usado internamente para comparações).

#### mapping_manager.py
Singleton-like class que gerencia arquivo CSV de mapeamento:
- **Paths:** Busca em `config.ini` no AppData. Se não encontrar, cria em AppData com template de `resources/mapeamento_programas.csv`.
- **Methods:**
  - `load_mapping_as_dict()` → Retorna `(mapping_dict, error)` onde dict = `{"Nome_do_PDF": "Nome_Padronizado"}`.
  - `load_mapping_as_df()` → Retorna `(DataFrame, error)` para edição.
  - `save_mapping_from_df(df)` → Persiste alterações.
  - `set_mapping_filepath(new_path)` → Permite conectar arquivo diferente via config.ini.

**Pattern:** Métodos retornam tuplas `(resultado, erro)` onde erro é None (sucesso) ou string descritiva.

---

## Critical Developer Workflows

### 1. Adding/Modifying PDF Extraction Logic
**File:** `app/tasks/schedule_processor.py` → `_extract_raw_data_from_pdfs()`

**Current Approach:** Agrupa palavras por eixo Y, separa coluna X em horário (<70px) vs programa (>70px).

**Risks:** PDFs com layouts variados podem quebrar. Ajuste `COLUMN_DIVIDER_X = 70.0` se necessário.

**Test:** Use `tools.py` para analisar diffs antes/depois das mudanças.

### 2. Updating Comparison Logic (Pintura Excel)
**File:** `app/tasks/schedule_processor.py` → `generate_comparison_report()`

**Key:** Chave de comparação é `weekday_HH:MM`. Se horários chegarem em formatos diferentes, use `_get_weekday_key()` que normaliza.

**Recent Fix:** Horários agora normalizados para `HH:MM` antes de comparar (evita `00:00:00` vs `00:00` mismatch).

**Fuzzy Matching:** Se precisar de comparação "quase igual", use `difflib.SequenceMatcher(...).ratio() >= THRESHOLD` (recomendado 0.87).

### 3. Mapping File Management
**File:** `app/ui/mapping_editor_widget.py` + `app/tasks/mapping_manager.py`

**Flow:**
1. User abre editor → `MappingEditorWidget` carrega `mapping_manager.load_mapping_as_df()`.
2. User edita tabela (add_row, remove_row, inline edits).
3. User clica "Salvar" → `save_and_close()` chama `mapping_manager.save_mapping_from_df(df)`.
4. Se `new_unmapped_list` foi fornecido (modo aprendizado), concatena com dados antigos, remove duplicatas, limpa vazios.

**Convention:** Sempre chamar `mapping_manager.load_mapping_as_dict()` para obter mapeamento corrente (respeita config.ini).

### 4. Diagnostic & Analysis Tool (NOT Part of App Runtime)
**File:** `tools.py` (standalone diagnostic script - NÃO faz parte do código da aplicação)

**Purpose:** Apenas para análise/debug — compara arquivo Excel antigo com o novo gerado pela app e detecta diferenças reais vs. falsos positivos.

**Command:**
```powershell
& .\venv\Scripts\python.exe .\tools.py "path\nova.xlsx" "path\antiga.xlsx" "output.xlsx"
```

**Output:** `grade_diff_report.xlsx` com abas `diff_rows` (detalhes linha-a-linha) e `summary` (contagens Status).

**What it does:** Normaliza horários (HH:MM) + nomes (remove acentos, espaços, lower-case) e cria chave `weekday_HH:MM` para comparação precisa.

**When to use:** Quando o comparador do app (generate_comparison_report) marca muitas mudanças, rode `tools.py` para confirmar se são verdadeiras alterações ou falsos positivos causados por formatação.

---

## Project-Specific Patterns & Conventions

### Signal/Slot Naming
- Worker signals: `finished = Signal(result_type, str)` → Sempre emite `(resultado, msg_erro)`.
- UI slots: `_on_worker_finished(self, result, error)` → Trata ambos os casos.

### Error Handling Pattern
```python
resultado, erro = mapping_manager.load_mapping_as_dict()
if erro:
    QMessageBox.critical(self, "Erro", erro)
    return
# usar resultado
```

### DataFrame Column Conventions
- **Extraído:** `Data` (str "DD/MM/YYYY"), `Horario` (str "HH:MM"), `Programa_Bruto` (raw PDF text), `Programa_Padronizado` (após mapeamento).
- **Comparison:** Adiciona coluna `chave` (weekday_HH:MM) para lookup em histórico.

### File I/O & Paths
- **Executável (PyInstaller):** `sys._MEIPASS` aponta para bundle. Usa AppData para arquivos persistentes.
- **Development:** Usa `resources/` para templates (cópia para AppData se não existir).
- **Config:** `config.ini` no AppData define caminhos custom (ex: arquivo mapeamento em rede).

---

## Common Debugging Techniques

1. **Comparison "tudo alterado"?**
   - Inspecione `tools.py` output de `Antigo_Normalizado` vs `Programa_Normalizado`.
   - Verifique se horários batem (HH:MM sem segundos).
   - Use fuzzy threshold (~0.87) para tolerância de pequenas diferenças.

2. **PDF extraction quebrado?**
   - Abra PDF em PyMuPDF viewer, confirme que `COLUMN_DIVIDER_X` está correto.
   - Log: `print(lines[line_key])` antes de processar para inspecionar agrupamento de palavras.

3. **Mapping não encontrado?**
   - Verifique `mapping_manager.get_mapping_filepath()` → Confirma caminho usado.
   - Se customizado, verifique `config.ini` em AppData.

4. **UI congelada?**
   - Sempre use `GradeExtractionWorker` (QThread) para operações longas (PDFs, Excel grande).
   - Conecte `worker.finished.connect(self._on_finished)` antes de `worker.start()`.

---

## Key Dependencies & Versions
- **PySide6** (6.10.1): UI framework.
- **pandas** (2.3.3): DataFrame manipulation.
- **PyMuPDF (fitz)** (1.26.6): PDF text extraction (não OCR, apenas coordenadas).
- **openpyxl** (3.1.5): Excel file manipulation.
- **xlsxwriter** (3.2.9): Excel generation.

---

## Recent Issues & Solutions
1. **Horário mismatch (HH:MM vs HH:MM:SS):** Normalizar em `_get_weekday_key()` e coluna `Horario` antes de comparar.
2. **Falsos positivos em comparação:** Usar `value_counts().idxmax()` (moda) ao mapear histórico, não `keep='last'`.
3. **Unmapped programs popup:** Função `find_unmapped_programs()` retorna `(lista, erro)` e dispara `MappingEditorWidget` se necessário.

---

## AI Agent Checklist Before Modifying Core Logic
- [ ] Testei mudança com `tools.py` (análise de diff).
- [ ] Mantive convenção de retorno `(resultado, erro)`.
- [ ] Se altero chave de comparação, verifiquei todas as 3 saídas (simples, comparada, EPG).
- [ ] Normalizei strings/datas consistentemente (use `_normalize_text_for_compare()` ou `_get_weekday_key()`).
- [ ] Executei fluxo GUI e testei popup de mapeamento com PDFs não-mapeados.
- [ ] Fiz commit com mensagem clara referenciando tipo de mudança (fix, refactor, feature).

---

## File Structure Reference
```
U:\automateTools/
├── main.py                          # Entry point
├── tools.py                         # Standalone analyzer (não parte da app)
├── requirements.txt
├── resources/
│   └── mapeamento_programas.csv     # Template de mapeamento
├── app/
│   ├── workers.py                   # QThread workers
│   ├── tasks/
│   │   ├── schedule_processor.py    # Core: PDF extraction, comparison, EPG
│   │   ├── mapping_manager.py       # File/config management
│   │   └── excel_consolidator.py    # Log consolidation (separate feature)
│   └── ui/
│       ├── main_window.py
│       ├── grade_creator_widget.py  # Main workflow
│       ├── mapping_editor_widget.py # Table editor
│       └── consolidator_widget.py
└── .github/
    └── copilot-instructions.md      # This file
```
