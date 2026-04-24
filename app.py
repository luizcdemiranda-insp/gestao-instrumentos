import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage
import json
import os

# --- CONFIGURAÇÃO E ENGINE VISUAL (IDENTIDADE VISUAL VERMELHA) ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

st.markdown("""
    <style>
    /* Fundo e Sidebar */
    .stApp { background-color: #0b1325; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #121e36; border-right: 1px solid #1f3052; }
    
    /* Painel de Navegação: ALINHADO À ESQUERDA */
    div[role="radiogroup"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label {
        background-color: #1a2942; border: 1px solid #2a3d66; padding: 10px 20px;
        border-radius: 8px; margin-bottom: 8px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: flex-start; 
        width: 100%; color: #b0b4c4; cursor: pointer; text-align: left;
    }
    div[role="radiogroup"] > label:hover { border-color: #ff4b4b; color: white; }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #ff4b4b; color: white; border-color: #ff4b4b;
        box-shadow: 0 0 10px rgba(255, 75, 75, 0.4);
    }

    /* Indicadores Compactos */
    .kpi-container {
        padding: 12px; border-radius: 10px; text-align: center;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3); margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .kpi-value { font-size: 28px; font-weight: 800; line-height: 1.1; margin: 5px 0; }
    .kpi-label { font-size: 12px; font-weight: 600; text-transform: uppercase; opacity: 0.8; }

    /* Estilo de Cards Compactos */
    .card-instrumento {
        background-color: #1a2942; border-radius: 8px; padding: 10px;
        margin-bottom: 5px; border-left: 5px solid #ccc;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .vencido-card { border-left-color: #ff4b4b; background: linear-gradient(to right, #3d1414, #1a2942); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2e2811, #1a2942); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #112e1a, #1a2942); }

    .vencido-kpi { color: #ff4b4b; border-bottom: 3px solid #ff4b4b; }
    .proximo-kpi { color: #fcc419; border-bottom: 3px solid #fcc419; }
    .apto-kpi { color: #2ecc71; border-bottom: 3px solid #2ecc71; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE MEMÓRIA (PERSISTÊNCIA) ---
def carregar_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except: pass
    return {"emails": "luizclaudio@tempermar.com.br"}

def salvar_config(emails):
    with open("config.json", "w") as f:
        json.dump({"emails": emails}, f)

# --- CARGA E PROCESSAMENTO DE DADOS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
    def extrair_data(texto):
        if pd.isna(texto): return None
        match = re.search(r'\d{2}/\d{2}/\d{4}', str(texto))
        return pd.to_datetime(match.group(0), dayfirst=True) if match else None

    df.columns = [c.strip() for c in df.columns]
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), "Características")
    df['DATA_CALIBRACAO'] = df[col_caract].apply(extrair_data)
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna("N/A")
    hoje = datetime.now()
    if df['DATA_CALIBRACAO'] is not None:
        df['DIAS_RESTANTES'] = (df['DATA_CALIBRACAO'] - hoje).dt.days
        df['STATUS'] = df['DIAS_RESTANTES'].apply(lambda d: "VENCIDO" if d < 0 else ("PRÓXIMO VENCIMENTO" if d <= 30 else "APTOS"))
    return df

def enviar_email_consolidado(destinatarios, df_criticos):
    msg = EmailMessage()
    msg['Subject'] = f"🚨 ALERTA: {len(df_criticos)} Instrumentos Selecionados"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destinatarios
    conteudo = "Relatório de Instrumentos Selecionados para Alerta:\n\n"
    for _, row in df_criticos.iterrows():
        conteudo += f"- {row['Descrição']} (TAG: {row['Código']}) - Vencimento: {row['DATA_STR']}\n"
    msg.set_content(conteudo)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

def render_mini_kpi(label, valor, classe):
    st.markdown(f'<div class="kpi-container {classe}"><div class="kpi-label">{label}</div><div class="kpi-value">{valor}</div></div>', unsafe_allow_html=True)

def sistema_filtros(key_sufix):
    st.markdown("##### 🔍 Filtros de pesquisa")
    c_f1, c_f2, c_f3 = st.columns(3)
    f_nome = c_f1.text_input("Por Nome:", key=f"f_n_{key_sufix}", value="")
    f_cod = c_f2.text_input("Por Código:", key=f"f_c_{key_sufix}", value="")
    f_data = c_f3.text_input("Por Data (dd/mm/aaaa):", key=f"f_d_{key_sufix}", value="")
    return f_nome, f_cod, f_data

# --- INICIALIZAÇÃO DE SESSÃO E MEMÓRIA ---
config_atual = carregar_config()
if 'config_emails' not in st.session_state: st.session_state.config_emails = config_atual["emails"]
if 'selecionados' not in st.session_state: st.session_state.selecionados = []

# --- NAVEGAÇÃO ---
st.sidebar.markdown("<h3 style='color: white;'>SISTEMA DE MONITORAMENTO DE INSTRUMENTOS</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Painel de navegação", ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos de vencer", "🚨 VENCIDOS", "⚙️ Ajustes"], index=0)

df = processar_dados(carregar_dados())

# --- PÁGINAS ---
if menu == "🛠️ Visão Geral":
    st.markdown("### 🛠️ Dashboard Geral")
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi("Aptos", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Atenção", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mini_kpi("Vencidos", len(df[df['STATUS'] == 'VENCIDO']), "vencido-kpi")
    st.dataframe(df, use_container_width=True)

elif menu == "✅ APTOS":
    st.markdown("### ✅ Instrumentos Aptos")
    fn, fc, fd = sistema_filtros("aptos")
    df_f = df[df['STATUS'] == 'APTOS']
    if fn: df_f = df_f[df_f['Descrição'].str.contains(fn, case=False, na=False)]
    if fc: df_f = df_f[df_f['Código'].str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].str.contains(fd, case=False, na=False)]
    
    render_mini_kpi("Total Aptos", len(df_f), "apto-kpi")
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            st.markdown(f"<div class='card-instrumento apto-card'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br><span style='font-size:11px;'>📅 {row['DATA_STR']}</span></div>", unsafe_allow_html=True)

elif menu == "⏳ Próximos de vencer" or menu == "🚨 VENCIDOS":
    status_alvo = "PRÓXIMO VENCIMENTO" if menu == "⏳ Próximos de vencer" else "VENCIDO"
    classe_kpi = "proximo-kpi" if menu == "⏳ Próximos de vencer" else "vencido-kpi"
    classe_card = "proximo-card" if menu == "⏳ Próximos de vencer" else "vencido-card"
    
    st.markdown(f"### {menu}")
    fn, fc, fd = sistema_filtros(status_alvo)
    df_f = df[df['STATUS'] == status_alvo]
    if fn: df_f = df_f[df_f['Descrição'].str.contains(fn, case=False, na=False)]
    if fc: df_f = df_f[df_f['Código'].str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].str.contains(fd, case=False, na=False)]
    
    render_mini_kpi("Quantidade Filtrada", len(df_f), classe_kpi)

    if menu == "🚨 VENCIDOS":
        if st.button("🚨 Enviar alerta agora", use_container_width=True):
            if st.session_state.selecionados:
                try:
                    enviar_email_consolidado(st.session_state.config_emails, df.loc[st.session_state.selecionados])
                    st.success(f"Alerta enviado para {len(st.session_state.selecionados)} itens!")
                except Exception as e: st.error(f"Erro no envio: {e}")
            else: st.warning("Selecione os instrumentos nos cards abaixo.")

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            st.markdown(f"<div class='card-instrumento {classe_card}'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br><b>📅 {row['DATA_STR']}</b></div>", unsafe_allow_html=True)
            check = st.checkbox("Selecionar", key=f"sel_{idx}", value=(idx in st.session_state.selecionados))
            if check and idx not in st.session_state.selecionados: st.session_state.selecionados.append(idx)
            elif not check and idx in st.session_state.selecionados: st.session_state.selecionados.remove(idx)

elif menu == "⚙️ Ajustes":
    st.markdown("### ⚙️ Configurações")
    
    st.markdown("#### 📧 E-mails de Alerta")
    st.write("Defina para quais endereços o sistema enviará as notificações manuais e automáticas.")
    
    novos_emails = st.text_input("Digitar novos e-mails (separados por vírgula):", value="", key="set_emails")
    if st.button("Salvar E-mails"):
        if novos_emails:
            st.session_state.config_emails = novos_emails
            salvar_config(st.session_state.config_emails)
            st.success("E-mails memorizados com sucesso!")
            
    st.info(f"**E-mails configurados atualmente:** {st.session_state.config_emails}")
