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
    
    /* 1. Botões Principais no Sidebar (Destaque Laranja) */
    section[data-testid="stSidebar"] div.stButton > button {
        background-color: #112240; border: 1px solid #233554; padding: 12px 20px;
        border-radius: 8px; font-weight: bold; transition: 0.3s;
        justify-content: flex-start; text-align: left; color: #b0b4c4; width: 100%;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover { border-color: #ff9800; color: white; }
    
    /* Força a cor laranja para o botão selecionado (Primary) */
    section[data-testid="stSidebar"] div.stButton > button[data-testid="baseButton-primary"] {
        background-color: #ff9800 !important; 
        color: white !important; 
        border-color: #ff9800 !important;
        box-shadow: 0 0 15px rgba(255, 152, 0, 0.5) !important;
    }

    /* 2. Sub-menu (Menu Acordeão) */
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

    /* Indicadores e Cards */
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

import requests # Adicione isso no topo do seu arquivo app.py junto com os outros imports

# --- CONEXÃO DIRETA COM O OMIE ---
@st.cache_data(ttl=600) # Mantém os dados na memória por 10 minutos para não travar o Omie
def carregar_dados():
    app_key = "6531794134866"
    app_secret = "5d3f1060b0b5c474561b7e23adf747ef"
    url_omie = "https://app.omie.com.br/api/v1/geral/produtos/"
    
    pagina = 1
    produtos_totais = []
    
    # O Omie entrega os produtos em "páginas". Este loop baixa todas as páginas automaticamente.
    while True:
        payload = {
            "call": "ListarProdutos",
            "app_key": app_key,
            "app_secret": app_secret,
            "param": [{
                "pagina": pagina,
                "registros_por_pagina": 100,
                "apenas_importado_api": "N",
                "filtrar_apenas_omiepdv": "N"
            }]
        }
        
        try:
            resposta = requests.post(url_omie, json=payload).json()
            
            if "produto_servico_cadastro" in resposta:
                produtos_totais.extend(resposta["produto_servico_cadastro"])
                
            # Se chegamos na última página, encerra a busca
            if pagina >= resposta.get("total_de_paginas", 1):
                break
                
            pagina += 1
            
        except Exception as e:
            st.error(f"Erro ao conectar com o OMIE: {e}")
            return pd.DataFrame()

    # Transforma os dados brutos do Omie no formato que nosso sistema já conhece
    lista_formatada = []
    for p in produtos_totais:
        lista_formatada.append({
            "Código": p.get("codigo_produto", ""),
            "Descrição": p.get("descricao", ""),
            "Características": p.get("observacao", ""), # <-- Precisamos confirmar este campo
            "Estoque Físico": 1 # <-- Placeholder temporário (explicado abaixo)
        })
        
    return pd.DataFrame(lista_formatada)

# --- INICIALIZAÇÃO E NAVEGAÇÃO ---
if 'modulo_ativo' not in st.session_state: st.session_state.modulo_ativo = "METROLOGIA"
if 'pagina_ativa' not in st.session_state: st.session_state.pagina_ativa = "🛠️ Visão Geral"

df = processar_dados(carregar_dados())
st.sidebar.markdown("<h3 style='color: white;'>MONITORAMENTO TEMPERMAR</h3>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Módulo Metrologia
btn_metro_type = "primary" if st.session_state.modulo_ativo == "METROLOGIA" else "secondary"
if st.sidebar.button("📏 METROLOGIA", use_container_width=True, type=btn_metro_type):
    st.session_state.modulo_ativo = "METROLOGIA"
    st.session_state.pagina_ativa = "🛠️ Visão Geral"
    st.rerun()

if st.session_state.modulo_ativo == "METROLOGIA":
    paginas_metro = ["🛠️ Visão Geral", "✅ APTOS", "⏳ Próximos de vencer", "🚨 VENCIDOS", "⚙️ Ajustes"]
    idx = paginas_metro.index(st.session_state.pagina_ativa) if st.session_state.pagina_ativa in paginas_metro else 0
    escolha = st.sidebar.radio("SubMetro", paginas_metro, index=idx, label_visibility="collapsed")
    if escolha != st.session_state.pagina_ativa:
        st.session_state.pagina_ativa = escolha
        st.rerun()

# Módulo Consulta EC
btn_ec_type = "primary" if st.session_state.modulo_ativo == "CONSULTA EC" else "secondary"
if st.sidebar.button("🔍 CONSULTA EC", use_container_width=True, type=btn_ec_type):
    st.session_state.modulo_ativo = "CONSULTA EC"
    st.session_state.pagina_ativa = "✅ DISPONÍVEIS"
    st.rerun()

if st.session_state.modulo_ativo == "CONSULTA EC":
    paginas_ec = ["✅ DISPONÍVEIS", "❌ FORA ESTOQUE"]
    idx = paginas_ec.index(st.session_state.pagina_ativa) if st.session_state.pagina_ativa in paginas_ec else 0
    escolha = st.sidebar.radio("SubEC", paginas_ec, index=idx, label_visibility="collapsed")
    if escolha != st.session_state.pagina_ativa:
        st.session_state.pagina_ativa = escolha
        st.rerun()

st.sidebar.markdown("---")
menu = st.session_state.pagina_ativa

# --- PÁGINAS ---
if menu == "🛠️ Visão Geral":
    st.markdown("### 🛠️ Visão Geral de Metrologia")
    c1, c2, c3 = st.columns(3)
    with c1: render_mini_kpi("Aptos", len(df[df['STATUS'] == 'APTOS']), "apto-kpi")
    with c2: render_mini_kpi("Atenção", len(df[df['STATUS'] == 'PRÓXIMO VENCIMENTO']), "proximo-kpi")
    with c3: render_mini_kpi("Vencidos", len(df[df['STATUS'] == 'VENCIDO']), "vencido-kpi")
    st.dataframe(df, use_container_width=True)

elif menu in ["✅ APTOS", "✅ DISPONÍVEIS", "❌ FORA ESTOQUE"]:
    classe_card = "apto-card" if menu != "❌ FORA ESTOQUE" else "vencido-card"
    st.markdown(f"### {menu}")
    
    fn, fc, fd = sistema_filtros(menu, True)
    df_f = df[df['STATUS'] == 'APTOS']
    
    # Lógica de Estoque
    if menu == "✅ DISPONÍVEIS": df_f = df_f[df_f['_ESTOQUE_VAL'] > 0]
    if menu == "❌ FORA ESTOQUE": df_f = df_f[df_f['_ESTOQUE_VAL'] <= 0]
    
    if fn: df_f = df_f[df_f['Descrição'].str.contains(fn, case=False, na=False)]
    if fc: df_f = df_f[df_f['Código'].str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].str.contains(fd, case=False, na=False)]
    
    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            st.markdown(f"<div class='card-instrumento {classe_card}'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br>📅 {row['DATA_STR']}</div>", unsafe_allow_html=True)

elif menu in ["⏳ Próximos de vencer", "🚨 VENCIDOS"]:
    status_alvo = "PRÓXIMO VENCIMENTO" if menu == "⏳ Próximos de vencer" else "VENCIDO"
    st.markdown(f"### {menu}")
    fn, fc, fd = sistema_filtros(menu, True)
    df_f = df[df['STATUS'] == status_alvo]
    
    if fn: df_f = df_f[df_f['Descrição'].str.contains(fn, case=False, na=False)]
    if fc: df_f = df_f[df_f['Código'].str.contains(fc, case=False, na=False)]
    if fd: df_f = df_f[df_f['DATA_STR'].str.contains(fd, case=False, na=False)]

    if menu == "🚨 VENCIDOS":
        if st.button("🚨 Alerta em Lote", use_container_width=True):
            if not st.session_state.selecionados:
                popup_confirmar_envio(len(df[df['STATUS']=='PRÓXIMO VENCIMENTO']), len(df[df['STATUS']=='VENCIDO']), df[df['STATUS'].isin(['VENCIDO','PRÓXIMO VENCIMENTO'])])
            else:
                enviar_email_consolidado(st.session_state.config_emails, df.loc[st.session_state.selecionados])
                st.success("Enviado!")

    cols = st.columns(4)
    for i, (idx, row) in enumerate(df_f.iterrows()):
        with cols[i % 4]:
            is_sel = idx in st.session_state.selecionados
            c_class = f"{'vencido-card' if menu=='🚨 VENCIDOS' else 'proximo-card'} {'card-selecionado' if is_sel else ''}"
            st.markdown(f"<div class='card-instrumento {c_class}'><b>{row['Descrição'][:25]}</b><br><small>{row['Código']}</small><br>{row['DATA_STR']}</div>", unsafe_allow_html=True)
            if st.button("✅" if is_sel else "⭕", key=f"s_{idx}"):
                if is_sel: st.session_state.selecionados.remove(idx)
                else: st.session_state.selecionados.append(idx)
                st.rerun()

elif menu == "⚙️ Ajustes":
    st.markdown("### ⚙️ Ajustes de E-mail")
    novos = st.text_input("Lista de e-mails:", value=st.session_state.config_emails)
    if st.button("Salvar"):
        st.session_state.config_emails = novos
        salvar_config(novos)
        st.success("Configuração salva!")
