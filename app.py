import streamlit as st
import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage
import json
import os
import requests
from dateutil.relativedelta import relativedelta

# --- CONFIGURAÇÃO E ENGINE VISUAL ---
st.set_page_config(page_title="Monitoramento de Instrumentos", layout="wide")

st.markdown("""
    <style>
    /* Fundo e Sidebar (Azul Marinho) */
    .stApp { background-color: #0a192f; color: #e0e0e0; }
    section[data-testid="stSidebar"] { background-color: #112240; border-right: 1px solid #233554; }
    
    /* 1. Botões Principais no Sidebar */
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

    /* 2. Sub-menu (Menu Acordeão) */
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

# --- CONEXÃO DIRETA COM OMIE ---
@st.cache_data(ttl=600, show_spinner=False)
def carregar_dados():
    app_key = "6531794134866"
    app_secret = "5d3f1060b0b5c474561b7e23adf747ef"
    
    df_final = pd.DataFrame()
    
    with st.spinner('Conectando ao OMIE e baixando a base de dados... Isso pode levar um minuto.'):
        # 1. Puxar Produtos (Código, Descrição e Características)
        url_produtos = "https://app.omie.com.br/api/v1/geral/produtos/"
        pagina = 1
        produtos_totais = []
        
        while True:
            payload = {
                "call": "ListarProdutos",
                "app_key": app_key,
                "app_secret": app_secret,
                "param": [{"pagina": pagina, "registros_por_pagina": 100, "apenas_importado_api": "N", "filtrar_apenas_omiepdv": "N"}]
            }
            try:
                resposta = requests.post(url_produtos, json=payload, timeout=15).json()
                
                if "faultstring" in resposta:
                    st.error(f"Erro OMIE (Produtos): {resposta['faultstring']}")
                    return pd.DataFrame()
                    
                if "produto_servico_cadastro" in resposta:
                    produtos_totais.extend(resposta["produto_servico_cadastro"])
                    
                if pagina >= resposta.get("total_de_paginas", 1): break
                pagina += 1
            except Exception as e: 
                st.error(f"Erro de conexão com a API de Produtos: {e}")
                return pd.DataFrame()

        df_produtos = pd.DataFrame([{
            "Código": p.get("codigo", ""), 
            "Descrição": p.get("descricao", ""),
            "Características": p.get("caracteristicas", "")
        } for p in produtos_totais])

        # 2. Puxar Estoque Físico Real
        url_estoque = "https://app.omie.com.br/api/v1/estoque/resumo/"
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        pagina_est = 1
        estoque_totais = []

        while True:
            payload_est = {
                "call": "ListarPosicaoEstoque",
                "app_key": app_key,
                "app_secret": app_secret,
                "param": [{"data_posicao": data_hoje, "pagina": pagina_est, "registros_por_pagina": 100}]
            }
            try:
                resp_est = requests.post(url_estoque, json=payload_est, timeout=15).json()
                
                if "faultstring" in resp_est:
                    st.error(f"Erro OMIE (Estoque): {resp_est['faultstring']}")
                    break

                if "produtos" in resp_est:
                    estoque_totais.extend(resp_est["produtos"])
                    
                if pagina_est >= resp_est.get("total_de_paginas", 1): break
                pagina_est += 1
            except Exception as e:
                st.error(f"Erro de conexão com a API de Estoque: {e}")
                break

        df_estoque = pd.DataFrame([{
            "Código": e.get("codigo", ""), 
            "Estoque Físico": e.
