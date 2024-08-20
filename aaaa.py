import os
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


def inserir_xml_no_bd(caminho_pasta, conn):
    cursor = conn.cursor()
    erros = []
    nao_encontrados = []
    total_processados = 0
    total_inseridos = 0

    for arquivo in os.listdir(caminho_pasta):
        if arquivo.endswith('.xml'):
            caminho_arquivo = os.path.join(caminho_pasta, arquivo)
            nome_arquivo = os.path.splitext(arquivo)[0]  # Remove a extensão .xml

            try:
                # Ler o conteúdo do arquivo XML como binário
                with open(caminho_arquivo, 'rb') as file:
                    conteudo_xml = file.read()

                # Verificar se o arquivo existe no banco de dados
                cursor.execute("""
                    SELECT id FROM dbo.cadastro_notas_fiscais WHERE cad_cod_xml = ?
                """, nome_arquivo)
                registro = cursor.fetchone()

                if registro:
                    # Se o registro existir, atualize o campo cad_arquivo_xml
                    cursor.execute("""
                        UPDATE dbo.cadastro_notas_fiscais
                        SET cad_arquivo_xml = ?
                        WHERE id = ?
                    """, conteudo_xml, registro[0])
                    total_inseridos += 1
                    print(f"Arquivo {nome_arquivo} inserido no banco de dados.")
                else:
                    # Adiciona o nome do arquivo à lista de não encontrados
                    nao_encontrados.append(nome_arquivo)
                    print(f"Registro não encontrado para o arquivo {nome_arquivo}.")

            except Exception as e:
                erros.append(f"Erro ao processar o arquivo {nome_arquivo}: {e}")
                print(f"Erro ao processar o arquivo {nome_arquivo}: {e}")

            total_processados += 1
            print(f"Processando {nome_arquivo}... ({total_processados})")

    conn.commit()
    cursor.close()

    print(f"Total de arquivos processados: {total_processados}")
    print(f"Total de arquivos inseridos no banco de dados: {total_inseridos}")

    # Escrever os arquivos que não foram encontrados em um arquivo de texto
    if nao_encontrados:
        with open("nao_encontrados.txt", "w") as file:
            for nome in nao_encontrados:
                file.write(nome + "\n")

    for item in erros:
        print(item)


def main():
    caminho_pasta_xml = './static/XML TEST'

    conn = conectar_db()

    inserir_xml_no_bd(caminho_pasta_xml, conn)

    conn.close()

if __name__ == "__main__":
    main()
