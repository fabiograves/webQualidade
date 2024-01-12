from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_session import Session
import pymysql

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração da extensão Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Configurações do banco de dados (Considere usar variáveis de ambiente para segurança)
db_host = 'ars.mysql.uhserver.com'
db_user = 'ars_qualidade'
db_password = 'q1w2e3r4@'
db_name = 'ars_qualidade'

def conectar_db():
    # Função para conectar ao banco de dados
    return pymysql.connect(host=db_host, user=db_user, password=db_password, db=db_name, cursorclass=pymysql.cursors.DictCursor)

def is_logged_in():
    return 'logged_in' in session

def is_logged_in():
    """Verifica se o usuário está logado."""
    return 'logged_in' in session
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['senha']

        connection = conectar_db()
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE nome_usuario = %s AND senha_usuario = %s', (username, password))
        user = cursor.fetchone()
        connection.close()

        if user:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Login falhou. Verifique seu nome de usuário e senha.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Você saiu com sucesso.')
    return redirect(url_for('login'))

@app.route('/')
def home():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/base')
def base():
    # Renderize o template 'base.html'
    return render_template('base.html')

@app.route('/pesquisar_certificado', methods=['GET', 'POST'])
def pesquisar_certificado():
    resultados = None
    if request.method == 'POST':
        # Extraia os dados do formulário
        numero_nota = request.form.get('pc_numero_nota')
        codigo_fornecedor = request.form.get('pc_codigo_fornecedor')
        codigo_produto = request.form.get('pc_codigo_produto')
        corrida = request.form.get('pc_corrida')

        # Busque os resultados do banco de dados
        resultados = buscar_certificados(numero_nota, codigo_fornecedor, codigo_produto, corrida)

    print("Enviando para o template:", resultados)  # Adicione esta linha para depuração
    return render_template('pesquisar_certificado.html', resultados=resultados)



def buscar_certificados(numero_nota, codigo_fornecedor, codigo_produto, corrida):
    connection = conectar_db()
    try:
        resultados_agrupados = {}

        with connection.cursor() as cursor:
            # Busca por cadastro de certificados
            sql = "SELECT * FROM cadastro_certificados WHERE cc_numero_nota = %s OR cc_cod_fornecedor = %s OR cc_cod_produto = %s OR cc_corrida = %s"
            cursor.execute(sql, (numero_nota, codigo_fornecedor, codigo_produto, corrida))
            cadastros = cursor.fetchall()

            for cadastro in cadastros:
                numero = cadastro['cc_numero_nota']
                if numero not in resultados_agrupados:
                    resultados_agrupados[numero] = {'cadastro_certificados': cadastro, 'comp_quimica': [], 'prop_mecanicas': [], 'tratamentos': []}

                # Busca por composição química
                sql = "SELECT * FROM comp_quimica WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['comp_quimica'] = cursor.fetchone()  # fetchone em vez de fetchall

                # Busca por propriedades mecânicas
                sql = "SELECT * FROM prop_mecanicas WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['prop_mecanicas'] = cursor.fetchone()

                # Busca por tratamentos
                sql = "SELECT * FROM tratamentos WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['tratamentos'] = cursor.fetchone()

                # Busca analise dimensional porcas
                sql = "SELECT * FROM ad_porcas WHERE cc_numero_nota = %s"
                cursor.execute(sql,(numero,))
                resultados_agrupados[numero]['ad_porcas'] = cursor.fetchone()

                # Busca analise dimensional pinos
                sql = "SELECT * FROM ad_pinos WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['ad_pinos'] = cursor.fetchone()

                # Busca analise dimensional parafusos
                sql = "SELECT * FROM ad_parafusos WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['ad_parafusos'] = cursor.fetchone()

                # Busca analise dimensional grampos
                sql = "SELECT * FROM ad_grampos WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['ad_grampos'] = cursor.fetchone()

                # Busca analise dimensional arruelas
                sql = "SELECT * FROM ad_arruelas WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['ad_arruelas'] = cursor.fetchone()

                # Busca analise dimensional anel
                sql = "SELECT * FROM ad_anel WHERE cc_numero_nota = %s"
                cursor.execute(sql, (numero,))
                resultados_agrupados[numero]['ad_anel'] = cursor.fetchone()


    except Exception as e:
        print(f"Erro ao buscar certificados: {e}")
        resultados_agrupados = None
    finally:
        connection.close()

    print("Resultados encontrados:", resultados_agrupados)  # Para depuração
    return resultados_agrupados


@app.route('/pesquisar_registro_inspecao')
def pesquisar_registro_inspecao():
    return render_template('pesquisar_registro_inspecao.html')

@app.route('/cadastro_certificados', methods=['GET', 'POST'])
def cadastro_certificados():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':

        # Capturando os dados do formulário
        nota_fiscal = request.form.get('cc_numero_nota')
        # Verificando se pelo menos o campo 'cc_numero_nota' não está em branco
        if nota_fiscal.strip() == '':
            flash('O campo Nota Fiscal não pode estar em branco.')
            return redirect(url_for('cadastro_certificados'))

        descricao = request.form.get('cc_descricao')
        corrida = request.form.get('cc_corrida')
        data = request.form.get('cc_data')
        cq = request.form.get('cc_cq')
        cod_fornecedor = request.form.get('cc_cod_fornecedor')
        qtd_pedido = request.form.get('cc_qtd_pedidos')
        cod_produto = request.form.get('cc_cod_produto')

        # Montando o dicionário de dados
        dados_certificado = {
            'nota_fiscal': nota_fiscal,
            'descricao': descricao,
            'corrida': corrida,
            'data': data,
            'cq': cq,
            'cod_fornecedor': cod_fornecedor,
            'qtd_pedido': qtd_pedido,
            'cod_produto': cod_produto
        }

        # Chamando a função para inserir os dados no banco de dados
        inserir_cadastro_certificados(dados_certificado)

        # Composição Química
        comp_quimica = request.form.get('comp_quimica') == 'on'
        elementos_quimicos = {}
        if comp_quimica:
            elementos_quimicos = {
                'nota_fiscal': nota_fiscal,
                'c': request.form.get('cc_c'),
                'mn': request.form.get('cc_mn'),
                'p': request.form.get('cc_p'),
                's': request.form.get('cc_s'),
                'si': request.form.get('cc_si'),
                'ni': request.form.get('cc_ni'),
                'cr': request.form.get('cc_cr'),
                'b': request.form.get('cc_b'),
                'cu': request.form.get('cc_cu'),
                'mo': request.form.get('cc_mo'),
                'co': request.form.get('cc_co'),
                'ti': request.form.get('cc_ti'),
                'sn': request.form.get('cc_sn'),
                'al': request.form.get('cc_al'),
                'n': request.form.get('cc_n'),
                'nb': request.form.get('cc_nb')
            }
            inserir_cadastro_composicao_quimica(elementos_quimicos)

        # Propriedades Mecânicas
        prop_mecanicas = request.form.get('prop_mecanicas') == 'on'
        propriedades_mec = {}
        if prop_mecanicas:
            propriedades_mec = {
                'nota_fiscal': nota_fiscal,
                'escoamento': request.form.get('cc_escoamento'),
                'tracao': request.form.get('cc_tracao'),
                'reducao': request.form.get('cc_reducao'),
                'alongamento': request.form.get('cc_alongamento'),
                'dureza': request.form.get('cc_dureza'),
                'carga': request.form.get('cc_carga')
            }
            inserir_cadastro_propriedades_mecanicas(propriedades_mec)

        # Tratamentos
        tratamentos = request.form.get('tratamentos') == 'on'
        dados_tratamentos = {}
        if tratamentos:
            dados_tratamentos = {
                'nota_fiscal': nota_fiscal,
                'revenimento': request.form.get('cc_revenimento'),
                'termico': request.form.get('cc_termico'),
                'superficial': request.form.get('cc_superficial'),
                'macrografia': request.form.get('cc_macrografia'),
                'observacao': request.form.get('cc_observacao')
            }
            inserir_cadastro_tratamentos(dados_tratamentos)

        # Análise Dimensional
        analise_dimensional = request.form.get('analise_dimensional') == 'on'
        medidas_dimensionais = {}
        if analise_dimensional:
            tipo_analise = request.form.get('selecaoTipo')
            print("Tipo de Análise:", tipo_analise)
            if tipo_analise == 'parafusos':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'altura': request.form.get('cc_parafuso_altura'),
                    'chave': request.form.get('cc_parafuso_chave'),
                    'comprimento': request.form.get('cc_parafuso_comprimento'),
                    'diametro': request.form.get('cc_parafuso_diametro'),
                    'diametro_cabeca': request.form.get('cc_parafuso_diametro_cabeca'),
                    'comprimento_rosca': request.form.get('cc_parafuso_comprimento_rosca'),
                    'diametro_ponta': request.form.get('cc_parafuso_diametro_ponta')
                }
                inserir_cadastro_adparafusos(medidas_dimensionais)

            if tipo_analise == 'porcas':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'altura': request.form.get('cc_porcas_altura'),
                    'chave': request.form.get('cc_porcas_chave'),
                    'diametro': request.form.get('cc_porcas_diametro'),
                    'diametro_estrutura': request.form.get('cc_porcas_diametro_estrutura'),
                    'diametro_interno': request.form.get('cc_porcas_diametro_interno'),
                    'diametro_externo': request.form.get('cc_porcas_diametro_externo')
                }
                inserir_cadastro_adporcas(medidas_dimensionais)

            if tipo_analise == 'arruelas':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'altura': request.form.get('cc_arruelas_altura'),
                    'diametro_interno': request.form.get('cc_arruelas_diametro_interno'),
                    'diametro_externo': request.form.get('cc_arruelas_diametro_externo')
                }
                inserir_cadastro_adarruelas(medidas_dimensionais)

            if tipo_analise == 'anel':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'altura': request.form.get('cc_anel_altura'),
                    'diametro_interno': request.form.get('cc_anel_diametro_interno'),
                    'diametro_externo': request.form.get('cc_anel_diametro_externo')
                }
                inserir_cadastro_adanel(medidas_dimensionais)

            if tipo_analise == 'grampos':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'comprimento': request.form.get('cc_grampos_comprimento'),
                    'diametro': request.form.get('cc_grampos_diametro')
                }
                inserir_cadastro_adgrampos(medidas_dimensionais)

            if tipo_analise == 'pinos':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'espessura': request.form.get('cc_pinos_espessura'),
                    'comprimento': request.form.get('cc_pinos_comprimento'),
                    'diametro': request.form.get('cc_pinos_diametro'),
                    'diametro_cabeca': request.form.get('cc_pinos_diametro_cabeca'),
                    'diametro_interno': request.form.get('cc_pinos_diametro_interno'),
                    'diametro_externo': request.form.get('cc_pinos_diametro_externo')
                }
                inserir_cadastro_adpinos(medidas_dimensionais)

        flash('Formulário enviado com sucesso!')
        return redirect(url_for('cadastro_certificados'))

    return render_template('cadastro_certificados.html')

def inserir_cadastro_certificados(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO cadastro_certificados 
            (cc_numero_nota, cc_descricao, cc_cod_fornecedor, cc_cod_produto, cc_corrida, cc_data, cc_cq, cc_qtd_pedidos)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['descricao'],
                dados['cod_fornecedor'],
                dados['cod_produto'],
                dados['corrida'],
                dados['data'],
                dados['cq'],
                dados['qtd_pedido']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_composicao_quimica(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO comp_quimica
            (cc_numero_nota, cc_c, cc_mn, cc_p, cc_s, cc_si, cc_ni, cc_cr, cc_b, cc_cu, cc_mo, cc_co, cc_ti, cc_sn, cc_al, cc_n, cc_nb)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['c'],
                dados['mn'],
                dados['p'],
                dados['s'],
                dados['si'],
                dados['ni'],
                dados['cr'],
                dados['b'],
                dados['cu'],
                dados['mo'],
                dados['co'],
                dados['ti'],
                dados['sn'],
                dados['al'],
                dados['n'],
                dados['nb']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_propriedades_mecanicas(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO prop_mecanicas
            (cc_numero_nota, cc_escoamento, cc_tracao, cc_reducao, cc_alongamento, cc_dureza, cc_carga)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['escoamento'],
                dados['tracao'],
                dados['reducao'],
                dados['alongamento'],
                dados['dureza'],
                dados['carga']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_tratamentos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO tratamentos
            (cc_numero_nota, cc_revenimento, cc_termico, cc_superficial, cc_macrografia, cc_observacao)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['revenimento'],
                dados['termico'],
                dados['superficial'],
                dados['macrografia'],
                dados['observacao']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_adparafusos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO ad_parafusos
            (cc_numero_nota, cc_adparafusos_altura, cc_adparafusos_chave, cc_adparafusos_comprimento, cc_adparafusos_diametro,
            cc_adparafusos_diametro_cabeca, cc_adparafusos_comprimento_rosca, cc_adparafusos_diametro_ponta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['altura'],
                dados['chave'],
                dados['comprimento'],
                dados['diametro'],
                dados['diametro_cabeca'],
                dados['comprimento_rosca'],
                dados['diametro_ponta']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_adporcas(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO ad_porcas
            (cc_numero_nota, cc_adporcas_altura, cc_adporcas_chave, cc_adporcas_diametro, cc_adporcas_diametro_estrutura, cc_adporcas_diametro_interno, cc_adporcas_diametro_externo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['altura'],
                dados['chave'],
                dados['diametro'],
                dados['diametro_estrutura'],
                dados['diametro_interno'],
                dados['diametro_externo']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_adarruelas(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO ad_arruelas
            (cc_numero_nota, cc_adarruelas_altura, cc_adarruelas_diametro_interno, cc_adarruelas_diametro_externo)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['altura'],
                dados['diametro_interno'],
                dados['diametro_externo']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_adanel(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO ad_anel
            (cc_numero_nota, cc_adanel_altura, cc_adanel_diametro_interno, cc_adanel_diametro_externo)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['altura'],
                dados['diametro_interno'],
                dados['diametro_externo']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_adgrampos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO ad_grampos
            (cc_numero_nota, cc_adgrampos_comprimento, cc_adgrampos_diametro)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['comprimento'],
                dados['diametro']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_adpinos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO ad_pinos
            (cc_numero_nota, cc_adpinos_espessura, cc_adpinos_comprimento, cc_adpinos_diametro, cc_adpinos_diametro_cabeca, cc_adpinos_diametro_interno, cc_adpinos_diametro_externo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['espessura'],
                dados['comprimento'],
                dados['diametro'],
                dados['diametro_cabeca'],
                dados['diametro_interno'],
                dados['diametro_externo']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()



@app.route('/registro_inspecao', methods=['GET', 'POST'])
def registro_inspecao():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Capturando os dados do formulário
        fornecedor = request.form.get('ri_fornecedor')
        nota_fiscal = request.form.get('ri_nota_fiscal')

        # Verificando se pelo menos o campo 'ri_nota_fiscal' não está em branco
        if nota_fiscal.strip() == '':
            flash('O campo Nota Fiscal não pode estar em branco.')
            return redirect(url_for('registro_inspecao'))

        pedido_compra = request.form.get('ri_pedido_compra')
        item = request.form.get('ri_item')
        quantidade_total = request.form.get('ri_quantidade_total')
        volume = request.form.get('ri_volume')
        desenho = request.form.get('ri_desenho')
        medidas_a = request.form.get('ri_medidas_a')
        medidas_b = request.form.get('ri_medidas_b')
        medidas_c = request.form.get('ri_medidas_c')
        medidas_d = request.form.get('ri_medidas_d')
        medidas_prosca = request.form.get('ri_medidas_prosca')
        conversao_e = request.form.get('ri_conversao_e')
        conversao_f = request.form.get('ri_conversao_f')
        conversao_g = request.form.get('ri_conversao_g')
        conversao_h = request.form.get('ri_conversao_h')
        acabamento = request.form.get('ri_acabamento')
        dureza = request.form.get('ri_dureza')
        a = request.form.get('ri_a')
        c = request.form.get('ri_c')
        r = request.form.get('ri_r')
        resp_inspecao = request.form.get('ri_resp_inspecao')
        data = request.form.get('ri_data')

        # Conectar ao banco de dados e inserir os dados
        try:
            connection = conectar_db()
            cursor = connection.cursor()

            # Substitua por sua própria consulta SQL e colunas da tabela
            sql = """INSERT INTO registro_inspecao (ri_fornecedor, ri_nota_fiscal, ri_pedido_compra, ri_item, ri_quantidade_total, ri_volume, ri_desenho, ri_medidas_a, ri_medidas_b, ri_medidas_c, ri_medidas_d, ri_medidas_prosca, ri_conversao_e, ri_conversao_f, ri_conversao_g, ri_conversao_h, ri_acabamento, ri_dureza, ri_a, ri_c, ri_r, ri_resp_inspecao, ri_data) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (
            fornecedor, nota_fiscal, pedido_compra, item, quantidade_total, volume, desenho, medidas_a, medidas_b,
            medidas_c, medidas_d, medidas_prosca, conversao_e, conversao_f, conversao_g, conversao_h, acabamento,
            dureza, a, c, r, resp_inspecao, data))

            connection.commit()
        finally:
            connection.close()

        flash('Registro de Inspeção criado com sucesso!')
        return redirect(url_for('registro_inspecao'))

    return render_template('registro_inspecao.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)

#if __name__ == '__main__':
#    app.run(debug=True)
