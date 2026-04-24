import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E ENGINE VISUAL ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

st.markdown("""
    <style>
    /* Fundo e Sidebar */
    .stApp { background-color: #0b1325; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #121e36; border-right: 1px solid #1f3052; }
    
    /* Painel de Navegação: ALINHADO À ESQUERDA */
    div[role="radiogroup"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label {
        background-color: #1a2942; border: 1px solid #2a3d66; padding: 10px 20px;
        border-radius: 8px; margin-bottom: 8px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: flex-start; 
        width: 100%; color: #b0b4c4; cursor: pointer; text-align: left;
    }
    div[role="radiogroup"] > label:hover { border-color: #ff8c00; color: white; }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #ff8c00; color: white; border-color: #ff8c00;
        box-shadow: 0 0 10px rgba(255, 140, 0, 0.3);
    }

    /* Indicadores Compactos */
    .kpi-container {
        padding: 12px; border-radius: 10px; text-align: center;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3); margin-bottom: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    .kpi-value { font-size: 28px; font-weight: 800; line-height: 1.1; margin: 5px 0; }
    .kpi-label { font-size: 12px; font-weight: 600; text-transform: uppercase; opacity: 0.8; }

    /* Cards de Instrumentos */
    .card-instrumento {
        background-color: #1a2942; border-radius: 8px; padding: 10px;
        margin-bottom: 5px; border-left: 5px solid #ccc;
    }
    .vencido-card { border-left-color: #ff8c00; background: linear-gradient(to right, #2e1111, #1a2942); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2e2811, #1a2942); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #112e1a, #1a2942); }

    .vencido-kpi { color: #ff8c00; border-bottom: 3px solid #ff8c00; }
    .proximo-kpi { color: #fcc419; border-bottom: 3px solid #fcc419; }
    .apto-kpi { color: #2ecc71; border-bottom: 3px solid #2ecc71; }
    </style>
""", unsafe_allow_html=True)

# --- CARGA E PROCESSAMENTO ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame()

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
    st.markdown(f'<div class="kpi-container {classe}"><div class="kpi-label">{label}</div><div class="kpi-value">{valor}</div></div>', unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE SESSÃO ---
if 'config_emails' not in st.session_state: st.session_state.config_emails = "luizclaudio@tempermar.com.br"
if 'config_horario' not in st.session_state: st.session_state.config_horario = "08:00"
if 'selecionados' not in st.session_state: st.session_state.selecionados = []

# --- NAVEGAÇÃO ---
st.sidebar.markdown("<h3 style='color: white;'>SISTEMA DE MONITORAMENTO DE INSTRUMENTOS</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Painel de navegação", ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos", "🚨 VENCIDOS", "⚙️ Ajustes"], index=0)

df = processar_dados(carregar_dados())

# --- PÁGINAS ---
if menu == "🛠️ Visão Geral":
    st.markdown("### 🛠️ Visão Geral")
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi("Aptos", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Atenção", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mini_kpi("Vencidos", len(df[df['STATUS'] == 'VENCIDO']), "vencido-kpi")
    st.dataframe(df, use_container_width=True)

elif menu == "✅ APTOS":
    st.markdown("### ✅ Instrumentos Aptos")
    df_aptos = df[df['STATUS'] == 'APTOS']
    render_mini_kpi("Total Aptos", len(df_aptos), "apto-kpi")
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_aptos.iterrows()):
        with cols[i % 4]:
            st.markdown(f"<div class='card-instrumento apto-card'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br><span style='font-size:11px;'>📅 {str(row['DATA_CALIBRACAO'])[:10]}</span></div>", unsafe_allow_html=True)

elif menu == "⏳ Próximos" or menu == "🚨 VENCIDOS":
    status_alvo = "PRÓXIMO VENCIMENTO" if menu == "⏳ Próximos" else "VENCIDO"
    classe_kpi = "proximo-kpi" if menu == "⏳ Próximos" else "vencido-kpi"
    classe_card = "proximo-card" if menu == "⏳ Próximos" else "vencido-card"
    
    st.markdown(f"### {menu}")
    df_f = df[df['STATUS'] == status_alvo]
    render_mini_kpi("Quantidade", len(df_f), classe_kpi)

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            st.markdown(f"<div class='card-instrumento {classe_card}'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br><b>📅 {str(row['DATA_CALIBRACAO'])[:10]}</b></div>", unsafe_allow_html=True)
            check = st.checkbox("Selecionar", key=f"sel_{idx}", value=(idx in st.session_state.selecionados))
            if check and idx not in st.session_state.selecionados: st.session_state.selecionados.append(idx)
            elif not check and idx in st.session_state.selecionados: st.session_state.selecionados.remove(idx)

elif menu == "⚙️ Ajustes":
    st.markdown("### ⚙️ Configurações")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.markdown("#### 📧 E-mails de Alerta")
        # Campo inicia vazio conforme solicitado
        novos_emails = st.text_input("Digitar novos e-mails (separados por vírgula):", value="")
        if st.button("Salvar E-mails"):
            if novos_emails:
                st.session_state.config_emails = novos_emails
                st.success("E-mails atualizados!")
        st.info(f"**E-mails configurados:** {st.session_state.config_emails}")

    with col_a2:
        st.markdown("#### ⏰ Horário do Alerta (HH:MM)")
        # Campo de texto livre que interpreta o horário
        horario_digitado = st.text_input("Digitar novo horário (ex: 14:30):", value="")
        if st.button("Salvar Horário"):
            if re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', horario_digitado):
                st.session_state.config_horario = horario_digitado
                st.success(f"Horário {horario_digitado} salvo com sucesso!")
            else:
                st.error("Formato inválido. Use HH:MM (ex: 08:00 ou 15:30).")
        st.warning(f"**Horário configurado:** {st.session_state.config_horario}")
