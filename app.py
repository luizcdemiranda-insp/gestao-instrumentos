import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E MOTOR VISUAL (TEMA NAVY & MERCÚRIO) ---
st.set_page_config(page_title="🛡️ Monitoramento", layout="wide")

st.markdown("""
    <style>
    /* 1. PALETA BASE (Azul Marinho Profundo) */
    .stApp { background-color: #0b132b; color: #ffffff; }
    section[data-testid="stSidebar"] { background-color: #1c2541; }
    
    /* 2. MENU ESTILO MERCÚRIO (Botões Blindados) */
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
    
    /* 3. CARDS COMPACTOS (Fundo Escuro) */
    .card-compact { 
        padding: 15px; border-radius: 8px; margin: 8px; 
        border-left: 6px solid #ccc; font-size: 0.95em;
        background-color: #1c2541; color: #e0e6ed;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.5);
        height: 125px; transition: transform 0.2s;
    }
    .card-compact:hover { transform: scale(1.02); }
    
    /* Cores de Status (Laranja no lugar de Vermelho) */
    .vencido { border-color: #ff8c00; } 
    .proximo { border-color: #f1c40f; }
    .em-dia { border-color: #2ecc71; }
    
    /* Ajustes Gerais de Texto */
    [data-testid="stMetricValue"] { font-size: 28px; color: #ffffff; }
    [data-testid="stMetricLabel"] { color: #a1b0c0; }
    h1, h2, h3 { color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# URL da Planilha (CORRIGIDA COM output=csv)
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
    return df

def enviar_email_lote(destino, lista_instrumentos):
    msg = EmailMessage()
    msg['Subject'] = "🚨 ALERTA: Monitoramento de Instrumentos"
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
st.sidebar.title("🛡️ Monitoramento de Instrumentos")
st.sidebar.markdown("<br>", unsafe_allow_html=True) # Espaçamento

# Label vazio para remover o texto "Navegar"
menu = st.sidebar.radio("", ["📊 Visão Geral", "⚠️ Vencidos", "✅ Em Dia"], index=0, label_visibility="collapsed")

# Carregamento
try:
    df_raw = carregar_dados()
    df = processar_dados(df_raw)
except Exception as e:
    st.error(f"Erro ao carregar dados. Verifique o link da planilha. Detalhe: {e}")
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

        cols = st.columns(3)
        for i, (idx, row) in enumerate(df_vencidos.iterrows()):
            with cols[i % 3]:
                st.checkbox("Selecionar", key=f"check_{idx}")
                tipo_classe = "vencido" if row['STATUS'] == "VENCIDO" else "proximo"
                data_str = row['DATA_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row['DATA_CALIBRACAO']) else "N/A"
                st.markdown(f"""
                    <div class='card-compact {tipo_classe}'>
                        <strong>{row['Descrição'][:40]}</strong><br>
                        <small style='color:#a1b0c0;'>Cód: {row['Código']}<br>
                        Vencimento: <b style='color:#ffffff;'>{data_str}</b></small>
                    </div>
                """, unsafe_allow_html=True)

# --- PÁGINA: EM DIA ---
elif "Em Dia" in menu:
    st.title("✅ Instrumentos Aptos")
    df_em_dia = df[df['STATUS'] == 'NO PRAZO'].copy()
    
    st.metric("Instrumentos aptos para uso", len(df_em_dia))
    
    if df_em_dia.empty:
        st.info("Nenhum instrumento no prazo encontrado.")
    else:
        cols = st.columns(3)
        for i, (idx, row) in enumerate(df_em_dia.iterrows()):
            with cols[i % 3]:
                data_str = row['DATA_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row['DATA_CALIBRACAO']) else "N/A"
                st.markdown(f"""
                    <div class='card-compact em-dia'>
                        <strong>{row['Descrição'][:40]}</strong><br>
                        <small style='color:#a1b0c0;'>Cód: {row['Código']}<br>
                        Vencimento: <b style='color:#ffffff;'>{data_str}</b></small>
                    </div>
                """, unsafe_allow_html=True)
