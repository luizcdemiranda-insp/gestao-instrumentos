import streamlit as st
import pandas as pd
import re
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="🛡️ Gestão de Calibração", layout="wide")

# Conexão com Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNÇÕES DE APOIO ---
def processar_dados(df):
    # Regex para buscar data (dd/mm/aaaa) no campo Características
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

df_raw = conn.read(worksheet="Página1") # Ajuste se necessário
df = processar_dados(df_raw)

# --- PÁGINA VISÃO GERAL ---
if menu == "Visão Geral":
    st.title("📋 Visão Geral de Instrumentos")
    
    # Filtros
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
            cor = "#ff4b4b" if row['STATUS'] == "VENCIDO" else "#F1C40F"
            with st.expander(f"{row['STATUS']} - {row['Descrição']}"):
                st.write(f"Código: {row['Código']} | Data: {str(row['DATA_CALIBRACAO'])[:10]}")
                email = st.text_input(f"E-mail do responsável para {row['Código']}:")
                if st.button(f"Disparar Alerta", key=row['Código']):
                    if email:
                        enviar_alerta(email, row['Descrição'], str(row['DATA_CALIBRACAO'])[:10])
                        st.success("E-mail enviado!")
                    else:
                        st.warning("Digite um e-mail.")
