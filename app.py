import pandas as pd
import re
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os

# 1. Busca as credenciais de segurança do GitHub
EMAIL_USUARIO = os.environ.get("EMAIL_USUARIO")
EMAIL_SENHA = os.environ.get("EMAIL_SENHA")
DESTINATARIOS = os.environ.get("DESTINATARIOS")

# URL da planilha
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

def extrair_data(texto):
    if pd.isna(texto): return None
    match = re.search(r'\d{2}/\d{2}/\d{4}', str(texto))
    return pd.to_datetime(match.group(0), dayfirst=True) if match else None

def rodar_verificacao():
    print("Iniciando varredura de instrumentos...")
    df = pd.read_csv(SHEET_URL)
    df.columns = [c.strip() for c in df.columns]
    col_caract = next((c for c in df.columns if 'CARACTER' in c.upper()), "Características")
    
    df['DATA_CALIBRACAO'] = df[col_caract].apply(extrair_data)
    df['DATA_STR'] = df['DATA_CALIBRACAO'].dt.strftime('%d/%m/%Y').fillna("N/A")
    
    hoje = datetime.now()
    df['DIAS_RESTANTES'] = (df['DATA_CALIBRACAO'] - hoje).dt.days
    df['STATUS'] = df['DIAS_RESTANTES'].apply(lambda d: "VENCIDO" if pd.notnull(d) and d < 0 else ("PRÓXIMO VENCIMENTO" if pd.notnull(d) and d <= 30 else "APTOS"))
    
    # Filtra apenas os que precisam de atenção
    df_criticos = df[df['STATUS'].isin(["VENCIDO", "PRÓXIMO VENCIMENTO"])]
    
    if not df_criticos.empty:
        print(f"Encontrados {len(df_criticos)} instrumentos críticos. Preparando e-mail...")
        enviar_email(df_criticos)
    else:
        print("Todos os instrumentos estão aptos. Nenhum e-mail enviado.")

def enviar_email(df_criticos):
    msg = EmailMessage()
    msg['Subject'] = f"🚨 ALERTA AUTOMÁTICO: {len(df_criticos)} Instrumentos Pendentes"
    msg['From'] = EMAIL_USUARIO
    msg['To'] = DESTINATARIOS
    
    conteudo = "Relatório Diário de Instrumentos Pendentes:\n\n"
    for _, row in df_criticos.iterrows():
        status = row['STATUS']
        conteudo += f"[{status}] - {row['Descrição']} (TAG: {row['Código']}) - Vencimento: {row['DATA_STR']}\n"
    
    msg.set_content(conteudo)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USUARIO, EMAIL_SENHA)
        smtp.send_message(msg)
        print("E-mail disparado com sucesso!")

if __name__ == "__main__":
    rodar_verificacao()
