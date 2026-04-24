import streamlit as st
import pandas as pd
import re
from datetime import datetime, time
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E ENGINE VISUAL ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

st.markdown("""
    <style>
    /* Fundo e Sidebar */
    .stApp { background-color: #0b1325; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #121e36; border-right: 1px solid #1f3052; }
    
    /* Menu Lateral Estilizado */
    div[role="radiogroup"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label {
        background-color: #1a2942; border: 1px solid #2a3d66; padding: 12px 15px;
        border-radius: 8px; margin-bottom: 10px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; color: #b0b4c4; cursor: pointer;
    }
    div[role="radiogroup"] > label:hover { border-color: #ff8c00; color: white; }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #ff8c00; color: white; border-color: #ff8c00;
        box-shadow: 0 0 15px rgba(255, 140, 0, 0.4);
    }

    /* Indicadores Modernos e Grandes */
    .kpi-container {
        padding: 30px; border-radius: 20px; text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.4); margin-bottom: 25px;
        transition: 0.4s ease; border: 1px solid rgba(255,255,255,0.1);
    }
    .kpi-container:hover { transform: translateY(-5px); }
    .kpi-value { font-size: 64px; font-weight: 800; line-height: 1; margin: 10px 0; }
    .kpi-label { font-size: 18px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }

    /* Cores dos Estados */
    .vencido-kpi { background: linear-gradient(145deg, #451a1a, #2e1111); color: #ff4b4b; border-bottom: 6px solid #ff4b4b; }
    .proximo-kpi { background: linear-gradient(145deg, #453b1a, #2e2811); color: #fcc419; border-bottom: 6px solid #fcc419; }
    .apto-kpi { background: linear-gradient(145deg, #1a4526, #112e1a); color: #2ecc71; border-bottom: 6px solid #2ecc71; }

    /* Cards de Instrumentos */
    .card-instrumento {
        background-color: #1a2942; border-radius: 12px; padding: 15px;
        margin-bottom: 10px; border: 1px solid #2a3d66; border-left: 6px solid #ccc;
    }
    </style>
""", unsafe_allow_html=True)

# --- CARGA E PROCESSAMENTO ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    return pd.read_csv(SHEET_URL)

def processar_dados(df):
    def extrair_data(texto):
        if pd.isna(texto): return None
        match = re.search(r'\d{2}/\d{2}/\d{4}', str(texto))
        return pd.to_datetime(match.group(0), dayfirst=True) if match else None

    df.columns = [c.strip() for c in df.columns]
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), "Características")
    
    df['DATA_CALIBRACAO'] = df[col_caract].apply(extrair_data)
    hoje = datetime.now()
    
    if df['DATA_CALIBRACAO'] is not None:
        df['DIAS_RESTANTES'] = (df['DATA_CALIBRACAO'] - hoje).dt.days
        df['STATUS'] = df['DIAS_RESTANTES'].apply(lambda d: "VENCIDO" if d < 0 else ("PRÓXIMO VENCIMENTO" if d <= 30 else "APTOS"))
    return df

def render_mega_kpi(label, valor, classe):
    st.markdown(f"""
        <div class="kpi-container {classe}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{valor}</div>
        </div>
    """, unsafe_allow_html=True)

# --- NAVEGAÇÃO ---
st.sidebar.markdown("<h2 style='text-align:center;'>Monitoramento</h2>", unsafe_allow_html=True)
menu = st.sidebar.radio("Navegação:", ["🏠 Visão Geral", "✅ APTOS", "⏳ Próximos de Vencer", "🚨 VENCIDOS", "⚙️ Configurações"], index=0)

df = processar_dados(carregar_dados())

# --- LÓGICA DE PÁGINAS ---
if menu == "🏠 Visão Geral":
    st.title("🏠 Painel de Controle Geral")
    c1, c2, c3 = st.columns(3)
    with c1: render_mega_kpi("Aptos", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mega_kpi("Atenção", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mega_kpi("Vencidos", len(df[df['STATUS'] == 'VENCIDO']), "vencido-kpi")
    st.dataframe(df, use_container_width=True)

elif menu == "✅ APTOS":
    st.title("✅ Instrumentos Aptos")
    df_aptos = df[df['STATUS'] == 'APTOS']
    render_mega_kpi("Total Aptos", len(df_aptos), "apto-kpi")
    st.dataframe(df_aptos, use_container_width=True)

elif menu == "⏳ Próximos de Vencer":
    st.title("⏳ Atenção: Próximos de Vencer")
    df_prox = df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']
    render_mega_kpi("Pendências Próximas", len(df_prox), "proximo-kpi")
    st.write("---")
    st.dataframe(df_prox, use_container_width=True)

elif menu == "🚨 VENCIDOS":
    st.title("🚨 Alerta: Instrumentos Vencidos")
    df_venc = df[df['STATUS'] == 'VENCIDO']
    render_mega_kpi("Críticos Vencidos", len(df_venc), "vencido-kpi")
    st.write("---")
    st.dataframe(df_venc, use_container_width=True)

elif menu == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    
    st.subheader("⏰ Agendamento de Relatório Diário")
    horarios_sugeridos = ["07:00", "08:00", "09:00", "12:00", "18:00", "Outro"]
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        escolha = st.selectbox("Selecione um horário pré-definido:", horarios_sugeridos)
        if escolha == "Outro":
            horario_manual = st.time_input("Ou digite o horário desejado:", value=time(8, 0))
            horario_final = horario_manual
        else:
            horario_final = escolha
            
    with col_h2:
        st.markdown("<div style='margin-top:25px;'></div>", unsafe_allow_html=True)
        if st.button("Salvar Configuração de Horário"):
            st.success(f"Horário definido para: {horario_final}")
