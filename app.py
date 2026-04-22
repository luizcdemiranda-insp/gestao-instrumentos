import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E CSS TÁTICO ---
st.set_page_config(page_title="🛡️ Gestão de Calibração", layout="wide")

st.markdown("""
    <style>
    /* Estilização melhorada para o Menu Lateral */
    section[data-testid="stSidebar"] { background-color: #1a1c24; }
    
    /* Cartões de Alerta com efeito visual */
    .card-vencido { 
        background: linear-gradient(135deg, #2d1b1b, #1e1e1e);
        border-left: 8px solid #ff4b4b;
        padding: 20px; border-radius: 10px; margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.2);
    }
    .card-proximo { 
        background: linear-gradient(135deg, #2d2a1b, #1e1e1e);
        border-left: 8px solid #F1C40F;
        padding: 20px; border-radius: 10px; margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(241, 196, 15, 0.2);
    }
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
    msg['Subject'] = f"🚨 ALERTA: Calibração de {instrumento}"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destino
    msg.set_content(f"O instrumento {instrumento} está com a calibração vencida/vencendo em {data}. Favor providenciar.")
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

# --- NAVEGAÇÃO ---
menu = st.sidebar.radio("Navegar:", ["Visão Geral", "⚠️ Vencidos"], index=0)

df = processar_dados(carregar_dados())

if menu == "Visão Geral":
    st.title("📋 Visão Geral de Instrumentos")
    df_exibicao = df.copy()
    st.dataframe(df_exibicao, use_container_width=True)

elif menu == "⚠️ Vencidos":
    st.title("⚠️ Instrumentos Vencidos / Críticos")
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])].copy()
    
    if df_vencidos.empty:
        st.success("Tudo em dia!")
    else:
        # Inicializa estado de seleção
        if 'selecionados' not in st.session_state: st.session_state.selecionados = []
        
        email_geral = st.sidebar.text_input("E-mail para envio em lote:")
        if st.sidebar.button("Disparar Selecionados"):
            for idx in st.session_state.selecionados:
                row = df_vencidos.loc[idx]
                try:
                    enviar_alerta(email_geral, row['Descrição'], str(row['DATA_CALIBRACAO'])[:10])
                    st.toast(f"Enviado: {row['Código']}")
                except Exception as e: st.error(f"Erro em {row['Código']}: {e}")

        for idx, row in df_vencidos.iterrows():
            classe = "card-vencido" if row['STATUS'] == "VENCIDO" else "card-proximo"
            with st.container():
                st.markdown(f"<div class='{classe}'>", unsafe_allow_html=True)
                col1, col2 = st.columns([0.1, 0.9])
                # Checkbox para seleção em lote
                check = col1.checkbox("Sel", key=f"check_{idx}")
                if check and idx not in st.session_state.selecionados: st.session_state.selecionados.append(idx)
                if not check and idx in st.session_state.selecionados: st.session_state.selecionados.remove(idx)
                
                col2.write(f"### {row['Descrição']}")
                col2.write(f"**Código:** {row['Código']} | **Data Vencimento:** {str(row['DATA_CALIBRACAO'])[:10]}")
                st.markdown("</div>", unsafe_allow_html=True)
