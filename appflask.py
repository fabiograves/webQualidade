import base64
import datetime

import pyodbc
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, make_response, jsonify
from werkzeug.utils import secure_filename
from flask_session import Session
from flask import send_file, Response
import os
import io
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.platypus import Image
from reportlab.platypus import Spacer
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração da extensão Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)


def conectar_db():
    driver = '{ODBC Driver 17 for SQL Server}'
    server = "172.16.2.27"
    database = "dbQualidade"
    username = "Qualidade"
    password = "y2%:ff4G4A>7"
    connectionString = f'DRIVER={driver};SERVER={server},1433;DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=yes;'

    try:
        connection = pyodbc.connect(connectionString)
        return connection
    except Exception as e:
        raise Exception(f"Erro ao conectar ao banco de dados: {e}")


def is_logged_in():
    """Verifica se o usuário está logado."""
    return 'logged_in' in session


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['senha']

        try:
            connection = conectar_db()
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM dbo.usuarios WHERE nome_usuario = ? AND senha_usuario = ?', (username, password))
            user = cursor.fetchone()

            if user:
                session['logged_in'] = True
                session['username'] = username

                session['privilegio'] = user.privilegio  # Ajuste conforme a estrutura do seu objeto 'user'

                # Armazenando informações adicionais na sessão
                session['nome_assinatura'] = user.nome_assinatura
                session['setor_assinatura'] = user.setor_assinatura
                session['telefone_assinatura'] = user.telefone_assinatura
                session['email_assinatura'] = user.email_assinatura

                return redirect(url_for('home'))
            else:
                flash('Login falhou. Verifique seu nome de usuário e senha.')
                return redirect(url_for('login'))
        finally:
            if 'connection' in locals():
                connection.close()

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


@app.route('/download_certificado', methods=['GET', 'POST'])
def download_certificado():

    return render_template('download_certificado.html')


@app.route('/baixar_certificado_por_id', methods=['POST'])
def baixar_certificado_por_id():
    numero_certificado = request.form.get('dc_numero_certificado')

    connection = conectar_db()
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT arquivo FROM dbo.certificados_gerados WHERE id = ?", (numero_certificado,))
        arquivo = cursor.fetchone()

        if arquivo:
            response = make_response(arquivo[0])
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename=certificado_{numero_certificado}.pdf'
            return response
        else:
            return "Certificado não encontrado.", 404
    except Exception as e:
        print(f"Erro ao buscar o certificado: {e}")
        return "Ocorreu um erro ao processar sua solicitação.", 500
    finally:
        cursor.close()
        connection.close()


@app.route('/criar_certificado')
def criar_certificado():
    return render_template('criar_certificado.html')


@app.route('/lista_norma')
def lista_norma():
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT norma, descricao FROM dbo.imagem_norma")
            normas = cursor.fetchall()
            # Ordena as normas com base na parte numérica antes do hífen
            normas = sorted(normas, key=lambda x: int(x[0].split('-')[0]))
    except Exception as e:
        print(f"Erro ao buscar normas: {e}")
        normas = []
    finally:
        connection.close()

    return render_template('lista_norma.html', normas=normas)


@app.route('/plano_controle_inspecao', methods=['GET', 'POST'])
def plano_controle_inspecao():
    if request.method == 'POST':
        numero = request.form['cad_numero_plano']
        imagem = request.files['imagem_plano']

        if imagem and allowed_file(imagem.filename):
            imagem_data = imagem.read()

            # Conexão com o banco de dados e inserção da norma, imagem e extensão
            connection = conectar_db()
            cursor = connection.cursor()
            cursor.execute("""INSERT INTO dbo.plano_controle_inspecao (numero, imagem) VALUES (?, ?)""",
                           (numero, imagem_data))
            connection.commit()
            connection.close()

            print("Controle número: ", numero, "cadastrado com sucesso.")
            return redirect(url_for('plano_controle_inspecao'))
        else:
            print("Controle número: ", numero, "ERRO ao cadastrar.")
            return redirect(url_for('cadastro_norma'))

    # Para o GET, vamos buscar todas as imagens no banco de dados
    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT numero, imagem FROM dbo.plano_controle_inspecao")
    imagens_db = cursor.fetchall()
    connection.close()

    # Converter imagens para base64 para serem exibidas no HTML
    imagens = [{'numero': img[0], 'imagem': base64.b64encode(img[1]).decode('utf-8')} for img in imagens_db]

    return render_template('plano_controle_inspecao.html', imagens=imagens)


@app.route('/base')
def base():
    return render_template('base.html')


@app.route('/pesquisar_certificado', methods=['GET', 'POST'])
def pesquisar_certificado():
    resultados = None
    if request.method == 'POST':
        numero_nota = request.form.get('pc_numero_nota')
        resultados = buscar_certificados(numero_nota)

    return render_template('pesquisar_certificado.html', resultados=resultados)


@app.route('/criar_certificado', methods=['POST'])
def tratar_formulario():
    resultado = None
    proximo_numero_certificado = None

    if 'bt_procurar_nota' in request.form:
        # Verifique se ambos os campos são fornecidos
        numero_nota = request.form.get('criar_numero_nota')
        cod_produto = request.form.get('criar_cod_produto')

        if not numero_nota or not cod_produto:
            # Se algum dos campos estiver vazio
            flash('É necessário fornecer o código do produto e o número da nota.')
        else:
            # Se ambos os campos foram fornecidos, proceda com a busca
            resultado = buscar_certificado_nota(numero_nota, cod_produto)
            if resultado and not all(value is None for value in resultado.values()):
                session['dados_pdf'] = resultado
                #print("dados_pdf")
                #print(session['dados_pdf'])
            else:
                flash('Nota fiscal e código não encontrados.')

    elif 'bt_criar_certificado' in request.form:
        if 'dados_pdf' in session and session['dados_pdf']:
            # Se os dados estão na sessão e não são None, prossegue para gerar o PDF
            return redirect(url_for('gerar_pdf'))
        else:
            # Se os dados não estão disponíveis, fornece feedback e não redireciona para 'gerar_pdf'
            flash('Os dados para criar o PDF não estão disponíveis. Por favor, procure a nota fiscal novamente.')
            return redirect(url_for(
                'criar_certificado'))

    # Buscar o último ID na tabela e sugerir o próximo número do certificado
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(id) AS ultimo_id FROM dbo.certificados_gerados")
            ultimo_id = cursor.fetchone()[0] or 0  # Usa 0 como fallback se não encontrar nenhum id
            proximo_numero_certificado = ultimo_id + 1
    except Exception as e:
        print(f"Erro ao buscar o último ID: {e}")
    finally:
        connection.close()

    return render_template('criar_certificado.html', resultado=session.get('dados_pdf', {}),
                           proximo_numero_certificado=proximo_numero_certificado)


@app.route('/gerar_pdf', methods=['POST'])
def gerar_pdf():
    # Recuperando os dados da sessão
    dados_pdf = session.get('dados_pdf')
    # print("session.get(dados_pdf)")
    # print(session.get('dados_pdf'))

    # Verifica se os dados necessários estão presentes
    if dados_pdf:

        # Extrai número da nota e código do produto
        numero_nota = dados_pdf.get('cadastro_certificados', {}).get('cc_numero_nota', 'desconhecido')
        cod_produto = dados_pdf.get('cadastro_certificados', {}).get('cc_cod_produto', 'desconhecido')

        criar_desc_material = request.form.get('criar_desc_material', 'Não informado')
        numero_certificado = request.form.get('criar_numero_certificado', 'Não informado')
        criar_data = request.form.get('criar_data', 'Não informado')
        criar_cliente = request.form.get('criar_cliente', 'Não informado')
        criar_pedido = request.form.get('criar_pedido', 'Não informado')
        criar_pedido_ars = request.form.get('criar_pedido_ars', 'Não informado')
        criar_numero_fabricante = request.form.get('criar_numero_fabricante', 'Não informado')
        criar_quantidade = request.form.get('criar_quantidade', 'Não informado')
        criar_material = request.form.get('criar_material', 'Não informado')
        criar_lote = request.form.get('criar_lote', 'Não informado')
        criar_codigo_fornecedor = request.form.get('criar_codigo_fornecedor', 'Não informado')

        tem_dados_comp_quimica = dados_pdf.get('comp_quimica') and any(dados_pdf['comp_quimica'].values())
        tem_dados_prop_mecanicas = dados_pdf.get('prop_mecanicas') and any(dados_pdf['prop_mecanicas'].values())
        tem_dados_tratamentos = dados_pdf.get('tratamentos') and any(dados_pdf['tratamentos'].values())
        tem_dados_ad_porcas = dados_pdf.get('ad_porcas') and any(dados_pdf['ad_porcas'].values())
        tem_dados_ad_pinos = dados_pdf.get('ad_pinos') and any(dados_pdf['ad_pinos'].values())
        tem_dados_ad_parafusos = dados_pdf.get('ad_parafusos') and any(dados_pdf['ad_parafusos'].values())
        tem_dados_ad_grampos = dados_pdf.get('ad_grampos') and any(dados_pdf['ad_grampos'].values())
        tem_dados_ad_arruelas = dados_pdf.get('ad_arruelas') and any(dados_pdf['ad_arruelas'].values())
        tem_dados_ad_anel = dados_pdf.get('ad_anel') and any(dados_pdf['ad_anel'].values())
        tem_dados_ad_prisioneiro_estojo = dados_pdf.get('ad_prisioneiro_estojo') and any(dados_pdf['ad_prisioneiro_estojo'].values())
        tem_dados_ad_chumbador = dados_pdf.get('ad_chumbador') and any(dados_pdf['ad_chumbador'].values())
        tem_dados_ad_rebite = dados_pdf.get('ad_rebite') and any(dados_pdf['ad_rebite'].values())
        tem_dados_ad_chaveta = dados_pdf.get('ad_chaveta') and any(dados_pdf['ad_chaveta'].values())
        tem_dados_ad_contrapino = dados_pdf.get('ad_contrapino') and any(dados_pdf['ad_contrapino'].values())
        tem_dados_ad_especial = dados_pdf.get('ad_especial') and any(dados_pdf['ad_especial'].values())

        # Cria um arquivo PDF na memória
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        page_width, page_height = letter

        # Estilo personalizado para parágrafos centralizados
        estilo_centralizado = ParagraphStyle(name='Centralizado', alignment=TA_CENTER, fontSize=8)

        # Defina as margens da página
        left_margin = 0.5 * inch
        right_margin = 0.5 * inch
        top_margin = 0.5 * inch
        bottom_margin = 0.5 * inch

        # Remove cabeçalho e rodapé
        doc.topMargin = top_margin
        doc.bottomMargin = bottom_margin

        # Defina a largura e altura efetivas da página
        effective_page_width = page_width - left_margin - right_margin
        effective_page_height = page_height - top_margin - bottom_margin

        # Lista para armazenar elementos do PDF
        elements = []

        # Estilo para o título
        texto_style1 = ParagraphStyle(name='TextoStyle1', fontSize=20, alignment=1, leading=22)
        texto_style2 = ParagraphStyle(name='TextoStyle2', fontSize=12, alignment=1, leading=14)

        # Texto dentro da tabela
        texto_tabela = "Certificado de Qualidade / Quality Certificate"

        # Cria o parágrafo do texto com o estilo personalizado
        texto_paragraph = Paragraph(texto_tabela, texto_style1)

        # Cria uma tabela com 2 colunas para posicionar a imagem e o texto
        data = [
            [Image(os.path.join(app.static_folder, 'images', 'LogoCertificado.png'), width=2 * inch, height=1 * inch),
             texto_paragraph]
        ]

        table = Table(data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Alinha a imagem à esquerda
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Alinha o texto ao centro
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        # Adiciona espaço entre a imagem e o texto
        elements.append(Spacer(0.1, 0.1 * inch))

        # Estilos para o texto
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']

        # Cria uma tabela com 3 colunas para posicionar os textos lado a lado
        data = [
            ["REG:7.1b - Revisao.04", "01/04/2010", f"Nº Certificado / Nº Certificate Nº{numero_certificado}"]
        ]

        table = Table(data, colWidths=[2 * inch, 2 * inch, 2 * inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alinha todas as colunas à esquerda
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        # Adiciona espaço entre as linhas de texto
        elements.append(Spacer(0.1, 0.1 * inch))

        data = [
            [Paragraph(f"<font size='6'>Cliente<br/>Customer: </font><font size='10'>{criar_cliente}</font>", getSampleStyleSheet()['Normal']),
             Paragraph(f"<font size='6'>Pedido<br/>Customer Order: </font><font size='10'>{criar_pedido}</font>", getSampleStyleSheet()['Normal'])],
            [Paragraph(f"<font size='6'>Nº Certificado do Fabricante<br/>Nº Certificate Supplier:      </font><font size='10'>{criar_numero_fabricante}</font>", getSampleStyleSheet()['Normal']),
             Paragraph(f"<font size='6'>Pedido<br/>ARS:     </font><font size='10'>{criar_pedido_ars}</font>", getSampleStyleSheet()['Normal'])],
            [Paragraph(
                f"<font size='6'>Descrição do Material<br/>Description of Material: </font><font size='10'>{criar_desc_material}</font>",
                getSampleStyleSheet()['Normal']),
             Paragraph(f"<font size='6'>Quantidade de Peças<br/>Quantity of Parts: </font><font size='10'>{criar_quantidade}</font>",
                       getSampleStyleSheet()['Normal'])],
            [Paragraph(
                f"<font size='6'>Material<br/>Material: </font><font size='10'>{criar_material}</font>",
                getSampleStyleSheet()['Normal']),
                Paragraph(
                    f"<font size='6'>Data<br/>Date: </font><font size='10'>{criar_data}</font>",
                    getSampleStyleSheet()['Normal'])],
            [Paragraph(
                f"<font size='6'>Lote<br/>Lote: </font><font size='10'>{criar_lote}</font>",
                getSampleStyleSheet()['Normal']),
                Paragraph(
                    f"<font size='6'>Cod. For.<br/>Code: </font><font size='10'>{criar_codigo_fornecedor}</font>",
                    getSampleStyleSheet()['Normal'])],

        ]

        # Defina a largura das colunas (em polegadas)
        colWidths = [(2/3) * effective_page_width, (1/3) * effective_page_width]

        # Crie a tabela
        table = Table(data, colWidths=colWidths)

        # Defina o estilo da tabela
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alinhar o texto à esquerda
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adicionar grade
        ]))

        elements.append(table)

        elements.append(Spacer(0.1, 0.1 * inch))

        # Se tem dados em 'comp_quimica', adiciona uma tabela ao PDF
        if tem_dados_comp_quimica:
            c = dados_pdf['comp_quimica'].get('cc_c', '')
            mn = dados_pdf['comp_quimica'].get('cc_mn', '')
            p = dados_pdf['comp_quimica'].get('cc_p', '')
            s = dados_pdf['comp_quimica'].get('cc_s', '')
            si = dados_pdf['comp_quimica'].get('cc_si', '')
            ni = dados_pdf['comp_quimica'].get('cc_ni', '')
            cr = dados_pdf['comp_quimica'].get('cc_cr', '')
            b = dados_pdf['comp_quimica'].get('cc_b', '')
            cu = dados_pdf['comp_quimica'].get('cc_cu', '')
            mo = dados_pdf['comp_quimica'].get('cc_mo', '')
            co = dados_pdf['comp_quimica'].get('cc_co', '')
            fe = dados_pdf['comp_quimica'].get('cc_fe', '')
            sn = dados_pdf['comp_quimica'].get('cc_sn', '')
            al = dados_pdf['comp_quimica'].get('cc_al', '')
            n = dados_pdf['comp_quimica'].get('cc_n', '')
            nb = dados_pdf['comp_quimica'].get('cc_nb', '')

            # Texto dentro da tabela
            texto_subtitulo = "Composição Química / Chemical Analysis"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            data = [
                [f"C: {c}", f"Mn: {mn}", f"P: {p}", f"S: {s}", f"Si: {si}", f"Ni: {ni}", f"Cr: {cr}", f"B: {b}"],
                [f"Cu: {cu}", f"Mo: {mo}", f"Co: {co}", f"Fe: {fe}", f"Al: {al}", f"N: {n}", f"Nb: {nb}", f"Sn: {sn}"]
            ]
            comp_quimica_table = Table(data, colWidths=effective_page_width / 8)

            comp_quimica_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
            ]))
            elements.append(comp_quimica_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        # Se tem dados em 'prop_mecanicas', adiciona uma tabela ao PDF
        if tem_dados_prop_mecanicas:
            escoamento = dados_pdf['prop_mecanicas'].get('cc_escoamento', '')
            tracao = dados_pdf['prop_mecanicas'].get('cc_tracao', '')
            reducao = dados_pdf['prop_mecanicas'].get('cc_reducao', '')
            alongamento = dados_pdf['prop_mecanicas'].get('cc_alongamento', '')
            carga = dados_pdf['prop_mecanicas'].get('cc_carga', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Mecânicas / Mechanical Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            data = [
                [Paragraph("Escoamento<br/>Yield Strenght", estilo_centralizado),
                 Paragraph("Resistência Tração<br/>Tensile Strenght", estilo_centralizado),
                 Paragraph("Redução de Área<br/>Reduction of Area", estilo_centralizado),
                 Paragraph("Alongamento<br/>Elongation", estilo_centralizado),
                 Paragraph("Prova de Carga<br/>Load Proof", estilo_centralizado)],
                [escoamento, tracao, reducao, alongamento, carga]
            ]
            prop_mecanicas_table = Table(data, colWidths=effective_page_width / 5)

            prop_mecanicas_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
            ]))
            elements.append(prop_mecanicas_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        # Se tem dados em 'tratamentos', adiciona uma tabela ao PDF
        if tem_dados_tratamentos:
            revenimento = dados_pdf['tratamentos'].get('cc_revenimento', '')
            termico = dados_pdf['tratamentos'].get('cc_termico', '')
            superficial = dados_pdf['tratamentos'].get('cc_superficial', '')
            macrografia = dados_pdf['tratamentos'].get('cc_macrografia', '')
            observacao = dados_pdf['tratamentos'].get('cc_observacao', '')

            # Texto dentro da tabela
            texto_subtitulo = "Tratamentos / Treatments"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Temperatura Revenimento<br/>Tempering Temperatura", estilo_centralizado),
                 Paragraph("Tratamento Térmico<br/>Thermal Treatment", estilo_centralizado),
                 Paragraph("Tratamento Superficial<br/>Surface Treatment", estilo_centralizado),
                 Paragraph("Macrografia<br/>Macrography", estilo_centralizado),
                 Paragraph("Observação<br/>Comments", estilo_centralizado)],
                [Paragraph(revenimento, estilo_centralizado), Paragraph(termico, estilo_centralizado), Paragraph(superficial, estilo_centralizado),
                 Paragraph(macrografia, estilo_centralizado), Paragraph(observacao, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            tratamentos_table = Table(data, colWidths=effective_page_width / 5)
            tratamentos_table.setStyle(TableStyle(cell_styles))

            elements.append(tratamentos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_porcas:
            dureza = dados_pdf['ad_porcas'].get('cc_adporcas_dureza', '')
            altura = dados_pdf['ad_porcas'].get('cc_adporcas_altura', '')
            chave = dados_pdf['ad_porcas'].get('cc_adporcas_chave', '')
            diametro = dados_pdf['ad_porcas'].get('cc_adporcas_diametro', '')
            diametro_estrutura = dados_pdf['ad_porcas'].get('cc_adporcas_diametro_estrutura', '')
            diametro_interno = dados_pdf['ad_porcas'].get('cc_adporcas_diamentro_interno', '')
            diametro_externo = dados_pdf['ad_porcas'].get('cc_adporcas_diametro_externo', '')
            norma = dados_pdf['ad_porcas'].get('cc_adporcas_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado),
                 Paragraph(altura, estilo_centralizado),
                 Paragraph(chave, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado)],
                [Paragraph("Diâmetro Estrutural<br/>Structural Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(diametro_estrutura, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adporcas_table = Table(data, colWidths=effective_page_width / 4)
            adporcas_table.setStyle(TableStyle(cell_styles))

            elements.append(adporcas_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_pinos:
            dureza = dados_pdf['ad_pinos'].get('cc_adpinos_dureza', '')
            espessura = dados_pdf['ad_pinos'].get('cc_adpinos_espeddura', '')
            comprimento = dados_pdf['ad_pinos'].get('cc_adpinos_comprimento', '')
            diametro = dados_pdf['ad_pinos'].get('cc_adpinos_diametro', '')
            diametro_cabeca = dados_pdf['ad_pinos'].get('cc_adpinos_diametro_cabeca', '')
            diametro_interno = dados_pdf['ad_pinos'].get('cc_adpinos_diametro_interno', '')
            diametro_externo = dados_pdf['ad_pinos'].get('cc_adpinos_diametro_externo', '')
            norma = dados_pdf['ad_pinos'].get('cc_adpinos_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Espessura<br/>Thickness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Length", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado),
                 Paragraph(espessura, estilo_centralizado),
                 Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado)],
                [Paragraph("Diâmetro Cabeça<br/>Head Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(diametro_cabeca, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adpinos_table = Table(data, colWidths=effective_page_width / 4)
            adpinos_table.setStyle(TableStyle(cell_styles))

            elements.append(adpinos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_parafusos:
            dureza = dados_pdf['ad_parafusos'].get('cc_adparafusos_dureza', "")
            altura = dados_pdf['ad_parafusos'].get('cc_adparafusos_altura', "")
            chave = dados_pdf['ad_parafusos'].get('cc_adparafusos_chave', "")
            comprimento = dados_pdf['ad_parafusos'].get('cc_adparafusos_comprimento', "")
            diametro = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro', "")
            diametro_cabeca = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro_cabeca', "")
            comprimento_rosca = dados_pdf['ad_parafusos'].get('cc_adparafusos_comprimento_rosca', "")
            diametro_ponta = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro_ponta', "")
            norma = dados_pdf['ad_parafusos'].get('cc_adparafusos_norma', "")

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(altura, estilo_centralizado),
                 Paragraph(chave, estilo_centralizado), Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado)],
                [Paragraph("Diâmetro Cabeça/Corpo<br/>Head/Body Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Diâmetro Ponta<br/>Tip Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(diametro_cabeca, estilo_centralizado), Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(diametro_ponta, estilo_centralizado), Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adparafusos_table = Table(data, colWidths=effective_page_width / 5)
            adparafusos_table.setStyle(TableStyle(cell_styles))

            elements.append(adparafusos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_grampos:
            dureza = dados_pdf['ad_grampos'].get('cc_adgrampos_dureza', '')
            comprimento = dados_pdf['ad_grampos'].get('cc_adgrampos_comprimento', '')
            diametro = dados_pdf['ad_grampos'].get('cc_adgrampos_diametro', '')
            comprimento_rosca = dados_pdf['ad_grampos'].get('cc_adgrampos_comprimento_rosca', '')
            diametro_interno = dados_pdf['ad_grampos'].get('cc_adgrampos_diametro_interno', '')
            norma = dados_pdf['ad_grampos'].get('cc_adgrampos_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado), Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado), Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adgrampos_table = Table(data, colWidths=effective_page_width / 6)
            adgrampos_table.setStyle(TableStyle(cell_styles))

            elements.append(adgrampos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_arruelas:
            dureza = dados_pdf['ad_arruelas'].get('cc_adarruelas_dureza', '')
            altura = dados_pdf['ad_arruelas'].get('cc_adarruelas_altura', '')
            diametro_interno = dados_pdf['ad_arruelas'].get('cc_adarruelas_diametro_interno', '')
            diametro_externo = dados_pdf['ad_arruelas'].get('cc_adarruelas_diametro_externo', '')
            norma = dados_pdf['ad_arruelas'].get('cc_adarruelas_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(altura, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado), Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adarruelas_table = Table(data, colWidths=effective_page_width / 5)
            adarruelas_table.setStyle(TableStyle(cell_styles))

            elements.append(adarruelas_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_anel:
            dureza = dados_pdf['ad_anel'].get('cc_adanel_dureza', '')
            altura = dados_pdf['ad_anel'].get('cc_adanel_altura', '')
            diametro_interno = dados_pdf['ad_anel'].get('cc_adanel_diametro_interno', '')
            diametro_externo = dados_pdf['ad_anel'].get('cc_adanel_diametro_externo', '')
            norma = dados_pdf['ad_anel'].get('cc_adanel_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(altura, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado), Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adanel_table = Table(data, colWidths=effective_page_width / 5)
            adanel_table.setStyle(TableStyle(cell_styles))

            elements.append(adanel_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_prisioneiro_estojo:
            dureza = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_dureza', '')
            comprimento = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_comprimento', '')
            diametro = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_diametro', '')
            comprimento_rosca = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_comprimento_rosca', '')
            norma = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado), Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adprisioneiroestojo_table = Table(data, colWidths=effective_page_width / 5)
            adprisioneiroestojo_table.setStyle(TableStyle(cell_styles))

            elements.append(adprisioneiroestojo_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_especial:
            dureza = dados_pdf['ad_especial'].get('cc_adespecial_dureza', '')
            altura = dados_pdf['ad_especial'].get('cc_adespecial_altura', '')
            chave = dados_pdf['ad_especial'].get('cc_adespecial_chave', '')
            comprimento = dados_pdf['ad_especial'].get('cc_adespecial_comprimento', '')
            diametro = dados_pdf['ad_especial'].get('cc_adespecial_diametro', '')
            diametro_cabeca = dados_pdf['ad_especial'].get('cc_adespecial_diametro_cabeca', '')
            comprimento_rosca = dados_pdf['ad_especial'].get('cc_adespecial_comprimento_rosca', '')
            diametro_interno = dados_pdf['ad_especial'].get('cc_adespecial_diametro_interno', '')
            diametro_externo = dados_pdf['ad_especial'].get('cc_adespecial_diametro_externo', '')
            norma = dados_pdf['ad_especial'].get('cc_adespecial_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(altura, estilo_centralizado),
                 Paragraph(chave, estilo_centralizado), Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado)],
                [Paragraph("Diâmetro Cabeça<br/>Head Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(diametro_cabeca, estilo_centralizado), Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado), Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adespecial_table = Table(data, colWidths=effective_page_width / 5)
            adespecial_table.setStyle(TableStyle(cell_styles))

            elements.append(adespecial_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_chumbador:
            dureza = dados_pdf['ad_chumbador'].get('cc_adchumbador_dureza', '')
            comprimento = dados_pdf['ad_chumbador'].get('cc_adchumbador_comprimento', '')
            bitola = dados_pdf['ad_chumbador'].get('cc_adchumbador_bitola', '')
            norma = dados_pdf['ad_chumbador'].get('cc_adchumbador_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Bitola<br/>Gauge", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(comprimento, estilo_centralizado),
                 Paragraph(bitola, estilo_centralizado), Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adchumbador_table = Table(data, colWidths=effective_page_width / 4)
            adchumbador_table.setStyle(TableStyle(cell_styles))

            elements.append(adchumbador_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_rebite:
            dureza = dados_pdf['ad_rebite'].get('cc_adrebite_dureza', '')
            comprimento = dados_pdf['ad_rebite'].get('cc_adrebite_comprimento', '')
            bitola = dados_pdf['ad_rebite'].get('cc_adrebite_bitola', '')
            diametro_cabeca = dados_pdf['ad_rebite'].get('cc_adrebite_diametro_cabeca', '')
            norma = dados_pdf['ad_rebite'].get('cc_adrebite_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Bitola<br/>Gauge", estilo_centralizado),
                 Paragraph("Diâmetro Cabeça<br/>Head Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(comprimento, estilo_centralizado),
                 Paragraph(bitola, estilo_centralizado), Paragraph(diametro_cabeca, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adrebite_table = Table(data, colWidths=effective_page_width / 5)
            adrebite_table.setStyle(TableStyle(cell_styles))

            elements.append(adrebite_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_chaveta:
            dureza = dados_pdf['ad_chaveta'].get('cc_adchaveta_dureza', '')
            comprimento = dados_pdf['ad_chaveta'].get('cc_adchaveta_comprimento', '')
            diametro = dados_pdf['ad_chaveta'].get('cc_adchaveta_diametro', '')
            altura = dados_pdf['ad_chaveta'].get('cc_adchaveta_altura', '')
            norma = dados_pdf['ad_chaveta'].get('cc_adchaveta_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado),
                 Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                 Paragraph(altura, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adchaveta_table = Table(data, colWidths=effective_page_width / 5)
            adchaveta_table.setStyle(TableStyle(cell_styles))

            elements.append(adchaveta_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_contrapino:
            dureza = dados_pdf['ad_contrapino'].get('cc_adcontrapino_dureza', '')
            comprimento = dados_pdf['ad_contrapino'].get('cc_adcontrapino_comprimento', '')
            diametro = dados_pdf['ad_contrapino'].get('cc_adcontrapino_diametro', '')
            norma = dados_pdf['ad_contrapino'].get('cc_adcontrapino_norma', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(dureza, estilo_centralizado), Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado), Paragraph(norma, estilo_centralizado)]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adcontrapino_table = Table(data, colWidths=effective_page_width / 4)
            adcontrapino_table.setStyle(TableStyle(cell_styles))

            elements.append(adcontrapino_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        nome_assinatura = session.get('nome_assinatura')
        setor_assinatura = session.get('setor_assinatura')
        telefone_assinatura = session.get('telefone_assinatura')
        email_assinatura = session.get('email_assinatura')


        # Defina o tamanho da fonte que você deseja para as células da tabela
        tamanho_da_fonte = 8

        data = [
            ["Observação - Comments", "Visto - Signs"],
            [Paragraph("* Com base nos resultados obtidos, certificamos<br/>"
                       "que o produto encontra-se dentro das normas citadas.<br/>"
                       "* In according with test results, we certify that the<br/>"
                       "product is in according with reference standards.<br/> ", estilo_centralizado),
             Paragraph(f"{nome_assinatura}<br/><b>{setor_assinatura}</b><br/>"
                       f"{telefone_assinatura}<br/>{email_assinatura}", estilo_centralizado)
             ]
        ]

        # Crie uma lista de estilos de célula com o tamanho da fonte definido
        cell_styles = [
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
            ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
            ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
        ]

        rodape_table = Table(data, colWidths=effective_page_width / 2)
        rodape_table.setStyle(TableStyle(cell_styles))

        elements.append(rodape_table)
        elements.append(Spacer(0.1, 0.1 * inch))

        # Constrói o PDF
        doc.build(elements)

        session.pop('dados_pdf', None)

        inserir_certificado_gerado(buffer, numero_nota, cod_produto)

        # Define o nome do arquivo PDF
        nome_arquivo_pdf = f"{numero_nota}-{cod_produto}.pdf"
        # Retorna o PDF como resposta
        buffer.seek(0)
        return Response(buffer.getvalue(), mimetype='application/pdf',
                        headers={"Content-Disposition": f"attachment;filename={nome_arquivo_pdf}"})

    else:
        flash("Dados necessários para gerar o PDF não foram encontrados.")
        return redirect(url_for('criar_certificado'))


def inserir_certificado_gerado(arquivo_pdf, numero_nota, cod_produto):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            # Convertendo o arquivo PDF para um objeto Binary para inserção no SQL Server
            arquivo_binario = arquivo_pdf.getvalue()

            sql = "INSERT INTO dbo.certificados_gerados (arquivo, numero_nota, cod_produto) VALUES (?, ?, ?)"
            cursor.execute(sql, (arquivo_binario, numero_nota, cod_produto))
            connection.commit()
    except Exception as e:
        print(f"Erro ao inserir o certificado gerado no banco de dados: {e}")
    finally:
        connection.close()


def fetch_dict(cursor):
    """
    Converte o resultado do cursor atual em um dicionário
    """
    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()
    if row:
        return dict(zip(columns, row))
    else:
        return None


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def buscar_certificado_nota(numero_nota, cod_produto):
    connection = conectar_db()
    try:
        resultado = {}

        with connection.cursor() as cursor:
            # Primeira etapa: Verifica se existe registro aprovado
            sql_registro_inspecao = """SELECT * FROM dbo.registro_inspecao 
                                                   WHERE ri_numero_nota = ? AND ri_cod_produto = ? 
                                                   AND ri_opcao = 'Aprovado' ORDER BY ri_data_inspecao DESC"""
            cursor.execute(sql_registro_inspecao, (numero_nota, cod_produto))
            registro_inspecao_aprovado = fetch_dict(cursor)

            # Busca na tabela de cadastro de certificados
            sql = "SELECT * FROM dbo.cadastro_certificados WHERE cc_numero_nota = ? AND cc_cod_produto = ?"
            cursor.execute(sql, (numero_nota, cod_produto))

            cadastro_certificados = fetch_dict(cursor)
            if cadastro_certificados:
                resultado['cadastro_certificados'] = cadastro_certificados
                if cadastro_certificados.get('cc_arquivo'):
                    resultado['arquivo'] = cadastro_certificados['cc_arquivo']
                else:
                    resultado['arquivo'] = None
            else:
                resultado['cadastro_certificados'] = None
                resultado['arquivo'] = None

            sql = "SELECT * FROM dbo.comp_quimica WHERE cc_numero_nota = ? AND cc_cod_produto = ?"
            cursor.execute(sql, (numero_nota, cod_produto))
            comp_quimica = fetch_dict(cursor)
            resultado['comp_quimica'] = comp_quimica if comp_quimica else None

            sql = "SELECT * FROM dbo.prop_mecanicas WHERE cc_numero_nota = ? AND cc_cod_produto = ?"
            cursor.execute(sql, (numero_nota, cod_produto))
            prop_mecanicas = fetch_dict(cursor)
            resultado['prop_mecanicas'] = prop_mecanicas if prop_mecanicas else None

            sql = "SELECT * FROM dbo.tratamentos WHERE cc_numero_nota = ? AND cc_cod_produto = ?"
            cursor.execute(sql, (numero_nota, cod_produto))
            tratamentos = fetch_dict(cursor)
            resultado['tratamentos'] = tratamentos if tratamentos else None

            # Se existe registro aprovado, busca dados adicionais
            if registro_inspecao_aprovado:
                pedido_compra = registro_inspecao_aprovado['ri_pedido_compra']

                sql_ad_porcas = "SELECT * FROM dbo.ad_porcas WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql_ad_porcas, (numero_nota, cod_produto, pedido_compra))
                ad_porcas = fetch_dict(cursor)
                resultado['ad_porcas'] = ad_porcas if ad_porcas else None

                sql = "SELECT * FROM dbo.ad_pinos WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_pinos = fetch_dict(cursor)
                resultado['ad_pinos'] = ad_pinos if ad_pinos else None

                sql = "SELECT * FROM dbo.ad_parafusos WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_parafusos = fetch_dict(cursor)
                resultado['ad_parafusos'] = ad_parafusos if ad_parafusos else None

                sql = "SELECT * FROM dbo.ad_grampos WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_grampos = fetch_dict(cursor)
                resultado['ad_grampos'] = ad_grampos if ad_grampos else None

                sql = "SELECT * FROM dbo.ad_arruelas WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_arruelas = fetch_dict(cursor)
                resultado['ad_arruelas'] = ad_arruelas if ad_arruelas else None

                sql = "SELECT * FROM dbo.ad_anel WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_anel = fetch_dict(cursor)
                resultado['ad_anel'] = ad_anel if ad_anel else None

                sql = "SELECT * FROM dbo.ad_prisioneiro_estojo WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_prisioneiro_estojo = fetch_dict(cursor)
                resultado['ad_prisioneiro_estojo'] = ad_prisioneiro_estojo if ad_prisioneiro_estojo else None

                sql = "SELECT * FROM dbo.ad_chumbador WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_chumbador = fetch_dict(cursor)
                resultado['ad_chumbador'] = ad_chumbador if ad_chumbador else None

                sql = "SELECT * FROM dbo.ad_rebite WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_rebite = fetch_dict(cursor)
                resultado['ad_rebite'] = ad_rebite if ad_rebite else None

                sql = "SELECT * FROM dbo.ad_chaveta WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_chaveta = fetch_dict(cursor)
                resultado['ad_chaveta'] = ad_chaveta if ad_chaveta else None

                sql = "SELECT * FROM dbo.ad_contrapino WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_contrapino = fetch_dict(cursor)
                resultado['ad_contrapino'] = ad_contrapino if ad_contrapino else None

                sql = "SELECT * FROM dbo.ad_especial WHERE cc_numero_nota = ? AND cc_cod_produto = ? AND cc_pedido_compra = ?"
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_especial = fetch_dict(cursor)
                resultado['ad_especial'] = ad_especial if ad_especial else None
            else:
                resultado['mensagem'] = 'Não existe registro aprovado para esta nota e produto.'

    except Exception as e:
        print(f"1 Erro ao buscar certificado por nota: {e}")
        resultado = None
    finally:
        connection.close()

    return resultado


@app.route('/download_arquivo/<numero_nota>/<cod_produto>')
def download_arquivo(numero_nota, cod_produto):
    resultado = buscar_certificado_nota(numero_nota, cod_produto)

    # Verifica se um arquivo foi encontrado
    if resultado and resultado['arquivo']:
        arquivo_binario = resultado['arquivo']
        nome_arquivo = f"certificado_{numero_nota}_{cod_produto}.pdf"
        file_like = io.BytesIO(arquivo_binario)

        response = make_response(file_like.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
        response.mimetype = 'application/pdf'
        return response
    else:
        return "Arquivo não encontrado", 404


def buscar_certificados(numero_nota):
    connection = conectar_db()
    try:
        resultados_agrupados = {}

        cursor = connection.cursor()

        # Busca por cadastro de certificados apenas pelo número da nota
        sql = "SELECT * FROM dbo.cadastro_certificados WHERE cc_numero_nota = ?"
        cursor.execute(sql, (numero_nota,))
        cadastros = cursor.fetchall()

        # Converte manualmente cada linha do resultado em um dicionário
        cadastros = [dict_factory(cursor, cadastro) for cadastro in cadastros]

        for cadastro in cadastros:
            # Usando apenas o número da nota e código do produto para chave
            chave = f"{cadastro['cc_numero_nota']}-{cadastro['cc_cod_produto']}"
            resultados_agrupados[chave] = {'cadastro_certificados': cadastro}

            # Inicializa listas para cada tipo de informação relacionada
            for tipo in ('comp_quimica', 'prop_mecanicas', 'tratamentos', 'ad_porcas', 'ad_pinos', 'ad_parafusos', 'ad_grampos',
                         'ad_rebite', 'ad_prisioneiro_estojo', 'ad_chumbador', 'ad_chaveta', 'ad_arruelas', 'ad_anel',
                         'ad_contrapino', 'ad_especial'):
                resultados_agrupados[chave][tipo] = []

        # Para cada tipo de dados relacionados, realizar uma busca e organizar os resultados
        tipos_relacionados = {
            'comp_quimica': "SELECT * FROM dbo.comp_quimica WHERE cc_numero_nota IN (?)",
            'prop_mecanicas': "SELECT * FROM dbo.prop_mecanicas WHERE cc_numero_nota IN (?)",
            'tratamentos': "SELECT * FROM dbo.tratamentos WHERE cc_numero_nota IN (?)",
            'ad_porcas': "SELECT * FROM dbo.ad_porcas WHERE cc_numero_nota IN (?)",
            'ad_pinos': "SELECT * FROM dbo.ad_pinos WHERE cc_numero_nota IN (?)",
            'ad_parafusos': "SELECT * FROM dbo.ad_parafusos WHERE cc_numero_nota IN (?)",
            'ad_grampos': "SELECT * FROM dbo.ad_grampos WHERE cc_numero_nota IN (?)",
            'ad_rebite': "SELECT * FROM dbo.ad_rebite WHERE cc_numero_nota IN (?)",
            'ad_prisioneiro_estojo': "SELECT * FROM dbo.ad_prisioneiro_estojo WHERE cc_numero_nota IN (?)",
            'ad_chumbador': "SELECT * FROM dbo.ad_chumbador WHERE cc_numero_nota IN (?)",
            'ad_chaveta': "SELECT * FROM dbo.ad_chaveta WHERE cc_numero_nota IN (?)",
            'ad_arruelas': "SELECT * FROM dbo.ad_arruelas WHERE cc_numero_nota IN (?)",
            'ad_anel': "SELECT * FROM dbo.ad_anel WHERE cc_numero_nota IN (?)",
            'ad_contrapino': "SELECT * FROM dbo.ad_contrapino WHERE cc_numero_nota IN (?)",
            'ad_especial': "SELECT * FROM dbo.ad_especial WHERE cc_numero_nota IN (?)"
        }

        for tipo, sql in tipos_relacionados.items():
            cursor.execute(sql, (numero_nota,))
            itens_relacionados = cursor.fetchall()
            itens_relacionados = [dict_factory(cursor, item) for item in itens_relacionados]

            for item in itens_relacionados:
                chave = f"{item['cc_numero_nota']}-{item['cc_cod_produto']}"
                if chave in resultados_agrupados:
                    resultados_agrupados[chave][tipo].append(item)

    except Exception as e:
        print(f"Erro ao buscar certificados: {e}")
        resultados_agrupados = None
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

    return resultados_agrupados


@app.route('/pesquisar_registro_inspecao', methods=['GET', 'POST'])
def pesquisar_registro_inspecao():
    if not is_logged_in():
        return redirect(url_for('login'))

    resultados = None
    if request.method == 'POST':
        numero_nota = request.form.get('pc_numero_nota')
        ri_data = request.form.get('ri_data')

        # Função que busca os dados apenas pelo número da nota
        resultados = buscar_registro_inspecao(numero_nota, ri_data)

    return render_template('pesquisar_registro_inspecao.html', resultados=resultados)


def buscar_registro_inspecao(numero_nota, ri_data):
    connection = conectar_db()
    try:
        resultados_agrupados = {}

        cursor = connection.cursor()

        # Verifica quais campos foram preenchidos e ajusta a consulta SQL
        if numero_nota and ri_data:
            # Ambos número da nota e data são fornecidos
            sql = "SELECT * FROM dbo.registro_inspecao WHERE ri_numero_nota = ? AND ri_data = ?"
            cursor.execute(sql, (numero_nota, ri_data))
        elif numero_nota:
            # Apenas número da nota fornecido
            sql = "SELECT * FROM dbo.registro_inspecao WHERE ri_numero_nota = ?"
            cursor.execute(sql, (numero_nota,))
        elif ri_data:
            print(ri_data)
            # Apenas data fornecida
            sql = "SELECT * FROM dbo.registro_inspecao WHERE ri_data = ?"
            cursor.execute(sql, (ri_data,))
        else:
            # Se nenhum campo foi preenchido, pode optar por retornar vazio ou todos os registros
            return resultados_agrupados

        cadastros = cursor.fetchall()

        # Converte manualmente cada linha do resultado em um dicionário
        cadastros_dict = [dict_factory(cursor, cadastro) for cadastro in cadastros]

        for cadastro in cadastros_dict:
            chave = f"{cadastro['ri_numero_nota']}-{cadastro['ri_cod_produto']}-{cadastro['ri_pedido_compra']}"
            if chave not in resultados_agrupados:
                resultados_agrupados[chave] = {'registro_inspecao': cadastro}

                # Inicializa listas para cada tipo de informação relacionada
                for tipo in ('ad_porcas', 'ad_pinos', 'ad_parafusos', 'ad_grampos', 'ad_rebite', 'ad_prisioneiro_estojo',
                             'ad_chumbador', 'ad_chaveta', 'ad_arruelas', 'ad_anel', 'ad_contrapino', 'ad_especial'):
                    resultados_agrupados[chave][tipo] = []

        # Para cada tipo de dados relacionados, realizar uma busca e organizar os resultados
        tipos_relacionados = {
            'ad_porcas': "SELECT * FROM dbo.ad_porcas WHERE cc_numero_nota IN (?)",
            'ad_pinos': "SELECT * FROM dbo.ad_pinos WHERE cc_numero_nota IN (?)",
            'ad_parafusos': "SELECT * FROM dbo.ad_parafusos WHERE cc_numero_nota IN (?)",
            'ad_grampos': "SELECT * FROM dbo.ad_grampos WHERE cc_numero_nota IN (?)",
            'ad_rebite': "SELECT * FROM dbo.ad_rebite WHERE cc_numero_nota IN (?)",
            'ad_prisioneiro_estojo': "SELECT * FROM dbo.ad_prisioneiro_estojo WHERE cc_numero_nota IN (?)",
            'ad_chumbador': "SELECT * FROM dbo.ad_chumbador WHERE cc_numero_nota IN (?)",
            'ad_chaveta': "SELECT * FROM dbo.ad_chaveta WHERE cc_numero_nota IN (?)",
            'ad_arruelas': "SELECT * FROM dbo.ad_arruelas WHERE cc_numero_nota IN (?)",
            'ad_anel': "SELECT * FROM dbo.ad_anel WHERE cc_numero_nota IN (?)",
            'ad_contrapino': "SELECT * FROM dbo.ad_contrapino WHERE cc_numero_nota IN (?)",
            'ad_especial': "SELECT * FROM dbo.ad_especial WHERE cc_numero_nota IN (?)",
            # Adicione mais conforme necessário
        }

        for tipo, sql in tipos_relacionados.items():
            cursor.execute(sql, (numero_nota,))
            itens_relacionados = cursor.fetchall()
            itens_relacionados = [dict_factory(cursor, item) for item in itens_relacionados]

            for item in itens_relacionados:
                chave = f"{item['cc_numero_nota']}-{item['cc_cod_produto']}-{item['cc_pedido_compra']}"
                if chave in resultados_agrupados:
                    resultados_agrupados[chave][tipo].append(item)

    except Exception as e:
        print(f"Erro ao buscar registros de inspeção: {e}")
        resultados_agrupados = None
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()

    print("resultados_agrupado: ", resultados_agrupados)
    return resultados_agrupados


@app.route('/cadastro_certificados', methods=['GET', 'POST'])
def cadastro_certificados():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Verificar qual botão foi clicado
        if 'bt_registrar_certificado' in request.form:
            # Capturando os dados do formulário
            nota_fiscal = request.form.get('cc_numero_nota')
            cod_produto = request.form.get('cc_cod_produto')

            # Verificando se pelo menos o campo 'cc_numero_nota' não está em branco
            if nota_fiscal.strip() == '' or cod_produto.strip() == '':
                flash('O campo Nota Fiscal e Cod Produto não podem estar em branco.')
                return redirect(url_for('cadastro_certificados'))

            descricao = request.form.get('cc_descricao')
            corrida = request.form.get('cc_corrida')
            data = request.form.get('cc_data')
            cq = request.form.get('cc_cq')
            cod_fornecedor = request.form.get('cc_cod_fornecedor')
            qtd_pedido = request.form.get('cc_qtd_pedidos')
            cod_produto = request.form.get('cc_cod_produto')

            # Capturar o arquivo enviado
            arquivo = request.files['arquivo']

            # Verificar se um arquivo foi enviado
            if arquivo:
                # Ler o conteúdo do arquivo
                arquivo_binario = arquivo.read()
            else:
                # Se nenhum arquivo foi enviado, definir arquivo_binario como None
                arquivo_binario = None

            # Montar o dicionário de dados com o arquivo (pode ser None se nenhum arquivo foi enviado)
            dados_certificado = {
                'nota_fiscal': nota_fiscal,
                'descricao': descricao,
                'corrida': corrida,
                'data': data,
                'cq': cq,
                'cod_fornecedor': cod_fornecedor,
                'qtd_pedido': qtd_pedido,
                'cod_produto': cod_produto,
                'arquivo': arquivo_binario  # Adicionar o arquivo binário (pode ser None)
            }

            # Chamando a função para inserir os dados no banco de dados
            inserir_cadastro_certificados(dados_certificado)

            # Composição Química
            comp_quimica = request.form.get('comp_quimica') == 'on'
            elementos_quimicos = {}
            if comp_quimica:
                elementos_quimicos = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
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
                    'fe': request.form.get('cc_fe'),
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
                    'cod_produto': cod_produto,
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
                    'cod_produto': cod_produto,
                    'revenimento': request.form.get('cc_revenimento'),
                    'termico': request.form.get('cc_termico'),
                    'superficial': request.form.get('cc_superficial'),
                    'macrografia': request.form.get('cc_macrografia'),
                    'observacao': request.form.get('cc_observacao')
                }
                inserir_cadastro_tratamentos(dados_tratamentos)

            flash('Formulário enviado com sucesso!')
            return redirect(url_for('cadastro_certificados'))

        elif 'bt_procurar_nota' in request.form:
            # Capturando os dados do formulário
            nota_fiscal = request.form.get('cc_numero_nota')
            cod_produto = request.form.get('cc_cod_produto')
            connection = conectar_db()
            try:
                with connection.cursor() as cursor:
                    # Consulta SQL para verificar se um registro existe com os valores fornecidos
                    query = "SELECT * FROM dbo.registro_inspecao WHERE ri_numero_nota = ? AND ri_cod_produto = ?"
                    cursor.execute(query, (nota_fiscal, cod_produto))
                    result = cursor.fetchone()  # Obtém a primeira linha correspondente

                    if result:
                        flash('Registro encontrado. Pode prosseguir com o registro do certificado.')

                        # Redirecionar para a página com os campos preenchidos
                        return render_template('cadastro_certificados.html',
                                               cc_numero_nota=nota_fiscal,
                                               cc_cod_produto=cod_produto)

                    else:
                        # Se nenhum registro correspondente foi encontrado
                        flash('Erro, não foi feito registro de inspeção. Verifique os valores inseridos.')

            except Exception as e:
                print(f"Ocorreu um erro bt_registrar_certificado: {e}")
            finally:
                connection.close()
            # flash('Botão "Registrar Certificado" clicado.')

    return render_template('cadastro_certificados.html')


def verificar_existencia_nota(nota_fiscal):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(1) FROM dbo.cadastro_certificados WHERE cc_numero_nota = ?"
            cursor.execute(sql, (nota_fiscal,))
            resultado = cursor.fetchone()
            return resultado['COUNT(1)'] > 0  # Verifique o nome da coluna retornado pelo cursor.
    except Exception as e:
        print(f"Erro ao verificar existência da nota: {e}")
    finally:
        connection.close()
    return False


def inserir_cadastro_certificados(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            # SQL query updated for clarity
            sql = """INSERT INTO dbo.cadastro_certificados 
                     (cc_numero_nota, cc_descricao, cc_cod_fornecedor, cc_cod_produto, cc_corrida, cc_data, cc_cq, cc_qtd_pedidos, cc_arquivo)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['descricao'],
                dados['cod_fornecedor'],
                dados['cod_produto'],
                dados['corrida'],
                dados['data'],
                dados['cq'],
                dados['qtd_pedido'],
                dados['arquivo']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro ao inserir o certificado: {e}")
    finally:
        connection.close()

def inserir_cadastro_composicao_quimica(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.comp_quimica
            (cc_numero_nota, cc_cod_produto, cc_c, cc_mn, cc_p, cc_s, cc_si, cc_ni, cc_cr, cc_b, cc_cu, 
            cc_mo, cc_co, cc_fe, cc_sn, cc_al, cc_n, cc_nb)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
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
                dados['fe'],
                dados['sn'],
                dados['al'],
                dados['n'],
                dados['nb']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro comp quimica: {e}")
    finally:
        connection.close()


def inserir_cadastro_propriedades_mecanicas(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.prop_mecanicas
            (cc_numero_nota, cc_cod_produto, cc_escoamento, cc_tracao, cc_reducao, cc_alongamento, cc_dureza, cc_carga)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['escoamento'],
                dados['tracao'],
                dados['reducao'],
                dados['alongamento'],
                dados['dureza'],
                dados['carga']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro prop mec: {e}")
    finally:
        connection.close()


def inserir_cadastro_tratamentos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.tratamentos
            (cc_numero_nota, cc_cod_produto, cc_revenimento, cc_termico, cc_superficial, cc_macrografia, cc_observacao)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['revenimento'],
                dados['termico'],
                dados['superficial'],
                dados['macrografia'],
                dados['observacao']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro tratamentos: {e}")
    finally:
        connection.close()


def inserir_cadastro_adparafusos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_parafusos
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adparafusos_dureza, cc_adparafusos_altura, cc_adparafusos_chave, cc_adparafusos_comprimento, 
            cc_adparafusos_diametro, cc_adparafusos_diametro_cabeca, cc_adparafusos_comprimento_rosca, 
            cc_adparafusos_diametro_ponta, cc_adparafusos_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['altura'],
                dados['chave'],
                dados['comprimento'],
                dados['diametro'],
                dados['diametro_cabeca'],
                dados['comprimento_rosca'],
                dados['diametro_ponta'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro parafusos: {e}")
    finally:
        connection.close()


def inserir_cadastro_adporcas(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_porcas
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adporcas_dureza, cc_adporcas_altura, cc_adporcas_chave, cc_adporcas_diametro, 
            cc_adporcas_diametro_estrutura, cc_adporcas_diametro_interno, cc_adporcas_diametro_externo, cc_adporcas_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['altura'],
                dados['chave'],
                dados['diametro'],
                dados['diametro_estrutura'],
                dados['diametro_interno'],
                dados['diametro_externo'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro porcas: {e}")
    finally:
        connection.close()


def inserir_cadastro_adarruelas(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_arruelas
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adarruelas_dureza, cc_adarruelas_altura, cc_adarruelas_diametro_interno, 
            cc_adarruelas_diametro_externo, cc_adarruelas_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['altura'],
                dados['diametro_interno'],
                dados['diametro_externo'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro arruelas: {e}")
    finally:
        connection.close()


def inserir_cadastro_adanel(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_anel
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adanel_dureza, cc_adanel_altura, cc_adanel_diametro_interno, 
            cc_adanel_diametro_externo, cc_adanel_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['altura'],
                dados['diametro_interno'],
                dados['diametro_externo'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro anel: {e}")
    finally:
        connection.close()


def inserir_cadastro_adgrampos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_grampos
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adgrampos_dureza, cc_adgrampos_comprimento, cc_adgrampos_diametro, 
            cc_adgrampos_comprimento_rosca, cc_adgrampos_diametro_interno, cc_adgrampos_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['comprimento'],
                dados['diametro'],
                dados['comprimento_rosca'],
                dados['diametro_interno'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro grampos: {e}")
    finally:
        connection.close()


def inserir_cadastro_adpinos(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_pinos
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adpinos_dureza, cc_adpinos_espessura, cc_adpinos_comprimento, cc_adpinos_diametro, 
            cc_adpinos_diametro_cabeca, cc_adpinos_diametro_interno, cc_adpinos_diametro_externo, cc_adpinos_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['espessura'],
                dados['comprimento'],
                dados['diametro'],
                dados['diametro_cabeca'],
                dados['diametro_interno'],
                dados['diametro_externo'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro pinos: {e}")
    finally:
        connection.close()


def inserir_cadastro_adprisioneiro_estojo(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_prisioneiro_estojo
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adprisioneiroestojo_dureza, cc_adprisioneiroestojo_comprimento, 
            cc_adprisioneiroestojo_diametro, cc_adprisioneiroestojo_comprimento_rosca, cc_adprisioneiroestojo_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['comprimento'],
                dados['diametro'],
                dados['comprimento_rosca'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro prisioneiro: {e}")
    finally:
        connection.close()


def inserir_cadastro_adespecial(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_especial
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adespecial_dureza, cc_adespecial_altura, cc_adespecial_chave, cc_adespecial_comprimento, 
            cc_adespecial_diametro, cc_adespecial_diametro_cabeca, cc_adespecial_comprimento_rosca,
            cc_adespecial_diametro_interno, cc_adespecial_diametro_externo, cc_adespecial_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['altura'],
                dados['chave'],
                dados['comprimento'],
                dados['diametro'],
                dados['diametro_cabeca'],
                dados['comprimento_rosca'],
                dados['diametro_interno'],
                dados['diametro_externo'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro especial: {e}")
    finally:
        connection.close()


def inserir_cadastro_adcontrapino(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_contrapino
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adcontrapino_dureza, cc_adcontrapino_comprimento, cc_adcontrapino_diametro, cc_adcontrapino_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['comprimento'],
                dados['diametro'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro contrapino: {e}")
    finally:
        connection.close()


def inserir_cadastro_adchaveta(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_chaveta
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adchaveta_dureza, cc_adchaveta_comprimento, cc_adchaveta_diametro, cc_adchaveta_altura, cc_adchaveta_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['comprimento'],
                dados['diametro'],
                dados['altura'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro chaveta: {e}")
    finally:
        connection.close()


def inserir_cadastro_adrebite(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_rebite
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adrebite_dureza, cc_adrebite_comprimento, cc_adrebite_bitola, cc_adrebite_diametro_cabeca, cc_adrebite_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['comprimento'],
                dados['bitola'],
                dados['diametro_cabeca'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro rebite: {e}")
    finally:
        connection.close()


def inserir_cadastro_adchumbador(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO dbo.ad_chumbador
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adchumbador_dureza, cc_adchumbador_comprimento, cc_adchumbador_bitola, cc_adchumbador_norma)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(sql, (
                dados['nota_fiscal'],
                dados['cod_produto'],
                dados['pedido_compra'],
                dados['dureza'],
                dados['comprimento'],
                dados['bitola'],
                dados['norma']
            ))
            connection.commit()
    except Exception as e:
        print(f"Ocorreu um erro chumbador: {e}")
    finally:
        connection.close()


@app.route('/verifica-produto-reprovado')
def verifica_produto_reprovado():
    codProduto = request.args.get('codProduto')
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT COUNT(*) FROM dbo.registro_inspecao
                              WHERE ri_cod_produto = ? AND ri_opcao = 'Reprovado'""", (codProduto))
            resultado = cursor.fetchone()
            reprovado = resultado[0] > 0
            return jsonify(reprovado=reprovado)
    finally:
        connection.close()


EXTENSION_TO_MIME_TYPE = {
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
}


@app.route('/buscar-imagem')
def buscar_imagem():
    norma = request.args.get('norma')
    # Conexão ao banco de dados
    connection = conectar_db()
    cursor = connection.cursor()

    cursor.execute("""SELECT imagem, extensao FROM dbo.imagem_norma WHERE norma = ?""", (norma,))
    row = cursor.fetchone()
    if row:
        imagem, formato_imagem = row
        # Obtém o tipo MIME baseado na extensão do arquivo
        mime_type = EXTENSION_TO_MIME_TYPE.get(formato_imagem.lower(), 'application/octet-stream')
        return send_file(io.BytesIO(imagem), mimetype=mime_type)
    else:
        return 'Imagem não encontrada', 404


@app.route('/cadastro_norma', methods=['GET', 'POST'])
def cadastro_norma():
    if request.method == 'POST':
        numero_norma = request.form['cad_numero_norma']
        imagem = request.files['imagem_norma']
        descricao_norma = request.form['cad_descricao_norma']

        if imagem and allowed_file(imagem.filename):
            filename = secure_filename(imagem.filename)
            extensao = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''  # Extrai a extensão do arquivo
            imagem_data = imagem.read()

            # Conexão com o banco de dados e inserção da norma, imagem e extensão
            connection = conectar_db()
            cursor = connection.cursor()
            cursor.execute("""INSERT INTO dbo.imagem_norma (norma, imagem, extensao, descricao) VALUES (?, ?, ?, ?)""",
                           (numero_norma, imagem_data, extensao, descricao_norma))
            connection.commit()
            connection.close()

            flash('Norma cadastrada com sucesso!')
            return redirect(url_for('cadastro_norma'))
        else:
            flash('Erro no cadastro da norma. Verifique o arquivo de imagem.')
            return redirect(url_for('cadastro_norma'))

    return render_template('cadastro_norma.html')


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}


@app.route('/registro_inspecao', methods=['GET', 'POST'])
def registro_inspecao():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Capturando os dados do formulário
        nota_fiscal = request.form.get('ri_nota_fiscal')
        cod_produto = request.form.get('ri_cod_produto')
        tipo_analise = request.form.get('selecaoTipo')  # Obtém o tipo selecionado

        # Verificando se pelo menos o campo 'ri_nota_fiscal' não está em branco
        if nota_fiscal.strip() == '' or cod_produto.strip() == '':
            flash('O campo Nota Fiscal não pode estar em branco.')
            return redirect(url_for('registro_inspecao'))

        fornecedor = request.form.get('ri_fornecedor')
        pedido_compra = request.form.get('ri_pedido_compra')
        quantidade_total = request.form.get('ri_quantidade_total')
        volume = request.form.get('ri_volume')
        desenho = request.form.get('ri_desenho')
        acabamento = request.form.get('ri_acabamento')
        ri_opcao = request.form.get('ri_option')
        print(ri_opcao)
        resp_inspecao = request.form.get('ri_resp_inspecao')
        data = request.form.get('ri_data')
        data_inspecao = datetime.date.today()

        connection = conectar_db()
        try:
            with connection.cursor() as cursor:
                # Verifica se já existe um registro
                if verificar_existencia_registro(nota_fiscal, cod_produto, pedido_compra):
                    # Se existe, deleta o antigo
                    cursor.execute("DELETE FROM dbo.registro_inspecao WHERE ri_numero_nota = ? AND ri_cod_produto = ? AND ri_pedido_compra = ?",
                                   (nota_fiscal, cod_produto, pedido_compra))
                    flash('Registro existente será substituído pelo novo.', 'warning')

            sql = """INSERT INTO dbo.registro_inspecao (ri_numero_nota, ri_cod_produto, ri_fornecedor, ri_pedido_compra, ri_quantidade_total, ri_volume, ri_desenho,
             ri_acabamento, ri_opcao, ri_resp_inspecao, ri_data, ri_data_inspecao) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            cursor.execute(sql, (nota_fiscal, cod_produto, fornecedor, pedido_compra, quantidade_total,
                                 volume, desenho, acabamento, ri_opcao, resp_inspecao, data, data_inspecao))

            if tipo_analise == 'parafusos':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_parafuso_dureza'),
                    'altura': request.form.get('cc_parafuso_altura'),
                    'chave': request.form.get('cc_parafuso_chave'),
                    'comprimento': request.form.get('cc_parafuso_comprimento'),
                    'diametro': request.form.get('cc_parafuso_diametro'),
                    'diametro_cabeca': request.form.get('cc_parafuso_diametro_cabeca'),
                    'comprimento_rosca': request.form.get('cc_parafuso_comprimento_rosca'),
                    'diametro_ponta': request.form.get('cc_parafuso_diametro_ponta'),
                    'norma': request.form.get('cc_parafuso_norma')
                }
                inserir_cadastro_adparafusos(medidas_dimensionais)

            if tipo_analise == 'porcas':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_porcas_dureza'),
                    'altura': request.form.get('cc_porcas_altura'),
                    'chave': request.form.get('cc_porcas_chave'),
                    'diametro': request.form.get('cc_porcas_diametro'),
                    'diametro_estrutura': request.form.get('cc_porcas_diametro_estrutura'),
                    'diametro_interno': request.form.get('cc_porcas_diametro_interno'),
                    'diametro_externo': request.form.get('cc_porcas_diametro_externo'),
                    'norma': request.form.get('cc_porcas_norma')
                }
                inserir_cadastro_adporcas(medidas_dimensionais)

            if tipo_analise == 'arruelas':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_arruelas_dureza'),
                    'altura': request.form.get('cc_arruelas_altura'),
                    'diametro_interno': request.form.get('cc_arruelas_diametro_interno'),
                    'diametro_externo': request.form.get('cc_arruelas_diametro_externo'),
                    'norma': request.form.get('cc_arruelas_norma')
                }
                inserir_cadastro_adarruelas(medidas_dimensionais)

            if tipo_analise == 'anel':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_anel_dureza'),
                    'altura': request.form.get('cc_anel_altura'),
                    'diametro_interno': request.form.get('cc_anel_diametro_interno'),
                    'diametro_externo': request.form.get('cc_anel_diametro_externo'),
                    'norma': request.form.get('cc_anel_norma')
                }
                inserir_cadastro_adanel(medidas_dimensionais)

            if tipo_analise == 'grampos':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_grampos_dureza'),
                    'comprimento': request.form.get('cc_grampos_comprimento'),
                    'diametro': request.form.get('cc_grampos_diametro'),
                    'comprimento_rosca': request.form.get('cc_grampos_comprimento_rosca'),
                    'diametro_interno': request.form.get('cc_grampos_diametro_interno'),
                    'norma': request.form.get('cc_grampos_norma')
                }
                inserir_cadastro_adgrampos(medidas_dimensionais)

            if tipo_analise == 'pinos':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_pinos_dureza'),
                    'espessura': request.form.get('cc_pinos_espessura'),
                    'comprimento': request.form.get('cc_pinos_comprimento'),
                    'diametro': request.form.get('cc_pinos_diametro'),
                    'diametro_cabeca': request.form.get('cc_pinos_diametro_cabeca'),
                    'diametro_interno': request.form.get('cc_pinos_diametro_interno'),
                    'diametro_externo': request.form.get('cc_pinos_diametro_externo'),
                    'norma': request.form.get('cc_pinos_norma')
                }
                inserir_cadastro_adpinos(medidas_dimensionais)

            if tipo_analise == 'prisioneiro_estojo':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_prisioneiro_dureza'),
                    'comprimento': request.form.get('cc_prisioneiro_comprimento'),
                    'diametro': request.form.get('cc_prisioneiro_diametro'),
                    'comprimento_rosca': request.form.get('cc_prisioneiro_comprimento_rosca'),
                    'norma': request.form.get('cc_prisioneiro_norma')
                }
                inserir_cadastro_adprisioneiro_estojo(medidas_dimensionais)

            if tipo_analise == 'chumbador':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_chumbador_dureza'),
                    'comprimento': request.form.get('cc_chumbador_comprimento'),
                    'bitola': request.form.get('cc_chumbador_bitola'),
                    'norma': request.form.get('cc_chumbador_norma')
                }
                inserir_cadastro_adchumbador(medidas_dimensionais)

            if tipo_analise == 'rebite':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_rebite_dureza'),
                    'comprimento': request.form.get('cc_rebite_comprimento'),
                    'bitola': request.form.get('cc_rebite_bitola'),
                    'diametro_cabeca': request.form.get('cc_rebite_diametro_cabeca'),
                    'norma': request.form.get('cc_rebite_norma')
                }
                inserir_cadastro_adrebite(medidas_dimensionais)

            if tipo_analise == 'chaveta':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_chaveta_dureza'),
                    'comprimento': request.form.get('cc_chaveta_comprimento'),
                    'diametro': request.form.get('cc_chaveta_diametro'),
                    'altura': request.form.get('cc_chaveta_altura'),
                    'norma': request.form.get('cc_chaveta_norma')
                }
                inserir_cadastro_adchaveta(medidas_dimensionais)

            if tipo_analise == 'contrapino':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_contrapino_dureza'),
                    'comprimento': request.form.get('cc_contrapino_comprimento'),
                    'diametro': request.form.get('cc_contrapino_diametro'),
                    'norma': request.form.get('cc_contrapino_norma')
                }
                inserir_cadastro_adcontrapino(medidas_dimensionais)

            if tipo_analise == 'especial':
                medidas_dimensionais = {
                    'nota_fiscal': nota_fiscal,
                    'cod_produto': cod_produto,
                    'pedido_compra': pedido_compra,
                    'dureza': request.form.get('cc_especial_dureza'),
                    'altura': request.form.get('cc_especial_altura'),
                    'chave': request.form.get('cc_especial_chave'),
                    'comprimento': request.form.get('cc_especial_comprimento'),
                    'diametro': request.form.get('cc_especial_diametro'),
                    'diametro_cabeca': request.form.get('cc_especial_diametro_cabeca'),
                    'comprimento_rosca': request.form.get('cc_especial_comprimento_rosca'),
                    'diametro_interno': request.form.get('cc_especial_diametro_interno'),
                    'diametro_externo': request.form.get('cc_especial_diametro_externo'),
                    'norma': request.form.get('cc_especial_norma')
                }
                inserir_cadastro_adespecial(medidas_dimensionais)

            connection.commit()
        finally:
            connection.close()

        flash('Registro de Inspeção criado com sucesso!')
        return redirect(url_for('registro_inspecao'))

    return render_template('registro_inspecao.html')


def verificar_existencia_registro(nota_fiscal, cod_produto, pedido_compra):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(1) FROM dbo.registro_inspecao WHERE ri_numero_nota = ? AND ri_cod_produto = ? AND ri_pedido_compra = ?"
            cursor.execute(sql, (nota_fiscal, cod_produto, pedido_compra))
            resultado = cursor.fetchone()
            if resultado and resultado[0] > 0:  # Verifica resultado contagem é maior que zero
                return True  # Existe um registro
            return False  # Não existe registro
    except Exception as e:
        print(f"Erro ao verificar existência do registro de inspeção: {e}")
    finally:
        connection.close()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)