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
    div[role="radiogroup"] > label { background-color: #1a2942; border: 1px solid #2a3d66; padding: 10px 20px; border-radius: 8px; margin-bottom: 8px; font-weight: bold; color: #b0b4c4; text-align: left; }
    div[role="radiogroup"] > label:has(input:checked) { background-color: #ff4b4b; color: white; border-color: #ff4b4b; box-shadow: 0 0 10px rgba(255, 75, 75, 0.4); }
    .kpi-container { padding: 12px; border-radius: 10px; text-align: center; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 10px; }
    .kpi-value { font-size: 28px; font-weight: 800; }
    .card-instrumento { background-color: #1a2942; border-radius: 8px; padding: 10px; margin-bottom: 5px; border-left: 5px solid #ccc; opacity: 0.7; transition: all 0.3s; }
    .vencido-card { border-left-color: #ff4b4b; background: linear-gradient(to right, #241010, #1a2942); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2e2811, #1a2942); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #112e1a, #1a2942); opacity: 1; }
    .card-selecionado { border: 2px solid #ff4b4b !important; box-shadow: 0 0 15px rgba(255, 75, 75, 0.6); transform: scale(1.02); opacity: 1 !important; background: linear-gradient(to right, #3d1414, #1a2942) !important; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE MEMÓRIA E CONFIG ---
def carregar_config():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f: return json.load(f)
    return {"emails": "luizclaudio@tempermar.com.br"}

def salvar_config(emails):
    with open("config.json", "w") as f: json.dump({"emails": emails}, f)

# --- CARGA E PROCESSAMENTO HIERÁRQUICO ---
@st.cache_data(ttl=600)
def carregar_dados():
    try: return pd.read_csv("https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv")
    except: return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), "Características")
    
    def extrair_vencimento(texto):
        if pd.isna(texto): return None, "SEM DATA DE CALIBRACAO"
        # 1. Tenta Próxima Calibração
        m_prox = re.search(r'Data da Próxima Calibração:\s*(\d{2}/\d{2}/\d{4})', str(texto))
        if m_prox: return pd.to_datetime(m_prox.group(1), dayfirst=True), None
        # 2. Tenta Última + 1 ano
        m_ult = re.search(r'Data da Última Calibração:\s*(\d{2}/\d{2}/\d{4})', str(texto))
        if m_ult:
            dt_ult = pd.to_datetime(m_ult.group(1), dayfirst=True)
            return dt_ult + relativedelta(years=1), None
        return None, "SEM DATA DE CALIBRACAO"

    res = df[col_caract].apply(extrair_vencimento)
    df['DATA_CALIBRACAO'] = [x[0] for x in res]
    df['ALERTA_DATA'] = [x[1] for x in res]
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna(df['ALERTA_DATA'])
    
    hoje = datetime.now()
    def classificar(row):
        if row['ALERTA_DATA'] == "SEM DATA DE CALIBRACAO": return "VENCIDO"
        dias = (row['DATA_CALIBRACAO'] - hoje).days
        return "VENCIDO" if dias < 0 else ("PRÓXIMO VENCIMENTO" if dias <= 30 else "APTOS")
    
    df['STATUS'] = df.apply(classificar, axis=1)
    return df

# --- FILTROS ---
def limpar_memoria_filtros(sufixo):
    for chave in [f"f_n_{sufixo}", f"f_c_{sufixo}", f"f_d_{sufixo}"]:
        if chave in st.session_state: st.session_state[chave] = ""

def sistema_filtros(key_sufix, mostrar_botao_limpar=False):
    col_titulo, col_botao = st.columns([4, 1])
    with col_titulo: st.markdown("##### 🔍 Filtros")
    with col_botao:
        if mostrar_botao_limpar: st.button("🧹 Limpar", on_click=limpar_memoria_filtros, args=(key_sufix,), use_container_width=True)
    c1, c2, c3 = st.columns(3)
    return c1.text_input("Nome:", key=f"f_n_{key_sufix}"), c2.text_input("Código:", key=f"f_c_{key_sufix}"), c3.text_input("Data:", key=f"f_d_{key_sufix}")

# --- APP ---
if 'selecionados' not in st.session_state: st.session_state.selecionados = []
df = processar_dados(carregar_dados())
menu = st.sidebar.radio("Navegação", ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos de vencer", "🚨 VENCIDOS", "⚙️ Ajustes"])

if menu == "🚨 VENCIDOS" or menu == "⏳ Próximos de vencer":
    status_alvo = "VENCIDO" if menu == "🚨 VENCIDOS" else "PRÓXIMO VENCIMENTO"
    fn, fc, fd = sistema_filtros(status_alvo, True)
    df_f = df[(df['STATUS'] == status_alvo) & (df['Descrição'].str.contains(fn, na=False)) & (df['Código'].str.contains(fc, na=False)) & (df['DATA_STR'].str.contains(fd, na=False))]
    
    for i, (idx, row) in enumerate(df_f.iterrows()):
        is_sel = idx in st.session_state.selecionados
        data_exib = "⚠️ SEM DATA" if row['DATA_STR'] == "SEM DATA DE CALIBRACAO" else f"📅 {row['DATA_STR']}"
        
        st.markdown(f"<div class='card-instrumento {'vencido-card' if menu=='🚨 VENCIDOS' else 'proximo-card'} {'card-selecionado' if is_sel else ''}'><b>{row['Descrição'][:20]}</b><br>{row['Código']}<br><b>{data_exib}</b></div>", unsafe_allow_html=True)
        if st.button("✅ SELECIONADO" if is_sel else "⭕ Selecionar", key=f"btn_{idx}"):
            if is_sel: st.session_state.selecionados.remove(idx)
            else: st.session_state.selecionados.append(idx)
            st.rerun()

elif menu == "⚙️ Ajustes":
    st.markdown("### ⚙️ Configurações")
    emails = st.text_input("E-mails:", value=st.session_state.get('config_emails', ''), key="set_emails")
    if st.button("Salvar"):
        st.session_state.config_emails = emails
        salvar_config(emails)
        st.success("Salvo!")
