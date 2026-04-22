import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E MOTOR VISUAL ---
st.set_page_config(page_title="🛠️ Monitoramento", layout="wide")

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
    
    /* 3. CARDS COMPACTOS */
    .card-compact { 
        padding: 15px; border-radius: 8px; margin: 8px; 
        border-left: 6px solid #ccc; font-size: 0.95em;
        background-color: #1c2541; color: #e0e6ed;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.5);
        height: 125px; transition: transform 0.2s;
    }
    .card-compact:hover { transform: scale(1.02); }
    
    /* Cores de Status (Vermelho voltou para os Vencidos) */
    .vencido { border-color: #ff4b4b; } /* Vermelho alerta */
    .proximo { border-color: #f1c40f; } /* Amarelo atenção */
    .em-dia { border-color: #2ecc71; }  /* Verde apto */
    
    /* Ajustes Gerais */
    [data-testid="stMetricValue"] { font-size: 28px; color: #ffffff; }
    [data-testid="stMetricLabel"] { color: #a1b0c0; }
    h1, h2, h3 { color: #ffffff; }
    hr { border-color: #3a506b; }
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
    # Coluna auxiliar de data formatada em texto para facilitar o filtro
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna("N/A")
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
st.sidebar.title("🛠️ Monitoramento de Instrumentos")
st.sidebar.markdown("<br>", unsafe_allow_html=True)

# Nova ordem e nomenclatura das abas
menu = st.sidebar.radio("", ["✅ INSTRUMENTOS APTOS", "⚠️ VENCIDOS", "📊 Visão Geral"], index=0, label_visibility="collapsed")

try:
    df_raw = carregar_dados()
    df = processar_dados(df_raw)
except Exception as e:
    st.error(f"Erro ao carregar dados. Detalhe: {e}")
    st.stop()


# --- PÁGINA 1: INSTRUMENTOS APTOS ---
if "APTOS" in menu:
    st.title("✅ INSTRUMENTOS APTOS")
    df_em_dia = df[df['STATUS'] == 'NO PRAZO'].copy()
    
    # Sistema de Filtros
    c1, c2, c3 = st.columns(3)
    f_nome = c1.text_input("🔍 Buscar por Nome:", key="f1_nome")
    f_cod = c2.text_input("🔍 Buscar por Código:", key="f1_cod")
    f_data = c3.text_input("📅 Filtrar Vencimento (ex: 2026 ou 05/10):", key="f1_data")
    
    if f_nome: df_em_dia = df_em_dia[df_em_dia['Descrição'].str.contains(f_nome, case=False, na=False)]
    if f_cod: df_em_dia = df_em_dia[df_em_dia['Código'].str.contains(f_cod, case=False, na=False)]
    if f_data: df_em_dia = df_em_dia[df_em_dia['DATA_STR'].str.contains(f_data, case=False, na=False)]

    st.metric("Instrumentos aptos para uso (Filtrados)", len(df_em_dia))
    st.markdown("<hr>", unsafe_allow_html=True)

    if df_em_dia.empty:
        st.info("Nenhum instrumento encontrado com esses filtros.")
    else:
        cols = st.columns(3)
        for i, (idx, row) in enumerate(df_em_dia.iterrows()):
            with cols[i % 3]:
                st.markdown(f"""
                    <div class='card-compact em-dia'>
                        <strong>{row['Descrição'][:40]}</strong><br>
                        <small style='color:#a1b0c0;'>Cód: {row['Código']}<br>
                        Vencimento: <b style='color:#ffffff;'>{row['DATA_STR']}</b></small>
                    </div>
                """, unsafe_allow_html=True)

# --- PÁGINA 2: VENCIDOS ---
elif "VENCIDOS" in menu:
    st.title("⚠️ VENCIDOS E PRÓXIMOS")
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])].copy()
    
    # Sistema de Filtros
    c1, c2, c3 = st.columns(3)
    f_nome = c1.text_input("🔍 Buscar por Nome:", key="f2_nome")
    f_cod = c2.text_input("🔍 Buscar por Código:", key="f2_cod")
    f_data = c3.text_input("📅 Filtrar Vencimento (ex: 2026 ou 05/10):", key="f2_data")
    
    if f_nome: df_vencidos = df_vencidos[df_vencidos['Descrição'].str.contains(f_nome, case=False, na=False)]
    if f_cod: df_vencidos = df_vencidos[df_vencidos['Código'].str.contains(f_cod, case=False, na=False)]
    if f_data: df_vencidos = df_vencidos[df_vencidos['DATA_STR'].str.contains(f_data, case=False, na=False)]

    st.metric("Instrumentos fora do prazo (Filtrados)", len(df_vencidos))
    st.markdown("<hr>", unsafe_allow_html=True)
    
    if df_vencidos.empty:
        st.success("Tudo limpo! Nenhum instrumento vencido ou próximo encontrado com esses filtros.")
    else:
        # Bloco de Disparo em Lote
        with st.sidebar.expander("📧 Disparo de Alerta", expanded=True):
            email_destino = st.text_input("E-mail do responsável:")
            if st.button("Enviar Alerta aos Selecionados"):
                selecionados = [idx for idx in df_vencidos.index if st.session_state.get(f"check_{idx}")]
                if selecionados and email_destino:
                    lista = [{'Desc': df_vencidos.loc[i, 'Descrição'], 
                              'Cod': df_vencidos.loc[i, 'Código'],
                              'Data': df_vencidos.loc[i, 'DATA_STR']} for i in selecionados]
                    try:
                        enviar_email_lote(email_destino, lista)
                        st.success("E-mail enviado com sucesso!")
                    except Exception as e: st.error(f"Erro no envio: {e}")
                else: st.warning("Selecione itens na tela e informe o e-mail.")

        # Renderização dos Cards Vencidos
        cols = st.columns(3)
        for i, (idx, row) in enumerate(df_vencidos.iterrows()):
            with cols[i % 3]:
                st.checkbox("Selecionar", key=f"check_{idx}")
                tipo_classe = "vencido" if row['STATUS'] == "VENCIDO" else "proximo"
                st.markdown(f"""
                    <div class='card-compact {tipo_classe}'>
                        <strong>{row['Descrição'][:40]}</strong><br>
                        <small style='color:#a1b0c0;'>Cód: {row['Código']}<br>
                        Vencimento: <b style='color:#ffffff;'>{row['DATA_STR']}</b></small>
                    </div>
                """, unsafe_allow_html=True)

# --- PÁGINA 3: VISÃO GERAL ---
elif "Visão Geral" in menu:
    st.title("📊 Status Geral do Inventário")
    # Pequeno ajuste para a tabela ficar bonita (remover colunas desnecessárias se quiser)
    df_tabela = df.drop(columns=['DATA_STR'], errors='ignore')
    st.dataframe(df_tabela, use_container_width=True)
