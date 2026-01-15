# app/tasks/dashboard_generator.py
"""
Gerador de Dashboard em PDF para relatório de antenas.
Gera 3 páginas: Resumo, Tendência e Histórico.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from datetime import datetime


# Configuração de cores
COLORS = {
    'red': '#E74C3C',
    'green': '#27AE60', 
    'blue': '#3498DB',
    'orange': '#F39C12',
    'purple': '#9B59B6',
    'gray': '#7F8C8D',
    'dark': '#2C3E50',
    'light_gray': '#ECF0F1',
    'white': '#FFFFFF',
}

# Paleta para gráficos
CHART_PALETTE = ['#3498DB', '#E74C3C', '#2ECC71', '#F39C12', '#9B59B6', 
                 '#1ABC9C', '#E67E22', '#34495E', '#16A085', '#C0392B']


def generate_dashboard_pdf(metrics, output_path, title="Relatório de Antenas"):
    """
    Gera um dashboard em PDF com 3 páginas.
    """
    try:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'DejaVu Sans']
        
        with PdfPages(output_path) as pdf:
            # Página 1: Resumo da Semana
            fig1 = _create_summary_page(metrics, title)
            pdf.savefig(fig1, bbox_inches='tight')
            plt.close(fig1)
            
            # Página 2: Análise de Tendência
            fig2 = _create_trend_page(metrics)
            pdf.savefig(fig2, bbox_inches='tight')
            plt.close(fig2)
            
            # Página 3: Histórico e Cidades Críticas
            fig3 = _create_history_page(metrics)
            pdf.savefig(fig3, bbox_inches='tight')
            plt.close(fig3)
        
        return True, f"Dashboard salvo em: {output_path}"
    
    except Exception as e:
        import traceback
        return False, f"Erro ao gerar dashboard: {e}\n{traceback.format_exc()}"


# =============================================================================
# PÁGINA 1: RESUMO DA SEMANA
# =============================================================================
def _create_summary_page(metrics, title):
    """Cria a página de resumo da semana."""
    fig = plt.figure(figsize=(11.69, 8.27))  # A4 Landscape
    
    periodo = metrics.get('periodo', {})
    periodo_str = f"{periodo.get('inicio', '')} a {periodo.get('fim', '')}"
    
    # Título
    fig.suptitle(f"📡 {title}", fontsize=20, fontweight='bold', 
                 color=COLORS['dark'], y=0.96)
    fig.text(0.5, 0.91, f"Período: {periodo_str}", 
             ha='center', fontsize=11, color=COLORS['gray'])
    
    # Grid
    gs = fig.add_gridspec(3, 3, hspace=0.35, wspace=0.3, 
                          left=0.06, right=0.94, top=0.85, bottom=0.08)
    
    # === LINHA 1: KPIs principais ===
    ax_kpi1 = fig.add_subplot(gs[0, 0])
    ax_kpi2 = fig.add_subplot(gs[0, 1])
    ax_kpi3 = fig.add_subplot(gs[0, 2])
    
    _draw_kpi_card(ax_kpi1, 
                   value=metrics.get('total_fora_atual', 0),
                   label="FORA DO AR",
                   sublabel="atualmente",
                   icon="🔴",
                   color=COLORS['red'])
    
    _draw_kpi_card(ax_kpi2,
                   value=metrics.get('total_resolvidas_semana', 0),
                   label="RESOLVIDAS",
                   sublabel="no período",
                   icon="✅",
                   color=COLORS['green'])
    
    _draw_kpi_card(ax_kpi3,
                   value=metrics.get('total_novas_semana', 0),
                   label="NOVAS",
                   sublabel="no período",
                   icon="🆕",
                   color=COLORS['orange'])
    
    # === LINHA 2: KPIs secundários + Gráfico por Estado ===
    ax_kpi4 = fig.add_subplot(gs[1, 0])
    ax_estados = fig.add_subplot(gs[1, 1:])
    
    # KPI de tempo médio e percentual
    tempo_medio = metrics.get('tempo_medio_resolucao', 0)
    percentual = metrics.get('percentual_fora')
    taxa = metrics.get('taxa_resolucao', 0)
    
    # Desenha KPIs menores
    ax_kpi4.axis('off')
    kpi_text = (
        f"⏱️ Tempo Médio Resolução\n"
        f"   {tempo_medio} dias\n\n"
        f"📊 % do Total Fora\n"
        f"   {percentual if percentual else 'N/D'}%\n\n"
        f"📈 Taxa de Resolução\n"
        f"   {taxa}%"
    )
    ax_kpi4.text(0.5, 0.5, kpi_text, ha='center', va='center',
                 fontsize=11, color=COLORS['dark'],
                 bbox=dict(boxstyle='round,pad=0.5', facecolor=COLORS['light_gray'],
                          edgecolor=COLORS['blue'], linewidth=2),
                 transform=ax_kpi4.transAxes, family='monospace')
    
    # Gráfico por Estado
    _draw_bar_chart(ax_estados, 
                    data=metrics.get('por_estado', {}),
                    title="📍 Distribuição por Estado (Atual)",
                    max_items=8)
    
    # === LINHA 3: Por Motivo e Por Região ===
    ax_motivo = fig.add_subplot(gs[2, 0:2])
    ax_regiao = fig.add_subplot(gs[2, 2])
    
    _draw_horizontal_bar(ax_motivo,
                         data=metrics.get('por_motivo', {}),
                         title="📊 Por Motivo de Parada",
                         color=COLORS['orange'])
    
    _draw_pie_chart(ax_regiao,
                    data=metrics.get('por_regiao', {}),
                    title="🗺️ Por Região")
    
    # Rodapé
    fig.text(0.5, 0.02, f"AutomateTools | Gerado em: {metrics.get('data_geracao', '')}", 
             ha='center', fontsize=8, color=COLORS['gray'], style='italic')
    
    return fig


# =============================================================================
# PÁGINA 2: ANÁLISE DE TENDÊNCIA
# =============================================================================
def _create_trend_page(metrics):
    """Cria a página de análise de tendência."""
    fig = plt.figure(figsize=(11.69, 8.27))
    
    fig.suptitle("📈 Análise de Tendência", fontsize=18, fontweight='bold', 
                 color=COLORS['dark'], y=0.96)
    
    periodo = metrics.get('periodo', {})
    fig.text(0.5, 0.91, f"Período: {periodo.get('inicio', '')} a {periodo.get('fim', '')}", 
             ha='center', fontsize=10, color=COLORS['gray'])
    
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.3, 
                          left=0.08, right=0.92, top=0.85, bottom=0.1)
    
    # === Gráfico de Evolução Diária ===
    ax_evolucao = fig.add_subplot(gs[0, :])
    evolucao = metrics.get('evolucao_diaria', [])
    
    if evolucao:
        datas = [e['data_str'] for e in evolucao]
        quantidades = [e['quantidade'] for e in evolucao]
        
        ax_evolucao.plot(datas, quantidades, marker='o', linewidth=2.5, 
                         markersize=10, color=COLORS['blue'])
        ax_evolucao.fill_between(datas, quantidades, alpha=0.2, color=COLORS['blue'])
        
        # Adiciona valores nos pontos
        for i, (x, y) in enumerate(zip(datas, quantidades)):
            ax_evolucao.annotate(str(y), (x, y), textcoords="offset points", 
                                 xytext=(0, 10), ha='center', fontsize=10, fontweight='bold')
        
        ax_evolucao.set_ylabel('Quantidade Fora do Ar', fontsize=10)
        ax_evolucao.set_xlabel('Data', fontsize=10)
        ax_evolucao.grid(True, alpha=0.3)
        
        # Indicador de tendência
        tendencia = metrics.get('tendencia', {})
        status = tendencia.get('status', 'N/D')
        diff = tendencia.get('diff', 0)
        
        if status == 'MELHORANDO':
            emoji = '↓'
            cor = COLORS['green']
        elif status == 'PIORANDO':
            emoji = '↑'
            cor = COLORS['red']
        else:
            emoji = '→'
            cor = COLORS['gray']
        
        ax_evolucao.set_title(f"Evolução Diária de Cidades Fora do Ar   |   {emoji} {status} ({diff})", 
                              fontsize=12, fontweight='bold', color=COLORS['dark'])
    else:
        ax_evolucao.text(0.5, 0.5, "Sem dados de evolução", ha='center', va='center')
        ax_evolucao.axis('off')
    
    ax_evolucao.spines['top'].set_visible(False)
    ax_evolucao.spines['right'].set_visible(False)
    
    # === Tempo Médio por Motivo ===
    ax_tempo_motivo = fig.add_subplot(gs[1, 0])
    tempo_motivo = metrics.get('tempo_medio_por_motivo', {})
    
    if tempo_motivo:
        _draw_horizontal_bar_with_values(ax_tempo_motivo, tempo_motivo,
                                         title="⏱️ Tempo Médio de Resolução por Motivo (dias)",
                                         color=COLORS['purple'],
                                         suffix=" dias")
    else:
        ax_tempo_motivo.text(0.5, 0.5, "Sem dados históricos\nde resolução por motivo", 
                             ha='center', va='center', fontsize=10, color=COLORS['gray'])
        ax_tempo_motivo.set_title("⏱️ Tempo Médio por Motivo", fontsize=11, fontweight='bold')
        ax_tempo_motivo.axis('off')
    
    # === Tempo Médio por Região ===
    ax_tempo_regiao = fig.add_subplot(gs[1, 1])
    tempo_regiao = metrics.get('tempo_medio_por_regiao', {})
    
    if tempo_regiao:
        _draw_horizontal_bar_with_values(ax_tempo_regiao, tempo_regiao,
                                         title="🗺️ Tempo Médio de Resolução por Região (dias)",
                                         color=COLORS['blue'],
                                         suffix=" dias")
    else:
        ax_tempo_regiao.text(0.5, 0.5, "Sem dados históricos\nde resolução por região", 
                             ha='center', va='center', fontsize=10, color=COLORS['gray'])
        ax_tempo_regiao.set_title("🗺️ Tempo Médio por Região", fontsize=11, fontweight='bold')
        ax_tempo_regiao.axis('off')
    
    # Rodapé
    fig.text(0.5, 0.02, "Os tempos médios são calculados com base no histórico de resoluções anteriores.", 
             ha='center', fontsize=8, color=COLORS['gray'], style='italic')
    
    return fig


# =============================================================================
# PÁGINA 3: HISTÓRICO E CIDADES CRÍTICAS
# =============================================================================
def _create_history_page(metrics):
    """Cria a página de histórico e cidades críticas."""
    fig = plt.figure(figsize=(11.69, 8.27))
    
    fig.suptitle("📚 Análise Histórica & Cidades Críticas", fontsize=18, fontweight='bold', 
                 color=COLORS['dark'], y=0.96)
    
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25, 
                          left=0.06, right=0.94, top=0.88, bottom=0.08)
    
    # === TOP 10 Críticas ===
    ax_criticas = fig.add_subplot(gs[0, :])
    top_criticas = metrics.get('top_criticas', [])
    
    ax_criticas.axis('off')
    ax_criticas.set_title("🔴 TOP 10 - Cidades há mais tempo fora do ar", 
                          fontsize=12, fontweight='bold', color=COLORS['dark'], loc='left')
    
    if top_criticas:
        # Cria tabela
        table_data = []
        for i, c in enumerate(top_criticas[:10], 1):
            table_data.append([
                f"{i}º",
                c.get('cidade', '')[:25],
                c.get('estado', ''),
                f"{c.get('dias', 0)} dias",
                c.get('motivo', '')[:20]
            ])
        
        headers = ['#', 'Cidade', 'UF', 'Tempo Fora', 'Motivo']
        
        table = ax_criticas.table(
            cellText=table_data,
            colLabels=headers,
            loc='center',
            cellLoc='left',
            colWidths=[0.06, 0.35, 0.08, 0.15, 0.25]
        )
        
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.2, 1.8)
        
        # Estiliza cabeçalho
        for j in range(len(headers)):
            cell = table[(0, j)]
            cell.set_facecolor(COLORS['red'])
            cell.set_text_props(color='white', fontweight='bold')
        
        # Alterna cores e destaca por tempo
        for i in range(1, len(table_data) + 1):
            dias = top_criticas[i-1].get('dias', 0)
            for j in range(len(headers)):
                cell = table[(i, j)]
                if dias >= 60:
                    cell.set_facecolor('#FADBD8')  # Vermelho claro
                elif dias >= 30:
                    cell.set_facecolor('#FCF3CF')  # Amarelo claro
                elif i % 2 == 0:
                    cell.set_facecolor(COLORS['light_gray'])
    else:
        ax_criticas.text(0.5, 0.5, "Nenhuma cidade no histórico ainda.", 
                         ha='center', va='center', fontsize=11, color=COLORS['gray'])
    
    # === Resolvidas no Período ===
    ax_resolvidas = fig.add_subplot(gs[1, 0])
    lista_resolvidas = metrics.get('lista_resolvidas', [])
    
    ax_resolvidas.axis('off')
    ax_resolvidas.set_title("✅ Resolvidas no Período", 
                            fontsize=11, fontweight='bold', color=COLORS['dark'], loc='left')
    
    if lista_resolvidas:
        table_data = []
        for c in lista_resolvidas[:8]:
            table_data.append([
                c.get('cidade', '')[:20],
                c.get('estado', ''),
                f"{c.get('dias', 0)} dias",
                c.get('motivo', '')[:15]
            ])
        
        headers = ['Cidade', 'UF', 'Tempo', 'Motivo']
        
        table = ax_resolvidas.table(
            cellText=table_data,
            colLabels=headers,
            loc='center',
            cellLoc='left',
            colWidths=[0.35, 0.12, 0.18, 0.30]
        )
        
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1.1, 1.6)
        
        for j in range(len(headers)):
            cell = table[(0, j)]
            cell.set_facecolor(COLORS['green'])
            cell.set_text_props(color='white', fontweight='bold')
        
        for i in range(1, len(table_data) + 1):
            for j in range(len(headers)):
                cell = table[(i, j)]
                if i % 2 == 0:
                    cell.set_facecolor('#D5F5E3')  # Verde claro
    else:
        ax_resolvidas.text(0.5, 0.5, "Nenhuma cidade\nresolvida no período", 
                           ha='center', va='center', fontsize=10, color=COLORS['gray'])
    
    # === Resumo do Histórico ===
    ax_resumo = fig.add_subplot(gs[1, 1])
    ax_resumo.axis('off')
    ax_resumo.set_title("📊 Resumo do Período", 
                        fontsize=11, fontweight='bold', color=COLORS['dark'], loc='left')
    
    total_fora = metrics.get('total_fora_atual', 0)
    total_resolvidas = metrics.get('total_resolvidas_semana', 0)
    total_novas = metrics.get('total_novas_semana', 0)
    tempo_medio = metrics.get('tempo_medio_resolucao', 0)
    taxa = metrics.get('taxa_resolucao', 0)
    
    resumo_text = (
        f"┌────────────────────────────────┐\n"
        f"│                                │\n"
        f"│  🔴 Fora do ar atual:    {total_fora:>4}  │\n"
        f"│  ✅ Resolvidas:          {total_resolvidas:>4}  │\n"
        f"│  🆕 Novas ocorrências:   {total_novas:>4}  │\n"
        f"│                                │\n"
        f"│  ⏱️ Tempo médio:      {tempo_medio:>5} dias │\n"
        f"│  📈 Taxa resolução:    {taxa:>5}%  │\n"
        f"│                                │\n"
        f"└────────────────────────────────┘"
    )
    
    ax_resumo.text(0.5, 0.5, resumo_text, ha='center', va='center',
                   fontsize=10, color=COLORS['dark'],
                   transform=ax_resumo.transAxes, family='monospace',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_gray'],
                            edgecolor=COLORS['blue'], linewidth=2))
    
    # Rodapé
    fig.text(0.5, 0.02, f"AutomateTools | Gerado em: {metrics.get('data_geracao', '')}", 
             ha='center', fontsize=8, color=COLORS['gray'], style='italic')
    
    return fig


# =============================================================================
# FUNÇÕES AUXILIARES DE DESENHO
# =============================================================================

def _draw_kpi_card(ax, value, label, sublabel="", icon="", color=COLORS['blue']):
    """Desenha um card de KPI."""
    ax.axis('off')
    
    rect = mpatches.FancyBboxPatch((0.05, 0.1), 0.9, 0.8,
                                    boxstyle="round,pad=0.02,rounding_size=0.1",
                                    facecolor=COLORS['light_gray'],
                                    edgecolor=color, linewidth=3)
    ax.add_patch(rect)
    
    ax.text(0.5, 0.65, f"{icon} {value}", ha='center', va='center',
            fontsize=28, fontweight='bold', color=color,
            transform=ax.transAxes)
    
    ax.text(0.5, 0.3, label, ha='center', va='center',
            fontsize=11, fontweight='bold', color=COLORS['dark'],
            transform=ax.transAxes)
    
    if sublabel:
        ax.text(0.5, 0.15, sublabel, ha='center', va='center',
                fontsize=8, color=COLORS['gray'], style='italic',
                transform=ax.transAxes)
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)


def _draw_bar_chart(ax, data, title="", max_items=10):
    """Desenha gráfico de barras horizontal."""
    if not data:
        ax.text(0.5, 0.5, "Sem dados", ha='center', va='center', color=COLORS['gray'])
        ax.set_title(title, fontsize=11, fontweight='bold', color=COLORS['dark'])
        ax.axis('off')
        return
    
    items = list(data.items())[:max_items]
    labels = [item[0] for item in items][::-1]
    values = [item[1] for item in items][::-1]
    
    y_pos = np.arange(len(labels))
    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))][::-1]
    
    bars = ax.barh(y_pos, values, color=colors, edgecolor='white', height=0.6)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title(title, fontsize=11, fontweight='bold', color=COLORS['dark'], pad=10)
    
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.2, bar.get_y() + bar.get_height()/2,
                f'{int(width)}', va='center', fontsize=9, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(0, max(values) * 1.2 if values else 1)


def _draw_horizontal_bar(ax, data, title="", color=COLORS['blue']):
    """Desenha barras horizontais simples."""
    if not data:
        ax.text(0.5, 0.5, "Sem dados", ha='center', va='center', color=COLORS['gray'])
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.axis('off')
        return
    
    labels = list(data.keys())[::-1]
    values = list(data.values())[::-1]
    
    y_pos = np.arange(len(labels))
    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))][::-1]
    
    bars = ax.barh(y_pos, values, color=colors, height=0.5)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title(title, fontsize=11, fontweight='bold', color=COLORS['dark'])
    
    total = sum(values)
    for bar, val in zip(bars, values):
        pct = round((val / total) * 100) if total > 0 else 0
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height()/2,
                f'{val} ({pct}%)', va='center', fontsize=9)
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(0, max(values) * 1.35 if values else 1)


def _draw_horizontal_bar_with_values(ax, data, title="", color=COLORS['blue'], suffix=""):
    """Desenha barras horizontais com valores numéricos."""
    if not data:
        ax.axis('off')
        return
    
    labels = list(data.keys())
    values = list(data.values())
    
    y_pos = np.arange(len(labels))
    colors = [CHART_PALETTE[i % len(CHART_PALETTE)] for i in range(len(labels))]
    
    bars = ax.barh(y_pos, values, color=colors, height=0.5)
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title(title, fontsize=10, fontweight='bold', color=COLORS['dark'])
    
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{val}{suffix}', va='center', fontsize=9, fontweight='bold')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(0, max(values) * 1.3 if values else 1)


def _draw_pie_chart(ax, data, title=""):
    """Desenha gráfico de pizza."""
    if not data:
        ax.text(0.5, 0.5, "Sem dados", ha='center', va='center', color=COLORS['gray'])
        ax.set_title(title, fontsize=11, fontweight='bold')
        ax.axis('off')
        return
    
    labels = list(data.keys())
    values = list(data.values())
    colors = CHART_PALETTE[:len(labels)]
    
    labels_short = [l[:10] + '..' if len(str(l)) > 10 else l for l in labels]
    
    wedges, texts, autotexts = ax.pie(
        values, labels=labels_short, autopct='%1.0f%%',
        colors=colors, startangle=90,
        textprops={'fontsize': 8}
    )
    
    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_fontweight('bold')
    
    ax.set_title(title, fontsize=11, fontweight='bold', color=COLORS['dark'], pad=5)
