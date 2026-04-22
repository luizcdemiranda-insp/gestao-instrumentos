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
    /* Cards limpos e legíveis */
    .card-compact { 
        padding: 15px; border-radius: 8px; margin: 8px; 
        border-left: 6px solid #ccc; font-size: 0.95em;
        background-color: #ffffff; color: #2c3e50;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        height: 120px;
    }
    .vencido { border-color: #e74c3c; }
    .proximo { border-color: #f1c40f; }
    .em-dia { border-color: #2ecc71; }
    
    /* Ajuste de métricas */
    [data-testid="stMetricValue"] { font-size: 28px; }
    </style>
""", unsafe_allow_html=True)

# URL da Planilha (Certifique-se de que está publicada como CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pubhtml"

@st.cache_data(ttl=600)
def carregar_dados():
    # Nota: Em ambiente real, use a URL terminada em /export?format=csv
    # Aqui usaremos a que você forneceu na Versão 1
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
    return df

def enviar_email_lote(destino, lista_instrumentos):
    msg = EmailMessage()
    msg['Subject'] = "🚨 ALERTA: Calibração de Instrumentos"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destino
    
    conteudo = "Relatório de Instrumentos com Pendência de Calibração:\n\n"
    for item in lista_instrumentos:
        conteudo += f"- {item['Desc']} (Cód: {item['Cod']}) | Vencimento: {item['Data']}\n"
    
    msg.set_content(conteudo)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

# --- NAVEGAÇÃO ---
st.sidebar.title("🛡️ Sistema de Calibração")
menu = st.sidebar.radio("Navegar:", ["📊 Visão Geral", "⚠️ Vencidos", "✅ Em Dia"], index=0)

# Carregamento e Processamento
try:
    df_raw = carregar_dados()
    df = processar_dados(df_raw)
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.stop()

# --- PÁGINA: VISÃO GERAL ---
if "Visão Geral" in menu:
    st.title("📋 Status Geral do Inventário")
    st.dataframe(df, use_container_width=True)

# --- PÁGINA: VENCIDOS ---
elif "Vencidos" in menu:
    st.title("⚠️ Gestão de Prazos Críticos")
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])].copy()
    
    st.metric("Instrumentos fora do prazo de calibração", len(df_vencidos))
    
    if df_vencidos.empty:
        st.success("Excelente! Não há instrumentos vencidos.")
    else:
        # Interface de Envio em Lote
        with st.sidebar.expander("📧 Disparo de Alerta", expanded=True):
            email_destino = st.text_input("E-mail do responsável:")
            if st.button("Enviar Alerta em Lote"):
                selecionados = [idx for idx in df_vencidos.index if st.session_state.get(f"check_{idx}")]
                if selecionados and email_destino:
                    lista = [{'Desc': df_vencidos.loc[i, 'Descrição'], 
                              'Cod': df_vencidos.loc[i, 'Código'],
                              'Data': df_vencidos.loc[i, 'DATA_CALIBRACAO'].strftime('%d/%m/%Y')} for i in selecionados]
                    try:
                        enviar_email_lote(email_destino, lista)
                        st.success("E-mail consolidado enviado!")
                    except Exception as e: st.error(f"Erro no envio: {e}")
                else: st.warning("Selecione itens e informe o e-mail.")

        # Grid de Cards Vencidos
        cols = st.columns(3)
        for i, (idx, row) in enumerate(df_vencidos.iterrows()):
            with cols[i % 3]:
                st.checkbox("Selecionar", key=f"check_{idx}")
                tipo_classe = "vencido" if row['STATUS'] == "VENCIDO" else "proximo"
                data_str = row['DATA_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row['DATA_CALIBRACAO']) else "N/A"
                st.markdown(f"""
                    <div class='card-compact {tipo_classe}'>
                        <strong>{row['Descrição'][:40]}</strong><br>
                        <small>Cód: {row['Código']}<br>
                        Vencimento: <b>{data_str}</b></small>
                    </div>
                """, unsafe_allow_html=True)

# --- PÁGINA: EM DIA ---
elif "Em Dia" in menu:
    st.title("✅ Instrumentos em Conformidade")
    df_em_dia = df[df['STATUS'] == 'NO PRAZO'].copy()
    
    st.metric("Instrumentos com calibração em dia", len(df_em_dia))
    
    if df_em_dia.empty:
        st.info("Nenhum instrumento no prazo encontrado.")
    else:
        # Grid de Cards Em Dia (sem checkbox, apenas visualização)
        cols = st.columns(3)
        for i, (idx, row) in enumerate(df_em_dia.iterrows()):
            with cols[i % 3]:
                data_str = row['DATA_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row['DATA_CALIBRACAO']) else "N/A"
                st.markdown(f"""
                    <div class='card-compact em-dia'>
                        <strong>{row['Descrição'][:40]}</strong><br>
                        <small>Cód: {row['Código']}<br>
                        Vencimento: {data_str}</small>
                    </div>
                """, unsafe_allow_html=True)
