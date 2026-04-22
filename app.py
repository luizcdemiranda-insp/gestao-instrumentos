import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="🛡️ Gestão de Calibração", layout="wide")

# URL de publicação da sua planilha como CSV
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MQ1i0fZ_uV_lE9EZA92YOJ-jMYuPxppQ9qKql1_E5bY/export?format=csv&gid=0"

# --- FUNÇÕES DE APOIO ---
@st.cache_data(ttl=600)
def carregar_dados():
    # Lê a planilha diretamente como CSV (muito mais estável)
    df = pd.read_csv(SHEET_URL)
    return df

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
    return df

def enviar_alerta(destino, instrumento, data):
    msg = EmailMessage()
    msg['Subject'] = f"🚨 ALERTA: Calibração Vencida - {instrumento}"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destino
    msg.set_content(f"O instrumento {instrumento} está com a calibração vencida desde {data}. Favor providenciar nova calibração.")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

# --- NAVEGAÇÃO ---
st.sidebar.title("🎛️ MENU")
menu = st.sidebar.radio("Navegar:", ["Visão Geral", "⚠️ Vencidos"])

df_raw = carregar_dados()
df = processar_dados(df_raw)

# --- PÁGINA VISÃO GERAL ---
if menu == "Visão Geral":
    st.title("📋 Visão Geral de Instrumentos")
    status_filter = st.sidebar.multiselect("Filtrar por Status:", df['STATUS'].unique(), default=df['STATUS'].unique())
    df_exibicao = df[df['STATUS'].isin(status_filter)]
    st.dataframe(df_exibicao, use_container_width=True)

# --- PÁGINA VENCIDOS ---
elif menu == "⚠️ Vencidos":
    st.title("⚠️ Instrumentos Vencidos / Críticos")
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])]
    
    if df_vencidos.empty:
        st.success("Tudo em dia! Nenhum vencimento pendente.")
    else:
        for _, row in df_vencidos.iterrows():
            with st.expander(f"{row['STATUS']} - {row['Descrição']}"):
                st.write(f"**Código:** {row['Código']} | **Data:** {str(row['DATA_CALIBRACAO'])[:10]}")
                email = st.text_input(f"E-mail para {row['Código']}:", key=f"email_{row['Código']}")
                if st.button(f"Disparar Alerta", key=f"btn_{row['Código']}"):
                    if email:
                        try:
                            enviar_alerta(email, row['Descrição'], str(row['DATA_CALIBRACAO'])[:10])
                            st.success("E-mail enviado!")
                        except Exception as e:
                            st.error(f"Erro: {e}")
                    else:
                        st.warning("Digite um e-mail.")
