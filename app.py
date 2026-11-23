import streamlit as st
from streamlit_option_menu import option_menu
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
if 'sub_nc_ativa' not in st.session_state: st.session_state.sub_nc_ativa = "INSTRUMENTOS"
if 'sub_mapa_ativa' not in st.session_state: st.session_state.sub_mapa_ativa = "MAPA ANALÍTICO"
if 'config_emails' not in st.session_state: st.session_state.config_emails = carregar_emails()
if 'analises_certificados' not in st.session_state: st.session_state.analises_certificados = carregar_analises_certificados()

# --- MOTOR CSS GLOBAL ---
st.markdown("""
    <style>
    .stApp { background-color: #0a192f; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #121212; border-right: 1px solid #222222; }

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

    /* VARIANTE COMPACTA PARA CANTO SUPERIOR DIREITO */
    .kpi-container.kpi-compact {
        padding: 8px 14px;
        margin-bottom: 0px;
        border-radius: 10px;
    }
    .kpi-container.kpi-compact .kpi-value {
        font-size: 22px;
        margin: 0px;
    }
    .kpi-container.kpi-compact .kpi-label {
        font-size: 10px;
        letter-spacing: 0.4px;
    }
    
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
        
        if re.search(r'd[ei]spensa\s+(?:de\s+)?calibracao', t_ajustado): return None, "DISPENSADO", None
        
        match_prox = re.search(r'data\s+(?:da\s+)?proxima\s+calibracao\s*:?\s*(\d{2}/\d{2}/\d{2,4})', t_ajustado)
        if match_prox:
            dt = pd.to_datetime(match_prox.group(1), dayfirst=True, errors='coerce')
            if pd.notna(dt):
                return dt, None, dt - relativedelta(years=1)
            return None, "DATA ERRADA", None
            
        match_ultima = re.search(r'data\s+(?:da\s+)?ultima\s+calibracao\s*:?\s*(\d{2}/\d{2}/\d{2,4})', t_ajustado)
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
        return "VENCIDO" if dias < 0 else ("PRÓXIMO DE VENCER" if dias <= 30 else "APTOS")

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
        conteudo += f"- {row.get('Descrição', 'N/I')} ({row.get('Código', 'N/I')}) - Vencimento: {row.get('DATA_STR', 'N/I')}\n"
    msg.set_content(conteudo)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_usuario, email_senha)
        smtp.send_message(msg)

def render_mini_kpi(label, valor, classe, compacto=False):
    extra_cls = " kpi-compact" if compacto else ""
    st.markdown(f'<div class="kpi-container {classe}{extra_cls}"><div class="kpi-value">{valor}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

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

# --- NAVEGAÇÃO LATERAL COM STREAMLIT-OPTION-MENU ---
df = processar_dados(carregar_dados())
col_familia = next((c for c in df.columns if 'FAMÍLIA' in c.upper() or 'FAMILIA' in c.upper()), "FAMÍLIA DE PRODUTO")
if col_familia not in df.columns: df[col_familia] = "INSTRUMENTOS"

def renderizar_logo_sidebar():
    caminho_imagem = "icone.png"
    try:
        with open(caminho_imagem, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        html_logo = f"""
        <div style="display: flex; align-items: center; margin-bottom: 16px; margin-top: -10px;">
            <img src="data:image/png;base64,{encoded_string}" style="width: 34px; height: 34px; object-fit: contain; margin-right: 12px; border-radius: 6px;">
            <h2 style="color: #ffffff; margin: 0; font-weight: 900; letter-spacing: 1px; font-size: 20px;">TEMPERMAR</h2>
        </div>
        """
        st.sidebar.markdown(html_logo, unsafe_allow_html=True)
    except:
        st.sidebar.markdown("<h2 style='color: white; font-weight: 900; margin-bottom: 16px;'>TEMPERMAR</h2>", unsafe_allow_html=True)

with st.sidebar:
    renderizar_logo_sidebar()
    st.markdown("<h4 style='color: #e0e6f0; font-weight: 700; margin-bottom: 14px; font-size: 15px;'>Olá, Luiz Cláudio</h4>", unsafe_allow_html=True)

    menu_opcoes = [
        "VISÃO GERAL",
        "EQUIPAMENTOS APTOS",
        "PRÓXIMO DE VENCER",
        "NECESSÁRIO CALIBRAÇÃO",
        "MAPA DE CALIBRAÇÃO",
        "CONFIGURAÇÕES"
    ]
    menu_icones = [
        "bar-chart-line",
        "check-circle",
        "hourglass-split",
        "exclamation-triangle",
        "map",
        "gear"
    ]

    menu_selecionado = option_menu(
        menu_title=None,
        options=menu_opcoes,
        icons=menu_icones,
        default_index=0,
        styles={
            "container": {"padding": "4px 0", "background-color": "#121212"},
            "icon": {"color": "#9aa3b8", "font-size": "15px"},
            "nav-link": {
                "font-size": "12.5px",
                "font-weight": "700",
                "color": "#9aa3b8",
                "text-align": "left",
                "margin": "3px 0px",
                "padding": "9px 12px",
                "border-radius": "6px",
                "border-left": "3px solid transparent",
                "background-color": "transparent",
            },
            "nav-link-selected": {
                "background-color": "#1E2130",
                "color": "#ffffff",
                "font-weight": "800",
                "border-left": "4px solid #ff4b4b",
                "border-radius": "3px 6px 6px 3px",
            },
        }
    )

    if menu_selecionado == "NECESSÁRIO CALIBRAÇÃO":
        sub_nc = option_menu(
            menu_title="CATEGORIA",
            options=["INSTRUMENTOS", "EQUIPAMENTOS DE IÇAMENTO"],
            icons=["rulers", "box-arrow-up"],
            menu_icon="arrow-return-right",
            default_index=0 if st.session_state.sub_nc_ativa == "INSTRUMENTOS" else 1,
            styles={
                "container": {"padding": "4px 0 4px 10px", "background-color": "#121212", "border-left": "2px solid #2d3348", "margin-top": "4px"},
                "menu-title": {"color": "#ff4b4b", "font-size": "11px", "font-weight": "800", "letter-spacing": "0.8px", "margin-bottom": "4px"},
                "icon": {"color": "#8f98b0", "font-size": "13px"},
                "nav-link": {"font-size": "11.5px", "font-weight": "700", "color": "#8f98b0", "text-align": "left", "margin": "2px 0", "padding": "7px 10px", "border-radius": "6px"},
                "nav-link-selected": {"background-color": "#191d2b", "color": "#ffffff", "border-left": "3px solid #ff4b4b"},
            }
        )
        st.session_state.sub_nc_ativa = sub_nc
    else:
        sub_nc = st.session_state.sub_nc_ativa

    if menu_selecionado == "MAPA DE CALIBRAÇÃO":
        visao_mapa = option_menu(
            menu_title="VISÃO DO MAPA",
            options=["MAPA ANALÍTICO", "MAPA GERAL"],
            icons=["list-check", "grid-1x2"],
            menu_icon="arrow-return-right",
            default_index=0 if st.session_state.sub_mapa_ativa == "MAPA ANALÍTICO" else 1,
            styles={
                "container": {"padding": "4px 0 4px 10px", "background-color": "#121212", "border-left": "2px solid #2d3348", "margin-top": "4px"},
                "menu-title": {"color": "#3498DB", "font-size": "11px", "font-weight": "800", "letter-spacing": "0.8px", "margin-bottom": "4px"},
                "icon": {"color": "#8f98b0", "font-size": "13px"},
                "nav-link": {"font-size": "11.5px", "font-weight": "700", "color": "#8f98b0", "text-align": "left", "margin": "2px 0", "padding": "7px 10px", "border-radius": "6px"},
                "nav-link-selected": {"background-color": "#191d2b", "color": "#ffffff", "border-left": "3px solid #3498DB"},
            }
        )
        st.session_state.sub_mapa_ativa = visao_mapa
    else:
        visao_mapa = st.session_state.sub_mapa_ativa

    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 14px 0 10px 0;'>", unsafe_allow_html=True)

    disparar = False
    if menu_selecionado == "NECESSÁRIO CALIBRAÇÃO":
        disparar = st.button("🚨 Disparar Alerta", use_container_width=True, type="primary")
        st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)

    if st.button("🔄 Atualizar Planilha", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- RENDERIZAÇÃO DAS PÁGINAS PRINCIPAIS ---
st.markdown("""
    <h1 style='text-align: center; color: #ffffff; font-size: 2.2rem; font-weight: 900; 
               margin-bottom: 5px; margin-top: -20px; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 4px 10px rgba(0,0,0,0.5);'>
        SISTEMA DE APOIO A METROLOGIA
    </h1>
    <hr style='border: 0; border-top: 1px solid #233554; margin-bottom: 24px;'>
""", unsafe_allow_html=True)

if menu_selecionado == "VISÃO GERAL":
    st.markdown("### 📊 Dashboard Geral")
    df_vencidos = df[df['STATUS'] == 'VENCIDO']
    mask_icamento = df_vencidos[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)
    qtd_instrumentos = len(df_vencidos[~mask_icamento])
    qtd_icamento = len(df_vencidos[mask_icamento])

    c1, c2, c3, c4 = st.columns(4)
    with c1: render_mini_kpi("Aptos / Dispensados", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Atenção (30 dias)", len(df[df['STATUS'] == 'PRÓXIMO DE VENCER']), "proximo-kpi")
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

elif menu_selecionado == "EQUIPAMENTOS APTOS":
    df_f = df[df['STATUS'] == 'APTOS']
    col_tit, col_kpi = st.columns([3.5, 1.5], vertical_alignment="center")
    with col_tit:
        st.markdown("### ✅ Equipamentos Aptos")
    with col_kpi:
        render_mini_kpi("Total Equipamentos Aptos", len(df_f), "apto-kpi", compacto=True)
    st.markdown("---")
    fn, fc, fd = sistema_filtros()
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]
    
    cols = st.columns(4)
    for i, (_, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            desc = str(row.get('Descrição', 'N/I'))
            cod = str(row.get('Código', 'N/I'))
            data_str = str(row.get('DATA_STR', 'N/I'))
            if data_str == "DISPENSADO":
                badge_class, badge_text, data_exibicao = "badge-dispensa", "DISPENSADO", "♾️ ISENTO DE CALIBRAÇÃO"
            else:
                badge_class, badge_text, data_exibicao = "badge-apto", "REGULAR", f"📅 {data_str}"
            st.markdown(f"""
            <div class='card-instrumento apto-card'>
                <div class='badge-status {badge_class}'>{badge_text}</div>
                <div style="flex-grow: 1;"><b style="font-size: 14px; line-height: 1.2;">{desc}</b><br><small style="color: #a0aabf;">{cod}</small></div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 12px; font-weight: 600; text-align: center;">{data_exibicao}</div>
            </div>""", unsafe_allow_html=True)

elif menu_selecionado == "PRÓXIMO DE VENCER":
    df_f = df[df['STATUS'] == 'PRÓXIMO DE VENCER']
    col_tit, col_kpi = st.columns([3.5, 1.5], vertical_alignment="center")
    with col_tit:
        st.markdown("### ⏳ Próximo de Vencer")
    with col_kpi:
        render_mini_kpi("Equipamentos em Atenção", len(df_f), "proximo-kpi", compacto=True)
    st.markdown("---")
    fn, fc, fd = sistema_filtros()
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]

    cols = st.columns(4)
    for i, (_, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            st.markdown(f"""
            <div class='card-instrumento proximo-card'>
                <div class='badge-status badge-proximo'>ATENÇÃO</div>
                <div style="flex-grow: 1;"><b style="font-size: 14px; line-height: 1.2;">{row.get('Descrição', 'N/I')}</b><br><small style="color: #a0aabf;">{row.get('Código', 'N/I')}</small></div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 13px; font-weight: 700; text-align: center; color: #F1C40F;">📅 {row.get('DATA_STR', 'N/I')}</div>
            </div>""", unsafe_allow_html=True)

elif menu_selecionado == "NECESSÁRIO CALIBRAÇÃO":
    st.markdown(f"### 🚨 Necessário Calibração › {sub_nc}")
    df_f = df[df['STATUS'] == 'VENCIDO']
    if sub_nc == "INSTRUMENTOS": df_f = df_f[~df_f[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)]
    else: df_f = df_f[df_f[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)]
        
    qtd_total = len(df_f)
    qtd_sem_data = len(df_f[df_f['ALERTA_DATA'].isin(['SEM DATA', 'DATA ERRADA'])])
    
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi("Total na Lista", qtd_total, "vencido-kpi")
    with c2: render_mini_kpi("Falta Cadastrar Data", qtd_sem_data, "vencido-kpi")
    with c3: render_mini_kpi("Vencimento Ultrapassado", qtd_total - qtd_sem_data, "vencido-kpi")
    st.markdown("---")
    
    fn, fc, fd = sistema_filtros()
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]

    if disparar:
        if not df_f.empty: popup_confirmar_envio(len(df_f), df_f)
        else: st.warning("A lista atual está vazia. Não há nada para enviar.")

    cols = st.columns(4)
    for i, (_, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            desc, cod, data_str = str(row.get('Descrição', 'N/I')), str(row.get('Código', 'N/I')), str(row.get('DATA_STR', 'N/I'))
            if data_str == "SEM DATA":
                data_exibicao, badge_class, badge_text, cor_data = "⚠️ DADO FALTANTE", "badge-alerta", "INCOMPLETO", "#8E44AD"
            elif data_str == "DATA ERRADA":
                data_exibicao, badge_class, badge_text, cor_data = "❌ ERRO DE DIGITAÇÃO", "badge-alerta", "REVISAR DATA", "#8E44AD"
            else:
                data_exibicao, badge_class, badge_text, cor_data = f"📅 Vencido em: {data_str}", "badge-vencido", "URGENTE", "#ff4b4b"
            st.markdown(f"""
            <div class='card-instrumento vencido-card'>
                <div class='badge-status {badge_class}'>{badge_text}</div>
                <div style="flex-grow: 1;"><b style="font-size: 14px; line-height: 1.2;">{desc}</b><br><small style="color: #a0aabf;">{cod}</small></div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 12px; font-weight: 700; text-align: center; color: {cor_data};">{data_exibicao}</div>
            </div>""", unsafe_allow_html=True)

elif menu_selecionado == "MAPA DE CALIBRAÇÃO":
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
        g1, g2, g3, g4 = st.columns(4)
        with g1: render_mini_kpi("Total Mapeados", len(df_inst), "mapa-kpi")
        with g2: render_mini_kpi("Certificados Aprovados", len(df_inst[df_inst['_STATUS_CERT'] == "Aprovado"]), "apto-kpi")
        with g3: render_mini_kpi("Pendentes de Análise", len(df_inst[df_inst['_STATUS_CERT'] == "Pendente"]), "proximo-kpi")
        with g4: render_mini_kpi("Certificados Reprovados", len(df_inst[df_inst['_STATUS_CERT'] == "Reprovado"]), "vencido-kpi")
        st.markdown("---")
        st.markdown("#### 📆 Consolidado por Mês de Calibração")
        if df_inst.empty:
            st.info("Nenhum instrumento com data de calibração identificada na base.")
        else:
            resumo_meses = df_inst.groupby('MES_CALIBRACAO')['_STATUS_CERT'].value_counts().unstack(fill_value=0).reset_index()
            for col_st in ["Pendente", "Aprovado", "Reprovado"]:
                if col_st not in resumo_meses.columns: resumo_meses[col_st] = 0
            resumo_meses["Total"] = resumo_meses["Pendente"] + resumo_meses["Aprovado"] + resumo_meses["Reprovado"]
            resumo_meses = resumo_meses.sort_values(by="MES_CALIBRACAO", key=lambda s: s.map(lambda m: datetime.strptime(m, "%m/%Y")), ascending=False)
            resumo_meses = resumo_meses.rename(columns={"MES_CALIBRACAO": "Mês Calibração", "Pendente": "Pendentes", "Aprovado": "Aprovados", "Reprovado": "Reprovados"})[["Mês Calibração", "Total", "Pendentes", "Aprovados", "Reprovados"]]
            st.dataframe(resumo_meses, use_container_width=True, hide_index=True)

            st.markdown("#### 📋 Relação Geral dos Instrumentos Mapeados")
            col_desc = 'Descrição' if 'Descrição' in df_inst.columns else ('DESCRICAO' if 'DESCRICAO' in df_inst.columns else None)
            col_cod = 'Código' if 'Código' in df_inst.columns else ('CODIGO' if 'CODIGO' in df_inst.columns else None)
            st.dataframe(pd.DataFrame({
                "Código": df_inst[col_cod] if col_cod else "N/I",
                "Descrição": df_inst[col_desc] if col_desc else "N/I",
                "Mês Calibração": df_inst["MES_CALIBRACAO"],
                "Data Calibração": df_inst["DATA_ULT_CALIBRACAO"].dt.strftime('%d/%m/%Y').fillna("N/I"),
                "Vencimento": df_inst["DATA_STR"],
                "Status Análise": df_inst["_STATUS_CERT"],
                "Observação / Certificado": df_inst["_OBS_CERT"]
            }), use_container_width=True, hide_index=True)
    else:
        st.markdown("### 🗺️ Mapa de Calibração › Mapa Analítico")
        st.write("Selecione o mês da calibração para acompanhar e gerenciar a análise crítica dos certificados emitidos.")
        mes_atual_str = datetime.now().strftime('%m/%Y')
        meses_base = df_inst['MES_CALIBRACAO'].unique().tolist()
        if mes_atual_str not in meses_base: meses_base.append(mes_atual_str)
        meses_ordenados = sorted(meses_base, key=lambda m: datetime.strptime(m, "%m/%Y"), reverse=True)

        c_mes, c_status, c_busca = st.columns([2, 2, 3])
        with c_mes: mes_selecionado = st.selectbox("📅 Mês da Calibração:", meses_ordenados, index=0, key="mapa_mes_sel")
        with c_status: filtro_status_cert = st.selectbox("📌 Status da Análise:", ["Todos", "Pendente", "Aprovado", "Reprovado"], key="mapa_status_sel")
        with c_busca: busca_cert = st.text_input("🔎 Buscar por Nome ou Código:", key="mapa_busca_txt")

        df_mes = df_inst[df_inst['MES_CALIBRACAO'] == mes_selecionado].copy()
        k1, k2, k3, k4 = st.columns(4)
        with k1: render_mini_kpi(f"Calibrados em {mes_selecionado}", len(df_mes), "mapa-kpi")
        with k2: render_mini_kpi("Pendentes", len(df_mes[df_mes['_STATUS_CERT'] == "Pendente"]), "proximo-kpi")
        with k3: render_mini_kpi("Aprovados", len(df_mes[df_mes['_STATUS_CERT'] == "Aprovado"]), "apto-kpi")
        with k4: render_mini_kpi("Reprovados", len(df_mes[df_mes['_STATUS_CERT'] == "Reprovado"]), "vencido-kpi")
        st.markdown("---")

        df_view = df_mes.copy()
        if filtro_status_cert != "Todos": df_view = df_view[df_view['_STATUS_CERT'] == filtro_status_cert]
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
            for i, (_, row) in enumerate(df_view.iterrows()):
                desc, cod = str(row.get('Descrição', 'N/I')), str(row.get('Código', 'N/I'))
                chave_cert, status_atual, obs_atual, atualizado_em = row['_CHAVE_CERT'], row['_STATUS_CERT'], row['_OBS_CERT'], row['_ATUALIZADO_CERT']
                data_cal_exib = row['DATA_ULT_CALIBRACAO'].strftime('%d/%m/%Y') if pd.notna(row.get('DATA_ULT_CALIBRACAO')) else "N/I"
                venc_exib = str(row.get('DATA_STR', 'N/I'))
                cor_borda, badge_cor = ("#2ecc71", "badge-apto") if status_atual == "Aprovado" else (("#ff4b4b", "badge-vencido") if status_atual == "Reprovado" else ("#F1C40F", "badge-proximo"))

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
                    key_base = f"{mes_selecionado}_{i}_{cod}"
                    novo_status = c_sel.selectbox("Status do certificado", opcoes_status, index=idx_st, key=f"cert_st_{key_base}", label_visibility="collapsed")
                    nova_obs = c_obs.text_input("Nº do certificado / observação da análise", value=obs_atual, placeholder="Ex: Cert. 1234/2026 - Aprovado conforme critério...", key=f"cert_obs_{key_base}", label_visibility="collapsed")
                    if c_btn.button("💾 Salvar", key=f"cert_save_{key_base}", use_container_width=True):
                        st.session_state.analises_certificados[chave_cert] = {
                            "status": novo_status,
                            "observacao": nova_obs.strip(),
                            "atualizado_em": datetime.now().strftime("%d/%m/%Y %H:%M")
                        }
                        salvar_analises_certificados(st.session_state.analises_certificados)
                        st.success(f"Análise de {cod} salva como {novo_status}.")
                        st.rerun()
                    st.markdown("<div style='margin-bottom:14px;'></div>", unsafe_allow_html=True)

elif menu_selecionado == "CONFIGURAÇÕES":
    st.markdown("### ⚙️ Gestão de E-mails para Alertas")
    st.write("Gerencie quem recebe os avisos automáticos de calibração.")
    col1, col2 = st.columns([3, 1])
    with col1: novo_email = st.text_input("Adicionar novo e-mail:", placeholder="exemplo@tempermar.com.br")
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
