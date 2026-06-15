import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage
import json
import os
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO E ENGINE VISUAL ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

# --- INICIALIZAÇÃO DE MEMÓRIA ---
if 'pagina_ativa' not in st.session_state: st.session_state.pagina_ativa = "🛠️ Visão Geral"
if 'config_emails' not in st.session_state: st.session_state.config_emails = "luizclaudio@tempermar.com.br"
if 'selecionados' not in st.session_state: st.session_state.selecionados = []

st.markdown("""
    <style>
    .stApp { background-color: #0a192f; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }
    
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #112240; border: 1px solid #233554; padding: 12px 20px;
        border-radius: 8px; font-weight: bold; transition: 0.3s;
        justify-content: flex-start; text-align: left; color: #b0b4c4; width: 100%;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover { border-color: #ff9800; color: white; }
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #ff9800 !important; color: white !important; border-color: #ff9800 !important;
        box-shadow: 0 0 15px rgba(255, 152, 0, 0.5) !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background-color: transparent; border: none; padding: 8px 10px 8px 45px;
        margin-bottom: 0px; font-weight: normal; transition: 0.2s; display: flex; align-items: center; 
        justify-content: flex-start; width: 100%; color: #8a91a8; cursor: pointer; border-left: 4px solid transparent;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { color: white; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        color: #ff9800; border-left: 4px solid #ff9800; background-color: rgba(255, 152, 0, 0.05); font-weight: bold;
    }

    .kpi-container { padding: 12px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3); margin-bottom: 10px; border: 1px solid rgba(255,255,255,0.05); }
    .kpi-value { font-size: 28px; font-weight: 800; line-height: 1.1; margin: 5px 0; }
    .kpi-label { font-size: 12px; font-weight: 600; text-transform: uppercase; opacity: 0.8; }
    
    /* GATILHO DE IMPRESSÃO SEGURO */
    .card-instrumento { display: inline-block; width: 100%; background-color: #112240; border-radius: 8px; padding: 10px; margin-bottom: 5px; border-left: 5px solid #ccc; opacity: 0.7; transition: all 0.3s ease; box-sizing: border-box;}
    .vencido-card { border-left-color: #ff4b4b; background: linear-gradient(to right, #2a1616, #112240); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2a2510, #112240); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #102416, #112240); opacity: 1; }
    .card-selecionado { border: 2px solid #ff9800 !important; box-shadow: 0 0 15px rgba(255, 152, 0, 0.6) !important; transform: scale(1.02); opacity: 1 !important; background: linear-gradient(to right, #332100, #112240) !important; }
    .vencido-kpi { color: #ff4b4b; border-bottom: 3px solid #ff4b4b; }
    .proximo-kpi { color: #fcc419; border-bottom: 3px solid #fcc419; }
    .apto-kpi { color: #2ecc71; border-bottom: 3px solid #2ecc71; }
    </style>
""", unsafe_allow_html=True)

def salvar_config(emails):
    with open("config.json", "w") as f: json.dump({"emails": emails}, f)

# --- CARREGAMENTO RÁPIDO VIA PLANILHA ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try: 
        return pd.read_csv(SHEET_URL)
    except: 
        return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
    
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), "Características")
    
    if col_caract not in df.columns:
        df[col_caract] = "N/I"
        
    def extrair_vencimento(texto):
        if pd.isna(texto) or str(texto).strip().upper() in ["NAN", "N/I", ""]: 
            return None, "SEM DATA"
            
        t_ajustado = str(texto).lower()
        t_ajustado = re.sub(r'[áàâãä]', 'a', t_ajustado)
        t_ajustado = re.sub(r'[éèêë]', 'e', t_ajustado)
        t_ajustado = re.sub(r'[íìîï]', 'i', t_ajustado)
        t_ajustado = re.sub(r'[óòôõö]', 'o', t_ajustado)
        t_ajustado = re.sub(r'[úùûü]', 'u', t_ajustado)
        t_ajustado = re.sub(r'[ç]', 'c', t_ajustado)
        
        t_ajustado = t_ajustado.replace("：", ":").replace(" ;", ":").replace(";", ":")
        t
