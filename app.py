import streamlit as st
import pandas as pd
import re
from datetime import datetime, time
import smtplib
from email.message import EmailMessage

# --- CONFIGURAÇÃO E CSS (ESTILO COMPACTO) ---
st.set_page_config(page_title="🛡️ Gestão de Calibração", layout="wide")

st.markdown("""
    <style>
    .card-compact { 
        padding: 10px; border-radius: 6px; margin: 4px; 
        border-left: 4px solid #ccc; font-size: 0.85em;
        background-color: #f8f9fa; color: #333;
    }
    .vencido { border-color: #ff6b6b; background-color: #fff5f5; }
    .proximo { border-color: #fcc419; background-color: #fff9db; }
    .stMetric { background: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
    </style>
""", unsafe_allow_html=True)

# URL CSV da Planilha (Certifique-se de que é o link de exportação CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    return pd.read_csv(SHEET_URL)

def processar_dados(df):
    def extrair_data(texto):
        if pd.isna(texto): return None
        match = re.search(r'\d{2}/\d{2}/\d{4}', str(texto))
        return pd.to_datetime(match.group(0), dayfirst=True) if match else None

    # Ajuste dinâmico de colunas (case insensitive)
    df.columns = [c.strip() for c in df.columns]
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), None)
    
    df['DATA_CALIBRACAO'] = df[col_caract].apply(extrair_data) if col_caract else None
    hoje = datetime.now()
    
    if df['DATA_CALIBRACAO'] is not None:
        df['DIAS_RESTANTES'] = (df['DATA_CALIBRACAO'] - hoje).dt.days
        df['STATUS'] = df['DIAS_RESTANTES'].apply(lambda d: "VENCIDO" if d < 0 else ("PRÓXIMO VENCIMENTO" if d <= 30 else "NO PRAZO"))
    return df

def enviar_email_consolidado(destinatarios, df_criticos):
    if df_criticos.empty: return
    
    # Montagem do corpo do e-mail em HTML (Atacado)
    corpo_html = "<h2>Relatório Diário de Calibração</h2><p>Segue a lista de instrumentos em estado crítico:</p>"
    corpo_html += "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    corpo_html += "<tr style='background-color: #f2f2f2;'><th>Código</th><th>Descrição</th><th>Vencimento</th><th>Status</th></tr>"
    
    for _, row in df_criticos.iterrows():
        cor = "red" if row['STATUS'] == "VENCIDO" else "orange"
        corpo_html += f"<tr><td>{row['Código']}</td><td>{row['Descrição']}</td><td>{str(row['DATA_CALIBRACAO'])[:10]}</td><td style='color:{cor}'><b>{row['STATUS']}</b></td></tr>"
    
    corpo_html += "</table><br><p>Sistema de Gestão Automática</p>"

    msg = EmailMessage()
    msg['Subject'] = f"🚨 RELATÓRIO CRÍTICO: {len(df_criticos)} Instrumentos Pendentes"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destinatarios
    msg.add_alternative(corpo_html, subtype='html')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

# --- INICIALIZAÇÃO DE SETTINGS (SESSÃO) ---
if 'config_emails' not in st.session_state: st.session_state.config_emails = "luizclaudio@tempermar.com.br"
if 'config_horario' not in st.session_state: st.session_state.config_horario = time(8, 0)

# --- NAVEGAÇÃO ---
menu = st.sidebar.radio("Navegar:", ["Visão Geral", "⚠️ Vencidos", "⚙️ Configurações"], index=1)
df = processar_dados(carregar_dados())

# --- PÁGINA: CONFIGURAÇÕES ---
if menu == "⚙️ Configurações":
    st.title("⚙️ Configurações do Sistema")
    
    st.subheader("🔔 Envio Automático de Alertas")
    
    with st.container():
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            st.markdown("### 📧 Destinatários")
            novos_emails = st.text_area("Definir e-mail(s) padrão (separe por vírgula):", value=st.session_state.config_emails)
            if st.button("Salvar E-mails"):
                st.session_state.config_emails = novos_emails
                st.success("E-mails atualizados!")
            
            st.info(f"**Atualmente configurados:**\n\n{st.session_state.config_emails}")

        with col_c2:
            st.markdown("### ⏰ Agendamento")
            novo_horario = st.time_input("Definir horário de envio diário:", value=st.session_state.config_horario)
            if st.button("Salvar Horário"):
                st.session_state.config_horario = novo_horario
                st.success("Horário de envio atualizado!")
            
            st.warning(f"**Horário escolhido:** {st.session_state.config_horario.strftime('%H:%M')}")
    
    st.write("---")
    if st.button("🚀 Testar Envio de Relatório Geral Agora"):
        df_criticos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])]
        try:
            enviar_email_consolidado(st.session_state.config_emails, df_criticos)
            st.success("Relatório consolidado enviado para a lista padrão!")
        except Exception as e:
            st.error(f"Falha no teste: {e}")

# --- PÁGINA: VENCIDOS ---
elif menu == "⚠️ Vencidos":
    df_vencidos = df[df['STATUS'].isin(['VENCIDO', 'PRÓXIMO VENCIMENTO'])].copy()
    
    st.title("⚠️ Gestão de Prazos")
    col_kpi1, col_kpi2, col_kpi3 = st.columns([1, 1, 3])
    col_kpi1.metric("Pendentes", len(df_vencidos))
    col_kpi2.metric("Já Vencidos", len(df_vencidos[df_vencidos['STATUS'] == "VENCIDO"]))
    
    if df_vencidos.empty:
        st.success("Parabéns! Todos os instrumentos estão aptos.")
    else:
        st.write("---")
        # Grid Compacto
        cols = st.columns(4) # Aumentado para 4 colunas para ser ainda menor
        if 'selecionados' not in st.session_state: st.session_state.selecionados = []
        
        for i, (idx, row) in enumerate(df_vencidos.iterrows()):
            with cols[i % 4]:
                tipo = "vencido" if row['STATUS'] == "VENCIDO" else "proximo"
                st.markdown(f"""
                    <div class='card-compact {tipo}'>
                        <b>{row['Descrição'][:25]}</b><br>
                        <small>TAG: {row['Código']}</small><br>
                        <span style='color: #d9534f;'>📅 {str(row['DATA_CALIBRACAO'])[:10]}</span>
                    </div>
                """, unsafe_allow_html=True)
                if st.checkbox("Sel.", key=f"sel_{idx}"):
                    if idx not in st.session_state.selecionados: st.session_state.selecionados.append(idx)
                elif idx in st.session_state.selecionados: st.session_state.selecionados.remove(idx)

# --- PÁGINA: VISÃO GERAL ---
elif menu == "Visão Geral":
    st.title("📋 Visão Geral")
    st.dataframe(df, use_container_width=True)
