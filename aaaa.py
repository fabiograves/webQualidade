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

import pandas as pd

def limpar_dados(df):
    df = df.copy()

    # Converter campos de data para o formato correto, tratando tanto números de série quanto strings de data
    campos_data = ['DataEmissao', 'DataEntradaARS']
    for campo in campos_data:
        df[campo] = df[campo].apply(lambda x: tratar_data(x))

    # Remover espaços dos códigos XML
    df['XML'] = df['XML'].apply(lambda x: str(x).replace(' ', '') if pd.notnull(x) else '')

    # Converter todas as colunas para string
    cols = ['DataEmissao', 'PEDIDO', 'Nota', 'DataEntradaARS', 'FORNECEDOR', 'VOLUME',
            'PESO', 'Natureza', 'XML', 'CERTIFICADO ', 'OBS', 'LANÇAMENTO / Viviane ']
    for col in cols:
        df[col] = df[col].apply(lambda x: str(x) if pd.notnull(x) else '')

    return df

def tratar_data(data):
    try:
        # Verificar se o valor é numérico (número de série do Excel)
        if pd.isnull(data):
            return ''
        elif isinstance(data, (int, float)):
            # Converter de número de série para data
            data = pd.to_datetime(data, origin='1899-12-30', unit='D')
        else:
            # Converter de string no formato BR para data
            data = pd.to_datetime(data, format='%d/%m/%Y', errors='coerce')
        return data.strftime('%Y-%m-%d') if pd.notnull(data) else ''
    except Exception as e:
        print(f"Erro ao tratar a data: {data} - {e}")
        return ''

def inserir_dados(df, conn):
    cursor = conn.cursor()
    erros = []
    for index, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO dbo.cadastro_notas_fiscais (cad_data_emissao_nf, cad_pedido, cad_numero_nota, 
                cad_data_entrada_ars, cad_fornecedor, cad_volume, cad_peso, cad_natureza, cad_cod_xml, 
                cad_certificado, cad_observacao, cad_lancamento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, row['DataEmissao'], row['PEDIDO'], row['Nota'], row['DataEntradaARS'], row['FORNECEDOR'],
                           row['VOLUME'], row['PESO'], row['Natureza'], row['XML'], row['CERTIFICADO '],
                           row['OBS'], row['LANÇAMENTO / Viviane ']
                           )
            print(f"Executando linha: {index + 1}")
        except Exception as e:
            erros.append(f"Erro ao inserir a linha {index + 1}: {e} - Dados: {row.to_dict()}")
            print(f"Erro ao inserir a linha {index + 1}: {e} - Dados: {row.to_dict()}")
    conn.commit()
    cursor.close()
    for item in erros:
        print(item)

def main():
    caminho_arquivo = './static/NotasFiscais.xlsx'
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
