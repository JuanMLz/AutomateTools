# Análise Detalhada: `generate_comparison_report()`

## Fluxo Atual da Função

```
INPUT: df_novo (saída de extract_and_clean_from_pdfs com colunas: Data, Horario, Programa_Bruto, Programa_Padronizado, chave)
       excel_anterior_path (caminho para planilha anterior)
       output_path (onde salvar o Excel comparado)

OUTPUT: Excel com pintura verde (NOVO/ALTERADO) e linhas amarelas separando dias
```

---

## Passo a Passo — O Que Faz

### **PASSO 1: Leitura do Template Anterior**
```python
try:
    df_antigo = pd.read_excel(excel_anterior_path, header=0)
    if 'Data' not in df_antigo.columns: raise ValueError()
except:
    df_antigo = pd.read_excel(excel_anterior_path, header=2)
```
**O que faz:** Tenta ler Excel anterior com `header=0`. Se não tiver coluna `Data`, tenta com `header=2`.

**Problema 1:** A lógica tenta 2 variações de header mas não garante que `Data` existe na segunda tentativa. Se falhar na segunda, levanta exceção genérica.

**Problema 2:** Assume que a estrutura anterior é sempre compatível com a nova (mesmas colunas `Data`, `Horario`, etc).

---

### **PASSO 2: Limpeza de Colunas**
```python
df_antigo = df_antigo.loc[:, ~df_antigo.columns.str.contains('^Unnamed')]
df_antigo.columns = df_antigo.columns.str.strip()

if 'Programa' in df_antigo.columns:
    df_antigo.rename(columns={'Programa': 'Programa_Padronizado'}, inplace=True)
```
**O que faz:** Remove colunas com prefixo `Unnamed`, limpa espaços dos nomes, renomeia `Programa` para `Programa_Padronizado`.

**Problema 3:** Pressupõe que a coluna de programa se chama `Programa` (não `Programa_Padronizado`, não `Nome`, etc). Se tiver outro nome, fica sem a coluna esperada e cai em erro silencioso depois.

---

### **PASSO 3: Criar Mapas de Índice de Dia (0–6)**
```python
df_novo['Data'] = df_novo['Data'].astype(str)
unique_dates_novo = df_novo['Data'].unique()
day_index_map_novo = {date_str: idx for idx, date_str in enumerate(unique_dates_novo)}

df_antigo['Data'] = df_antigo['Data'].astype(str)
unique_dates_antigo = df_antigo['Data'].unique()
day_index_map_antigo = {date_str: idx for idx, date_str in enumerate(unique_dates_antigo)}
```
**O que faz:** Para cada planilha, cria um mapa: `Data_string → índice_sequencial (0, 1, 2, ...)`.

**Problema 4:** `df_novo` já vem com `Data` como string de `extract_and_clean_from_pdfs`. A conversão é redundante.

**Problema 5:** Os mapas são criados a partir da ordem de aparição das datas **nas duas planilhas separadamente**. Se a planilha antiga tiver datas 01/11, 02/11, 03/11 e a nova tiver 03/11, 04/11, 05/11, os índices não correspondem:
- Antigo: {01/11: 0, 02/11: 1, 03/11: 2}
- Novo: {03/11: 0, 04/11: 1, 05/11: 2}

A chave para 03/11 09:00 será `2_09:00` na antigo, mas `0_09:00` na novo → **mismatch automático!**

---

### **PASSO 4: Gerar Chaves de Comparação**
```python
df_novo['chave'] = df_novo.apply(lambda row: _get_weekday_key(row, day_index_map_novo), axis=1)
df_antigo['chave'] = df_antigo.apply(lambda row: _get_weekday_key(row, day_index_map_antigo), axis=1)
```
**O que faz:** Aplica `_get_weekday_key()` a ambas planilhas, gerando chaves do tipo `"0_09:00"`.

**Problema 6:** Decorre diretamente do Problema 5 — as chaves não correspondem entre as duas planilhas!

---

### **PASSO 5: Construir Mapa de Consulta (Antigo)**
```python
db_sinopses = df_antigo.drop_duplicates(subset=['Programa_Padronizado'], keep='last')
mapa_antigo = pd.Series(df_antigo.Programa_Padronizado.values, index=df_antigo.chave).to_dict()
```
**O que faz:** 
- `db_sinopses`: Deduplica por nome do programa (guardar metadados / sinopses).
- `mapa_antigo`: Dicionário chave → nome do programa da planilha antigo.

**Problema 7:** O mapa usa **a última ocorrência** de cada chave (`.to_dict()` sempre pega o último valor em caso de duplicate). Se a mesma hora ocorre 2x na antigo, só a última fica no mapa.

**Problema 8:** Se uma chave não existir na antigo (por ex., porque a data é diferente entre os mapas), nunca será encontrada → marca como `NOVO` mesmo que o programa foi só movido de dia.

---

### **PASSO 6: Processamento de Registros (Comparação Efetiva)**
```python
for _, row in df_novo.iterrows():
    item = {
        'Data': row['Data'], 'Horario': row['Horario'], 'Programa': row['Programa_Padronizado'],
        'Status': 'SEM MUDANÇA'
    }
    
    # Recupera dados extras (Sinopse, etc)
    dados = db_sinopses[db_sinopses['Programa_Padronizado'] == item['Programa']]
    for col in colunas_extras:
        val = dados.iloc[0][col] if not dados.empty else ""
        item[col] = val if pd.notna(val) else ""

    # Verifica Mudanças
    prog_antigo = mapa_antigo.get(row['chave'])
    if not prog_antigo: item['Status'] = 'NOVO'
    elif item['Programa'] != prog_antigo: item['Status'] = 'ALTERADO'
```
**O que faz:**
1. Para cada linha da nova grade, cria um registro com Data, Horario, Programa_Padronizado.
2. Procura na `db_sinopses` por metadados do programa (sinopse, diretor, etc).
3. Consulta `mapa_antigo` pela chave. Se não achar, marca `NOVO`. Se achar mas programa diferente, marca `ALTERADO`.

**Problema 9:** A busca em `db_sinopses` usa `==` exato no nome do programa. Se houver variação mínima (espaço, acento que não foi filtrado), não encontra sinopse e deixa em branco.

**Problema 10:** A comparação `item['Programa'] != prog_antigo` compara strings diretamente. Ambas já deveriam ser normalizadas (via `extract_and_clean_from_pdfs`), mas se houver diferença mínima, marca como alterado.

**Problema 11:** O loop `for col in colunas_extras` faz uma busca **para cada linha**. Se a nova grade tem 500 linhas e 10 colunas extras, isso faz ~5000 buscas em `db_sinopses` — ineficiente.

---

### **PASSO 7: Escrita e Pintura do Excel**
```python
wb = load_workbook(excel_anterior_path)
ws = wb.active

fill_green = PatternFill("solid", fgColor="C6EFCE")
fill_yellow = PatternFill("solid", fgColor="FFFF00")
# ...

for reg in registros:
    # Linha Amarela (Separador de Dia)
    if last_date and reg['Data'] != last_date:
        for c in range(2, len(cols_order) + 3):
            cell = ws.cell(curr_row, c)
            cell.fill = fill_yellow
            cell.border = border
        curr_row += 1
    
    last_date = reg['Data']
    is_changed = reg['Status'] in ['NOVO', 'ALTERADO']

    # Escreve Dados
    for i, col in enumerate(cols_order):
        cell = ws.cell(curr_row, i + 2)
        cell.value = reg.get(col, "")
        cell.border = border
        cell.alignment = align
        if is_changed: cell.fill = fill_green
    
    curr_row += 1

wb.save(output_path)
```
**O que faz:** Carrega o template anterior, limpa as linhas de dados (linha 4+), escreve os novos registros com pintura (verde se alterado, separador amarelo entre dias).

**Problema 12:** Carrega o arquivo anterior inteiro usando `load_workbook()` — se o template tiver formatos/imagens/gráficos, tudo é carregado em memória. Ineficiente para arquivos grandes.

**Problema 13:** Limpa **100 linhas no mínimo** (`ws.delete_rows(start_row, amount=ws.max_row + 100)`). Se o arquivo anterior tem 50 linhas, deleta 150 — pode afetarcuidado com mergings/formatos abaixo.

---

## Resumo dos Problemas Críticos

| # | Problema | Impacto | Severidade |
|---|----------|--------|-----------|
| 5 | Mapas de índice de dia separados → **chaves não correspondem** | Falso positivo em mudar quase tudo | 🔴 CRÍTICO |
| 10 | Comparação sem normalização explícita | Pequenas variações marcam como alterado | 🟠 ALTO |
| 11 | Loop aninhado para buscar sinopses | Lento para grandes grades | 🟡 MÉDIO |
| 3 | Não detecta coluna `Programa` com nomes alternativos | Pode quebrar silenciosamente | 🟠 ALTO |
| 4 | Conversão redundante de `Data` para string | Micro-otimização | 🟢 BAIXO |

---

## Solução Proposta

### **Núcleo do Problema: Mapas de Índice Desalinhados**

A solução é simples: **usar a mesma estratégia de índice que foi usada em `extract_and_clean_from_pdfs`**.

Como `df_novo` já vem com `chave` calculada (no passo de extração), e já tem o índice correto, o ideal é:

1. **Reutilizar a `chave` de `df_novo`** (já validada).
2. **Ao ler `df_antigo`, recriar a `chave` usando a MESMA ordem de datas que `df_novo`**.
   - Se `df_antigo` tiver datas que não estão em `df_novo`, elas não entram no mapa → naturalmente marcadas como `NOVO`.
   - Se ambas compartilham datas, a chave será idêntica.

### **Pseudocódigo Simplificado**

```python
def generate_comparison_report(clean_schedule_df, excel_anterior_path, output_path):
    df_novo = clean_schedule_df.copy()  # Já tem: Data, Horario, Programa_Bruto, Programa_Padronizado, chave
    
    # Ler antigo
    df_antigo = pd.read_excel(excel_anterior_path, header=0|2)
    # Normalizar colunas (renomear se precisar)
    
    # Usar o MESMO mapa de índices que foi criado em df_novo!
    unique_dates_novo = df_novo['Data'].unique()
    day_index_map = {date_str: idx for idx, date_str in enumerate(unique_dates_novo)}
    
    # Normalizar Data/Horario em df_antigo (para garantir consistência)
    # ... (conversão de formatos)
    
    # Gerar chaves em df_antigo usando o MESMO mapa
    df_antigo['chave'] = df_antigo.apply(lambda row: _get_weekday_key(row, day_index_map), axis=1)
    
    # Comparação
    mapa_antigo = df_antigo.drop_duplicates(subset=['chave'], keep='last').set_index('chave')['Programa_Padronizado'].to_dict()
    
    # Loop simples
    for _, row in df_novo.iterrows():
        prog_novo = row['Programa_Padronizado']
        prog_antigo = mapa_antigo.get(row['chave'], None)
        
        if prog_antigo is None:
            status = 'NOVO'
        elif prog_novo != prog_antigo:
            status = 'ALTERADO'
        else:
            status = 'SEM MUDANÇA'
        
        # Escrever registro
```

---

## Próximos Passos

1. ✅ Corrigir **Problema 5** (Mapas desalinhados) — usar o mesmo mapa para ambas.
2. ✅ Simplificar a busca de sinopses (usar `.to_dict()` ao invés de busca em loop).
3. ⚠️ Melhorar tratamento de colunas variáveis (detecção de coluna `Programa`).
4. 📝 Remover conversões redundantes.

