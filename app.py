import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage
import json
import os
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO E ENGINE VISUAL ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

st.markdown("""
    <style>
    /* Fundo e Sidebar (Azul Marinho) */
    .stApp { background-color: #0a192f; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }
    
    /* 1. Botões Principais no Sidebar (Substituindo o padrão do Streamlit) */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #112240; border: 1px solid #233554; padding: 12px 20px;
        border-radius: 8px; font-weight: bold; transition: 0.3s;
        justify-content: flex-start; text-align: left; color: #b0b4c4; width: 100%;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover { border-color: #ff9800; color: white; }
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #ff9800; color: white; border-color: #ff9800;
        box-shadow: 0 0 10px rgba(255, 152, 0, 0.4);
    }

    /* 2. Sub-menu (Menu Acordeão da Metrologia) */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background-color: transparent; border: none; padding: 8px 10px 8px 45px;
        margin-bottom: 0px; font-weight: normal; transition: 0.2s;
        display: flex; align-items: center; justify-content: flex-start; 
        width: 100%; color: #8a91a8; cursor: pointer; border-left: 4px solid transparent;
        border-radius: 0; box-shadow: none;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { color: white; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        color: #ff9800; border-left: 4px solid #ff9800; background-color: rgba(255, 152, 0, 0.05);
        font-weight: bold; box-shadow: none;
    }

    /* Indicadores Compactos e Cards (Mantidos do original) */
    .kpi-container { padding: 12px; border-radius: 10px; text-align: center; box-shadow: 0 5px 15px rgba(0,0,0,0.3); margin-bottom: 10px; border: 1px solid rgba(255,255,255,0.05); }
    .kpi-value { font-size: 28px; font-weight: 800; line-height: 1.1; margin: 5px 0; }
    .kpi-label { font-size: 12px; font-weight: 600; text-transform: uppercase; opacity: 0.8; }

    .card-instrumento { background-color: #112240; border-radius: 8px; padding: 10px; margin-bottom: 5px; border-left: 5px solid #ccc; opacity: 0.7; transition: all 0.3s ease; }
    .vencido-card { border-left-color: #ff4b4b; background: linear-gradient(to right, #2a1616, #112240); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2a2510, #112240); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #102416, #112240); opacity: 1; }
    .card-selecionado { border: 2px solid #ff9800 !important; box-shadow: 0 0 15px rgba(255, 152, 0, 0.6) !important; transform: scale(1.02); opacity: 1 !important; background: linear-gradient(to right, #332100, #112240) !important; }
    
    .vencido-kpi { color: #ff4b4b; border-bottom: 3px solid #ff4b4b; }
    .proximo-kpi { color: #fcc419; border-bottom: 3px solid #fcc419; }
    .apto-kpi { color: #2ecc71; border-bottom: 3px solid #2ecc71; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE MEMÓRIA E PERSISTÊNCIA ---
def carregar_config():
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f: return json.load(f)
        except: pass
    return {"emails": "luizclaudio@tempermar.com.br"}

def salvar_config(emails):
    with open("config.json", "w") as f: json.dump({"emails": emails}, f)

# --- CARGA E PROCESSAMENTO HIERÁRQUICO COM BLINDAGEM ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
    
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), "Características")
    
    def extrair_vencimento(texto):
        if pd.isna(texto): return None, "SEM DATA"
        match_prox = re.search(r'Data da Próxima Calibração:\s*(\d{2}/\d{2}/\d{4})', str(texto))
        if match_prox:
            dt = pd.to_datetime(match_prox.group(1), dayfirst=True, errors='coerce')
            if pd.notna(dt): return dt, None
            else: return None, "DATA ERRADA"
        
        match_ultima = re.search(r'Data da Última Calibração:\s*(\d{2}/\d{2}/\d{4})', str(texto))
        if match_ultima:
            dt_ult = pd.to_datetime(match_ultima.group(1), dayfirst=True, errors='coerce')
            if pd.notna(dt_ult): return dt_ult + relativedelta(years=1), None
            else: return None, "DATA ERRADA"
        
        return None, "SEM DATA"

    resultados = df[col_caract].apply(extrair_vencimento)
    df['DATA_CALIBRACAO'] = [x[0] for x in resultados]
    df['ALERTA_DATA'] = [x[1] for x in resultados]
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna(df['ALERTA_DATA'])
    hoje = datetime.now()
    
    def classificar(row):
        if row['ALERTA_DATA'] in ["SEM DATA", "DATA ERRADA"]: return "VENCIDO"
        dias = (row['DATA_CALIBRACAO'] - hoje).days
        if dias < 0: return "VENCIDO"
        if dias <= 30: return "PRÓXIMO VENCIMENTO"
        return "APTOS"

    df['STATUS'] = df.apply(classificar, axis=1)
    return df

def enviar_email_consolidado(destinatarios, df_criticos):
    msg = EmailMessage()
    msg['Subject'] = f"🚨 ALERTA: {len(df_criticos)} Instrumentos Selecionados"
    msg['From'] = st.secrets["email"]["email_usuario"]
    msg['To'] = destinatarios
    conteudo = "Relatório de Instrumentos Selecionados para Alerta:\n\n"
    for _, row in df_criticos.iterrows():
        conteudo += f"- {row['Descrição']} (TAG: {row['Código']}) - Vencimento: {row['DATA_STR']}\n"
    msg.set_content(conteudo)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["email"]["email_usuario"], st.secrets["email"]["email_senha"])
        smtp.send_message(msg)

def render_mini_kpi(label, valor, classe):
    st.markdown(f'<div class="kpi-container {classe}"><div class="kpi-label">{label}</div><div class="kpi-value">{valor}</div></div>', unsafe_allow_html=True)

# --- FUNÇÕES DOS FILTROS ---
def limpar_memoria_filtros(sufixo):
    for chave in [f"f_n_{sufixo}", f"f_c_{sufixo}", f"f_d_{sufixo}"]:
        if chave in st.session_state: st.session_state[chave] = ""

def sistema_filtros(key_sufix, mostrar_botao_limpar=False):
    col_titulo, col_botao = st.columns([4, 1])
    with col_titulo: st.markdown("##### 🔍 Filtros de pesquisa")
    with col_botao:
        if mostrar_botao_limpar: st.button("🧹 Limpar Filtros", key=f"btn_limpar_{key_sufix}", on_click=limpar_memoria_filtros, args=(key_sufix,), use_container_width=True)
            
    c_f1, c_f2, c_f3 = st.columns(3)
    f_nome = c_f1.text_input("Por Nome:", key=f"f_n_{key_sufix}")
    f_cod = c_f2.text_input("Por Código:", key=f"f_c_{key_sufix}")
    f_data = c_f3.text_input("Por Data (dd/mm/aaaa):", key=f"f_d_{key_sufix}")
    return f_nome, f_cod, f_data

# --- FUNÇÃO DE POP-UP (DIALOG) ---
@st.dialog("Confirmação de Envio em Lote")
def popup_confirmar_envio(x, y, df_alvo):
    st.write("Será enviado um e-mail com uma relação completa de todos os instrumentos não aptos:")
    st.write(f"**# {x} Próximos de vencer**")
    st.write(f"**# {y} Vencidos / Pendências**")
    
    col1, col2 = st.columns(2)
    if col1.button("Cancelar", use_container_width=True):
        st.rerun()
    if col2.button("OK", use_container_width=True, type="primary"):
        try:
            enviar_email_consolidado(st.session_state.config_emails, df_alvo)
            st.success("E-mail disparado com sucesso para toda a base não apta!")
        except Exception as e:
            st.error(f"Erro no envio: {e}")

# --- INICIALIZAÇÃO DE SESSÃO ---
config_atual = carregar_config()
if 'config_emails' not in st.session_state: st.session_state.config_emails = config_atual["emails"]
if 'selecionados' not in st.session_state: st.session_state.selecionados = []

# Variáveis para controlar o menu acordeão
if 'modulo_ativo' not in st.session_state: st.session_state.modulo_ativo = "METROLOGIA"
if 'pagina_ativa' not in st.session_state: st.session_state.pagina_ativa = "🛠️ Visão Geral"

df = processar_dados(carregar_dados())

# --- NAVEGAÇÃO ESTRUTURADA (ACORDEÃO INTERATIVO) ---
st.sidebar.markdown("<h3 style='color: white;'>SISTEMA DE MONITORAMENTO</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Botão 1: Módulo Metrologia
btn_metro_type = "primary" if st.session_state.modulo_ativo == "METROLOGIA" else "secondary"
if st.sidebar.button("📏 METROLOGIA", use_container_width=True, type=btn_metro_type):
    st.session_state.modulo_ativo = "METROLOGIA"
    if st.session_state.pagina_ativa == "🔍 CONSULTA EC":
        st.session_state.pagina_ativa = "🛠️ Visão Geral" # Abre no default da Metrologia
    st.rerun()

# Se Metrologia estiver ativa, exibe o sub-menu (que "empurra" o botão de baixo)
if st.session_state.modulo_ativo == "METROLOGIA":
    paginas_metro = ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos de vencer", "🚨 VENCIDOS", "⚙️ Ajustes"]
    idx = paginas_metro.index(st.session_state.pagina_ativa) if st.session_state.pagina_ativa in paginas_metro else 0
    escolha_sub = st.sidebar.radio("Sub", paginas_metro, index=idx, label_visibility="collapsed")
    
    if escolha_sub != st.session_state.pagina_ativa:
        st.session_state.pagina_ativa = escolha_sub
        st.rerun()

# Botão 2: Módulo Consulta EC
btn_ec_type = "primary" if st.session_state.modulo_ativo == "CONSULTA EC" else "secondary"
if st.sidebar.button("🔍 CONSULTA EC", use_container_width=True, type=btn_ec_type):
    st.session_state.modulo_ativo = "CONSULTA EC"
    st.session_state.pagina_ativa = "🔍 CONSULTA EC"
    st.rerun()

st.sidebar.markdown("---")
menu = st.session_state.pagina_ativa

# --- PÁGINAS ---
if menu == "🛠️ Visão Geral":
    st.markdown("### 🛠️ Dashboard Geral (Metrologia)")
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi("Aptos", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Atenção", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mini_kpi("Vencidos", len(df[df['STATUS'] == 'VENCIDO']), "vencido-kpi")
    st.dataframe(df, use_container_width=True)

elif menu == "✅ APTOS" or menu == "🔍 CONSULTA EC":
    if menu == "✅ APTOS":
        st.markdown("### ✅ Instrumentos Aptos (Metrologia)")
        sufixo_chave = "aptos"
    else:
        st.markdown("### 🔍 Consulta de Equipamentos Conformes (EC)")
        sufixo_chave = "consulta_ec"
        
    fn, fc, fd = sistema_filtros(sufixo_chave, mostrar_botao_limpar=True)
    df_f = df[df['STATUS'] == 'APTOS']
    if fn: df_f = df_f[df_f['Descrição'].str.contains(fn, case=False, na=False)]
    if fc: df_f = df_f[df_f['Código'].str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].str.contains(fd, case=False, na=False)]
    
    render_mini_kpi("Total Encontrado", len(df_f), "apto-kpi")
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            st.markdown(f"<div class='card-instrumento apto-card'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br><span style='font-size:11px;'>📅 {row['DATA_STR']}</span></div>", unsafe_allow_html=True)

elif menu == "⏳ Próximos de vencer" or menu == "🚨 VENCIDOS":
    status_alvo = "PRÓXIMO VENCIMENTO" if menu == "⏳ Próximos de vencer" else "VENCIDO"
    classe_kpi = "proximo-kpi" if menu == "⏳ Próximos de vencer" else "vencido-kpi"
    classe_card = "proximo-card" if menu == "⏳ Próximos de vencer" else "vencido-card"
    
    st.markdown(f"### {menu}")
    
    fn, fc, fd = sistema_filtros(status_alvo, mostrar_botao_limpar=True)
    
    df_f = df[df['STATUS'] == status_alvo]
    if fn: df_f = df_f[df_f['Descrição'].str.contains(fn, case=False, na=False)]
    if fc: df_f = df_f[df_f['Código'].str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].str.contains(fd, case=False, na=False)]
    
    render_mini_kpi("Quantidade Filtrada", len(df_f), classe_kpi)

    if menu == "🚨 VENCIDOS":
        if st.button("🚨 Enviar alerta agora", use_container_width=True):
            if st.session_state.selecionados:
                try:
                    enviar_email_consolidado(st.session_state.config_emails, df.loc[st.session_state.selecionados])
                    st.success(f"Alerta enviado para {len(st.session_state.selecionados)} itens selecionados!")
                except Exception as e: st.error(f"Erro no envio: {e}")
            else:
                qtd_prox = len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO'])
                qtd_venc = len(df[df['STATUS'] == 'VENCIDO'])
                df_nao_aptos = df[df['STATUS'].isin(['PRÓXIMO VENCIMENTO', 'VENCIDO'])]
                popup_confirmar_envio(qtd_prox, qtd_venc, df_nao_aptos)

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            is_selected = idx in st.session_state.selecionados
            card_class = f"{classe_card} card-selecionado" if is_selected else classe_card
            
            if row['DATA_STR'] == "SEM DATA": data_exibicao = "⚠️ SEM DATA"
            elif row['DATA_STR'] == "DATA ERRADA": data_exibicao = "❌ DATA ERRADA"
            else: data_exibicao = f"📅 {row['DATA_STR']}"
            
            st.markdown(f"<div class='card-instrumento {card_class}'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br><b>{data_exibicao}</b></div>", unsafe_allow_html=True)
            
            if is_selected:
                if st.button("✅ SELECIONADO", key=f"btn_{idx}", use_container_width=True, type="primary"):
                    st.session_state.selecionados.remove(idx)
                    st.rerun()
            else:
                if st.button("⭕ Selecionar", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.selecionados.append(idx)
                    st.rerun()

elif menu == "⚙️ Ajustes":
    st.markdown("### ⚙️ Configurações (Metrologia)")
    st.markdown("#### 📧 E-mails de Alerta")
    novos_emails = st.text_input("Digitar novos e-mails (separados por vírgula):", value="", key="set_emails")
    if st.button("Salvar E-mails"):
        if novos_emails:
            st.session_state.config_emails = novos_emails
            salvar_config(st.session_state.config_emails)
            st.success("E-mails memorizados com sucesso!")
    st.info(f"**E-mails configurados atualmente:** {st.session_state.config_emails}")
