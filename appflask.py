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

@app.route('/cadastro_certificados', methods=['GET', 'POST'])
def cadastro_certificados():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':

        # Capturando os dados do formulário
        nota_fiscal = request.form.get('cc_numero_nota')
        # Verificando se pelo menos o campo 'ri_nota_fiscal' não está em branco
        if nota_fiscal.strip() == '':
            flash('O campo Nota Fiscal não pode estar em branco.')
            return redirect(url_for('cadastro_certificados'))
        descricao = request.form.get('cc_descricao')
        corrida = request.form.get('cc_corrida')
        data = request.form.get('cc_data')
        cq = request.form.get('cc_cq')
        cod_fornecedor = request.form.get('cc_cod_fornecedor')
        qtd_pedido = request.form.get('cc_qtd_pedido')
        cod_produto = request.form.get('cc_cod_produto')

        # Composição Química
        comp_quimica = request.form.get('comp_quimica') == 'on'
        elementos_quimicos = {}
        if comp_quimica:
            elementos_quimicos = {
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

        # Propriedades Mecânicas
        prop_mecanicas = request.form.get('prop_mecanicas') == 'on'
        propriedades_mec = {}
        if prop_mecanicas:
            propriedades_mec = {
                'escoamento': request.form.get('cc_escoamento'),
                'tracao': request.form.get('cc_tracao'),
                'reducao': request.form.get('cc_reducao'),
                'alongamento': request.form.get('cc_alongamento'),
                'dureza': request.form.get('cc_dureza'),
                'carga': request.form.get('cc_carga')
            }

        # Tratamentos
        tratamentos = request.form.get('tratamentos') == 'on'
        dados_tratamentos = {}
        if tratamentos:
            dados_tratamentos = {
                'revenimento': request.form.get('cc_revenimento'),
                'termico': request.form.get('cc_termico'),
                'superficial': request.form.get('cc_superficial'),
                'macrografia': request.form.get('cc_macrografia'),
                'observacao': request.form.get('cc_observacao')
            }

        # Análise Dimensional
        analise_dimensional = request.form.get('analise_dimensional') == 'on'
        medidas_dimensionais = {}
        if analise_dimensional:
            tipo_analise = request.form.get('selecaoTipo')
            if tipo_analise == 'parafusos':
                medidas_dimensionais = {
                    'altura': request.form.get('cc_parafuso_altura'),
                    'chave': request.form.get('cc_parafuso_chave'),
                    'comprimento': request.form.get('cc_parafuso_comprimento'),
                    'diametro': request.form.get('cc_parafuso_diametro'),
                    'diametro_cabeca': request.form.get('cc_parafuso_diametro_cabeca'),
                    'comprimento_rosca': request.form.get('cc_parafuso_comprimento_rosca'),
                    'diametro_ponta': request.form.get('cc_parafuso_diametro_ponta')
                }
            if tipo_analise == 'porcas':
                medidas_dimensionais = {
                    'altura': request.form.get('cc_porcas_altura'),
                    'chave': request.form.get('cc_porcas_chave'),
                    'diametro': request.form.get('cc_porcas_diametro'),
                    'diametro_estrutura': request.form.get('cc_porcas_diametro_estrutura'),
                    'diametro_interno': request.form.get('cc_porcas_diametro_interno'),
                    'diametro_externo': request.form.get('cc_porcas_diametro_externo')
                }
            if tipo_analise == 'arruelas':
                medidas_dimensionais = {
                    'altura': request.form.get('cc_arruelas_altura'),
                    'diametro_interno': request.form.get('cc_arruelas_diametro_interno'),
                    'diametro_externo': request.form.get('cc_arruelas_diametro_externo')
                }
            if tipo_analise == 'anel':
                medidas_dimensionais = {
                    'altura': request.form.get('cc_anel_altura'),
                    'diametro_interno': request.form.get('cc_anel_diametro_interno'),
                    'diametro_externo': request.form.get('cc_anel_diametro_externo')
                }
            if tipo_analise == 'grampos':
                medidas_dimensionais = {
                    'comprimento': request.form.get('cc_grampos_comprimento'),
                    'medida_b': request.form.get('cc_grampos_diametro')
                }
            if tipo_analise == 'pinos':
                medidas_dimensionais = {
                    'espessura': request.form.get('cc_pinos_espessura'),
                    'comprimento': request.form.get('cc_pinos_comprimento'),
                    'diametro': request.form.get('cc_pinos_diametro'),
                    'diametro_cabeca': request.form.get('cc_pinos_diametro_cabeca'),
                    'diametro_interno': request.form.get('cc_pinos_diametro_interno'),
                    'diametro_externo': request.form.get('cc_pinos_diametro_externo')
                }
        # Aqui você pode usar os dados coletados para salvar no banco de dados ou processar de acordo com a necessidade
        # Por exemplo, inserir no banco de dados

        flash('Formulário enviado com sucesso!')
        return redirect(url_for('cadastro_certificados'))

    return render_template('cadastro_certificados.html')




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
