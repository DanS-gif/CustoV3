"""
OrçaObra - Sistema Inteligente e Paramétrico para Cálculo e Orçamento de Obras
===============================================================================
MVP v3.0  |  Stack: Streamlit · Pandas · st-aggrid · Matplotlib · fpdf2 · JSON

Arquitetura em blocos lógicos:
  [A] Imports, Configuração de Página e Guarda de Dependências
  [B] CSS - Premium Tech Dark Mode (Vercel/Linear aesthetic)
  [C] Constantes e Dados-Padrão
  [D] Gestão do sugestoes_mercado.json
  [E] Inicialização do Session State
  [F] Algoritmo Heurístico de Layout de Planta (Matplotlib + ABNT Orange)
  [G] Gráfico de Custo por Insumo (Matplotlib)
  [H] Geração de Proposta em PDF (fpdf2)
  [I] Helpers: AgGrid Dark, Cálculo de Custo, CSV
  [J] Sidebar Global
  [K] Abas da Interface (Gerenciador · Preços · Resultados · PDF)
  [L] Ponto de Entrada (main)
"""

# ═══════════════════════════════════════════════════════════════════════════
# [A] IMPORTS, CONFIGURAÇÃO DE PÁGINA E GUARDA DE DEPENDÊNCIAS
# ═══════════════════════════════════════════════════════════════════════════

import io
import json
import math
import os
from typing import Optional

import streamlit as st

st.set_page_config(
    page_title="OrçaObra · Orçamento Paramétrico",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Guarda de dependências - exibe erro amigável antes de crashar ──────────
_PACOTES_NECESSARIOS: dict[str, str] = {
    "matplotlib": "matplotlib>=3.8.0",
    "numpy":      "numpy>=1.26.0",
    "pandas":     "pandas>=2.0.0",
    "fpdf":       "fpdf2>=2.7.9",
    "st_aggrid":  "streamlit-aggrid>=0.3.4",
}

_faltando: list[str] = []
for _mod, _pkg in _PACOTES_NECESSARIOS.items():
    try:
        __import__(_mod)
    except ModuleNotFoundError:
        _faltando.append(_pkg)

if _faltando:
    st.error(
        "### 📦 Dependências não instaladas\n\n"
        + "\n".join(f"- `{p}`" for p in _faltando)
        + "\n\n**Corrija com:**\n```bash\npip install -r requirements.txt\n```\n\n"
        "> ☁️ **Streamlit Cloud:** certifique-se de que `requirements.txt` "
        "está na **raiz do repositório** antes do deploy."
    )
    st.stop()

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt        # noqa: E402
import matplotlib.ticker as ticker     # noqa: E402
import numpy as np                     # noqa: E402
import pandas as pd                    # noqa: E402
from fpdf import FPDF                  # noqa: E402
from st_aggrid import (                # noqa: E402
    AgGrid,
    DataReturnMode,
    GridOptionsBuilder,
    GridUpdateMode,
)

# ═══════════════════════════════════════════════════════════════════════════
# [B] CSS - PREMIUM TECH DARK MODE
# ═══════════════════════════════════════════════════════════════════════════

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* ── Background global com grid milimetrado ─────────────────────────────── */
.stApp {
    background-color: #0a0a0a;
    background-image:
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    color: #a3a3a3;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #111111 !important;
    border-right: 1px solid #1f1f1f !important;
}
[data-testid="stSidebar"] .block-container { padding: 1.5rem 1rem; }
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p {
    color: #737373 !important;
    font-size: 0.82rem !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #fafafa !important; }

/* ── Header com Glow laranja ─────────────────────────────────────────────── */
.oc-header {
    background:
        radial-gradient(circle at 50% 0%, rgba(249,115,22,0.15) 0%, transparent 60%),
        #111111;
    border: 1px solid #262626;
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.oc-header::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
        linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
}
.oc-header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: #fafafa;
    letter-spacing: -0.5px;
    margin: 0;
    position: relative;
}
.oc-header h1 .accent { color: #f97316; }
.oc-header p {
    color: #525252;
    margin: 6px 0 0;
    font-size: 0.88rem;
    letter-spacing: 0.2px;
    position: relative;
}

/* ── Metric cards ────────────────────────────────────────────────────────── */
.oc-card {
    background: #171717;
    border: 1px solid #262626;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 6px 0;
    transition: border-color 0.2s ease;
}
.oc-card:hover { border-color: #404040; }
.oc-card .lbl {
    font-size: 0.72rem;
    color: #525252;
    text-transform: uppercase;
    letter-spacing: 1.6px;
    font-weight: 500;
}
.oc-card .val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.85rem;
    font-weight: 700;
    color: #fafafa;
    line-height: 1.2;
    margin-top: 4px;
}
.oc-card .sub {
    font-size: 0.76rem;
    color: #f97316;
    margin-top: 4px;
    font-weight: 500;
}

/* ── Suggestion cards ────────────────────────────────────────────────────── */
.sug-card {
    background: #171717;
    border: 1px solid #262626;
    border-radius: 12px;
    padding: 20px;
    height: 100%;
    transition: border-color 0.2s ease, transform 0.2s ease;
}
.sug-card:hover { border-color: #f97316; transform: translateY(-2px); }
.sug-card h4 {
    font-family: 'Space Grotesk', sans-serif;
    color: #fafafa;
    margin: 0 0 8px;
    font-size: 0.95rem;
    font-weight: 600;
}
.sug-card .badge {
    display: inline-block;
    background: rgba(249,115,22,0.1);
    border: 1px solid rgba(249,115,22,0.25);
    color: #f97316;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.70rem;
    font-weight: 500;
    margin: 3px 2px 0;
}
.sug-card p { color: #737373; font-size: 0.83rem; line-height: 1.6; margin: 8px 0 6px; }

/* ── Abas ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid #262626;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #525252;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 12px 20px;
    font-family: 'Inter', sans-serif;
    font-size: 0.84rem;
    font-weight: 500;
    transition: color 0.15s ease;
}
.stTabs [data-baseweb="tab"]:hover { color: #a3a3a3; }
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: #fafafa !important;
    border-bottom: 2px solid #f97316 !important;
}

/* ── Inputs e Selects ────────────────────────────────────────────────────── */
.stNumberInput input,
.stTextInput input,
.stSelectbox select,
.stTextArea textarea {
    background: #171717 !important;
    border: 1px solid #262626 !important;
    color: #fafafa !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    transition: border-color 0.15s ease !important;
}
.stNumberInput input:focus,
.stTextInput input:focus,
.stTextArea textarea:focus {
    border-color: #f97316 !important;
    box-shadow: 0 0 0 3px rgba(249,115,22,0.12) !important;
    outline: none !important;
}
/* Dropdown de selectbox */
[data-baseweb="select"] > div {
    background: #171717 !important;
    border-color: #262626 !important;
    color: #fafafa !important;
}
[data-baseweb="popover"] { background: #171717 !important; border: 1px solid #262626 !important; }
[data-baseweb="option"]  { background: #171717 !important; color: #a3a3a3 !important; }
[data-baseweb="option"]:hover { background: #262626 !important; color: #fafafa !important; }

/* ── Botões ──────────────────────────────────────────────────────────────── */
.stDownloadButton button,
.stButton button {
    background: #f97316 !important;
    color: #0a0a0a !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.45rem 1.2rem !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton button:hover,
.stButton button:hover {
    background: #ea6c0a !important;
    box-shadow: 0 0 20px rgba(249,115,22,0.35) !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton button:active,
.stButton button:active {
    transform: translateY(0) !important;
    box-shadow: 0 0 10px rgba(249,115,22,0.2) !important;
}
/* Botão de exclusão - variante vermelha sutil */
button[kind="secondary"] {
    background: #1f0a0a !important;
    color: #f87171 !important;
    border: 1px solid #3f1010 !important;
    box-shadow: none !important;
}
button[kind="secondary"]:hover {
    background: #3f1010 !important;
    box-shadow: 0 0 12px rgba(248,113,113,0.2) !important;
}

/* ── Formulários st.form ─────────────────────────────────────────────────── */
[data-testid="stForm"] {
    background: #111111 !important;
    border: 1px solid #262626 !important;
    border-radius: 12px !important;
    padding: 20px !important;
}
[data-testid="stFormSubmitButton"] button {
    width: 100% !important;
    margin-top: 8px !important;
}

/* ── Expander ────────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #171717 !important;
    border: 1px solid #262626 !important;
    border-radius: 8px !important;
    color: #a3a3a3 !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    transition: border-color 0.15s ease !important;
}
.streamlit-expanderHeader:hover { border-color: #f97316 !important; color: #fafafa !important; }

/* ── Slider ──────────────────────────────────────────────────────────────── */
.stSlider [data-baseweb="slider"] div[role="slider"] {
    background: #f97316 !important; border-color: #f97316 !important;
}

/* ── Métricas nativas ────────────────────────────────────────────────────── */
[data-testid="stMetricValue"] {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #fafafa !important; font-weight: 700 !important;
}
[data-testid="stMetricLabel"] { color: #525252 !important; }
[data-testid="stMetricDelta"]  { color: #f97316 !important; }

/* ── st.dataframe e st.data_editor - Dark Theme ──────────────────────────── */
[data-testid="stDataFrame"],
[data-testid="stDataFrameResizable"] {
    background-color: #171717 !important;
    border: 1px solid #262626 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
/* Cabeçalhos das tabelas */
[data-testid="stDataFrame"] th,
[data-testid="stDataFrameResizable"] th {
    background-color: #111111 !important;
    color: #f97316 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.8px !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid #262626 !important;
}
/* Células das tabelas */
[data-testid="stDataFrame"] td,
[data-testid="stDataFrameResizable"] td {
    background-color: #171717 !important;
    color: #a3a3a3 !important;
    border-bottom: 1px solid #1f1f1f !important;
    font-size: 0.85rem !important;
}
[data-testid="stDataFrame"] tr:hover td,
[data-testid="stDataFrameResizable"] tr:hover td {
    background-color: #1f1f1f !important;
    color: #fafafa !important;
}
/* Data editor */
[data-testid="stDataEditor"] {
    background: #171717 !important;
    border: 1px solid #262626 !important;
    border-radius: 10px !important;
}
[data-testid="stDataEditor"] th {
    background: #111111 !important;
    color: #f97316 !important;
    font-size: 0.76rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}
[data-testid="stDataEditor"] td {
    background: #171717 !important;
    color: #a3a3a3 !important;
}

/* ── Alerts ──────────────────────────────────────────────────────────────── */
.stAlert {
    background: #111111 !important;
    border: 1px solid #262626 !important;
    border-radius: 10px !important;
}

/* ── Divider ─────────────────────────────────────────────────────────────── */
hr { border-color: #1f1f1f !important; margin: 28px 0 !important; }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: #0a0a0a; }
::-webkit-scrollbar-thumb { background: #262626; border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #f97316; }

/* ── Spinner ─────────────────────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #f97316 !important; }

/* ── Código / JSON ───────────────────────────────────────────────────────── */
.stCodeBlock, pre {
    background: #111111 !important;
    border: 1px solid #262626 !important;
    border-radius: 8px !important;
}

/* ── AgGrid dark override ────────────────────────────────────────────────── */
.ag-theme-alpine-dark,
.ag-theme-balham-dark {
    --ag-background-color: #171717 !important;
    --ag-header-background-color: #111111 !important;
    --ag-odd-row-background-color: #171717 !important;
    --ag-row-hover-color: #1f1f1f !important;
    --ag-selected-row-background-color: #1f2a1a !important;
    --ag-foreground-color: #a3a3a3 !important;
    --ag-header-foreground-color: #f97316 !important;
    --ag-border-color: #262626 !important;
    --ag-cell-horizontal-border: 1px solid #1f1f1f !important;
    --ag-font-family: 'Inter', sans-serif !important;
    --ag-font-size: 13px !important;
    --ag-grid-size: 5px !important;
    --ag-input-background-color: #0a0a0a !important;
    --ag-input-border-color: #262626 !important;
    --ag-input-focus-border-color: #f97316 !important;
    border: 1px solid #262626 !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}
.ag-theme-alpine-dark .ag-header-cell-label,
.ag-theme-balham-dark .ag-header-cell-label {
    font-size: 0.74rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.6px !important;
    text-transform: uppercase !important;
}
.ag-theme-alpine-dark .ag-cell-editor input,
.ag-theme-balham-dark .ag-cell-editor input {
    background: #0a0a0a !important;
    color: #fafafa !important;
    border: 1px solid #f97316 !important;
}
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════
# [C] CONSTANTES E DADOS-PADRÃO
# ═══════════════════════════════════════════════════════════════════════════

JSON_PATH: str = "sugestoes_mercado.json"

TIPOS_APLICACAO: list[str] = ["Piso/Fundação", "Alvenaria/Reboco", "Ambos"]

COLUNAS_INSUMOS: list[str] = [
    "Insumo",
    "Unidade",
    "Custo Unitário (R$)",
    "Tipo de Aplicação",
    "Índice Técnico / m²",
]

# Projeto-exemplo para cold start
COMODOS_PADRAO: list[dict] = [
    {"Nome": "Sala",             "Largura (m)": 4.0, "Comprimento (m)": 4.0},
    {"Nome": "Quarto Principal", "Largura (m)": 3.0, "Comprimento (m)": 3.0},
    {"Nome": "Cozinha",          "Largura (m)": 3.0, "Comprimento (m)": 2.5},
    {"Nome": "Banheiro",         "Largura (m)": 2.0, "Comprimento (m)": 1.5},
]

# Tabela de insumos-base (Simplificada - 5 itens estruturais essenciais)
INSUMOS_PADRAO: list[dict] = [
    {"Insumo": "Mão de Obra Geral",  "Unidade": "hora",    "Custo Unitário (R$)": 65.00,  "Tipo de Aplicação": "Ambos",            "Índice Técnico / m²": 8.0},
    {"Insumo": "Cimento CP II",      "Unidade": "kg",      "Custo Unitário (R$)": 0.85,   "Tipo de Aplicação": "Ambos",            "Índice Técnico / m²": 12.0},
    {"Insumo": "Areia Média Lavada", "Unidade": "m³",      "Custo Unitário (R$)": 110.00, "Tipo de Aplicação": "Ambos",            "Índice Técnico / m²": 0.04},
    {"Insumo": "Brita 1",            "Unidade": "m³",      "Custo Unitário (R$)": 130.00, "Tipo de Aplicação": "Piso/Fundação",    "Índice Técnico / m²": 0.03},
    {"Insumo": "Blocos Cerâmicos",   "Unidade": "unidade", "Custo Unitário (R$)": 1.40,   "Tipo de Aplicação": "Alvenaria/Reboco", "Índice Técnico / m²": 18.0},
]

SUGESTOES_PADRAO: dict = {
    "versao": "1.0",
    "descricao": "Sugestões de materiais sustentáveis e tendências de mercado para Métrica.",
    "sugestoes": [
        {
            "categoria": "Sustentabilidade",
            "icone": "🌿",
            "titulo": "Bloco de Concreto com Agregado Reciclado",
            "descricao": "Fabricado com RCD, reduz extração de argila e diminui custo em até 12%.",
            "economia_estimada": "10–15%",
            "tags": ["reciclado", "estrutural", "ABNT NBR 15270"],
        },
        {
            "categoria": "Eficiência Energética",
            "icone": "⚡",
            "titulo": "Argamassa Térmica com Perlita",
            "descricao": "Isolamento térmico superior ao reboco comum, reduz climatização em até 20%.",
            "economia_estimada": "15–20% (energia)",
            "tags": ["isolante", "leve", "conforto térmico"],
        },
        {
            "categoria": "Custo-Benefício",
            "icone": "💡",
            "titulo": "Steel Frame para Vedação",
            "descricao": "Reduz peso, tempo de obra e desperdício de argamassa em até 30%.",
            "economia_estimada": "20–30% (tempo + mão de obra)",
            "tags": ["seco", "rápido", "leve"],
        },
        {
            "categoria": "Revestimentos",
            "icone": "🔲",
            "titulo": "Porcelanato Técnico Retificado 120×60",
            "descricao": "Formato grande reduz rejuntes e facilita limpeza. Indicado para alto padrão.",
            "economia_estimada": "-",
            "tags": ["premium", "durável", "baixa manutenção"],
        },
        {
            "categoria": "Impermeabilização",
            "icone": "💧",
            "titulo": "Manta EPDM Autoadesiva",
            "descricao": "Vida útil +25 anos, instalação simplificada sem maçarico.",
            "economia_estimada": "8–12% (mão de obra)",
            "tags": ["durável", "fácil aplicação", "sustentável"],
        },
        {
            "categoria": "Tendência 2025",
            "icone": "🏡",
            "titulo": "Microcimento sobre Base Existente",
            "descricao": "Elimina demolição de revestimentos antigos. Reduz entulho e cria estética contemporânea.",
            "economia_estimada": "Reduz demolição em 100%",
            "tags": ["contemporâneo", "sem demolição", "multissuperfície"],
        },
    ],
}

# Paleta de cômodos - tons grafite para contrastar com borda laranja
CORES_COMODOS: list[str] = [
    "#171717", "#141414", "#111111",
    "#161616", "#131313", "#181818",
    "#121212", "#151515", "#101010",
]

# ═══════════════════════════════════════════════════════════════════════════
# [D] GESTÃO DO sugestoes_mercado.json
# ═══════════════════════════════════════════════════════════════════════════


def garantir_json_sugestoes() -> dict:
    """
    Garante existência do arquivo JSON de sugestões.
    Cria-o com conteúdo padrão se não existir.
    """
    if not os.path.exists(JSON_PATH):
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(SUGESTOES_PADRAO, f, ensure_ascii=False, indent=2)
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return SUGESTOES_PADRAO


def salvar_json_sugestoes(dados: dict) -> bool:
    """Persiste o dicionário de sugestões no arquivo JSON."""
    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# [E] INICIALIZAÇÃO DO SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════


def inicializar_estado() -> None:
    """
    Inicializa todas as variáveis persistentes do session_state.
    Cold start com projeto-exemplo pré-carregado (UX inclusiva).
    """
    defaults: dict = {
        "comodos":        pd.DataFrame(COMODOS_PADRAO),
        "df_insumos":     pd.DataFrame(INSUMOS_PADRAO),
        "pe_direito":     2.80,
        "desperdicio_pct": 10,
        "nome_projeto":   "Projeto Residencial - Exemplo",
    }
    for chave, valor in defaults.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


# ═══════════════════════════════════════════════════════════════════════════
# [F] ALGORITMO HEURÍSTICO DE LAYOUT + PLANTA ABNT (MATPLOTLIB - ORANGE)
# ═══════════════════════════════════════════════════════════════════════════


def _calcular_posicoes(comodos: list[dict], gap: float = 1.6) -> list[dict]:
    """
    Dispõe cômodos em grid adjacente.
    Gap aumentado para 1.6 para garantir espaço seguro para as cotas ABNT.
    """
    n = len(comodos)
    if n == 0:
        return []

    n_cols = max(1, math.ceil(math.sqrt(n)))
    n_rows = math.ceil(n / n_cols)

    col_widths:  list[float] = [0.0] * n_cols
    row_heights: list[float] = [0.0] * n_rows

    for idx, c in enumerate(comodos):
        col = idx % n_cols
        row = idx // n_cols
        col_widths[col]  = max(col_widths[col],  float(c.get("Largura (m)", 1.0)))
        row_heights[row] = max(row_heights[row], float(c.get("Comprimento (m)", 1.0)))

    x_starts: list[float] = []
    acc = 0.0
    for w in col_widths:
        x_starts.append(acc)
        acc += w + gap

    y_starts: list[float] = []
    acc = 0.0
    for h in row_heights:
        y_starts.append(acc)
        acc += h + gap

    resultado: list[dict] = []
    for idx, c in enumerate(comodos):
        col = idx % n_cols
        row = idx // n_cols
        resultado.append({**c, "x": x_starts[col], "y": y_starts[row]})

    return resultado


def _desenhar_cota_horizontal(
    ax: plt.Axes,
    x0: float, x1: float, y_cota: float,
    valor: float, fontsize: float,
    cor: str = "#f97316",
) -> None:
    """Cota horizontal ABNT - laranja accent."""
    tick = 0.12
    ax.annotate(
        "", xy=(x1, y_cota), xytext=(x0, y_cota),
        arrowprops=dict(arrowstyle="<->", color=cor, lw=0.9),
        zorder=6,
    )
    for xp in (x0, x1):
        ax.plot([xp - tick/2, xp + tick/2],
                [y_cota - tick/2, y_cota + tick/2],
                color=cor, lw=1.0, zorder=7)
    ax.text(
        (x0 + x1) / 2, y_cota - 0.28,
        f"{valor:.2f} m",
        ha="center", va="top",
        fontsize=fontsize, color="#fdba74",
        fontfamily="monospace", fontweight="bold", zorder=7,
    )


def _desenhar_cota_vertical(
    ax: plt.Axes,
    y0: float, y1: float, x_cota: float,
    valor: float, fontsize: float,
    cor: str = "#f97316",
) -> None:
    """Cota vertical ABNT - laranja accent."""
    tick = 0.12
    ax.annotate(
        "", xy=(x_cota, y1), xytext=(x_cota, y0),
        arrowprops=dict(arrowstyle="<->", color=cor, lw=0.9),
        zorder=6,
    )
    for yp in (y0, y1):
        ax.plot([x_cota - tick/2, x_cota + tick/2],
                [yp - tick/2, yp + tick/2],
                color=cor, lw=1.0, zorder=7)
    ax.text(
        x_cota - 0.28, (y0 + y1) / 2,
        f"{valor:.2f} m",
        ha="right", va="center",
        fontsize=fontsize, color="#fdba74",
        fontfamily="monospace", fontweight="bold",
        rotation=90, zorder=7,
    )


def plotar_planta_esquematica(df_comodos: pd.DataFrame) -> Optional[plt.Figure]:
    """
    Gera a planta baixa esquemática - Premium Tech Dark Mode.

    Estilo: fundo #0a0a0a · grid #1c1c1c · cômodos grafite #171717
            bordas e cotas laranja #f97316 · textos #fdba74
    """
    registros = df_comodos.dropna(
        subset=["Nome", "Largura (m)", "Comprimento (m)"]
    ).to_dict("records")
    registros = [
        r for r in registros
        if float(r.get("Largura (m)", 0)) > 0 and float(r.get("Comprimento (m)", 0)) > 0
    ]
    if not registros:
        return None

    posicoes = _calcular_posicoes(registros)
    max_x = max(p["x"] + float(p["Largura (m)"]) for p in posicoes)
    max_y = max(p["y"] + float(p["Comprimento (m)"]) for p in posicoes)

    margem = 1.8
    fig_w  = min(12, max(7, max_x + 2 * margem + 1))
    fig_h  = min(10, max(6, max_y + 2 * margem + 1))

    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    fig.patch.set_facecolor("#0a0a0a")
    ax.set_facecolor("#0a0a0a")

    # ── Grade técnica escura ───────────────────────────────────────────
    passo = max(0.5, round(max(max_x, max_y) / 20, 1))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(passo / 5))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(passo / 5))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(passo))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(passo))
    ax.grid(which="major", color="#1c1c1c", lw=0.6, ls="-")
    ax.grid(which="minor", color="#141414", lw=0.25, ls="-")
    ax.set_axisbelow(True)

    ax.set_xlim(-margem, max_x + margem)
    ax.set_ylim(-margem, max_y + margem)
    ax.set_aspect("equal")

    # ── Cômodos ───────────────────────────────────────────────────────
    for idx, pos in enumerate(posicoes):
        w, h = float(pos["Largura (m)"]), float(pos["Comprimento (m)"])
        x, y = pos["x"], pos["y"]
        nome     = str(pos.get("Nome", f"Cômodo {idx+1}"))
        min_dim  = min(w, h)
        fs_nome  = max(6.0, min(9.5, min_dim * 3.2))
        fs_dim   = max(5.5, min(8.5,  min_dim * 2.8))

        # Retângulo grafite + borda laranja
        rect = mpatches.FancyBboxPatch(
            (x, y), w, h,
            boxstyle="square,pad=0",
            facecolor="#171717",
            edgecolor="#f97316",
            linewidth=1.8,
            zorder=3,
        )
        ax.add_patch(rect)

        # Hachura interna sutil
        hatch = plt.Polygon(
            [(x,y),(x+w,y),(x+w,y+h),(x,y+h)],
            closed=True, fill=False, hatch="///",
            edgecolor="#262626", lw=0, zorder=2,
        )
        ax.add_patch(hatch)

        # Nome do cômodo
        ax.text(
            x + w/2, y + h/2 + h*0.12, nome,
            ha="center", va="center",
            fontsize=fs_nome, color="#fafafa",
            fontfamily="monospace", fontweight="bold",
            zorder=5, clip_on=True,
        )
        # Dimensões + área (Com Badge SaaS de alto contraste)
        ax.text(
            x + w/2, y + h/2 - h*0.14,
            f"{w:.1f}×{h:.1f} m  |  {w*h:.1f}m²",
            ha="center", va="center",
            fontsize=fs_dim, color="#e5e5e5",
            fontfamily="monospace", fontweight="bold",
            bbox=dict(
                facecolor="#0a0a0a",
                edgecolor="#262626",
                boxstyle="round,pad=0.3",
                alpha=0.85
            ),
            zorder=6, clip_on=True,
        )
        # Cotas ABNT por cômodo
        offset = 0.55
        _desenhar_cota_horizontal(ax, x, x+w, y - offset, w,
                                   fontsize=max(5.5, fs_dim - 1.0))
        _desenhar_cota_vertical(ax,   y, y+h, x - offset, h,
                                 fontsize=max(5.5, fs_dim - 1.0))

    # ── Bounding box total ─────────────────────────────────────────────
    bb = plt.Polygon(
        [(0,0),(max_x,0),(max_x,max_y),(0,max_y)],
        closed=True, fill=False,
        edgecolor="#404040", lw=1.0, ls="--", zorder=1,
    )
    ax.add_patch(bb)
    offset_ext = margem * 0.65
    _desenhar_cota_horizontal(ax, 0, max_x, -offset_ext, max_x, fontsize=8.5)
    _desenhar_cota_vertical(ax,   0, max_y, -offset_ext, max_y, fontsize=8.5)

    ax.set_title(
        "PLANTA BAIXA ESQUEMÁTICA — ORÇAOBRA",
        color="#fafafa", fontfamily="monospace",
        fontsize=11, fontweight="bold", pad=12,
    )
    fig.text(
        0.5, 0.005,
        "OrçaObra  |  Heurístico Grid  |  ABNT NBR 6492  |  Escala: sem escala",
        ha="center", fontsize=7, color="#404040", fontfamily="monospace",
    )
    ax.tick_params(colors="#404040", labelsize=6.5)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1c1c1c")

    plt.tight_layout(pad=1.0)
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# [G] GRÁFICO DE CUSTO POR INSUMO (MATPLOTLIB)
# ═══════════════════════════════════════════════════════════════════════════


def plotar_grafico_custo_por_insumo(df_orcamento: pd.DataFrame) -> Optional[plt.Figure]:
    """
    Gráfico de barras horizontal - custo total por insumo.
    Tema dark com degradê laranja → teal.
    """
    if df_orcamento.empty:
        return None

    df_plot = df_orcamento.sort_values("Custo Total (R$)", ascending=True).tail(12)
    n = len(df_plot)

    # Degradê de cores laranja → amarelo → verde-escuro
    cmap = plt.cm.YlOrBr(np.linspace(0.3, 0.9, n))

    fig, ax = plt.subplots(figsize=(8, max(4, n * 0.58)))
    fig.patch.set_facecolor("#0a0a0a")
    ax.set_facecolor("#0a0a0a")

    barras = ax.barh(
        df_plot["Insumo"], df_plot["Custo Total (R$)"],
        color=cmap, height=0.65,
        edgecolor="#0a0a0a", linewidth=1.2, zorder=3,
    )

    max_val = df_plot["Custo Total (R$)"].max()
    for barra, val in zip(barras, df_plot["Custo Total (R$)"]):
        ax.text(
            val + max_val * 0.01,
            barra.get_y() + barra.get_height() / 2,
            f"R$ {val:,.0f}".replace(",", "."),
            va="center", ha="left",
            fontsize=8, color="#fdba74", fontfamily="monospace",
        )

    ax.set_xlabel("Custo Total Estimado (R$)", color="#525252",
                  fontsize=9, fontfamily="monospace")
    ax.set_title("DISTRIBUIÇÃO DE CUSTOS POR INSUMO",
                 color="#fafafa", fontsize=10,
                 fontfamily="monospace", fontweight="bold", pad=10)
    ax.xaxis.set_major_formatter(
        ticker.FuncFormatter(lambda v, _: f"R$ {v:,.0f}".replace(",", "."))
    )
    ax.tick_params(axis="x", colors="#404040", labelsize=7.5)
    ax.tick_params(axis="y", colors="#a3a3a3", labelsize=8.5)
    ax.grid(axis="x", color="#1c1c1c", lw=0.7, ls="--", zorder=0)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_edgecolor("#1c1c1c")

    plt.tight_layout(pad=0.9)
    return fig


# ═══════════════════════════════════════════════════════════════════════════
# [H] GERAÇÃO DE PROPOSTA EM PDF (fpdf2 - MEMORIAL DESCRITIVO EXECUTIVO)
# ═══════════════════════════════════════════════════════════════════════════

def tx(texto: str) -> str:
    """Transliteração global de caracteres para compatibilidade nativa fpdf2."""
    texto = str(texto)
    mapa = {
        "ã":"a","â":"a","á":"a","à":"a","ä":"a",
        "ê":"e","é":"e","è":"e","ë":"e",
        "í":"i","î":"i","ì":"i",
        "õ":"o","ô":"o","ó":"o","ò":"o","ö":"o",
        "ú":"u","û":"u","ù":"u","ü":"u",
        "ç":"c","ñ":"n",
        "Ã":"A","Â":"A","Á":"A","À":"A",
        "Ê":"E","É":"E","Í":"I","Î":"I",
        "Õ":"O","Ô":"O","Ó":"O","Ú":"U","Û":"U","Ç":"C",
    }
    for orig, sub in mapa.items():
        texto = texto.replace(orig, sub)
    return texto


class OrcaObraRelatorio(FPDF):
    """Classe customizada para injeção de cabeçalhos e rodapés executivos."""
    def __init__(self, nome_projeto: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nome_projeto = nome_projeto

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, tx(f"OrçaObra  |  Relatorio Tecnico Executivo: {self.nome_projeto}"), 
                      border="B", new_x="LMARGIN", new_y="NEXT", align="R")
            self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 150)
        self.set_draw_color(230, 230, 230)
        self.set_line_width(0.2)
        self.line(15, self.get_y(), 195, self.get_y())
        
        self.cell(90, 10, tx("OrçaObra  |  Inteligencia Parametrica"), align="L")
        self.cell(90, 10, tx(f"Pagina {self.page_no()}"), align="R")

def _fig_para_bytes(fig: plt.Figure, dpi: int = 150) -> io.BytesIO:
    """Serializa figura Matplotlib para PNG em memória."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf


def gerar_pdf(
    nome_projeto: str,
    metricas: dict,
    df_orcamento: pd.DataFrame,
    fig_planta: Optional[plt.Figure],
    fig_custos: Optional[plt.Figure],
) -> bytes:
    """Gera uma proposta executiva estruturada com memorial descritivo integrado."""
    pdf = OrcaObraRelatorio(nome_projeto=nome_projeto, orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(left=15, top=15, right=15)

    # ── PÁGINA 1: CAPA, INTRODUÇÃO E MÉTRICAS ─────────────────────────────
    pdf.add_page()

    # Faixa de topo institucional (Premium Minimalist Gray + Orange Dot)
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(0, 0, 210, 45, "F")
    
    pdf.set_xy(15, 14)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(42, 12, tx("OrçaObra"))  # Largura corrigida para acomodar o texto perfeitamente
    pdf.set_text_color(249, 115, 22)
    pdf.cell(0, 12, tx("."), new_x="LMARGIN", new_y="NEXT")

    pdf.set_xy(15, 26)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 6, tx(f"PROPOSTA TECNICA E MEMORIAL DESCRITIVO: {nome_projeto}"), new_x="LMARGIN", new_y="NEXT")

    # Espaçamento pós-cabeçalho
    pdf.set_xy(15, 52)

    # Texto de Introdução / Contexto Descritivo
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, tx("1. RESUMO EXECUTIVO"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    introducao = (
        f"Este documento consolida o planejamento metrico e a estimativa orcamentaria parametrizada "
        f"para o empreendimento denominado '{nome_projeto}'. As analises volumetricas e de consumo "
        f"foram processadas de forma automatizada pelo motor computacional da plataforma Metrica, utilizando "
        f"como base as diretrizes geometricas fornecidas pelo projetista e os indices de rendimento do canteiro."
    )
    pdf.multi_cell(0, 5, tx(introducao), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Bloco de métricas geométricas
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, tx("2. QUADRO DE AREAS E METRICAS GLOBAIS"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    col_w = 87.5
    dados_metricas = [
        ("Area de Piso Total",      f"{metricas.get('area_piso', 0):.2f} m2"),
        ("Perimetro Interno Total", f"{metricas.get('perimetro', 0):.2f} m"),
        ("Pe-direito Cadastrado",   f"{metricas.get('pe_direito', 2.80):.2f} m"),
        ("Area de Parede Total",    f"{metricas.get('area_parede', 0):.2f} m2"),
        ("Margem de Desperdicio",   f"{metricas.get('desperdicio_pct', 10)}%"),
        ("CUSTO TOTAL ESTIMADO",    f"R$ {metricas.get('custo_total', 0):,.2f}".replace(",", ".")),
    ]

    for i, (lbl, val) in enumerate(dados_metricas):
        y_pos = pdf.get_y()
        col   = i % 2
        x_pos = 15 + col * col_w

        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(241, 245, 249)
        pdf.set_xy(x_pos, y_pos)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(col_w - 2, 5, tx(lbl), fill=True, border=1, new_x="RIGHT", new_y="TOP")

        pdf.set_xy(x_pos, y_pos + 5)
        pdf.set_font("Helvetica", "B", 10.5)
        is_custo = "CUSTO" in lbl
        pdf.set_text_color(249, 115, 22) if is_custo else pdf.set_text_color(15, 23, 42)
        pdf.cell(col_w - 2, 7, tx(val), fill=True, border=1, new_x="RIGHT", new_y="TOP")

        if col == 1 or i == len(dados_metricas) - 1:
            pdf.set_xy(15, y_pos + 14)

    pdf.ln(4)

    # ── PÁGINA 2: ANÁLISE ESPACIAL (PLANTA BAIXA) ─────────────────────────
    if fig_planta is not None:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, tx("3. CONFIGURACAO ESPACIAL E ZONEAMENTO"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        texto_planta = (
            "Abaixo, apresenta-se a planta baixa esquematica gerada pelo algoritmo heuristico de "
            "adjacencia em grid. O zoneamento respeita rigorosamente as cotas e dimensoes informadas, "
            "providenciando uma inspecao visual rapida para a analise de perimetros de vedacao e "
            "conforto geometrico dos ambientes segundo as normas de desempenho."
        )
        pdf.multi_cell(0, 5, tx(texto_planta), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        
        try:
            buf = _fig_para_bytes(fig_planta, dpi=130)
            pdf.image(buf, x=15, y=None, w=180)
        except Exception:
            pdf.cell(0, 8, tx("[Imagem da planta indisponivel]"), new_x="LMARGIN", new_y="NEXT")

    # ── PÁGINA 3: ORÇAMENTO E GRÁFICOS ────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, tx("4. PLANEJAMENTO ORCAMENTARIO COMPOSITO"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    texto_orcamento = (
        "As quantidades finais discriminadas abaixo incorporam a margem de seguranca configurada contra "
        "perdas e quebras comuns de canteiro. Os calculos cruzam a area geometrica de referencia (piso ou parede) "
        "com as tabelas de composicao analitica (Indices Tecnicos por metro quadrado)."
    )
    pdf.multi_cell(0, 5, tx(texto_orcamento), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    if not df_orcamento.empty:
        cols_pdf = ["Insumo", "Unid.", "Qtd. c/ Desp.", "Custo Unit.", "Custo Total"]
        larguras = [65, 18, 30, 32, 35]

        # Cabeçalho da tabela limpo (Corporativo)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "B", 8.5)
        for nome_col, larg in zip(cols_pdf, larguras):
            pdf.cell(larg, 8, tx(nome_col), border=1, align="C", fill=True)
        pdf.ln()

        # Linhas
        pdf.set_font("Helvetica", "", 8)
        for i, (_, row) in enumerate(df_orcamento.iterrows()):
            fill_rgb = (255, 255, 255) if i % 2 == 0 else (248, 250, 252)
            pdf.set_fill_color(*fill_rgb)
            pdf.set_text_color(51, 65, 85)

            vals = [
                tx(str(row.get("Insumo", "")))[:38],
                tx(str(row.get("Unidade", "")))[:8],
                f"{row.get('Qtd. c/ Desperdicio', 0):.3f}",
                f"R$ {row.get('Custo Unit. (R$)', 0):.2f}",
                f"R$ {row.get('Custo Total (R$)', 0):,.2f}".replace(",", "."),
            ]
            aligns = ["L", "C", "R", "R", "R"]
            for val, larg, alg in zip(vals, larguras, aligns):
                pdf.cell(larg, 7, val, border=1, align=alg, fill=True)
            pdf.ln()

        # Totalizador
        total = df_orcamento["Custo Total (R$)"].sum()
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.cell(sum(larguras[:-1]), 9, tx("TOTAL CONSOLIDADO  "), border=1, align="R", fill=True)
        pdf.cell(larguras[-1], 9, f"R$ {total:,.2f}".replace(",", "."), border=1, align="R", fill=True)
        pdf.ln(12)

    # ── Gráfico analítico de custos ────────────────────────────────────
    if fig_custos is not None:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, tx("5. ANALISE GRAFICA DE IMPACTO FINANCEIRO"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        try:
            buf = _fig_para_bytes(fig_custos, dpi=110)
            espaco = 297 - 20 - pdf.get_y()
            h_img  = min(100.0, max(50.0, float(espaco) - 5.0))
            pdf.image(buf, x=15, y=None, w=180, h=h_img)
        except Exception:
            pass

    return bytes(pdf.output())


# ═══════════════════════════════════════════════════════════════════════════
# [I] HELPERS: AgGrid DARK, CÁLCULO DE CUSTO, CSV
# ═══════════════════════════════════════════════════════════════════════════


def construir_aggrid(df: pd.DataFrame, altura: int = 360) -> pd.DataFrame:
    """
    Renderiza AgGrid com tema 'alpine-dark' - integrado ao Premium Tech Dark Mode.

    Parâmetros
    ----------
    df : pd.DataFrame
        DataFrame de insumos.
    altura : int
        Altura em pixels do componente.

    Retorna
    -------
    pd.DataFrame
        DataFrame atualizado com edições do usuário.
    """
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        editable=True,
        resizable=True,
        sortable=True,
        filter=True,
        min_width=80,
    )
    gb.configure_column(
        "Insumo", min_width=180, pinned="left",
        headerTooltip="Nome do material ou serviço",
    )
    gb.configure_column(
        "Unidade", width=110,
        headerTooltip="Unidade de medida (kg, m², hora...)",
    )
    gb.configure_column(
        "Custo Unitário (R$)", width=155,
        type=["numericColumn"],
        valueFormatter="'R$ ' + Number(value).toFixed(2)",
        headerTooltip="Custo por unidade sem desperdício",
    )
    gb.configure_column(
        "Tipo de Aplicação", width=170,
        cellEditor="agSelectCellEditor",
        cellEditorParams={"values": TIPOS_APLICACAO},
        headerTooltip="Define a base de cálculo: piso, parede ou ambos",
    )
    gb.configure_column(
        "Índice Técnico / m²", width=165,
        type=["numericColumn"],
        headerTooltip="Quantidade por m² de área de referência (TCPO/SINAPI)",
    )
    gb.configure_grid_options(
        stopEditingWhenCellsLoseFocus=True,
        rowHeight=36,
        headerHeight=42,
    )

    resp = AgGrid(
        df,
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False,
        theme="alpine-dark",
        height=altura,
        allow_unsafe_jscode=True,
        key="aggrid_insumos",
    )

    df_ret = resp.get("data")
    if df_ret is None or (isinstance(df_ret, pd.DataFrame) and df_ret.empty):
        return df
    return pd.DataFrame(df_ret)


def calcular_metricas_geometricas(
    df_comodos: pd.DataFrame,
    pe_direito: float,
) -> dict:
    """Calcula area_piso, perimetro e area_parede a partir dos cômodos."""
    df_v = df_comodos.dropna(subset=["Largura (m)", "Comprimento (m)"]).copy()
    df_v["Largura (m)"]     = pd.to_numeric(df_v["Largura (m)"],     errors="coerce")
    df_v["Comprimento (m)"] = pd.to_numeric(df_v["Comprimento (m)"], errors="coerce")
    df_v = df_v[(df_v["Largura (m)"] > 0) & (df_v["Comprimento (m)"] > 0)]

    area_piso   = float((df_v["Largura (m)"] * df_v["Comprimento (m)"]).sum())
    perimetro   = float((2 * (df_v["Largura (m)"] + df_v["Comprimento (m)"])).sum())
    area_parede = perimetro * pe_direito

    return {
        "area_piso":   area_piso,
        "perimetro":   perimetro,
        "area_parede": area_parede,
        "pe_direito":  pe_direito,
    }


def calcular_orcamento(
    df_insumos: pd.DataFrame,
    metricas: dict,
    desperdicio_pct: int,
) -> pd.DataFrame:
    """
    Cruza índices técnicos com preços e tipo de aplicação.

    Regras volumétricas:
      Piso/Fundação    → base = area_piso
      Alvenaria/Reboco → base = area_parede (perímetro × pé-direito)
      Ambos            → base = area_piso + area_parede
    """
    if df_insumos.empty or metricas["area_piso"] <= 0:
        return pd.DataFrame()

    fator       = 1.0 + desperdicio_pct / 100.0
    area_piso   = metricas["area_piso"]
    area_parede = metricas["area_parede"]
    linhas: list[dict] = []

    for _, row in df_insumos.iterrows():
        tipo = str(row.get("Tipo de Aplicação", "Ambos"))
        if tipo == "Piso/Fundação":
            base = area_piso
        elif tipo == "Alvenaria/Reboco":
            base = area_parede
        else:
            base = area_piso + area_parede

        try:
            indice = float(row.get("Índice Técnico / m²", 0))
            cu     = float(row.get("Custo Unitário (R$)", 0))
        except (ValueError, TypeError):
            continue

        if indice <= 0 or cu <= 0:
            continue

        qtd_teorica = base * indice
        qtd_desp    = qtd_teorica * fator
        custo_total = qtd_desp * cu

        linhas.append({
            "Insumo":              str(row.get("Insumo", "-")),
            "Unidade":             str(row.get("Unidade", "-")),
            "Tipo":                tipo,
            "Base (m²)":          round(base, 2),
            "Qtd. Teórica":       round(qtd_teorica, 3),
            "Qtd. c/ Desperdicio": round(qtd_desp, 3),
            "Custo Unit. (R$)":   round(cu, 2),
            "Custo Total (R$)":   round(custo_total, 2),
        })

    return pd.DataFrame(linhas)


def carregar_csv_insumos(arquivo) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Importa CSV com tratamento de codificação e separador decimal BR."""
    conteudo = arquivo.read()
    df: Optional[pd.DataFrame] = None

    for enc in ("utf-8", "utf-8-sig", "latin1"):
        try:
            df = pd.read_csv(io.BytesIO(conteudo), encoding=enc,
                             sep=None, engine="python")
            break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue

    if df is None:
        return None, "❌ Não foi possível decodificar o arquivo. Use UTF-8 ou latin1."

    faltando = set(COLUNAS_INSUMOS) - set(df.columns)
    if faltando:
        return None, f"❌ Colunas ausentes: {', '.join(faltando)}"

    for col in ("Custo Unitário (R$)", "Índice Técnico / m²"):
        if df[col].dtype == object:
            df[col] = (df[col].astype(str)
                       .str.replace(".", "", regex=False)
                       .str.replace(",", ".", regex=False))
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    return df, None


# ═══════════════════════════════════════════════════════════════════════════
# [J] SIDEBAR GLOBAL
# ═══════════════════════════════════════════════════════════════════════════


def renderizar_sidebar() -> None:
    """
    Sidebar global com:
    - Título 'OrçaObra' com ponto laranja
    - Inputs globais: nome do projeto, pé-direito, desperdício
    - Resumo rápido de métricas
    """
    with st.sidebar:
        # ── BANNER / LOGO ORÇAOBRA NO SIDEBAR ──────────────────────────────────
        st.sidebar.markdown(
        """
        <div style="padding: 10px 0px 20px 0px;">
            <h1 style="font-family: 'Inter', sans-serif; font-size: 2.2rem; font-weight: 800; color: #fafafa; margin: 0; letter-spacing: -1px;">
                OrçaObra<span style="color: #f97316;">.</span>
            </h1>
            <p style="color: #737373; font-size: 0.85rem; margin: 4px 0 0 0; font-family: 'Inter', sans-serif;">
                Painel de Controle Geral
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
        st.divider()

        # ── Inputs globais ──────────────────────────────────────────────
        st.markdown(
            "<p style='font-size:.7rem;color:#525252;text-transform:uppercase;"
            "letter-spacing:1.5px;font-weight:600;margin-bottom:12px;'>"
            "⚙️ Configurações Globais</p>",
            unsafe_allow_html=True,
        )

        nome = st.text_input(
            "Nome do Projeto",
            value=st.session_state["nome_projeto"],
            help="Identificação exibida na proposta PDF e no cabeçalho.",
        )
        st.session_state["nome_projeto"] = nome

        pe = st.number_input(
            "Pé-direito (m)",
            min_value=2.0,
            max_value=6.0,
            value=float(st.session_state["pe_direito"]),
            step=0.05,
            format="%.2f",
            help=(
                "Altura do teto ao piso. Padrão NBR: 2,50 m mínimo residencial. "
                "Afeta diretamente a área de parede para alvenaria e reboco."
            ),
        )
        st.session_state["pe_direito"] = pe

        desp = st.select_slider(
            "Margem de Desperdício",
            options=[5, 10, 15],
            value=st.session_state["desperdicio_pct"],
            format_func=lambda v: f"{v}%",
            help=(
                "Fator adicional sobre as quantidades teóricas. "
                "5% = obras simples · 10% = padrão · 15% = remodelações."
            ),
        )
        st.session_state["desperdicio_pct"] = desp

        st.divider()

        # ── Resumo rápido ───────────────────────────────────────────────
        metricas = calcular_metricas_geometricas(
            st.session_state["comodos"], pe
        )
        n_comodos = len(
            st.session_state["comodos"].dropna(
                subset=["Largura (m)", "Comprimento (m)"]
            )
        )

        st.markdown(
            "<p style='font-size:.7rem;color:#525252;text-transform:uppercase;"
            "letter-spacing:1.5px;font-weight:600;margin-bottom:12px;'>"
            "📐 Resumo do Projeto</p>",
            unsafe_allow_html=True,
        )

        resumo_items = [
            ("Cômodos",      f"{n_comodos}"),
            ("Área Piso",    f"{metricas['area_piso']:.2f} m²"),
            ("Área Parede",  f"{metricas['area_parede']:.2f} m²"),
            ("Perímetro",    f"{metricas['perimetro']:.2f} m"),
        ]
        for lbl, val in resumo_items:
            st.markdown(
                f"""<div style="display:flex;justify-content:space-between;
                    align-items:center;padding:7px 0;
                    border-bottom:1px solid #1f1f1f;">
                    <span style="font-size:.8rem;color:#525252;">{lbl}</span>
                    <span style="font-family:'Space Grotesk',sans-serif;
                        font-size:.88rem;font-weight:600;color:#fafafa;">
                        {val}
                    </span>
                </div>""",
                unsafe_allow_html=True,
            )

        st.divider()
        st.markdown(
            "<p style='font-size:.72rem;color:#404040;text-align:center;"
            "line-height:1.5;'>Índices: SINAPI / TCPO / PINI<br>"
            "Valores são estimativas.</p>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════
# [K] ABAS DA INTERFACE STREAMLIT
# ═══════════════════════════════════════════════════════════════════════════

# ── K.1  Header ────────────────────────────────────────────────────────────


def renderizar_header() -> None:
    """Renderiza o cabeçalho com identidade visual Premium Tech Dark Mode."""
    st.markdown(
        """
        <div class="oc-header">
            <h1>OrçaObra<span>.</span></h1>
            <p>Sistema Inteligente e Paramétrico para Cálculo e Orçamento de Obras · MVP v3.0</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── K.2  Cards de Métricas ─────────────────────────────────────────────────


def renderizar_cards(metricas: dict, custo_total: float) -> None:
    """Exibe os 5 cards de métricas no topo da aba Resultados."""
    desperdicio = st.session_state["desperdicio_pct"]
    area_piso   = metricas["area_piso"]

    c1, c2, c3, c4, c5 = st.columns(5)
    dados = [
        (c1, "📐 Área de Piso",    f"{area_piso:.2f} m²",                  "Soma das áreas dos cômodos"),
        (c2, "📏 Perímetro",       f"{metricas['perimetro']:.2f} m",        "Soma dos perímetros internos"),
        (c3, "🧱 Área de Parede",  f"{metricas['area_parede']:.2f} m²",     f"Pé-direito: {metricas['pe_direito']:.2f} m"),
        (c4, "🔧 Desperdício",     f"{desperdicio}%",                        "Margem sobre qtd. teórica"),
        (c5, "💰 Custo Estimado",  f"R$ {custo_total:,.0f}".replace(",","."), "Total consolidado"),
    ]
    for col, lbl, val, sub in dados:
        with col:
            st.markdown(
                f"""<div class="oc-card">
                    <div class="lbl">{lbl}</div>
                    <div class="val">{val}</div>
                    <div class="sub">{sub}</div>
                </div>""",
                unsafe_allow_html=True,
            )


# ── K.3  Aba 1: Gerenciador de Cômodos ────────────────────────────────────


def aba_gerenciador() -> None:
    """
    Aba 1 - Gerenciador Paramétrico de Cômodos.

    Layout:
      Coluna Esquerda - st.form para adicionar + selectbox para excluir
      Coluna Direita  - Planta baixa gerada em tempo real
    """
    st.markdown("### 📐 Gerenciador de Cômodos")
    st.caption(
        "Use o formulário para adicionar ambientes. "
        "Selecione um cômodo e clique em **Excluir** para removê-lo."
    )

    col_form, col_plot = st.columns([1, 2], gap="large")

    # ── Coluna Esquerda: Formulários ──────────────────────────────────
    with col_form:

        # ── FORM: Adicionar cômodo ─────────────────────────────────────
        with st.form("form_add_comodo", clear_on_submit=True):
            st.markdown(
                "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
                "letter-spacing:1.5px;font-weight:600;margin-bottom:4px;'>"
                "➕ Adicionar Cômodo</p>",
                unsafe_allow_html=True,
            )
            nome_novo = st.text_input(
                "Nome",
                placeholder="Ex: Sala de Estar",
                help="Nome do ambiente. Ex: Sala, Quarto, Banheiro, Garagem.",
            )
            col_l, col_c = st.columns(2)
            with col_l:
                larg_novo = st.number_input(
                    "Largura (m)",
                    min_value=0.5, max_value=99.0,
                    value=3.0, step=0.1, format="%.2f",
                    help="Largura interna em metros. Mínimo: 0,5 m.",
                )
            with col_c:
                comp_novo = st.number_input(
                    "Comprimento (m)",
                    min_value=0.5, max_value=99.0,
                    value=3.0, step=0.1, format="%.2f",
                    help="Comprimento interno em metros. Mínimo: 0,5 m.",
                )
            submitted_add = st.form_submit_button(
                "✅ Adicionar Cômodo",
                use_container_width=True,
            )

        if submitted_add:
            nome_limpo = nome_novo.strip()
            if not nome_limpo:
                st.warning("⚠️ Informe um nome para o cômodo.", icon="⚠️")
            else:
                novo = pd.DataFrame([{
                    "Nome":          nome_limpo,
                    "Largura (m)":   larg_novo,
                    "Comprimento (m)": comp_novo,
                }])
                st.session_state["comodos"] = pd.concat(
                    [st.session_state["comodos"], novo],
                    ignore_index=True,
                )
                st.success(f"✅ **{nome_limpo}** adicionado!", icon="🏠")
                st.rerun()

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        # ── FORM: Excluir cômodo ───────────────────────────────────────
        df_atual = st.session_state["comodos"].dropna(
            subset=["Nome", "Largura (m)", "Comprimento (m)"]
        )
        if not df_atual.empty:
            with st.form("form_del_comodo"):
                st.markdown(
                    "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
                    "letter-spacing:1.5px;font-weight:600;margin-bottom:4px;'>"
                    "🗑️ Excluir Cômodo</p>",
                    unsafe_allow_html=True,
                )
                opcoes = [
                    f"{row['Nome']} ({float(row['Largura (m)']):.1f}×"
                    f"{float(row['Comprimento (m)']):.1f} m)"
                    for _, row in df_atual.iterrows()
                ]
                selecionado = st.selectbox(
                    "Selecione o cômodo",
                    options=opcoes,
                    help="Escolha o cômodo a ser removido do projeto.",
                    label_visibility="collapsed",
                )
                submitted_del = st.form_submit_button(
                    "🗑️ Excluir Selecionado",
                    use_container_width=True,
                )

            if submitted_del and selecionado:
                idx_del = opcoes.index(selecionado)
                idx_real = df_atual.index[idx_del]
                st.session_state["comodos"] = (
                    st.session_state["comodos"]
                    .drop(index=idx_real)
                    .reset_index(drop=True)
                )
                st.success(f"🗑️ Cômodo removido.", icon="✅")
                st.rerun()
        else:
            st.info("ℹ️ Nenhum cômodo cadastrado.", icon="📋")

        st.divider()

     # ── Tabela atual de cômodos ────────────────────────────────────
        st.markdown(
            "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
            "letter-spacing:1.5px;font-weight:600;margin-bottom:8px;'>"
            "📋 Cômodos Cadastrados</p>",
            unsafe_allow_html=True,
        )
        
        # Correção: Apontando para a variável real "comodos" em vez de "df_comodos"
        if not st.session_state["comodos"].empty:
            st.caption("Dica: Clique duas vezes nas células para editar os nomes ou dimensões.")
            
            st.session_state["comodos"] = st.data_editor(
                st.session_state["comodos"],
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                height=min(300, 42 + len(st.session_state["comodos"]) * 36)
            )
        else:
            st.caption("Nenhum cômodo adicionado ainda.")
          
    # ── Coluna Direita: Planta ─────────────────────────────────────────
    with col_plot:
        st.markdown(
            "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
            "letter-spacing:1.5px;font-weight:600;margin-bottom:12px;'>"
            "🏠 Planta Baixa - Layout Heurístico Grid · ABNT NBR 6492</p>",
            unsafe_allow_html=True,
        )
        df_valido = st.session_state["comodos"].dropna(
            subset=["Nome", "Largura (m)", "Comprimento (m)"]
        )
        if df_valido.empty:
            st.info(
                "ℹ️ Adicione ao menos um cômodo para renderizar a planta.",
                icon="📐",
            )
        else:
            with st.spinner("Renderizando planta..."):
                fig = plotar_planta_esquematica(df_valido)
            if fig:
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)


# ── K.4  Aba 2: Tabela de Preços com AgGrid ────────────────────────────────


def aba_precos() -> None:
    """
    Aba 2 - Tabela de Preços Locais.

    Layout:
      Topo: st.form para adicionar insumo + st.form para excluir
      Corpo: AgGrid dark + botões de importação/exportação CSV
    """
    st.markdown("### 💲 Tabela de Preços Locais")
    st.caption(
        "Adicione ou remova insumos pelo formulário. "
        "Edite valores diretamente no grid abaixo."
    )

    col_add, col_del = st.columns([3, 2], gap="large")

    # ── FORM: Adicionar insumo ─────────────────────────────────────────
    with col_add:
        with st.form("form_add_insumo", clear_on_submit=True):
            st.markdown(
                "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
                "letter-spacing:1.5px;font-weight:600;margin-bottom:6px;'>"
                "➕ Adicionar Insumo</p>",
                unsafe_allow_html=True,
            )
            col_n, col_u = st.columns([3, 1])
            with col_n:
                ins_nome = st.text_input(
                    "Nome do Insumo",
                    placeholder="Ex: Porcelanato 60×60",
                    help="Nome do material ou serviço a ser orçado.",
                )
            with col_u:
                ins_unid = st.text_input(
                    "Unidade",
                    value="m²",
                    help="Unidade de medida: m², kg, litro, hora, unidade...",
                )

            col_c, col_t, col_i = st.columns(3)
            with col_c:
                ins_custo = st.number_input(
                    "Custo Unit. (R$)",
                    min_value=0.0, value=50.0, step=1.0, format="%.2f",
                    help="Preço por unidade na sua região (sem desperdício).",
                )
            with col_t:
                ins_tipo = st.selectbox(
                    "Tipo de Aplicação",
                    options=TIPOS_APLICACAO,
                    help="Define se o índice aplica ao piso, parede ou ambos.",
                )
            with col_i:
                ins_indice = st.number_input(
                    "Índice / m²",
                    min_value=0.0, value=1.0, step=0.01, format="%.4f",
                    help="Quantidade teórica por m² de área (ref. SINAPI/TCPO).",
                )

            submitted_ins = st.form_submit_button(
                "✅ Adicionar Insumo",
                use_container_width=True,
            )

        if submitted_ins:
            nome_ins = ins_nome.strip()
            if not nome_ins:
                st.warning("⚠️ Informe o nome do insumo.", icon="⚠️")
            elif ins_custo <= 0 or ins_indice <= 0:
                st.warning("⚠️ Custo e Índice devem ser maiores que zero.", icon="⚠️")
            else:
                novo_ins = pd.DataFrame([{
                    "Insumo":              nome_ins,
                    "Unidade":             ins_unid.strip() or "un",
                    "Custo Unitário (R$)": ins_custo,
                    "Tipo de Aplicação":   ins_tipo,
                    "Índice Técnico / m²": ins_indice,
                }])
                st.session_state["df_insumos"] = pd.concat(
                    [st.session_state["df_insumos"], novo_ins],
                    ignore_index=True,
                )
                st.success(f"✅ **{nome_ins}** adicionado!", icon="📦")
                st.rerun()

    # ── FORM: Excluir insumo ───────────────────────────────────────────
    with col_del:
        df_ins_atual = st.session_state["df_insumos"]
        if not df_ins_atual.empty:
            with st.form("form_del_insumo"):
                st.markdown(
                    "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
                    "letter-spacing:1.5px;font-weight:600;margin-bottom:6px;'>"
                    "🗑️ Excluir Insumo</p>",
                    unsafe_allow_html=True,
                )
                opcoes_ins = df_ins_atual["Insumo"].tolist()
                ins_del = st.selectbox(
                    "Insumo a excluir",
                    options=opcoes_ins,
                    label_visibility="collapsed",
                    help="Selecione o insumo a ser removido da tabela.",
                )
                submitted_del_ins = st.form_submit_button(
                    "🗑️ Excluir Insumo",
                    use_container_width=True,
                )

            if submitted_del_ins and ins_del:
                st.session_state["df_insumos"] = (
                    df_ins_atual[df_ins_atual["Insumo"] != ins_del]
                    .reset_index(drop=True)
                )
                st.success(f"🗑️ **{ins_del}** removido.", icon="✅")
                st.rerun()

    st.divider()

    # ── Importar / Exportar CSV ────────────────────────────────────────
    col_imp, col_tpl, col_exp = st.columns(3)

    with col_tpl:
        tpl = st.session_state["df_insumos"].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button(
            "📥 Template CSV",
            data=tpl,
            file_name="template_insumos.csv",
            mime="text/csv",
            help="Baixe o modelo CSV para preencher com preços locais.",
            use_container_width=True,
        )

    with col_imp:
        arq = st.file_uploader(
            "Importar CSV",
            type=["csv"],
            help="CSV com colunas: Insumo · Unidade · Custo Unitário (R$) · "
                 "Tipo de Aplicação · Índice Técnico / m²",
            label_visibility="collapsed",
        )
        if arq:
            df_imp, erro = carregar_csv_insumos(arq)
            if erro:
                st.error(erro)
            else:
                st.session_state["df_insumos"] = df_imp
                st.success(f"✅ {len(df_imp)} insumos importados.")
                st.rerun()

    with col_exp:
        exp = st.session_state["df_insumos"].to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
        st.download_button(
            "📤 Exportar CSV",
            data=exp,
            file_name="insumos_atualizados.csv",
            mime="text/csv",
            help="Salve a tabela atual com suas edições.",
            use_container_width=True,
        )

    st.markdown(
        "<p style='font-size:.78rem;color:#525252;margin:8px 0 4px;'>"
        "💡 Clique em qualquer célula do grid para editar inline.</p>",
        unsafe_allow_html=True,
    )

    # ── AgGrid dark ───────────────────────────────────────────────────
    df_att = construir_aggrid(st.session_state["df_insumos"])
    if df_att is not None and not df_att.empty:
        for col_num in ["Custo Unitário (R$)", "Índice Técnico / m²"]:
            if col_num in df_att.columns:
                df_att[col_num] = pd.to_numeric(
                    df_att[col_num], errors="coerce"
                ).fillna(0.0)
        st.session_state["df_insumos"] = df_att

    # Totais rápidos
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("Total de Insumos", len(st.session_state["df_insumos"]))
    col_t2.metric(
        "Piso/Fundação",
        len(st.session_state["df_insumos"][
            st.session_state["df_insumos"]["Tipo de Aplicação"] == "Piso/Fundação"
        ]),
    )
    col_t3.metric(
        "Alvenaria/Reboco",
        len(st.session_state["df_insumos"][
            st.session_state["df_insumos"]["Tipo de Aplicação"] == "Alvenaria/Reboco"
        ]),
    )


# ── K.5  Aba 3: Resultados ─────────────────────────────────────────────────


def aba_resultados() -> None:
    """Aba 3 - Dashboard: cards, orçamento detalhado, gráfico e sugestões."""
    st.markdown("### 📊 Resultados e Orçamento")

    metricas = calcular_metricas_geometricas(
        st.session_state["comodos"],
        st.session_state["pe_direito"],
    )

    if metricas["area_piso"] <= 0:
        st.warning(
            "⚠️ Nenhuma área válida. Verifique os cômodos na aba **Gerenciador**.",
            icon="⚠️",
        )
        return

    df_orc = calcular_orcamento(
        st.session_state["df_insumos"],
        metricas,
        st.session_state["desperdicio_pct"],
    )
    custo_total = float(df_orc["Custo Total (R$)"].sum()) if not df_orc.empty else 0.0

    renderizar_cards(metricas, custo_total)
    st.divider()

    col_tab, col_graf = st.columns([3, 2], gap="large")

    with col_tab:
        st.markdown(
            "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
            "letter-spacing:1.5px;font-weight:600;margin-bottom:8px;'>"
            "📋 Orçamento Detalhado</p>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"Desperdício: {st.session_state['desperdicio_pct']}%  ·  "
            f"Área piso: {metricas['area_piso']:.2f} m²  ·  "
            f"Área parede: {metricas['area_parede']:.2f} m²"
        )

        if df_orc.empty:
            st.info(
                "ℹ️ Orçamento vazio. Verifique se há insumos com custo e índice > 0.",
                icon="📦",
            )
        else:
            df_exib = df_orc.copy()
            df_exib["Custo Unit. (R$)"] = df_exib["Custo Unit. (R$)"].apply(
                lambda v: f"R$ {v:,.2f}".replace(",", ".")
            )
            df_exib["Custo Total (R$)"] = df_exib["Custo Total (R$)"].apply(
                lambda v: f"R$ {v:,.2f}".replace(",", ".")
            )
            st.dataframe(
                df_exib,
                use_container_width=True,
                hide_index=True,
                height=400,
            )

            # Card custo total
            custo_m2 = custo_total / metricas["area_piso"] if metricas["area_piso"] > 0 else 0
            st.markdown(
                f"""<div class="oc-card" style="border-left:4px solid #f97316;margin-top:10px">
                    <div class="lbl">💰 Custo Total Consolidado</div>
                    <div class="val">R$ {custo_total:,.2f}</div>
                    <div class="sub">
                        R$ {custo_m2:,.0f}/m² · Ref: SINAPI/PINI
                    </div>
                </div>""".replace(",", "."),
                unsafe_allow_html=True,
            )

            csv_orc = df_orc.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")
            nome_arq = st.session_state["nome_projeto"].replace(" ", "_")[:30]
            st.download_button(
                "📥 Exportar Orçamento CSV",
                data=csv_orc,
                file_name=f"orcamento_{nome_arq}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    with col_graf:
        st.markdown(
            "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
            "letter-spacing:1.5px;font-weight:600;margin-bottom:8px;'>"
            "📊 Distribuição por Insumo</p>",
            unsafe_allow_html=True,
        )
        if not df_orc.empty:
            fig_c = plotar_grafico_custo_por_insumo(df_orc)
            if fig_c:
                st.pyplot(fig_c, use_container_width=True)
                plt.close(fig_c)
        else:
            st.info("O gráfico aparecerá após o cálculo do orçamento.")

    # ── Sugestões do JSON ─────────────────────────────────────────────
    st.divider()
    dados_json = garantir_json_sugestoes()
    sugestoes  = dados_json.get("sugestoes", [])

    if sugestoes:
        st.markdown(
            "<p style='font-size:.72rem;color:#525252;text-transform:uppercase;"
            "letter-spacing:1.5px;font-weight:600;margin-bottom:12px;'>"
            "💡 Sugestões de Mercado e Sustentabilidade</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(min(3, len(sugestoes)))
        for i, sug in enumerate(sugestoes[:6]):
            with cols[i % len(cols)]:
                tags_html = "".join(
                    f'<span class="badge">{t}</span>'
                    for t in sug.get("tags", [])
                )
                st.markdown(
                    f"""<div class="sug-card">
                        <h4>{sug.get('icone','💡')} {sug.get('titulo','-')}</h4>
                        <span style="font-size:.68rem;color:#404040;
                            text-transform:uppercase;letter-spacing:1px;
                            font-weight:600;">
                            {sug.get('categoria','').upper()}
                        </span>
                        <p>{sug.get('descricao','')}</p>
                        <div style="font-size:.74rem;color:#f97316;
                            margin-bottom:6px;font-weight:500;">
                            💰 {sug.get('economia_estimada','-')}
                        </div>
                        {tags_html}
                    </div>""",
                    unsafe_allow_html=True,
                )


# ── K.6  Aba 4: Proposta PDF + Admin JSON ─────────────────────────────────


def aba_proposta_pdf() -> None:
    """Aba 4 - Geração de PDF e Área do Administrador (edição do JSON)."""
    st.markdown("### 📄 Proposta Técnica em PDF")

    metricas = calcular_metricas_geometricas(
        st.session_state["comodos"],
        st.session_state["pe_direito"],
    )

    if metricas["area_piso"] <= 0:
        st.warning(
            "⚠️ Adicione cômodos com dimensões válidas antes de gerar o PDF.",
            icon="⚠️",
        )
    else:
        df_orc = calcular_orcamento(
            st.session_state["df_insumos"],
            metricas,
            st.session_state["desperdicio_pct"],
        )
        custo_total = float(df_orc["Custo Total (R$)"].sum()) if not df_orc.empty else 0.0
        metricas["custo_total"]    = custo_total
        metricas["desperdicio_pct"] = st.session_state["desperdicio_pct"]

        n_com = len(st.session_state["comodos"].dropna(
            subset=["Largura (m)", "Comprimento (m)"]
        ))
        custo_m2 = custo_total / metricas["area_piso"] if metricas["area_piso"] > 0 else 0

        st.markdown(
            f"""<div class="oc-card">
                <div class="lbl">📋 Resumo do Documento</div>
                <div style="margin-top:10px;color:#737373;font-size:.88rem;line-height:1.8;">
                    <b style="color:#f97316;">Projeto:</b>
                    {st.session_state['nome_projeto']}<br>
                    <b style="color:#f97316;">Cômodos:</b>
                    {n_com} ambientes ·
                    <b style="color:#f97316;">Área:</b>
                    {metricas['area_piso']:.2f} m² ·
                    <b style="color:#f97316;">Pé-direito:</b>
                    {metricas['pe_direito']:.2f} m<br>
                    <b style="color:#f97316;">Custo Estimado:</b>
                    R$ {custo_total:,.2f} ·
                    <b style="color:#f97316;">Custo/m²:</b>
                    R$ {custo_m2:,.0f}
                </div>
            </div>""".replace(",", "."),
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

        if st.button("🔄 Gerar Proposta PDF", use_container_width=False):
            with st.spinner("Compilando planta e gerando PDF..."):
                df_valido = st.session_state["comodos"].dropna(
                    subset=["Nome", "Largura (m)", "Comprimento (m)"]
                )
                fig_planta = plotar_planta_esquematica(df_valido) if not df_valido.empty else None
                fig_custos = plotar_grafico_custo_por_insumo(df_orc) if not df_orc.empty else None

                try:
                    pdf_bytes = gerar_pdf(
                        nome_projeto=st.session_state["nome_projeto"],
                        metricas=metricas,
                        df_orcamento=df_orc,
                        fig_planta=fig_planta,
                        fig_custos=fig_custos,
                    )
                    st.success("✅ PDF gerado! Clique abaixo para baixar.")
                    nome_arq = (
                        st.session_state["nome_projeto"]
                        .replace(" ", "_").replace("/", "-")[:40]
                    )
                    st.download_button(
                        "📥 Baixar Proposta PDF",
                        data=pdf_bytes,
                        file_name=f"proposta_{nome_arq}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"❌ Erro ao gerar PDF: {e}")
                finally:
                    if fig_planta:
                        plt.close(fig_planta)
                    if fig_custos:
                        plt.close(fig_custos)

    st.divider()

    # ── Área do Administrador ─────────────────────────────────────────
    with st.expander("🔧 Área do Administrador - Editar sugestoes_mercado.json", expanded=False):
        st.caption(
            "Edite o JSON de sugestões de mercado diretamente. "
            "Alterações são salvas em `sugestoes_mercado.json` e refletidas imediatamente."
        )
        dados_atuais = garantir_json_sugestoes()
        json_texto = st.text_area(
            "Conteúdo JSON",
            value=json.dumps(dados_atuais, ensure_ascii=False, indent=2),
            height=400,
            help="Edite e clique em Salvar. Estrutura: objeto com chave 'sugestoes' (lista).",
        )

        col_s, col_r = st.columns(2)
        with col_s:
            if st.button("💾 Salvar Alterações", use_container_width=True):
                try:
                    dados_novos = json.loads(json_texto)
                    if "sugestoes" not in dados_novos:
                        st.error("❌ JSON inválido: chave 'sugestoes' ausente.")
                    elif not isinstance(dados_novos["sugestoes"], list):
                        st.error("❌ 'sugestoes' deve ser uma lista.")
                    else:
                        ok = salvar_json_sugestoes(dados_novos)
                        if ok:
                            st.success(f"✅ {len(dados_novos['sugestoes'])} sugestões salvas.")
                        else:
                            st.error("❌ Erro ao gravar o arquivo.")
                except json.JSONDecodeError as e:
                    st.error(f"❌ JSON inválido: {e}")

        with col_r:
            if st.button("↩️ Restaurar Padrão", use_container_width=True):
                if salvar_json_sugestoes(SUGESTOES_PADRAO):
                    st.success("✅ JSON restaurado ao padrão.")
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# [L] PONTO DE ENTRADA
# ═══════════════════════════════════════════════════════════════════════════


def main() -> None:
    """
    Ponto de entrada da aplicação Métrica.

    Sequência:
    1. CSS global (Premium Tech Dark Mode)
    2. Cold start do session_state
    3. Garantia do JSON de sugestões
    4. Sidebar global (inputs + resumo)
    5. Header principal
    6. Quatro abas da interface
    7. Rodapé técnico
    """
    st.markdown(CSS, unsafe_allow_html=True)
    inicializar_estado()
    garantir_json_sugestoes()
    renderizar_sidebar()
    renderizar_header()

    aba1, aba2, aba3, aba4 = st.tabs([
        "📐  Cômodos",
        "💲  Preços",
        "📊  Resultados",
        "📄  Proposta PDF",
    ])

    with aba1:
        aba_gerenciador()
    with aba2:
        aba_precos()
    with aba3:
        aba_resultados()
    with aba4:
        aba_proposta_pdf()

    st.markdown("---")
    st.markdown(
        "<p style='text-align:center;color:#2a2a2a;font-size:.72rem;"
        "font-family:\"Space Grotesk\",sans-serif;'>"
        "Métrica. MVP v3.0 · Streamlit · Pandas · st-aggrid · Matplotlib · fpdf2  |  "
        "Ref: SINAPI / TCPO / PINI  |  Valores são estimativas."
        "</p>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
