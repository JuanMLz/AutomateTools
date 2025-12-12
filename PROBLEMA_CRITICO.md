# 🔴 PROBLEMA CRÍTICO ENCONTRADO

## Mapas de Índice de Dia Desalinhados

### O Problema

Quando a função `generate_comparison_report()` lê a planilha anterior, ela cria um **novo** mapa de índices a partir das datas daquela planilha:

```python
# Planilha Nova:   01/11, 02/11, 03/11
day_index_map_novo = {
    '01/11': 0,
    '02/11': 1,
    '03/11': 2
}
# Chave para 03/11 09:00 = "2_09:00"

# Planilha Antiga: 03/11, 04/11, 05/11
day_index_map_antigo = {
    '03/11': 0,
    '04/11': 1,
    '05/11': 2
}
# Chave para 03/11 09:00 = "0_09:00"  ← CHAVE DIFERENTE!
```

**Resultado:** Um programa que estava em `03/11 09:00` na semana anterior é procurado com chave `"2_09:00"` na nova, mas a planilha antiga só tem `"0_09:00"` → **não encontra, marca como NOVO mesmo que existia.**

---

## A Solução

Usar o **MESMO mapa de índices** para ambas as planilhas:

```python
# Criar mapa UMA VEZ, com base na NOVA grade
unique_dates_novo = df_novo['Data'].unique()  # [01/11, 02/11, 03/11, ...]
day_index_map = {date_str: idx for idx, date_str in enumerate(unique_dates_novo)}

# Aplicar ESSE MESMO MAPA a AMBAS as planilhas
df_novo['chave'] = df_novo.apply(lambda row: _get_weekday_key(row, day_index_map), axis=1)
df_antigo['chave'] = df_antigo.apply(lambda row: _get_weekday_key(row, day_index_map), axis=1)
```

**Efeito:** 
- Datas que existem em AMBAS → mesmo índice → mesma chave → correto.
- Datas que existem SÓ na antigo → mapa não tem a data → `_get_weekday_key` faz fallback (`day_index=0`) → chave diferente → naturalmente descartada.
- Datas que existem SÓ na nova → comparação correta (marca como NOVO).

---

## Impacto Esperado

**Antes:** Marca muitos `NOVO`/`ALTERADO` falsos.  
**Depois:** Só marca `NOVO`/`ALTERADO` se houver mudança real no programa entre as mesmas datas/horas.

