import streamlit as st
import pandas as pd
import re
from datetime import datetime, time
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E ENGINE VISUAL REFINADA ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

st.markdown("""
    <style>
    /* Fundo e Sidebar */
    .stApp { background-color: #0b1325; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #121e36; border-right: 1px solid #1f3052; }
    
    /* Painel de Navegação: Botões com tamanhos iguais e ALINHADOS À ESQUERDA */
    div[role="radiogroup"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label {
        background-color: #1a2942; border: 1px solid #2a3d66; padding: 10px 20px;
        border-radius: 8px; margin-bottom: 8px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: flex-start; /* Alinhado à esquerda */
        width: 100%; min-width: 100%; box-sizing: border-box; 
        color: #b0b4c4; cursor: pointer; text-align: left;
    }
    div[role="radiogroup"] > label:hover { border-color: #ff8c00; color: white; }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #ff8c00; color: white; border-color: #ff8c00;
        box-shadow: 0 0 10px rgba(255, 140, 0, 0.3);
    }

    /* Indicadores Compactos */
    .kpi-container {
        padding: 15px; border-radius: 12px; text-align: center;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3); margin-bottom: 15px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .kpi-value { font-size: 32px; font-weight: 800; line-height: 1.2; margin: 5px 0; }
    .kpi-label { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }

    /* Estilo de Cards */
    .card-instrumento {
        background-color: #1a2942; border-radius: 8px; padding: 12px;
        margin-bottom: 8px; border-left: 5px solid #ccc;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
    }
    .vencido-card { border-left-color: #ff8c00; background: linear-gradient(to right, #2e1111, #1a2942); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2e2811, #1a2942); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #112e1a, #1a2942); }

    /* Cores dos KPIs */
    .vencido-kpi { color: #ff8c00; border-bottom: 4px solid #ff8c00; }
    .proximo-kpi { color: #fcc419; border-bottom: 4px solid #fcc419; }
    .apto-kpi { color: #2ecc71; border-bottom: 4px solid #2ecc71; }
    </style>
""", unsafe_allow_html=True)

# --- CARGA E PROCESSAMENTO ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try:
        return pd.read_csv(SHEET_URL)
    except:
        return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
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

def render_mini_kpi(label, valor, classe):
    st.markdown(f"""
        <div class="kpi-container {classe}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{valor}</div>
        </div>
    """, unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE SESSÃO ---
if 'config_emails' not in st.session_state: st.session_state.config_emails = "luizclaudio@tempermar.com.br"
if 'config_horario' not in st.session_state: st.session_state.config_horario = time(8, 0)

# --- NAVEGAÇÃO ---
st.sidebar.markdown("<h3 style='text-align:left; color: white;'>SISTEMA DE MONITORAMENTO DE INSTRUMENTOS</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Painel de navegação", ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos", "🚨 VENCIDOS", "⚙️ Ajustes"], index=0)

df_raw = carregar_dados()
df = processar_dados(df_raw)

# --- PÁGINAS ---
if menu == "🛠️ Visão Geral":
    st.markdown("### 🛠️ Dashboard Geral")
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi("Instrumentos Aptos", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Próximos de Vencer", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mini_kpi("Vencidos", len(df[df['STATUS'] == 'VENCIDO']), "vencido-kpi")
    st.dataframe(df, use_container_width=True)

elif menu == "✅ APTOS":
    st.markdown("### ✅ Instrumentos Aptos")
    df_aptos = df[df['STATUS'] == 'APTOS']
    render_mini_kpi("Total Aptos", len(df_aptos), "apto-kpi")
    
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_aptos.iterrows()):
        with cols[i % 4]:
            st.markdown(f"""<div class='card-instrumento apto-card'>
                <b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br>
                <span style='font-size:11px;'>📅 {str(row['DATA_CALIBRACAO'])[:10]}</span>
            </div>""", unsafe_allow_html=True)

elif menu == "⏳ Próximos":
    st.markdown("### ⏳ Próximos de Vencer")
    df_prox = df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']
    render_mini_kpi("Pendências Próximas", len(df_prox), "proximo-kpi")
    
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_prox.iterrows()):
        with cols[i % 4]:
            st.markdown(f"""<div class='card-instrumento proximo-card'>
                <b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br>
                <b>Vence em: {str(row['DATA_CALIBRACAO'])[:10]}</b>
            </div>""", unsafe_allow_html=True)

elif menu == "🚨 VENCIDOS":
    st.markdown("### 🚨 Instrumentos Vencidos")
    df_venc = df[df['STATUS'] == 'VENCIDO']
    render_mini_kpi("Críticos Vencidos", len(df_venc), "vencido-kpi")
    
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_venc.iterrows()):
        with cols[i % 4]:
            st.markdown(f"""<div class='card-instrumento vencido-card'>
                <b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br>
                <b style='color:#ff8c00;'>Vencido em: {str(row['DATA_CALIBRACAO'])[:10]}</b>
            </div>""", unsafe_allow_html=True)

elif menu == "⚙️ Ajustes":
    st.markdown("### ⚙️ Configurações de Alerta")
    
    col_e1, col_e2 = st.columns(2)
    with col_e1:
        st.markdown("#### 📧 Definição de E-mails")
        emails_input = st.text_area("E-mails padrão (separados por vírgula):", value=st.session_state.config_emails)
        if st.button("Salvar E-mails"):
            st.session_state.config_emails = emails_input
            st.success("Configuração de e-mails atualizada!")

    with col_e2:
        st.markdown("#### ⏰ Horário de Alerta Diário")
        opcoes_h = ["07:00", "08:00", "09:00", "10:00", "Personalizado"]
        escolha = st.selectbox("Escolha um horário sugerido:", opcoes_h)
        
        if escolha == "Personalizado":
            horario_custom = st.time_input("Defina o horário exato:", value=st.session_state.config_horario)
            if st.button("Aplicar Horário Personalizado"):
                st.session_state.config_horario = horario_custom
                st.success(f"Agendado para às {horario_custom.strftime('%H:%M')}")
        else:
            if st.button(f"Confirmar horário de {escolha}"):
                st.session_state.config_horario = datetime.strptime(escolha, "%H:%M").time()
                st.success(f"Agendado para às {escolha}")
        
        st.info(f"**Horário configurado:** {st.session_state.config_horario.strftime('%H:%M')}")
