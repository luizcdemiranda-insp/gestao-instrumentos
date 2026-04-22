import streamlit as st
import pandas as pd
import re
from datetime import datetime

# --- CONFIGURAÇÃO VISUAL (FLEXBOX ENGINE) ---
st.set_page_config(page_title="🛡️ Gestão de Instrumentos", layout="wide")

st.markdown("""
    <style>
    .card { background-color:#1E2130; padding:20px; border-radius:12px; border-top:5px solid #4a4f63; margin-bottom:15px; transition: 0.3s; }
    .card:hover { transform: scale(1.01); box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .stApp { background-color: #0E1117; }
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DE PROCESSAMENTO ---
@st.cache_data
def carregar_dados():
    # Carrega seu CSV (ajuste o nome se necessário)
    df = pd.read_csv("compras,_estoque_e_producao_274482357544975.csv", sep=';')
    
    # Extração robusta de data
    def extrair_data(texto):
        if pd.isna(texto): return None
        # Procura datas no formato dd/mm/aaaa
        match = re.search(r'\d{2}/\d{2}/\d{4}', str(texto))
        return pd.to_datetime(match.group(0), dayfirst=True) if match else None

    df['DATA_CALIBRACAO'] = df['Características'].apply(extrair_data)
    
    # Lógica de status (Assumindo hoje como referência)
    hoje = datetime.now()
    df['DIAS_RESTANTES'] = (df['DATA_CALIBRACAO'] - hoje).dt.days
    
    def rotular_status(dias):
        if pd.isna(dias): return "SEM DATA"
        if dias < 0: return "VENCIDO"
        if dias <= 30: return "PRÓXIMO VENCIMENTO"
        return "NO PRAZO"
    
    df['STATUS'] = df['DIAS_RESTANTES'].apply(rotular_status)
    return df

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ CONTROLE DE INSTRUMENTOS")
df = carregar_dados()

# Filtros (Sidebar)
st.sidebar.header("🔍 FILTROS")
status_filter = st.sidebar.multiselect("Status do Instrumento:", df['STATUS'].unique(), default=df['STATUS'].unique())
df_filtrado = df[df['STATUS'].isin(status_filter)]

# KPIs (Dashboard)
col1, col2, col3 = st.columns(3)
col1.metric("Total de Itens", len(df_filtrado))
col2.metric("⚠️ Vencidos", len(df_filtrado[df_filtrado['STATUS'] == 'VENCIDO']))
col3.metric("⏳ Próximos", len(df_filtrado[df_filtrado['STATUS'] == 'PRÓXIMO VENCIMENTO']))

# Exibição dos cards
for _, row in df_filtrado.iterrows():
    cor = "#ff4b4b" if row['STATUS'] == "VENCIDO" else ("#F1C40F" if row['STATUS'] == "PRÓXIMO VENCIMENTO" else "#2ecc71")
    
    with st.container():
        st.markdown(f"""
        <div class='card' style='border-top: 5px solid {cor};'>
            <h3 style='margin:0;'>{row['Descrição']}</h3>
            <p style='color:#b0b4c4;'>Código: {row['Código']} | Data: {str(row['DATA_CALIBRACAO'])[:10]}</p>
            <div style='background-color:{cor}; color:white; padding:5px 10px; border-radius:5px; display:inline-block; font-weight:bold;'>
                {row['STATUS']}
            </div>
        </div>
        """, unsafe_allow_html=True)
