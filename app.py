import streamlit as st
import pandas as pd
import re
from datetime import datetime, time
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E MOTOR VISUAL AVANÇADO ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

st.markdown("""
    <style>
    /* Paleta Navy Blue e Laranja */
    .stApp { background-color: #0b1325; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #121e36; border-right: 1px solid #1f3052; }
    
    /* Restauração dos Botões Laterais Avançados (Radio) */
    div[role="radiogroup"] > label > div:first-child { display: none; }
    div[role="radiogroup"] > label {
        background-color: #1a2942; border: 1px solid #2a3d66; padding: 12px 15px;
        border-radius: 8px; margin-bottom: 10px; font-weight: bold; transition: 0.3s;
        display: flex; align-items: center; justify-content: flex-start; cursor: pointer;
        width: 100%; color: #b0b4c4;
    }
    div[role="radiogroup"] > label:hover { border-color: #ff8c00; color: white; }
    div[role="radiogroup"] > label:has(input:checked) {
        background-color: #ff8c00; color: white; border-color: #ff8c00;
        box-shadow: 0 0 12px rgba(255, 140, 0, 0.4);
    }

    /* Cards Compactos e Indicadores Coloridos */
    .card-compact { 
        padding: 12px; border-radius: 8px; margin: 6px 0; 
        border-left: 5px solid #ccc; font-size: 0.85em;
        background-color: #1a2942; color: #ffffff;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.2);
    }
    .vencido { border-color: #ff8c00; background-color: #2e1e12; }
    .proximo { border-color: #fcc419; background-color: #2b2713; }
    
    /* Indicadores KPI Coloridos */
    div[data-testid="metric-container"] {
        background-color: #1a2942; border: 1px solid #2a3d66; 
        padding: 15px; border-radius: 10px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="metric-container"] label { color: #b0b4c4 !important; font-size: 16px !important; }
    div[data-testid="metric-container"] div { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# URL CSV da Planilha
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
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), None)
    
    df['DATA_CALIBRACAO'] = df[col_caract].apply(extrair_data) if col_caract else None
    hoje = datetime.now()
    
    if df['DATA_CALIBRACAO'] is not None:
        df['DIAS_RESTANTES'] = (df['DATA_CALIBRACAO'] - hoje).dt.days
        df['STATUS'] = df['DIAS_RESTANTES'].apply(lambda d: "VENCIDO" if d < 0 else ("PRÓXIMO VENCIMENTO" if d <= 30 else "APTOS"))
    return df

def enviar_email_consolidado(destinatarios, df_criticos):
    if df_criticos.empty: return
    
    corpo_html = "<h2 style='color: #0b1325;'>Relatório de Monitoramento</h2><p>Instrumentos requerendo atenção:</p>"
    corpo_html += "<table border='1' style='border-collapse: collapse; width: 100%; font-family: sans-serif;'>"
    corpo_html += "<tr style='background-color: #1a2942; color: white;'><th>TAG</th><th>Descrição</th><th>Vencimento</th><th>Status</th></tr>"
    
    for _, row in df_criticos.iterrows():
        cor = "#ff8c00" if row['STATUS'] == "VENCIDO" else "#fcc419"
        corpo_html += f"<tr><td>{row['Código']}</td><td>{row['Descrição']}</td><td>{str(row['DATA_CALIBRACAO'])[:10]}</td><td style='color:{cor}; font-weight:bold;'>{row['STATUS']}</td></tr>"
    
    corpo_html += "</table><br><p>Sistema de Monitoramento Automático</p>"

    msg = EmailMessage()
    msg['Subject'] = f"🔔 AVISO: {len(df_criticos)} Instrumentos Pendentes"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destinatarios
    msg.add_alternative(corpo_html, subtype='html')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

# --- INICIALIZAÇÃO DE SESSÃO ---
if 'config_emails' not in st.session_state: st.session_state.config_emails = "luizclaudio@tempermar.com.br"
if 'config_horario' not in st.session_state: st.session_state.config_horario = time(8, 0)
if 'selecionados' not in st.session_state: st.session_state.selecionados = []

# --- NAVEGAÇÃO E CABEÇALHO ---
st.sidebar.markdown("<h2 style='text-align: center; color: white;'>Monitoramento</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navegação:", ["📊 Visão Geral", "⚠️ Gestão de Prazos", "⚙️ Configurações"], index=1)

df = processar_dados(carregar_dados())

# --- PÁGINA: VISÃO GERAL ---
if menu == "📊 Visão Geral":
    st.markdown("<h2>📊 Visão Geral de Instrumentos</h2>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Cadastrado", len(df))
    c2.metric("Instrumentos Aptos", len(df[df['STATUS'] == 'APTOS']))
    c3.metric("Atenção Necessária", len(df[df['STATUS'] != 'APTOS']))
    
    st.write("<br>", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True)

# --- PÁGINA: GESTÃO DE PRAZOS (VENCIDOS) ---
elif menu == "⚠️ Gestão de Prazos":
    st.markdown("<h2>⚠️ Gestão de Prazos e Calibração</h2>", unsafe_allow_html=True)
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])].copy()
    
    col_kpi1, col_kpi2, _ = st.columns([1, 1, 3])
    col_kpi1.metric("Pendentes Totais", len(df_vencidos))
    col_kpi2.metric("Já Vencidos", len(df_vencidos[df_vencidos['STATUS'] == "VENCIDO"]))
    st.write("<br>", unsafe_allow_html=True)
    
    if df_vencidos.empty:
        st.success("Todos os instrumentos estão aptos.")
    else:
        # Ações em lote
        c_acao1, c_acao2 = st.columns([3, 1])
        with c_acao2:
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            if st.button("Disparar Alerta p/ Selecionados", use_container_width=True):
                if st.session_state.selecionados:
                    df_selecionados = df_vencidos.loc[st.session_state.selecionados]
                    try:
                        enviar_email_consolidado(st.session_state.config_emails, df_selecionados)
                        st.success(f"Alerta enviado sobre {len(df_selecionados)} itens!")
                    except Exception as e: st.error(f"Erro: {e}")
                else:
                    st.warning("Selecione ao menos um item abaixo.")

        # Grid de Cards Menores
        cols = st.columns(4) 
        for i, (idx, row) in enumerate(df_vencidos.iterrows()):
            with cols[i % 4]:
                tipo = "vencido" if row['STATUS'] == "VENCIDO" else "proximo"
                st.markdown(f"""
                    <div class='card-compact {tipo}'>
                        <b>{row['Descrição'][:28]}...</b><br>
                        <span style='color: #8c9eff; font-size: 0.9em;'>TAG: {row['Código']}</span><br>
                        <span style='color: #ffffff; font-weight: bold;'>📅 Venc.: {str(row['DATA_CALIBRACAO'])[:10]}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                check = st.checkbox("Incluir no Alerta", key=f"sel_{idx}", value=(idx in st.session_state.selecionados))
                if check and idx not in st.session_state.selecionados: st.session_state.selecionados.append(idx)
                elif not check and idx in st.session_state.selecionados: st.session_state.selecionados.remove(idx)

# --- PÁGINA: CONFIGURAÇÕES ---
elif menu == "⚙️ Configurações":
    st.markdown("<h2>⚙️ Configurações do Sistema</h2>", unsafe_allow_html=True)
    
    st.markdown("### 🔔 Envio Automático de Alertas")
    st.write("Configure os parâmetros para o relatório diário consolidado.")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("<div class='card-compact'>", unsafe_allow_html=True)
        st.markdown("#### 📧 E-mails Destinatários")
        novos_emails = st.text_input("Separe por vírgula:", value=st.session_state.config_emails)
        if st.button("Atualizar E-mails"):
            st.session_state.config_emails = novos_emails
            st.success("E-mails atualizados!")
        st.info(f"**Atuais:** {st.session_state.config_emails}")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_c2:
        st.markdown("<div class='card-compact'>", unsafe_allow_html=True)
        st.markdown("#### ⏰ Horário de Disparo")
        novo_horario = st.time_input("Definir envio diário:", value=st.session_state.config_horario)
        if st.button("Atualizar Horário"):
            st.session_state.config_horario = novo_horario
            st.success("Horário atualizado!")
        st.info(f"**Atual:** {st.session_state.config_horario.strftime('%H:%M')}")
        st.markdown("</div>", unsafe_allow_html=True)
