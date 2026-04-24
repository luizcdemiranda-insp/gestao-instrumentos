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

st.markdown("""
    <style>
    .stApp { background-color: #0b1325; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #121e36; border-right: 1px solid #1f3052; }
    div[role="radiogroup"] > label { background-color: #1a2942; border: 1px solid #2a3d66; padding: 10px; border-radius: 8px; margin-bottom: 8px; color: #b0b4c4; }
    div[role="radiogroup"] > label:has(input:checked) { background-color: #ff4b4b; color: white; border-color: #ff4b4b; }
    .kpi-container { padding: 12px; border-radius: 10px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }
    .card-instrumento { background-color: #1a2942; border-radius: 8px; padding: 15px; margin-bottom: 10px; border-left: 5px solid #ccc; transition: all 0.3s; }
    .vencido-card { border-left-color: #ff4b4b; background: linear-gradient(to right, #241010, #1a2942); }
    .card-selecionado { border: 2px solid #ff4b4b !important; box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); transform: scale(1.02); }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE DADOS E LÓGICA ---
def carregar_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f: return json.load(f)
    return {"emails": "luizclaudio@tempermar.com.br"}

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), "Características")
    
    def extrair_vencimento(texto):
        if pd.isna(texto): return None, "SEM DATA DE CALIBRACAO"
        # Regra 1: Próxima Calibração
        match_prox = re.search(r'Data da Próxima Calibração:\s*(\d{2}/\d{2}/\d{4})', str(texto))
        if match_prox: return pd.to_datetime(match_prox.group(1), dayfirst=True), None
        
        # Regra 2: Última Calibração + 1 ano
        match_ultima = re.search(r'Data da Última Calibração:\s*(\d{2}/\d{2}/\d{4})', str(texto))
        if match_ultima:
            data_ultima = pd.to_datetime(match_ultima.group(1), dayfirst=True)
            return data_ultima + relativedelta(years=1), None
        
        return None, "SEM DATA DE CALIBRACAO"

    resultados = df[col_caract].apply(extrair_vencimento)
    df['DATA_CALIBRACAO'] = [x[0] for x in resultados]
    df['ALERTA_DATA'] = [x[1] for x in resultados]
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna(df['ALERTA_DATA'])
    
    hoje = datetime.now()
    def classificar(row):
        if row['ALERTA_DATA'] == "SEM DATA DE CALIBRACAO": return "VENCIDO"
        dias = (row['DATA_CALIBRACAO'] - hoje).days
        if dias < 0: return "VENCIDO"
        if dias <= 30: return "PRÓXIMO VENCIMENTO"
        return "APTOS"
    
    df['STATUS'] = df.apply(classificar, axis=1)
    return df

# --- NAVEGAÇÃO E INTERFACE ---
if 'selecionados' not in st.session_state: st.session_state.selecionados = []
df = processar_dados(carregar_dados())

menu = st.sidebar.radio("Navegação", ["🛠️ Visão Geral", "🚨 VENCIDOS"])

if menu == "🚨 VENCIDOS":
    df_f = df[df['STATUS'] == "VENCIDO"]
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            is_sel = idx in st.session_state.selecionados
            css_sel = "card-selecionado" if is_sel else ""
            data_exib = "⚠️ SEM DATA" if row['DATA_STR'] == "SEM DATA DE CALIBRACAO" else f"📅 {row['DATA_STR']}"
            
            st.markdown(f"<div class='card-instrumento vencido-card {css_sel}'><b>{row['Descrição'][:20]}</b><br><small>{row['Código']}</small><br><b>{data_exib}</b></div>", unsafe_allow_html=True)
            
            if st.button("✅ SELECIONADO" if is_sel else "⭕ Selecionar", key=f"btn_{idx}"):
                if is_sel: st.session_state.selecionados.remove(idx)
                else: st.session_state.selecionados.append(idx)
                st.rerun()
