import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage
import json
import os
from dateutil.relativedelta import relativedelta
import base64

# --- CONFIGURAÇÃO E ENGINE VISUAL ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

# --- GERENCIAMENTO DE CONFIGURAÇÕES (E-MAILS E CERTIFICADOS) ---
def carregar_emails():
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                return json.load(f).get("emails", ["luizclaudio@tempermar.com.br"])
        except: pass
    return ["luizclaudio@tempermar.com.br"]

def salvar_config(emails):
    with open("config.json", "w") as f: json.dump({"emails": emails}, f)

def carregar_analises_certificados():
    if os.path.exists("certificados_analise.json"):
        try:
            with open("certificados_analise.json", "r", encoding="utf-8") as f:
                dados = json.load(f)
                if isinstance(dados, dict):
                    return dados
        except: pass
    return {}

def salvar_analises_certificados(dados):
    with open("certificados_analise.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

# --- INICIALIZAÇÃO DE MEMÓRIA ---
if 'pagina_ativa' not in st.session_state: st.session_state.pagina_ativa = "📊 VISÃO GERAL"
if 'sub_nc_ativa' not in st.session_state: st.session_state.sub_nc_ativa = "INSTRUMENTOS"
if 'sub_mapa_ativa' not in st.session_state: st.session_state.sub_mapa_ativa = "MAPA ANALÍTICO"
if 'config_emails' not in st.session_state: st.session_state.config_emails = carregar_emails()
if 'analises_certificados' not in st.session_state: st.session_state.analises_certificados = carregar_analises_certificados()

# --- MOTOR CSS GLOBAL E SIDEBAR (OPÇÃO 2: BARRA TÁTICA + CONTÊINER ESCURO) ---
st.markdown("""
    <style>
    .stApp { background-color: #0a192f; color: #e0e0e0; }
    
    /* SIDEBAR CONTAINER */
    section[data-testid="stSidebar"] {
        background-color: #121212;
        border-right: 1px solid #222222;
    }

    /* BOTÕES PADRÃO DA SIDEBAR (ITENS INATIVOS E AÇÕES) */
    section[data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        padding: 10px 14px !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        color: #9aa3b8 !important;
        width: 100% !important;
        justify-content: flex-start !important;
        text-align: left !important;
        letter-spacing: 0.4px !important;
        box-shadow: none !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background-color: #1E2130 !important;
        color: #ffffff !important;
        border-color: #2d3348 !important;
    }

    /* ITEM ATIVO NA SIDEBAR (CONTÊINER ESCURO + BARRA TÁTICA LATERAL) */
    section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {
        background-color: #1E2130 !important;
        color: #ffffff !important;
        border: 1px solid #2e344b !important;
        border-left: 4px solid #ff4b4b !important;
        border-radius: 4px 8px 8px 4px !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35) !important;
    }
    section[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"]:hover {
        background-color: #24283a !important;
        color: #ffffff !important;
    }

    /* BOTÃO DE ALERTA NO RODAPÉ */
    section[data-testid="stSidebar"] .alerta-sidebar-wrap .stButton > button {
        background: linear-gradient(135deg, #ff4b4b, #d63031) !important;
        color: #ffffff !important;
        border: none !important;
        border-left: none !important;
        border-radius: 8px !important;
        justify-content: center !important;
        text-align: center !important;
        text-transform: uppercase !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 14px rgba(255, 75, 75, 0.35) !important;
    }
    section[data-testid="stSidebar"] .alerta-sidebar-wrap .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(255, 75, 75, 0.55) !important;
    }

    /* BOTÃO ATUALIZAR PLANILHA NO RODAPÉ */
    section[data-testid="stSidebar"] .atualizar-sidebar-wrap .stButton > button {
        background-color: #181a22 !important;
        border: 1px solid #2c3142 !important;
        border-radius: 8px !important;
        justify-content: center !important;
        text-align: center !important;
        color: #c5cde0 !important;
    }
    section[data-testid="stSidebar"] .atualizar-sidebar-wrap .stButton > button:hover {
        border-color: #3498DB !important;
        color: #ffffff !important;
        background-color: #1E2130 !important;
    }

    /* GLASSMORPHISM NOS KPIS */
    .kpi-container { 
        padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 15px; 
        border: 1px solid rgba(255,255,255,0.08); 
        background: rgba(17, 34, 64, 0.6); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2); transition: transform 0.3s ease;
    }
    .kpi-container:hover { transform: translateY(-3px); }
    .kpi-value { font-size: 28px; font-weight: 900; line-height: 1.1; margin: 5px 0; }
    .kpi-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.8; }
    
    .vencido-kpi { color: #ff4b4b; border-bottom: 3px solid #ff4b4b; }
    .proximo-kpi { color: #fcc419; border-bottom: 3px solid #fcc419; }
    .apto-kpi { color: #2ecc71; border-bottom: 3px solid #2ecc71; }
    .mapa-kpi { color: #3498DB; border-bottom: 3px solid #3498DB; }

    /* CARDS EM GRID PERFEITO E EFEITO HOVER */
    .card-instrumento { 
        display: flex; flex-direction: column; justify-content: space-between; min-height: 125px;
        width: 100%; background-color: #112240; border-radius: 10px; 
        padding: 22px 15px 15px 15px; margin-bottom: 15px; margin-top: 5px; 
        border-left: 5px solid #ccc; transition: all 0.3s ease; box-sizing: border-box;
        position: relative; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .card-instrumento:hover { transform: translateY(-5px); box-shadow: 0 12px 25px rgba(0,0,0,0.4); }
    
    .badge-status {
        position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
        padding: 3px 10px; border-radius: 4px; border: 1px dashed; font-size: 10px; 
        font-weight: 800; letter-spacing: 0.5px; background-color: #0a192f; text-transform: uppercase;
        box-shadow: 0 3px 8px rgba(0,0,0,0.4);
    }
    .badge-vencido { color: #ff4b4b; border-color: #ff4b4b; }
    .badge-proximo { color: #F1C40F; border-color: #F1C40F; }
    .badge-apto { color: #2ecc71; border-color: #2ecc71; }
    .badge-alerta { color: #8E44AD; border-color: #8E44AD; }
    .badge-dispensa { color: #3498DB; border-color: #3498DB; }

    .vencido-card { border-left-color: #ff4b4b; background: linear-gradient(to right, #2a1616, #112240); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2a2510, #112240); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #102416, #112240); }
    </style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
    
    col_caract = "Características" 
    
    if col_caract not in df.columns:
        st.error(f"🚨 ERRO DE LEITURA: A coluna '{col_caract}' não foi encontrada! Verifique o cabeçalho no Sheets.")
        df[col_caract] = "N/I"
        
    def extrair_vencimento(texto):
        if pd.isna(texto) or str(texto).strip().upper() in ["NAN", "N/I", "NONE", ""]: 
            return None, "SEM DATA", None
            
        t_ajustado = str(texto).lower()
        t_ajustado = re.sub(r'[áàâãä]', 'a', t_ajustado)
        t_ajustado = re.sub(r'[éèêë]', 'e', t_ajustado)
        t_ajustado = re.sub(r'[íìîï]', 'i', t_ajustado)
        t_ajustado = re.sub(r'[óòôõö]', 'o', t_ajustado)
        t_ajustado = re.sub(r'[úùûü]', 'u', t_ajustado)
        t_ajustado = re.sub(r'[ç]', 'c', t_ajustado)
        t_ajustado = t_ajustado.replace("：", ":").replace(" ;", ":").replace(";", ":")
        t_ajustado = " ".join(t_ajustado.split())
        
        padrao_dispensa = r'd[ei]spensa\s+(?:de\s+)?calibracao'
        if re.search(padrao_dispensa, t_ajustado): return None, "DISPENSADO", None
        
        padrao_prox = r'data\s+(?:da\s+)?proxima\s+calibracao\s*:?\s*(\d{2}/\d{2}/\d{2,4})'
        match_prox = re.search(padrao_prox, t_ajustado)
        if match_prox:
            dt = pd.to_datetime(match_prox.group(1), dayfirst=True, errors='coerce')
            if pd.notna(dt):
                dt_cal_estimada = dt - relativedelta(years=1)
                return dt, None, dt_cal_estimada
            return None, "DATA ERRADA", None
            
        padrao_ult = r'data\s+(?:da\s+)?ultima\s+calibracao\s*:?\s*(\d{2}/\d{2}/\d{2,4})'
        match_ultima = re.search(padrao_ult, t_ajustado)
        if match_ultima:
            dt_ult = pd.to_datetime(match_ultima.group(1), dayfirst=True, errors='coerce')
            if pd.notna(dt_ult):
                return dt_ult + relativedelta(years=1), None, dt_ult
            return None, "DATA ERRADA", None
            
        return None, "SEM DATA", None

    resultados = df[col_caract].apply(extrair_vencimento)
    df['DATA_CALIBRACAO'] = pd.to_datetime([x[0] for x in resultados], errors='coerce')
    df['ALERTA_DATA'] = [x[1] for x in resultados]
    df['DATA_ULT_CALIBRACAO'] = pd.to_datetime([x[2] for x in resultados], errors='coerce')
    df['MES_CALIBRACAO'] = df['DATA_ULT_CALIBRACAO'].dt.strftime('%m/%Y').fillna("")
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna(df['ALERTA_DATA'])
    hoje = datetime.now()
    
    def classificar(row):
        alerta = row.get('ALERTA_DATA', 'SEM DATA')
        if alerta == "DISPENSADO": return "APTOS"
        if alerta in ["SEM DATA", "DATA ERRADA"]: return "VENCIDO"
        if pd.isna(row.get('DATA_CALIBRACAO')): return "APTOS" 
        
        dias = (row.get('DATA_CALIBRACAO') - hoje).days
        return "VENCIDO" if dias < 0 else ("PRÓXIMO VENCIMENTO" if dias <= 30 else "APTOS")

    df['STATUS'] = df.apply(classificar, axis=1)
    return df

def enviar_email_consolidado(destinatarios, df_criticos):
    msg = EmailMessage()
    msg['Subject'] = f"🚨 ALERTA TEMPERMAR: {len(df_criticos)} Equipamentos requerem atenção"
    email_config = st.secrets.get("email", {})
    email_usuario = email_config.get("email_usuario", "nao_configurado@sistema.com")
    email_senha = email_config.get("email_senha", "")
    
    msg['From'] = email_usuario
    msg['To'] = ", ".join(destinatarios)
    conteudo = "Relatório de Itens para Alerta de Calibração:\n\n"
    
    for _, row in df_criticos.iterrows():
        desc = row.get('Descrição', 'N/I')
        cod = row.get('Código', 'N/I')
        data_str = row.get('DATA_STR', 'N/I')
        conteudo += f"- {desc} ({cod}) - Vencimento: {data_str}\n"
        
    msg.set_content(conteudo)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_usuario, email_senha)
        smtp.send_message(msg)

def render_mini_kpi(label, valor, classe):
    st.markdown(f'<div class="kpi-container {classe}"><div class="kpi-value">{valor}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

def sistema_filtros():
    st.markdown("##### 🔍 Filtros de pesquisa")
    c1, c2, c3 = st.columns(3)
    return c1.text_input("Nome:"), c2.text_input("Código:"), c3.text_input("Data:")

@st.dialog("Confirmação de Envio")
def popup_confirmar_envio(qtd, df_alvo):
    st.write(f"Será enviado um e-mail com a relação dos **{qtd} equipamentos** listados na tela para os contatos cadastrados em Configurações.")
    if st.button("Confirmar Envio", use_container_width=True, type="primary"):
        try:
            enviar_email_consolidado(st.session_state.config_emails, df_alvo)
            st.success("Enviado com sucesso!")
        except Exception as e: st.error(f"Erro: {e}")

# --- NAVEGAÇÃO LATERAL (OPÇÃO 2: BOTÕES + BARRA TÁTICA LATERAL) ---
df = processar_dados(carregar_dados())

col_familia = next((c for c in df.columns if 'FAMÍLIA' in c.upper() or 'FAMILIA' in c.upper()), "FAMÍLIA DE PRODUTO")
if col_familia not in df.columns: df[col_familia] = "INSTRUMENTOS"

def renderizar_logo_sidebar():
    caminho_imagem = "icone.png"
    try:
        with open(caminho_imagem, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        html_logo = f"""
        <div style="display: flex; align-items: center; margin-bottom: 22px; margin-top: -10px;">
            <img src="data:image/png;base64,{encoded_string}" style="width: 35px; margin-right: 12px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5));">
            <h2 style="color: #ffffff; margin: 0; font-weight: 900; letter-spacing: 1px; font-size: 20px;">TEMPERMAR</h2>
        </div>
        """
        st.sidebar.markdown(html_logo, unsafe_allow_html=True)
    except:
        st.sidebar.markdown("<h2 style='color: white; font-weight: 900; margin-bottom: 20px;'>TEMPERMAR</h2>", unsafe_allow_html=True)

renderizar_logo_sidebar()

st.sidebar.markdown("<h4 style='color: #e0e6f0; font-weight: 700; margin-bottom: 18px; font-size: 15px;'>Olá, Luiz Cláudio</h4>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='display: flex; align-items: center; color: #ffffff; font-size: 13px; font-weight: 800; letter-spacing: 1.2px;'><span style='font-size: 16px; margin-right: 8px;'>🖥️</span> NAVEGAÇÃO</div>", unsafe_allow_html=True)
st.sidebar.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin-top: 8px; margin-bottom: 14px;'>", unsafe_allow_html=True)

paginas_metro = [
    "📊 VISÃO GERAL",
    "✅ EQUIPAMENTOS APTOS",
    "⏳ PRÓXIMOS DO VENCIMENTO",
    "🚨 NECESSÁRIO CALIBRAÇÃO",
    "🗺️ MAPA DE CALIBRAÇÃO",
    "⚙️ CONFIGURAÇÕES"
]

for idx_p, pag in enumerate(paginas_metro):
    ativo = (st.session_state.pagina_ativa == pag)
    if st.sidebar.button(pag, key=f"nav_main_{idx_p}", use_container_width=True, type="primary" if ativo else "secondary"):
        st.session_state.pagina_ativa = pag
        st.rerun()

    # SUB-OPÇÕES DE NECESSÁRIO CALIBRAÇÃO
    if pag == "🚨 NECESSÁRIO CALIBRAÇÃO" and ativo:
        st.sidebar.markdown("<div style='margin-left: 14px; padding-left: 10px; border-left: 2px solid #2d3348; margin-top: 4px; margin-bottom: 8px;'>", unsafe_allow_html=True)
        for idx_s, sub_op in enumerate(["INSTRUMENTOS", "EQUIPAMENTOS DE IÇAMENTO"]):
            sub_ativo = (st.session_state.sub_nc_ativa == sub_op)
            if st.sidebar.button(f"↳ {sub_op}", key=f"sub_nc_btn_{idx_s}", use_container_width=True, type="primary" if sub_ativo else "secondary"):
                st.session_state.sub_nc_ativa = sub_op
                st.rerun()
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

    # SUB-OPÇÕES DE MAPA DE CALIBRAÇÃO
    if pag == "🗺️ MAPA DE CALIBRAÇÃO" and ativo:
        st.sidebar.markdown("<div style='margin-left: 14px; padding-left: 10px; border-left: 2px solid #2d3348; margin-top: 4px; margin-bottom: 8px;'>", unsafe_allow_html=True)
        for idx_m, sub_m in enumerate(["MAPA ANALÍTICO", "MAPA GERAL"]):
            sub_m_ativo = (st.session_state.sub_mapa_ativa == sub_m)
            if st.sidebar.button(f"↳ {sub_m}", key=f"sub_mapa_btn_{idx_m}", use_container_width=True, type="primary" if sub_m_ativo else "secondary"):
                st.session_state.sub_mapa_ativa = sub_m
                st.rerun()
        st.sidebar.markdown("</div>", unsafe_allow_html=True)

menu = st.session_state.pagina_ativa
sub_nc = st.session_state.sub_nc_ativa
visao_mapa = st.session_state.sub_mapa_ativa

# ESPAÇAMENTO E BOTÕES DO RODAPÉ
st.sidebar.markdown("<br><br>", unsafe_allow_html=True)

if menu == "🚨 NECESSÁRIO CALIBRAÇÃO":
    st.sidebar.markdown("<div class='alerta-sidebar-wrap'>", unsafe_allow_html=True)
    disparar = st.sidebar.button("🚨 Disparar Alerta", key="btn_disparar_rodape", use_container_width=True)
    st.sidebar.markdown("</div><div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

st.sidebar.markdown("<div class='atualizar-sidebar-wrap'>", unsafe_allow_html=True)
if st.sidebar.button("🔄 Atualizar Planilha", key="btn_atualizar_rodape", use_container_width=True):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown("</div>", unsafe_allow_html=True)

# --- RENDERIZAÇÃO DAS PÁGINAS PRINCIPAIS ---

st.markdown("""
    <h1 style='text-align: center; color: #ffffff; font-size: 2.2rem; font-weight: 900; 
               margin-bottom: 5px; margin-top: -20px; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 4px 10px rgba(0,0,0,0.5);'>
        SISTEMA DE APOIO A METROLOGIA
    </h1>
    <hr style='border: 0; border-top: 1px solid #233554; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

if menu == "📊 VISÃO GERAL":
    st.markdown("### 📊 Dashboard Geral")
    df_vencidos = df[df['STATUS'] == 'VENCIDO']
    mask_icamento = df_vencidos[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)
    qtd_instrumentos = len(df_vencidos[~mask_icamento])
    qtd_icamento = len(df_vencidos[mask_icamento])

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_mini_kpi("Aptos / Dispensados", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Atenção (30 dias)", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mini_kpi("Calibração. Instrumentos", qtd_instrumentos, "vencido-kpi")
    with c4: render_mini_kpi("Calibração. Içamento", qtd_icamento, "vencido-kpi")
    
    st.dataframe(df.drop(columns=['DATA_CALIBRACAO', 'DATA_ULT_CALIBRACAO'], errors='ignore'), use_container_width=True)
    
    with st.expander("🔍 Auditoria de Segurança: Verificar possíveis falsos negativos"):
        possiveis_erros = df[(df['STATUS'] == 'VENCIDO') & (df['ALERTA_DATA'] == 'SEM DATA') & (df["Características"].astype(str).str.contains(r'\d{2}/\d{2}', na=False))]
        if not possiveis_erros.empty:
            st.warning(f"Atenção: Detectamos {len(possiveis_erros)} itens sem data calculada, mas com menção a datas no texto:")
            st.dataframe(possiveis_erros[['Código', 'Descrição', "Características"]], use_container_width=True)
        else:
            st.success("🔥 Varredura concluída: Zero falsos negativos na base!")

elif menu == "✅ EQUIPAMENTOS APTOS":
    st.markdown("### ✅ Equipamentos Aptos")
    df_f = df[df['STATUS'] == 'APTOS']
    
    c1, _, _ = st.columns(3)
    with c1: render_mini_kpi("Total Equipamentos Aptos", len(df_f), "apto-kpi")
    st.markdown("---")
    
    fn, fc, fd = sistema_filtros()
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]
    
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            desc = str(row.get('Descrição', 'N/I'))
            cod = str(row.get('Código', 'N/I'))
            data_str = str(row.get('DATA_STR', 'N/I'))
            
            if data_str == "DISPENSADO":
                badge_class = "badge-dispensa"
                badge_text = "DISPENSADO"
                data_exibicao = "♾️ ISENTO DE CALIBRAÇÃO"
            else:
                badge_class = "badge-apto"
                badge_text = "REGULAR"
                data_exibicao = f"📅 {data_str}"
            
            html_card = f"""
            <div class='card-instrumento apto-card'>
                <div class='badge-status {badge_class}'>{badge_text}</div>
                <div style="flex-grow: 1;">
                    <b style="font-size: 14px; line-height: 1.2;">{desc}</b><br>
                    <small style="color: #a0aabf;">{cod}</small>
                </div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 12px; font-weight: 600; text-align: center;">{data_exibicao}</div>
            </div>"""
            st.markdown(html_card, unsafe_allow_html=True)

elif menu == "⏳ PRÓXIMOS DO VENCIMENTO":
    st.markdown("### ⏳ Próximos do Vencimento")
    df_f = df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']
    
    c1, _, _ = st.columns(3)
    with c1: render_mini_kpi("Equipamentos em Atenção", len(df_f), "proximo-kpi")
    st.markdown("---")
    
    fn, fc, fd = sistema_filtros()
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            desc = str(row.get('Descrição', 'N/I'))
            cod = str(row.get('Código', 'N/I'))
            data_str = str(row.get('DATA_STR', 'N/I'))
            
            html_card = f"""
            <div class='card-instrumento proximo-card'>
                <div class='badge-status badge-proximo'>ATENÇÃO</div>
                <div style="flex-grow: 1;">
                    <b style="font-size: 14px; line-height: 1.2;">{desc}</b><br>
                    <small style="color: #a0aabf;">{cod}</small>
                </div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 13px; font-weight: 700; text-align: center; color: #F1C40F;">📅 {data_str}</div>
            </div>"""
            st.markdown(html_card, unsafe_allow_html=True)

elif menu == "🚨 NECESSÁRIO CALIBRAÇÃO":
    st.markdown(f"### 🚨 Necessário Calibração › {sub_nc}")
    
    df_f = df[df['STATUS'] == 'VENCIDO']
    if sub_nc == "INSTRUMENTOS": df_f = df_f[~df_f[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)]
    else: df_f = df_f[df_f[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)]
        
    qtd_total = len(df_f)
    qtd_sem_data = len(df_f[df_f['ALERTA_DATA'].isin(['SEM DATA', 'DATA ERRADA'])])
    
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi(f"Total na Lista", qtd_total, "vencido-kpi")
    with c2: render_mini_kpi("Falta Cadastrar Data", qtd_sem_data, "vencido-kpi")
    with c3: render_mini_kpi("Vencimento Ultrapassado", qtd_total - qtd_sem_data, "vencido-kpi")
    st.markdown("---")
    
    fn, fc, fd = sistema_filtros()
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]

    if 'disparar' in locals() and disparar:
        if not df_f.empty: popup_confirmar_envio(len(df_f), df_f)
        else: st.warning("A lista atual está vazia. Não há nada para enviar.")

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            desc = str(row.get('Descrição', 'N/I'))
            cod = str(row.get('Código', 'N/I'))
            data_str = str(row.get('DATA_STR', 'N/I'))
            
            if data_str == "SEM DATA": 
                data_exibicao = "⚠️ DADO FALTANTE"
                badge_class = "badge-alerta"
                badge_text = "INCOMPLETO"
                cor_data = "#8E44AD"
            elif data_str == "DATA ERRADA": 
                data_exibicao = "❌ ERRO DE DIGITAÇÃO"
                badge_class = "badge-alerta"
                badge_text = "REVISAR DATA"
                cor_data = "#8E44AD"
            else: 
                data_exibicao = f"📅 Vencido em: {data_str}"
                badge_class = "badge-vencido"
                badge_text = "URGENTE"
                cor_data = "#ff4b4b"

            html_card = f"""
            <div class='card-instrumento vencido-card'>
                <div class='badge-status {badge_class}'>{badge_text}</div>
                <div style="flex-grow: 1;">
                    <b style="font-size: 14px; line-height: 1.2;">{desc}</b><br>
                    <small style="color: #a0aabf;">{cod}</small>
                </div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 12px; font-weight: 700; text-align: center; color: {cor_data};">{data_exibicao}</div>
            </div>"""
            st.markdown(html_card, unsafe_allow_html=True)

elif menu == "🗺️ MAPA DE CALIBRAÇÃO":
    df_inst = df[
        (~df[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)) &
        (df['MES_CALIBRACAO'] != "")
    ].copy()

    def obter_registro_cert(row):
        cod_item = str(row.get('Código', '')).strip()
        data_cal_str = row['DATA_ULT_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row.get('DATA_ULT_CALIBRACAO')) else ""
        chave_item = f"{cod_item}|{data_cal_str}" if cod_item else str(row.name)
        reg = st.session_state.analises_certificados.get(chave_item, {})
        return chave_item, {
            "status": reg.get("status", "Pendente"),
            "observacao": reg.get("observacao", ""),
            "atualizado_em": reg.get("atualizado_em", "-")
        }

    chaves_e_regs = [obter_registro_cert(r) for _, r in df_inst.iterrows()]
    df_inst['_CHAVE_CERT'] = [x[0] for x in chaves_e_regs]
    df_inst['_STATUS_CERT'] = [x[1]['status'] for x in chaves_e_regs]
    df_inst['_OBS_CERT'] = [x[1]['observacao'] for x in chaves_e_regs]
    df_inst['_ATUALIZADO_CERT'] = [x[1]['atualizado_em'] for x in chaves_e_regs]

    if visao_mapa == "MAPA GERAL":
        st.markdown("### 🗺️ Mapa de Calibração › Mapa Geral")
        st.write("Panorama consolidado dos instrumentos de medição com calibração mapeada na base.")

        total_mapeados = len(df_inst)
        total_aprovados = len(df_inst[df_inst['_STATUS_CERT'] == "Aprovado"])
        total_pendentes = len(df_inst[df_inst['_STATUS_CERT'] == "Pendente"])
        total_reprovados = len(df_inst[df_inst['_STATUS_CERT'] == "Reprovado"])

        g1, g2, g3, g4 = st.columns(4)
        with g1: render_mini_kpi("Total Mapeados", total_mapeados, "mapa-kpi")
        with g2: render_mini_kpi("Certificados Aprovados", total_aprovados, "apto-kpi")
        with g3: render_mini_kpi("Pendentes de Análise", total_pendentes, "proximo-kpi")
        with g4: render_mini_kpi("Certificados Reprovados", total_reprovados, "vencido-kpi")

        st.markdown("---")
        st.markdown("#### 📆 Consolidado por Mês de Calibração")

        if df_inst.empty:
            st.info("Nenhum instrumento com data de calibração identificada na base.")
        else:
            resumo_meses = (
                df_inst.groupby('MES_CALIBRACAO')['_STATUS_CERT']
                .value_counts()
                .unstack(fill_value=0)
                .reset_index()
            )
            for col_st in ["Pendente", "Aprovado", "Reprovado"]:
                if col_st not in resumo_meses.columns:
                    resumo_meses[col_st] = 0

            resumo_meses["Total"] = resumo_meses["Pendente"] + resumo_meses["Aprovado"] + resumo_meses["Reprovado"]
            resumo_meses = resumo_meses.sort_values(
                by="MES_CALIBRACAO",
                key=lambda s: s.map(lambda m: datetime.strptime(m, "%m/%Y")),
                ascending=False
            )
            resumo_meses = resumo_meses.rename(columns={
                "MES_CALIBRACAO": "Mês Calibração",
                "Pendente": "Pendentes",
                "Aprovado": "Aprovados",
                "Reprovado": "Reprovados"
            })[["Mês Calibração", "Total", "Pendentes", "Aprovados", "Reprovados"]]

            st.dataframe(resumo_meses, use_container_width=True, hide_index=True)

            st.markdown("#### 📋 Relação Geral dos Instrumentos Mapeados")
            col_desc = 'Descrição' if 'Descrição' in df_inst.columns else ('DESCRICAO' if 'DESCRICAO' in df_inst.columns else None)
            col_cod = 'Código' if 'Código' in df_inst.columns else ('CODIGO' if 'CODIGO' in df_inst.columns else None)

            df_tabela_geral = pd.DataFrame({
                "Código": df_inst[col_cod] if col_cod else "N/I",
                "Descrição": df_inst[col_desc] if col_desc else "N/I",
                "Mês Calibração": df_inst["MES_CALIBRACAO"],
                "Data Calibração": df_inst["DATA_ULT_CALIBRACAO"].dt.strftime('%d/%m/%Y').fillna("N/I"),
                "Vencimento": df_inst["DATA_STR"],
                "Status Análise": df_inst["_STATUS_CERT"],
                "Observação / Certificado": df_inst["_OBS_CERT"]
            })
            st.dataframe(df_tabela_geral, use_container_width=True, hide_index=True)

    else:
        st.markdown("### 🗺️ Mapa de Calibração › Mapa Analítico")
        st.write("Selecione o mês da calibração para acompanhar e gerenciar a análise crítica dos certificados emitidos.")

        mes_atual_str = datetime.now().strftime('%m/%Y')
        meses_base = df_inst['MES_CALIBRACAO'].unique().tolist()
        if mes_atual_str not in meses_base:
            meses_base.append(mes_atual_str)

        meses_ordenados = sorted(
            meses_base,
            key=lambda m: datetime.strptime(m, "%m/%Y"),
            reverse=True
        )

        c_mes, c_status, c_busca = st.columns([2, 2, 3])
        with c_mes:
            mes_selecionado = st.selectbox("📅 Mês da Calibração:", meses_ordenados, index=0, key="mapa_mes_sel")
        with c_status:
            filtro_status_cert = st.selectbox(
                "📌 Status da Análise:",
                ["Todos", "Pendente", "Aprovado", "Reprovado"],
                key="mapa_status_sel"
            )
        with c_busca:
            busca_cert = st.text_input("🔎 Buscar por Nome ou Código:", key="mapa_busca_txt")

        df_mes = df_inst[df_inst['MES_CALIBRACAO'] == mes_selecionado].copy()

        qtd_mes_total = len(df_mes)
        qtd_pendente = len(df_mes[df_mes['_STATUS_CERT'] == "Pendente"])
        qtd_aprovado = len(df_mes[df_mes['_STATUS_CERT'] == "Aprovado"])
        qtd_reprovado = len(df_mes[df_mes['_STATUS_CERT'] == "Reprovado"])

        k1, k2, k3, k4 = st.columns(4)
        with k1: render_mini_kpi(f"Calibrados em {mes_selecionado}", qtd_mes_total, "mapa-kpi")
        with k2: render_mini_kpi("Pendentes", qtd_pendente, "proximo-kpi")
        with k3: render_mini_kpi("Aprovados", qtd_aprovado, "apto-kpi")
        with k4: render_mini_kpi("Reprovados", qtd_reprovado, "vencido-kpi")

        st.markdown("---")

        df_view = df_mes.copy()
        if filtro_status_cert != "Todos":
            df_view = df_view[df_view['_STATUS_CERT'] == filtro_status_cert]

        col_desc = 'Descrição' if 'Descrição' in df_view.columns else ('DESCRICAO' if 'DESCRICAO' in df_view.columns else None)
        col_cod = 'Código' if 'Código' in df_view.columns else ('CODIGO' if 'CODIGO' in df_view.columns else None)

        if busca_cert:
            termo = busca_cert.strip()
            mask_desc = df_view[col_desc].astype(str).str.contains(termo, case=False, na=False) if col_desc else False
            mask_cod = df_view[col_cod].astype(str).str.contains(termo, case=False, na=False) if col_cod else False
            df_view = df_view[mask_desc | mask_cod]

        if df_view.empty:
            st.info(f"Nenhum instrumento encontrado para **{mes_selecionado}** com os filtros atuais.")
        else:
            opcoes_status = ["Pendente", "Aprovado", "Reprovado"]
            for i, (idx, row) in enumerate(df_view.iterrows()):
                desc = str(row.get('Descrição', 'N/I'))
                cod = str(row.get('Código', 'N/I'))
                chave_cert = row['_CHAVE_CERT']
                status_atual = row['_STATUS_CERT']
                obs_atual = row['_OBS_CERT']
                atualizado_em = row['_ATUALIZADO_CERT']
                data_cal_exib = row['DATA_ULT_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row.get('DATA_ULT_CALIBRACAO')) else "N/I"
                venc_exib = str(row.get('DATA_STR', 'N/I'))

                if status_atual == "Aprovado":
                    cor_borda = "#2ecc71"
                    badge_cor = "badge-apto"
                elif status_atual == "Reprovado":
                    cor_borda = "#ff4b4b"
                    badge_cor = "badge-vencido"
                else:
                    cor_borda = "#F1C40F"
                    badge_cor = "badge-proximo"

                with st.container():
                    st.markdown(f"""
                    <div style="background-color:#112240; border-left:5px solid {cor_borda}; border-radius:10px; padding:14px 18px; margin-bottom:8px; position:relative;">
                        <span class="badge-status {badge_cor}" style="top:-10px; left:90px;">{status_atual}</span>
                        <div style="font-size:15px; font-weight:800; color:#ffffff; margin-top:4px;">{desc} <span style="color:#9099b2; font-weight:600;">({cod})</span></div>
                        <div style="font-size:12px; color:#b0b4c4; margin-top:4px;">
                            🛠️ Calibração: <b>{data_cal_exib}</b> &nbsp;|&nbsp; 📅 Vencimento: <b>{venc_exib}</b> &nbsp;|&nbsp; 🕒 Atualizado: <b>{atualizado_em}</b>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c_sel, c_obs, c_btn = st.columns([2, 4, 1])
                    idx_st = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0
                    novo_status = c_sel.selectbox(
                        "Status do certificado",
                        opcoes_status,
                        index=idx_st,
                        key=f"cert_st_{mes_selecionado}_{idx}",
                        label_visibility="collapsed"
                    )
                    nova_obs = c_obs.text_input(
                        "Nº do certificado / observação da análise",
                        value=obs_atual,
                        placeholder="Ex: Cert. 1234/2026 - Aprovado conforme critério...",
                        key=f"cert_obs_{mes_selecionado}_{idx}",
                        label_visibility="collapsed"
                    )
                    if c_btn.button("💾 Salvar", key=f"cert_save_{mes_selecionado}_{idx}", use_container_width=True):
                        st.session_state.analises_certificados[chave_cert] = {
                            "status": novo_status,
                            "observacao": nova_obs.strip(),
                            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        salvar_analises_certificados(st.session_state.analises_certificados)
                        st.success(f"Análise de {cod} salva como {novo_status}.")
                        st.rerun()

                    st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)

elif menu == "⚙️ CONFIGURAÇÕES":
    st.markdown("### ⚙️ Gestão de E-mails para Alertas")
    st.write("Gerencie quem recebe os avisos automáticos de calibração.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        novo_email = st.text_input("Adicionar novo e-mail:", placeholder="exemplo@tempermar.com.br")
    with col2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Incluir", use_container_width=True):
            if novo_email and novo_email not in st.session_state.config_emails:
                st.session_state.config_emails.append(novo_email)
                salvar_config(st.session_state.config_emails)
                st.success("E-mail adicionado com sucesso!")
                st.rerun()
            elif novo_email in st.session_state.config_emails:
                st.warning("Este e-mail já está na lista.")

    st.markdown("---")
    st.markdown("#### 📋 E-mails Cadastrados")
    
    for i, email in enumerate(st.session_state.config_emails):
        c_mail, c_btn = st.columns([4, 1])
        c_mail.markdown(f"<div style='background-color:#112240; padding:10px; border-radius:5px; margin-bottom:5px; font-weight:bold;'>✉️ {email}</div>", unsafe_allow_html=True)
        if c_btn.button("❌ Remover", key=f"del_{i}", use_container_width=True):
            st.session_state.config_emails.remove(email)
            salvar_config(st.session_state.config_emails)
            st.rerun()
