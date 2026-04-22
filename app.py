import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E CSS ---
st.set_page_config(page_title="🛡️ Gestão de Calibração", layout="wide")

st.markdown("""
    <style>
    /* Cards mais limpos e legíveis */
    .card-compact { 
        padding: 15px; border-radius: 8px; margin: 8px; 
        border-left: 6px solid #ccc; font-size: 0.95em;
        background-color: #ffffff; color: #2c3e50;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .vencido { border-color: #e74c3c; }
    .proximo { border-color: #f1c40f; }
    </style>
""", unsafe_allow_html=True)

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

def enviar_email_lote(destino, lista_instrumentos):
    msg = EmailMessage()
    msg['Subject'] = "🚨 ALERTA: Calibração de Instrumentos"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destino
    conteudo = "Os seguintes instrumentos estão fora do prazo ou próximos do vencimento:\n\n"
    for item in lista_instrumentos:
        conteudo += f"- {item['Desc']}: Vence em {item['Data']}\n"
    msg.set_content(conteudo)
    
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
    st.title("⚠️ Gestão de Prazos")
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])].copy()
    
    # Contador superior
    st.metric("Instrumentos fora do prazo de calibração", len(df_vencidos))
    
    if df_vencidos.empty:
        st.success("Tudo em dia!")
    else:
        email_geral = st.sidebar.text_input("E-mail para envio em lote:")
        if st.sidebar.button("Enviar e-mail para selecionados"):
            selecionados = [idx for idx in st.session_state.get('sel_map', []) if st.session_state.get(f"check_{idx}")]
            if selecionados and email_geral:
                lista = [{'Desc': df_vencidos.loc[i, 'Descrição'], 'Data': df_vencidos.loc[i, 'DATA_CALIBRACAO'].strftime('%d/%m/%Y')} for i in selecionados]
                try:
                    enviar_email_lote(email_geral, lista)
                    st.toast("E-mail único enviado com sucesso!")
                except Exception as e: st.error(f"Erro: {e}")
            else: st.warning("Selecione itens e digite um e-mail.")

        # Grid de cards
        cols = st.columns(3)
        st.session_state.sel_map = df_vencidos.index
        for i, (idx, row) in enumerate(df_vencidos.iterrows()):
            with cols[i % 3]:
                # Checkbox acima do card
                st.checkbox("Selecionar", key=f"check_{idx}")
                tipo = "vencido" if row['STATUS'] == "VENCIDO" else "proximo"
                data_formatada = row['DATA_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row['DATA_CALIBRACAO']) else "N/A"
                st.markdown(f"""
                    <div class='card-compact {tipo}'>
                        <strong>{row['Descrição'][:30]}...</strong><br>
                        <small>Código: {row['Código']}<br>
                        Vencimento: {data_formatada}</small>
                    </div>
                """, unsafe_allow_html=True)
