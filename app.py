import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E DESIGN SYSTEM (NAVY & NEON) ---
st.set_page_config(page_title="🛠️ Monitoramento", layout="wide")

st.markdown("""
    <style>
    /* PALETA E FUNDO */
    .stApp { background-color: #0b132b; color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #1c2541; }
    
    /* MENU ESTILO MERCÚRIO */
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
    
    /* KPI MODERNO (FONTE VIVA) */
    .kpi-container {
        background-color: #1c2541; padding: 20px; border-radius: 15px;
        text-align: center; border: 1px solid #3a506b;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3); margin-bottom: 20px;
    }
    .kpi-value {
        font-family: 'Inter', sans-serif; font-size: 64px; font-weight: 800;
        line-height: 1; margin: 10px 0;
        text-shadow: 0 0 15px var(--glow-color);
    }
    .kpi-label { font-size: 14px; color: #a1b0c0; text-transform: uppercase; letter-spacing: 1px; }

    /* CARDS COMPACTOS */
    .card-compact { 
        padding: 15px; border-radius: 8px; margin: 8px; 
        border-left: 6px solid #ccc; font-size: 0.95em;
        background-color: #1c2541; color: #e0e6ed;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.5);
        height: 125px;
    }
    .vencido { border-color: #ff4b4b; --glow-color: rgba(255, 75, 75, 0.6); }
    .proximo { border-color: #f1c40f; --glow-color: rgba(241, 196, 15, 0.6); }
    .aptos { border-color: #2ecc71; --glow-color: rgba(46, 204, 113, 0.6); }
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
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna("N/A")
    return df

def render_kpi(label, value, color_class):
    color = "#2ecc71" if color_class == "aptos" else ("#ff4b4b" if color_class == "vencido" else "#f1c40f")
    html = f"""
    <div class="kpi-container {color_class}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value" style="color: {color};">{value}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

def enviar_email_lote(destino, lista_instrumentos):
    msg = EmailMessage()
    msg['Subject'] = "🚨 ALERTA: Monitoramento de Instrumentos"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destino
    conteudo = "Relatório de Pendências:\n\n"
    for item in lista_instrumentos:
        conteudo += f"- {item['Desc']} (Cód: {item['Cod']}) | Vencimento: {item['Data']}\n"
    msg.set_content(conteudo)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

# --- NAVEGAÇÃO ---
st.sidebar.title("🛠️ Monitoramento de Instrumentos")
st.sidebar.markdown("<br>", unsafe_allow_html=True)

menu = st.sidebar.radio("", ["✅ INSTRUMENTOS APTOS", "🔴 VENCIDOS", "⚠️ PRÓXIMOS DE VENCER", "📊 VISÃO GERAL"], index=0, label_visibility="collapsed")

df = processar_dados(carregar_dados())

# Lógica de Limpar Filtros
def limpar_filtros():
    for key in st.session_state.keys():
        if key.startswith("f_"): st.session_state[key] = ""

# --- PÁGINA: INSTRUMENTOS APTOS ---
if "APTOS" in menu:
    st.title("✅ INSTRUMENTOS APTOS")
    df_pg = df[df['STATUS'] == 'NO PRAZO'].copy()
    
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    f_nome = c1.text_input("🔍 Nome", key="f_apt_nome")
    f_cod = c2.text_input("🔍 Código", key="f_apt_cod")
    f_data = c3.text_input("📅 Vencimento", key="f_apt_data")
    c4.markdown("<br>", unsafe_allow_html=True)
    c4.button("🧹 Limpar", on_click=limpar_filtros)

    if f_nome: df_pg = df_pg[df_pg['Descrição'].str.contains(f_nome, case=False, na=False)]
    if f_cod: df_pg = df_pg[df_pg['Código'].str.contains(f_cod, case=False, na=False)]
    if f_data: df_pg = df_pg[df_pg['DATA_STR'].str.contains(f_data, case=False, na=False)]

    render_kpi("INSTRUMENTOS APTOS PARA USO", len(df_pg), "aptos")

    cols = st.columns(3)
    for i, (idx, row) in enumerate(df_pg.iterrows()):
        with cols[i % 3]:
            st.markdown(f"<div class='card-compact em-dia'><strong>{row['Descrição'][:40]}</strong><br><small style='color:#a1b0c0;'>Cód: {row['Código']}<br>Vencimento: <b style='color:#ffffff;'>{row['DATA_STR']}</b></small></div>", unsafe_allow_html=True)

# --- PÁGINA: VENCIDOS ---
elif "🔴 VENCIDOS" in menu:
    st.title("🔴 INSTRUMENTOS VENCIDOS")
    df_pg = df[df['STATUS'] == 'VENCIDO'].copy()
    
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    f_nome = c1.text_input("🔍 Nome", key="f_ven_nome")
    f_cod = c2.text_input("🔍 Código", key="f_ven_cod")
    f_data = c3.text_input("📅 Vencimento", key="f_ven_data")
    c4.markdown("<br>", unsafe_allow_html=True)
    c4.button("🧹 Limpar", on_click=limpar_filtros)

    if f_nome: df_pg = df_pg[df_pg['Descrição'].str.contains(f_nome, case=False, na=False)]
    if f_cod: df_pg = df_pg[df_pg['Código'].str.contains(f_cod, case=False, na=False)]
    if f_data: df_pg = df_pg[df_pg['DATA_STR'].str.contains(f_data, case=False, na=False)]

    render_kpi("INSTRUMENTOS FORA DO PRAZO", len(df_pg), "vencido")

    email_destino = st.sidebar.text_input("E-mail para Alerta:")
    if st.sidebar.button("Disparar E-mail"):
        selecionados = [idx for idx in df_pg.index if st.session_state.get(f"ck_{idx}")]
        if selecionados and email_destino:
            lista = [{'Desc': df_pg.loc[i, 'Descrição'], 'Cod': df_pg.loc[i, 'Código'], 'Data': df_pg.loc[i, 'DATA_STR']} for i in selecionados]
            enviar_email_lote(email_destino, lista)
            st.success("Alerta enviado!")

    cols = st.columns(3)
    for i, (idx, row) in enumerate(df_pg.iterrows()):
        with cols[i % 3]:
            st.checkbox("Selecionar", key=f"ck_{idx}")
            st.markdown(f"<div class='card-compact vencido'><strong>{row['Descrição'][:40]}</strong><br><small style='color:#a1b0c0;'>Cód: {row['Código']}<br>Vencimento: <b style='color:#ffffff;'>{row['DATA_STR']}</b></small></div>", unsafe_allow_html=True)

# --- PÁGINA: PRÓXIMOS ---
elif "PRÓXIMOS" in menu:
    st.title("⚠️ PRÓXIMOS DE VENCER (30 DIAS)")
    df_pg = df[df['STATUS'] == 'PRÓXIMO VENCIMENTO'].copy()
    
    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
    f_nome = c1.text_input("🔍 Nome", key="f_px_nome")
    f_cod = c2.text_input("🔍 Código", key="f_px_cod")
    f_data = c3.text_input("📅 Vencimento", key="f_px_data")
    c4.markdown("<br>", unsafe_allow_html=True)
    c4.button("🧹 Limpar", on_click=limpar_filtros)

    render_kpi("ATENÇÃO: VENCIMENTO PRÓXIMO", len(df_pg), "proximo")

    cols = st.columns(3)
    for i, (idx, row) in enumerate(df_pg.iterrows()):
        with cols[i % 3]:
            st.markdown(f"<div class='card-compact proximo'><strong>{row['Descrição'][:40]}</strong><br><small style='color:#a1b0c0;'>Cód: {row['Código']}<br>Vencimento: <b style='color:#ffffff;'>{row['DATA_STR']}</b></small></div>", unsafe_allow_html=True)

# --- PÁGINA: VISÃO GERAL ---
elif "VISÃO GERAL" in menu:
    st.title("📊 STATUS GERAL DO INVENTÁRIO")
    st.dataframe(df.drop(columns=['DATA_STR']), use_container_width=True)
