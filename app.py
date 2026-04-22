import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E CSS (MODO COMPACTO) ---
st.set_page_config(page_title="🛡️ Gestão de Calibração", layout="wide")

st.markdown("""
    <style>
    .card-compact { 
        padding: 12px; border-radius: 8px; margin: 5px; 
        border-left: 5px solid #ccc; font-size: 0.9em;
        background-color: #f8f9fa; color: #333;
    }
    .vencido { border-color: #ff6b6b; background-color: #fff5f5; }
    .proximo { border-color: #fcc419; background-color: #fff9db; }
    .stMetric { background: #f1f3f5; padding: 10px; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# URL CSV da Planilha
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MQ1i0fZ_uV_lE9EZA92YOJ-jMYuPxppQ9qKql1_E5bY/export?format=csv&gid=0"

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
    df['STATUS'] = df['DIAS_RESTANTES'].apply(lambda d: "VENCIDO" if d < 0 else ("PRÓXIMO VENCIMENTO" if d <= 30 else "NO PRAZO"))
    return df

def enviar_alerta(destino, instrumento, data):
    msg = EmailMessage()
    msg['Subject'] = f"🚨 Alerta de Calibração: {instrumento}"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destino
    msg.set_content(f"O item {instrumento} vence em {data}.")
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

# --- NAVEGAÇÃO ---
menu = st.sidebar.radio("Navegar:", ["Visão Geral", "⚠️ Vencidos"], index=1)
df = processar_dados(carregar_dados())

if menu == "Visão Geral":
    st.title("📋 Visão Geral")
    st.dataframe(df, use_container_width=True)

elif menu == "⚠️ Vencidos":
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])].copy()
    
    # Contador de destaque
    st.title("⚠️ Gestão de Prazos")
    col_kpi1, col_kpi2 = st.columns([1, 4])
    col_kpi1.metric("Pendentes", len(df_vencidos))
    
    if df_vencidos.empty:
        st.success("Tudo em dia!")
    else:
        email_geral = st.sidebar.text_input("E-mail destino (lote):")
        if st.sidebar.button("Disparar Selecionados"):
            for idx in st.session_state.get('selecionados', []):
                row = df_vencidos.loc[idx]
                enviar_alerta(email_geral, row['Descrição'], str(row['DATA_CALIBRACAO'])[:10])
            st.toast("Alertas enviados!")

        # Grid de cards compactos (3 colunas)
        cols = st.columns(3)
        if 'selecionados' not in st.session_state: st.session_state.selecionados = []
        
        for i, (idx, row) in enumerate(df_vencidos.iterrows()):
            with cols[i % 3]:
                tipo = "vencido" if row['STATUS'] == "VENCIDO" else "proximo"
                st.markdown(f"""
                    <div class='card-compact {tipo}'>
                        <strong>{row['Descrição'][:30]}...</strong><br>
                        Código: {row['Código']}<br>
                        Vencimento: {str(row['DATA_CALIBRACAO'])[:10]}
                    </div>
                """, unsafe_allow_html=True)
                if st.checkbox("Selecionar", key=f"sel_{idx}"):
                    if idx not in st.session_state.selecionados: st.session_state.selecionados.append(idx)
                elif idx in st.session_state.selecionados: st.session_state.selecionados.remove(idx)
