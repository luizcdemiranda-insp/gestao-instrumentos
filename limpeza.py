import pandas as pd

# 1. URL da sua planilha original
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQTJGqK9uyb4mOwVMnRPdK1ugpXQHeYaEXeXnjYCx6_QfFNmkQ0i7Y5uMC-8QSeMPKMs_9IlywVqayM/pub?output=csv"

print("Baixando dados da planilha...")
df = pd.read_csv(SHEET_URL)
df.columns = [c.strip() for c in df.columns]

# 2. Palavras-chave para identificar o "Lixo" (Mobiliário, ferramentas genéricas, escritório)
# Você pode adicionar mais palavras a esta lista conforme necessário
termos_descarte = [
    'mesa', 'cadeira', 'armário', 'chave de fenda', 'chave phillips', 
    'martelo', 'alicate', 'parafusadeira', 'broca', 'gaveteiro', 
    'estante', 'esmerilhadeira', 'furadeira', 'computador', 'monitor'
]

# 3. Função para classificar cada linha
def classificar_item(descricao):
    descricao = str(descricao).lower()
    for termo in termos_descarte:
        if termo in descricao:
            return 'Lixo'
    return 'Instrumento'

# 4. Aplicar a classificação
df['Classificação'] = df['Descrição'].apply(classificar_item)

# 5. Separar os dados em duas tabelas diferentes
df_instrumentos = df[df['Classificação'] == 'Instrumento'].drop(columns=['Classificação'])
df_lixo = df[df['Classificação'] == 'Lixo'].drop(columns=['Classificação'])

# 6. Gerar o arquivo Excel com duas abas
nome_arquivo = 'base_dados_tempermar_higienizada.xlsx'

print("Gerando arquivo Excel...")
# É necessário ter a biblioteca 'openpyxl' instalada (pip install openpyxl)
with pd.ExcelWriter(nome_arquivo, engine='openpyxl') as writer:
    df_instrumentos.to_excel(writer, sheet_name='Instrumentos', index=False)
    df_lixo.to_excel(writer, sheet_name='Não-Instrumentos', index=False)

print(f"Sucesso! O arquivo '{nome_arquivo}' foi salvo na pasta atual.")
