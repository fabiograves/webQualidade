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


# Função para corrigir a descrição de um item
def corrigir_descricao(descricao):
    # Remover a vírgula no final, se existir
    if descricao.endswith(','):
        descricao = descricao[:-1]
    # Remover aspas duplas no início e no final
    if descricao.startswith('"') and descricao.endswith('"'):
        descricao = descricao[1:-1]

    return descricao


# Estabelecendo a conexão com o banco de dados
try:
    connection = conectar_db()
    cursor = connection.cursor()
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
    exit(1)

# Atualizando as descrições
try:
    # Contador de atualizações
    atualizacoes_realizadas = 0
    # Selecionar todos os registros
    cursor.execute("SELECT cod_item, descricao_item FROM dbo.cadastro_itens")
    registros = cursor.fetchall()

    for registro in registros:
        cod_item = registro[0]
        descricao_item = registro[1]
        atualizacoes_realizadas += 1

        # Corrigir a descrição
        descricao_corrigida = corrigir_descricao(descricao_item)

        # Verificar se houve alteração
        if descricao_corrigida != descricao_item:
            try:
                # Atualizar a descrição no banco de dados
                cursor.execute("""
                    UPDATE dbo.cadastro_itens
                    SET descricao_item = ?
                    WHERE cod_item = ?
                """, (descricao_corrigida, cod_item))
                connection.commit()
                print(f"Código {cod_item}: Descrição atualizada com sucesso, Total: {atualizacoes_realizadas}.")
            except pyodbc.Error as e:
                print(f"Erro ao atualizar o código {cod_item}: {e}")
        else:
            print(f"Código {cod_item}: Nenhuma atualização necessária.")

except pyodbc.Error as e:
    print(f"Erro ao consultar os registros: {e}")

# Fechar a conexão com o banco de dados
try:
    cursor.close()
    connection.close()
    print("\nConexão com o banco de dados fechada com sucesso.")
except pyodbc.Error as e:
    print(f"Erro ao fechar a conexão com o banco de dados: {e}")
