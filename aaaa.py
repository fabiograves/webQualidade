import pandas as pd
import pyodbc

def conectar_db():
    driver = '{ODBC Driver 17 for SQL Server}'
    server = "172.16.2.27"
    database = "dbQualidade"
    username = "Qualidade"
    password = "y2%:ff4G4A>7"
    connectionString = (f'DRIVER={driver};SERVER={server},1433;DATABASE={database};UID={username};'
                        f'PWD={password};Encrypt=yes;TrustServerCertificate=yes;')

    try:
        connection = pyodbc.connect(connectionString)
        return connection
    except Exception as e:
        raise Exception(f"Erro ao conectar ao banco de dados: {e}")

def limpar_dados(df):
    df = df.copy()
    df['Cod'] = df['Cod'].apply(lambda x: str(x) if pd.notnull(x) else '')
    df['Desc.Prod.'] = df['Desc.Prod.'].apply(lambda x: str(x) if pd.notnull(x) else '')
    return df

def inserir_dados(df, conn):
    cursor = conn.cursor()
    for index, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO dbo.cadastro_itens (cod_item, descricao_item)
                VALUES (?, ?)
            """, row['Cod'], row['Desc.Prod.'])
            print(f"Executando linha: {index + 1}")
        except Exception as e:
            print(f"Erro ao inserir a linha {index + 1}: {e} - Dados: {row.to_dict()}")
    conn.commit()
    cursor.close()

def main():
    caminho_arquivo = './static/itens ars.xlsx'
    df = pd.read_excel(caminho_arquivo)

    linha_inicial = int(input("Digite a linha inicial: "))
    linha_final = int(input("Digite a linha final: "))

    if linha_final > len(df):
        linha_final = len(df)

    df_filtrado = df.iloc[linha_inicial-1:linha_final]

    df_filtrado = limpar_dados(df_filtrado)

    conn = conectar_db()

    inserir_dados(df_filtrado, conn)

    conn.close()

if __name__ == "__main__":
    main()
