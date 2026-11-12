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

# --- GERENCIAMENTO DE CONFIGURAÇÕES (E-MAILS) ---
def carregar_emails():
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                return json.load(f).get("emails", ["luizclaudio@tempermar.com.br"])
        except: pass
    return ["luizclaudio@tempermar.com.br"]

def salvar_config(emails):
    with open("config.json", "w") as f: json.dump({"emails": emails}, f)

# --- INICIALIZAÇÃO DE MEMÓRIA ---
if 'pagina_ativa' not in st.session_state: st.session_state.pagina_ativa = "🛠️ Visão Geral"
if 'config_emails' not in st.session_state: st.session_state.config_emails = carregar_emails()

# --- MOTOR CSS ATUALIZADO (UI/UX PREMIUM) ---
st.markdown("""
    <style>
    .stApp { background-color: #0a192f; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }
    
    /* BOTÕES LATERAIS MODERNIZADOS */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: rgba(17, 34, 64, 0.8); border: 1px solid rgba(255,255,255,0.05); padding: 12px 20px;
        border-radius: 8px; font-weight: 700; transition: all 0.3s ease;
        justify-content: center; text-align: center; color: #b0b4c4; width: 100%;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    section[data-testid="stSidebar"] div.stButton > button:hover { 
        border-color: #3498DB; color: white; transform: translateY(-2px); box-shadow: 0 6px 15px rgba(52, 152, 219, 0.3);
    }
    
    /* BOTÃO PRIMÁRIO (DESTAQUE) */
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #ff9800, #e65100) !important; color: white !important; border: none !important;
        box-shadow: 0 4px 15px rgba(255, 152, 0, 0.4) !important; letter-spacing: 1px; text-transform: uppercase;
    }
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"]:hover {
        transform: translateY(-3px); box-shadow: 0 8px 20px rgba(255, 152, 0, 0.6) !important;
    }

    /* MENU DE SELEÇÃO LATERAL (RADIO BUTTONS) */
    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background-color: transparent; border: none; padding: 10px 10px 10px 45px;
        margin-bottom: 5px; font-weight: 600; transition: all 0.2s; display: flex; align-items: center; 
        width: 100%; color: #8a91a8; cursor: pointer; border-left: 4px solid transparent; border-radius: 0 8px 8px 0;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { 
        color: white; background-color: rgba(255,255,255,0.03); 
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        color: #ffffff; border-left: 4px solid #3498DB; background-color: rgba(52, 152, 219, 0.15); font-weight: 800;
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
            return None, "SEM DATA"
            
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
        if re.search(padrao_dispensa, t_ajustado): return None, "DISPENSADO"
        
        padrao_prox = r'data\s+(?:da\s+)?proxima\s+calibracao\s*:?\s*(\d{2}/\d{2}/\d{2,4})'
        match_prox = re.search(padrao_prox, t_ajustado)
        if match_prox:
            dt = pd.to_datetime(match_prox.group(1), dayfirst=True, errors='coerce')
            return (dt, None) if pd.notna(dt) else (None, "DATA ERRADA")
            
        padrao_ult = r'data\s+(?:da\s+)?ultima\s+calibracao\s*:?\s*(\d{2}/\d{2}/\d{2,4})'
        match_ultima = re.search(padrao_ult, t_ajustado)
        if match_ultima:
            dt_ult = pd.to_datetime(match_ultima.group(1), dayfirst=True, errors='coerce')
            return (dt_ult + relativedelta(years=1), None) if pd.notna(dt_ult) else (None, "DATA ERRADA")
            
        return None, "SEM DATA"

    resultados = df[col_caract].apply(extrair_vencimento)
    df['DATA_CALIBRACAO'] = pd.to_datetime([x[0] for x in resultados], errors='coerce')
    df['ALERTA_DATA'] = [x[1] for x in resultados]
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
    st.write(f"Será enviado um e-mail com a relação dos **{qtd} equipamentos** listados na tela para os contatos cadastrados em Ajustes.")
    if st.button("Confirmar Envio", use_container_width=True, type="primary"):
        try:
            enviar_email_consolidado(st.session_state.config_emails, df_alvo)
            st.success("Enviado com sucesso!")
        except Exception as e: st.error(f"Erro: {e}")

# --- NAVEGAÇÃO LATERAL ---
df = processar_dados(carregar_dados())

col_familia = next((c for c in df.columns if 'FAMÍLIA' in c.upper() or 'FAMILIA' in c.upper()), "FAMÍLIA DE PRODUTO")
if col_familia not in df.columns: df[col_familia] = "INSTRUMENTOS"

# RENDERIZAÇÃO DO LOGO COM TEXTO BRANCO NA SIDEBAR
def renderizar_logo_sidebar():
    caminho_imagem = "icone.png"
    try:
        with open(caminho_imagem, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        html_logo = f"""
        <div style="display: flex; align-items: center; margin-bottom: 25px; margin-top: -15px;">
            <img src="data:image/png;base64,{encoded_string}" style="width: 40px; margin-right: 15px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5));">
            <h2 style="color: #ffffff; margin: 0; font-weight: 900; letter-spacing: 1px; font-size: 22px;">TEMPERMAR</h2>
        </div>
        """
        st.sidebar.markdown(html_logo, unsafe_allow_html=True)
    except:
        st.sidebar.markdown("<h2 style='color: white; font-weight: 900; margin-bottom: 20px;'>TEMPERMAR</h2>", unsafe_allow_html=True)

renderizar_logo_sidebar()

# BOTÃO DE ATUALIZAÇÃO FORÇADA
if st.sidebar.button("🔄 Atualizar Planilha", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
paginas_metro = ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos de vencer", "🚨 NECESSÁRIO CALIBRAÇÃO", "⚙️ Ajustes"]
idx = paginas_metro.index(st.session_state.pagina_ativa) if st.session_state.pagina_ativa in paginas_metro else 0
escolha = st.sidebar.radio("SubMetro", paginas_metro, index=idx, label_visibility="collapsed")

if escolha != st.session_state.pagina_ativa:
    st.session_state.pagina_ativa = escolha
    st.rerun()

menu = st.session_state.pagina_ativa

# SUB-MENU E BOTÃO DE ALERTA CONDICIONAL NA SIDEBAR
if menu == "🚨 NECESSÁRIO CALIBRAÇÃO":
    st.sidebar.markdown("<div style='padding-left: 45px; font-size: 11px; color: #3498DB; font-weight: bold; text-transform: uppercase; margin-bottom: 2px; letter-spacing: 1px;'>📋 Sub-páginas:</div>", unsafe_allow_html=True)
    sub_nc = st.sidebar.radio("SubNC", ["INSTRUMENTOS", "EQUIPAMENTOS DE IÇAMENTO"], key="sub_nc_radio", label_visibility="collapsed")
    st.sidebar.markdown("---")
    
    # O Botão de Alerta Global
    disparar = st.sidebar.button("🚨 Disparar Alerta", use_container_width=True, type="primary")

# --- RENDERIZAÇÃO DAS PÁGINAS PRINCIPAIS ---

# INJEÇÃO DO TÍTULO GLOBAL EM TODAS AS TELAS
st.markdown("""
    <h1 style='text-align: center; color: #ffffff; font-size: 2.2rem; font-weight: 900; 
               margin-bottom: 5px; margin-top: -20px; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 4px 10px rgba(0,0,0,0.5);'>
        SISTEMA DE APOIO A METROLOGIA
    </h1>
    <hr style='border: 0; border-top: 1px solid #233554; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

if menu == "🛠️ Visão Geral":
    st.markdown("### 🛠️ Dashboard Geral")
    df_vencidos = df[df['STATUS'] == 'VENCIDO']
    mask_icamento = df_vencidos[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)
    qtd_instrumentos = len(df_vencidos[~mask_icamento])
    qtd_icamento = len(df_vencidos[mask_icamento])

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_mini_kpi("Aptos / Dispensados", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Atenção (30 dias)", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mini_kpi("Calibração. Instrumentos", qtd_instrumentos, "vencido-kpi")
    with c4: render_mini_kpi("Calibração. Içamento", qtd_icamento, "vencido-kpi")
    
    st.dataframe(df.drop(columns=['DATA_CALIBRACAO'], errors='ignore'), use_container_width=True)
    
    with st.expander("🔍 Auditoria de Segurança: Verificar possíveis falsos negativos"):
        possiveis_erros = df[(df['STATUS'] == 'VENCIDO') & (df['ALERTA_DATA'] == 'SEM DATA') & (df["Características"].astype(str).str.contains(r'\d{2}/\d{2}', na=False))]
        if not possiveis_erros.empty:
            st.warning(f"Atenção: Detectamos {len(possiveis_erros)} itens sem data calculada, mas com menção a datas no texto:")
            st.dataframe(possiveis_erros[['Código', 'Descrição', "Características"]], use_container_width=True)
        else:
            st.success("🔥 Varredura concluída: Zero falsos negativos na base!")

elif menu == "✅ APTOS":
    st.markdown(f"### {menu}")
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

elif menu == "⏳ Próximos de vencer":
    st.markdown(f"### {menu}")
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
    st.markdown(f"### 🚨 NECESSÁRIO CALIBRAÇÃO › {sub_nc}")
    
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

    # Gatilho do Botão Lateral de Alerta
    if disparar:
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

elif menu == "⚙️ Ajustes":
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
