import pandas as pd
import pyodbc

# Função de conexão ao banco de dados
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
        print("Conexão com o banco de dados estabelecida com sucesso.")
        return connection
    except pyodbc.Error as e:
        raise Exception(f"Erro ao conectar ao banco de dados: {str(e)}")


# Caminho para o arquivo Excel
# excel_file_path = 'static/scaui960e.xlsx'  # ajuste conforme o nome real do arquivo

# Definir o tamanho máximo permitido para as colunas no banco de dados
TAMANHO_MAXIMO_CODIGO = 99  # Tamanho máximo da coluna cod_item
TAMANHO_MAXIMO_DESCRICAO = 254  # Tamanho máximo da coluna descricao_item

# Contadores
linha_atual = 0
insercoes_realizadas = 0


# Função para verificar se o código já existe no banco de dados
def codigo_existe(codigo, cursor):
    try:
        cursor.execute("SELECT COUNT(*) FROM dbo.cadastro_itens WHERE cod_item = ?", (codigo,))
        result = cursor.fetchone()
        return result[0] > 0
    except pyodbc.Error as e:
        print(f"Erro ao verificar o código {codigo}: {e}")
        return False


# Estabelecendo a conexão com o banco de dados
try:
    connection = conectar_db()
    cursor = connection.cursor()
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
    exit(1)

# Lendo o arquivo Excel e processando os dados
try:
    df = pd.read_excel(excel_file_path, header=None, dtype=str)  # Ler o arquivo Excel como strings
    for index, row in df.iterrows():
        linha_atual += 1
        try:
            # Garantindo que a linha seja corretamente dividida em duas colunas (código e descrição)
            if isinstance(row[0], str):
                coluna_completa = row[0].split(",")  # Dividindo a linha completa por vírgula
                if len(coluna_completa) >= 2:
                    codigo = coluna_completa[0].strip()[:TAMANHO_MAXIMO_CODIGO]
                    descricao = ",".join(coluna_completa[1:]).strip()[:TAMANHO_MAXIMO_DESCRICAO]
                else:
                    continue
            else:
                continue

            # Debug para verificar o comprimento real das strings
            print(f"Linha {linha_atual}: Código [{codigo}] (len={len(codigo)}), Descrição [{descricao}] (len={len(descricao)})")

            # Ignorar colunas vazias
            if codigo and descricao:
                if not codigo_existe(codigo, cursor):
                    try:
                        cursor.execute("""
                            INSERT INTO dbo.cadastro_itens (cod_item, descricao_item)
                            VALUES (?, ?)
                        """, (codigo, descricao))
                        connection.commit()
                        insercoes_realizadas += 1
                        print(f"Linha {linha_atual}: Código {codigo} inserido com sucesso.")
                    except pyodbc.Error as e:
                        print(f"Erro ao inserir o código {codigo}: {e}")
                else:
                    print(f"Linha {linha_atual}: Código {codigo} já existente.")
        except Exception as e:
            print(f"Erro ao processar a linha {linha_atual}: {e}")
except FileNotFoundError as e:
    print(f"Erro: Arquivo Excel não encontrado - {e}")
except Exception as e:
    print(f"Erro ao ler o arquivo Excel: {e}")

# Fechar a conexão com o banco de dados
try:
    cursor.close()
    connection.close()
    print("\nConexão com o banco de dados fechada com sucesso.")
except pyodbc.Error as e:
    print(f"Erro ao fechar a conexão com o banco de dados: {e}")

print(f"\nProcessamento concluído. {insercoes_realizadas} itens foram inseridos.")
