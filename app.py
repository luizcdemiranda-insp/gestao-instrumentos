import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Configuração da página
st.set_page_config(page_title="🛡️ Gestão de Instrumentos", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÃO DE DADOS ---
@st.cache_data(ttl=600)
def carregar_dados():
    df = conn.read(worksheet="Página1") # Ajuste o nome da aba
    # ... (aqui entraria o tratamento de data conforme fizemos antes)
    return df

# --- NAVEGAÇÃO ---
st.sidebar.title("🎛️ MENU")
page = st.sidebar.radio("Navegar para:", ["Visão Geral", "Vencidos"])

df = carregar_dados()

# --- PÁGINA: VISÃO GERAL ---
if page == "Visão Geral":
    st.title("📋 Visão Geral dos Instrumentos")
    st.dataframe(df, use_container_width=True)

# --- PÁGINA: VENCIDOS ---
elif page == "Vencidos":
    st.title("⚠️ Instrumentos Vencidos")
    df_vencidos = df[df['STATUS'] == 'VENCIDO']
    
    if len(df_vencidos) == 0:
        st.success("Tudo em ordem! Nenhum instrumento vencido.")
    else:
        for _, row in df_vencidos.iterrows():
            st.error(f"**{row['Descrição']}** - Código: {row['Código']} (Venceu em: {row['DATA_CALIBRACAO']})")
