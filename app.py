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

# --- INICIALIZAÇÃO DE MEMÓRIA ---
if 'pagina_ativa' not in st.session_state: st.session_state.pagina_ativa = "🛠️ Visão Geral"
if 'config_emails' not in st.session_state: st.session_state.config_emails = "luizclaudio@tempermar.com.br"
if 'selecionados' not in st.session_state: st.session_state.selecionados = []

# --- MOTOR CSS ATUALIZADO (UI/UX PREMIUM) ---
st.markdown("""
    <style>
    .stApp { background-color: #0a192f; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }
    
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #112240; border: 1px solid #233554; padding: 12px 20px;
        border-radius: 8px; font-weight: bold; transition: 0.3s;
        justify-content: flex-start; text-align: left; color: #b0b4c4; width: 100%;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover { border-color: #ff9800; color: white; }
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #ff9800 !important; color: white !important; border-color: #ff9800 !important;
        box-shadow: 0 0 15px rgba(255, 152, 0, 0.5) !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child { display: none; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        background-color: transparent; border: none; padding: 8px 10px 8px 45px;
        margin-bottom: 0px; font-weight: normal; transition: 0.2s; display: flex; align-items: center; 
        justify-content: flex-start; width: 100%; color: #8a91a8; cursor: pointer; border-left: 4px solid transparent;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { color: white; }
    section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        color: #ff9800; border-left: 4px solid #ff9800; background-color: rgba(255, 152, 0, 0.05); font-weight: bold;
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
        display: flex; flex-direction: column; justify-content: space-between; min-height: 150px;
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
    .badge-dispensa { color: #3498DB; border-color: #3498DB; } /* Azul para dispensa */

    .vencido-card { border-left-color: #ff4b4b; background: linear-gradient(to right, #2a1616, #112240); }
    .proximo-card { border-left-color: #fcc419; background: linear-gradient(to right, #2a2510, #112240); }
    .apto-card { border-left-color: #2ecc71; background: linear-gradient(to right, #102416, #112240); }
    .card-selecionado { border: 2px solid #ff9800 !important; box-shadow: 0 0 20px rgba(255, 152, 0, 0.4) !important; transform: scale(1.02); background: linear-gradient(to right, #332100, #112240) !important; }
    </style>
""", unsafe_allow_html=True)

def salvar_config(emails):
    with open("config.json", "w") as f: json.dump({"emails": emails}, f)

# --- CARREGAMENTO DE DADOS ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

@st.cache_data(ttl=600)
def carregar_dados():
    try: return pd.read_csv(SHEET_URL)
    except: return pd.DataFrame()

def processar_dados(df):
    if df.empty: return df
    
    # 1. TRAVA EXPLÍCITA DA COLUNA (Resolve o problema do Omie)
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
        
        # BLINDAGEM DE DISPENSA
        padrao_dispensa = r'd[ei]spensa\s+(?:de\s+)?calibracao'
        if re.search(padrao_dispensa, t_ajustado):
            return None, "DISPENSADO"
        
        # VERIFICAÇÃO DE PRÓXIMA CALIBRAÇÃO (dayfirst=True)
        padrao_prox = r'data\s+(?:da\s+)?proxima\s+calibracao\s*:?\s*(\d{2}/\d{2}/\d{2,4})'
        match_prox = re.search(padrao_prox, t_ajustado)
        
        if match_prox:
            dt = pd.to_datetime(match_prox.group(1), dayfirst=True, errors='coerce')
            return (dt, None) if pd.notna(dt) else (None, "DATA ERRADA")
            
        # VERIFICAÇÃO DE ÚLTIMA CALIBRAÇÃO (dayfirst=True)
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
    msg['Subject'] = f"🚨 ALERTA: {len(df_criticos)} Itens Selecionados"
    email_config = st.secrets.get("email", {})
    email_usuario = email_config.get("email_usuario", "nao_configurado@sistema.com")
    email_senha = email_config.get("email_senha", "")
    
    msg['From'] = email_usuario
    msg['To'] = destinatarios
    conteudo = "Relatório de Itens Selecionados para Alerta:\n\n"
    
    for _, row in df_criticos.iterrows():
        desc = row.get('Descrição', 'N/I')
        cod = row.get('Código', 'N/I')
        data_str = row.get('DATA_STR', 'N/I')
        conteudo += f"- {desc} (TAG: {cod}) - Vencimento: {data_str}\n"
        
    msg.set_content(conteudo)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(email_usuario, email_senha)
        smtp.send_message(msg)

def render_mini_kpi(label, valor, classe):
    st.markdown(f'<div class="kpi-container {classe}"><div class="kpi-value">{valor}</div><div class="kpi-label">{label}</div></div>', unsafe_allow_html=True)

def sistema_filtros(key_sufix, mostrar_botao_limpar=False):
    col_titulo, col_botao = st.columns([4, 1])
    with col_titulo: st.markdown("##### 🔍 Filtros de pesquisa")
    with col_botao:
        if mostrar_botao_limpar:
            if st.button("🧹 Limpar", key=f"btn_limpar_{key_sufix}", use_container_width=True):
                for k in [f"f_n_{key_sufix}", f"f_c_{key_sufix}", f"f_d_{key_sufix}"]:
                    if k in st.session_state: st.session_state[k] = ""
                st.rerun()
    c1, c2, c3 = st.columns(3)
    return c1.text_input("Nome:", key=f"f_n_{key_sufix}"), c2.text_input("Código:", key=f"f_c_{key_sufix}"), c3.text_input("Data:", key=f"f_d_{key_sufix}")

@st.dialog("Confirmação de Envio")
def popup_confirmar_envio(x, y, df_alvo):
    st.write("Será enviado um e-mail com a relação completa de itens não aptos:")
    st.write(f"**# {x} Próximos de vencer** | **# {y} Necessário Calibração**")
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
st.sidebar.button("📏 METROLOGIA", use_container_width=True, type="primary")

paginas_metro = ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos de vencer", "🚨 NECESSÁRIO CALIBRAÇÃO", "⚙️ Ajustes"]
idx = paginas_metro.index(st.session_state.pagina_ativa) if st.session_state.pagina_ativa in paginas_metro else 0
escolha = st.sidebar.radio("SubMetro", paginas_metro, index=idx, label_visibility="collapsed")

if escolha != st.session_state.pagina_ativa:
    st.session_state.pagina_ativa = escolha
    st.rerun()

st.sidebar.markdown("---")
menu = st.session_state.pagina_ativa

if menu == "🚨 NECESSÁRIO CALIBRAÇÃO":
    st.sidebar.markdown("<div style='padding-left: 45px; font-size: 11px; color: #ff9800; font-weight: bold; text-transform: uppercase; margin-bottom: 2px; letter-spacing: 1px;'>📋 Sub-páginas:</div>", unsafe_allow_html=True)
    sub_nc = st.sidebar.radio("SubNC", ["INSTRUMENTOS", "EQUIPAMENTOS DE IÇAMENTO"], key="sub_nc_radio", label_visibility="collapsed")

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
    
    fn, fc, fd = sistema_filtros(menu, True)
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
                    <small style="color: #a0aabf;">TAG: {cod}</small>
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
    
    fn, fc, fd = sistema_filtros(menu, True)
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            is_sel = idx in st.session_state.selecionados
            c_class = f"proximo-card {'card-selecionado' if is_sel else ''}"
            
            desc = str(row.get('Descrição', 'N/I'))
            cod = str(row.get('Código', 'N/I'))
            data_str = str(row.get('DATA_STR', 'N/I'))
            
            html_card = f"""
            <div class='card-instrumento {c_class}'>
                <div class='badge-status badge-proximo'>ATENÇÃO</div>
                <div style="flex-grow: 1;">
                    <b style="font-size: 14px; line-height: 1.2;">{desc}</b><br>
                    <small style="color: #a0aabf;">TAG: {cod}</small>
                </div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 13px; font-weight: 700; text-align: center; color: #F1C40F;">📅 {data_str}</div>
            </div>"""
            st.markdown(html_card, unsafe_allow_html=True)
            
            if st.button("✅" if is_sel else "⭕", key=f"s_{idx}", use_container_width=True):
                if is_sel: st.session_state.selecionados.remove(idx)
                else: st.session_state.selecionados.append(idx)
                st.rerun()

elif menu == "🚨 NECESSÁRIO CALIBRAÇÃO":
    sub_ativa = st.session_state.get('sub_nc_radio', 'INSTRUMENTOS')
    st.markdown(f"### 🚨 NECESSÁRIO CALIBRAÇÃO › {sub_ativa}")
    
    suffix_nc = f"NC_{sub_ativa.replace(' ', '_')}"
    df_f = df[df['STATUS'] == 'VENCIDO']
    
    if sub_ativa == "INSTRUMENTOS": df_f = df_f[~df_f[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)]
    else: df_f = df_f[df_f[col_familia].astype(str).str.contains('IÇAMENTO|ICAMENTO', case=False, na=False)]
        
    qtd_total = len(df_f)
    qtd_sem_data = len(df_f[df_f['ALERTA_DATA'].isin(['SEM DATA', 'DATA ERRADA'])])
    
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi(f"Total na Lista", qtd_total, "vencido-kpi")
    with c2: render_mini_kpi("Falta Cadastrar Data", qtd_sem_data, "vencido-kpi")
    with c3: render_mini_kpi("Vencimento Ultrapassado", qtd_total - qtd_sem_data, "vencido-kpi")
    st.markdown("---")
    
    fn, fc, fd = sistema_filtros(suffix_nc, True)
    col_desc = 'Descrição' if 'Descrição' in df_f.columns else ('DESCRICAO' if 'DESCRICAO' in df_f.columns else None)
    col_cod = 'Código' if 'Código' in df_f.columns else ('CODIGO' if 'CODIGO' in df_f.columns else None)
    
    if fn and col_desc: df_f = df_f[df_f[col_desc].astype(str).str.contains(fn, case=False, na=False)]
    if fc and col_cod: df_f = df_f[df_f[col_cod].astype(str).str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].astype(str).str.contains(fd, case=False, na=False)]

    if st.button("🚨 Disparar Alerta por E-mail", key=f"btn_alerta_lote_{suffix_nc}", use_container_width=True, type="primary"):
        if not st.session_state.selecionados: popup_confirmar_envio(len(df[df['STATUS']=='PRÓXIMO VENCIMENTO']), len(df[df['STATUS']=='VENCIDO']), df[df['STATUS'].isin(['VENCIDO','PRÓXIMO VENCIMENTO'])])
        else:
            enviar_email_consolidado(st.session_state.config_emails, df.loc[st.session_state.selecionados])
            st.success("Enviado com sucesso!")

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            is_sel = idx in st.session_state.selecionados
            c_class = f"vencido-card {'card-selecionado' if is_sel else ''}"
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
            <div class='card-instrumento {c_class}'>
                <div class='badge-status {badge_class}'>{badge_text}</div>
                <div style="flex-grow: 1;">
                    <b style="font-size: 14px; line-height: 1.2;">{desc}</b><br>
                    <small style="color: #a0aabf;">TAG: {cod}</small>
                </div>
                <hr style='border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 10px 0;'>
                <div style="font-size: 12px; font-weight: 700; text-align: center; color: {cor_data};">{data_exibicao}</div>
            </div>"""
            st.markdown(html_card, unsafe_allow_html=True)
            
            if st.button("✅" if is_sel else "⭕", key=f"s_{suffix_nc}_{idx}", use_container_width=True):
                if is_sel: st.session_state.selecionados.remove(idx)
                else: st.session_state.selecionados.append(idx)
                st.rerun()

elif menu == "⚙️ Ajustes":
    st.markdown("### ⚙️ Ajustes de Sistema")
    novos = st.text_input("E-mails para recebimento de alertas (separe por vírgula):", value=st.session_state.config_emails)
    if st.button("Salvar Configurações", type="primary"):
        st.session_state.config_emails = novos
        salvar_config(novos)
        st.success("Configuração salva com sucesso!")
