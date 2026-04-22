import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E MOTOR VISUAL ---
st.set_page_config(page_title="🛠️ Monitoramento", layout="wide")

st.markdown("""
    <style>
    /* 1. PALETA BASE (Azul Marinho Profundo) */
    .stApp { background-color: #0b132b; color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #1c2541; }
    
    /* 2. MENU ESTILO MERCÚRIO (Botões Blindados) */
    div[role="radiogroup"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label {
        background-color: #2b3a55; border: 1px solid #3a506b; padding: 12px 15px;
        border-radius: 8px; margin-bottom: 8px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: flex-start; cursor: pointer;
        width: 100%; color: #ffffff;
    }
    div[role="radiogroup"] > label:hover { border-color: #ff8c00; }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #ff8c00; color: #ffffff; border-color: #ff8c00;
        box-shadow: 0 0 12px rgba(255, 140, 0, 0.4);
    }
    
    /* 3. CARDS COMPACTOS */
    .card-compact { 
        padding: 15px; border-radius: 8px; margin: 8px; 
        border-left: 6px solid #ccc; font-size: 0.95em;
        background-color: #1c2541; color: #e0e6ed;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.5);
        height: 125px; transition: transform 0.2s;
    }
    .card-compact:hover { transform: scale(1.02); }
    
    /* Cores de Status (Vermelho voltou para os Vencidos) */
    .vencido { border-color: #ff4b4b; } /* Vermelho alerta */
    .proximo { border-color: #f1c40f; } /* Amarelo atenção */
    .em-dia { border-color: #2ecc71; }  /* Verde apto */
    
    /* Ajustes Gerais */
    [data-testid="stMetricValue"] { font-size: 28px; color: #ffffff; }
    [data-testid="stMetricLabel"] { color: #a1b0c0; }
    h1, h2, h3 { color: #ffffff; }
    hr { border-color: #3a506b; }
    </style>
""", unsafe_allow_html=True)

# URL da Planilha
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    return pd.read_csv(SHEET_URL)

def processar_dados(df):
    def extrair_data(texto):
        if pd.isna(texto): return None
        match = re.search(r'\d{2}/\d{2}/\d{4}', str(texto))
        return pd.to_datetime(match.group(0), dayfirst=True) if match else None

    df['DATA_CALIBRACAO'] = df['Características'].apply(extrair_data)
    hoje = datetime.now()
    df['DIAS_RESTANTES'] = (df['DATA_CALIBRACAO'] - hoje).dt.days
    
    def rotular_status(dias):
        if pd.isna(dias): return "SEM DATA"
        if dias < 0: return "VENCIDO"
        if dias <= 30: return "PRÓXIMO VENCIMENTO"
        return "NO PRAZO"
    
    df['STATUS'] = df['DIAS_RESTANTES'].apply(rotular_status)
    # Coluna auxiliar de data formatada em texto para facilitar o filtro
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna("N/A")
    return df

def enviar_email_lote(destino, lista_instrumentos):
    msg = EmailMessage()
    msg['Subject'] = "🚨 ALERTA: Monitoramento de Instrumentos"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destino
    
    conteudo = "Relatório de Instrumentos com Pendência de Calibração:\n\n"
    for item in lista_instrumentos:
