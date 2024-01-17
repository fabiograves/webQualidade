from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, make_response
from flask_session import Session
import pymysql
import base64
from reportlab.pdfgen import canvas
from flask import send_file, Response, send_from_directory
import os
import io
from reportlab.lib.pagesizes import letter
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

            # Armazenar o privilegio na sessão
            session['privilegio'] = user['privilegio']  # Assumindo que 'privilegio' é o nome da coluna

            # Armazenando informações adicionais na sessão
            session['nome_assinatura'] = user['nome_assinatura']
            session['setor_assinatura'] = user['setor_assinatura']
            session['telefone_assinatura'] = user['telefone_assinatura']
            session['email_assinatura'] = user['email_assinatura']

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

@app.route('/criar_certificado')
def criar_certificado():
    return render_template('criar_certificado.html')

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

    # print("Enviando para o template:", resultados)  # Adicione esta linha para depuração
    return render_template('pesquisar_certificado.html', resultados=resultados)

@app.route('/criar_certificado', methods=['POST'])
def tratar_formulario():
    resultado = None  # Defina resultado com um valor padrão

    if 'bt_procurar_nota' in request.form:
        # Código para buscar nota
        numero_nota = request.form['criar_numero_nota']
        resultado = buscar_certificado_nota(numero_nota)
        if resultado:
            # Se os dados foram encontrados, armazene-os na sessão
            session['dados_pdf'] = resultado
        else:
            # Se os dados não foram encontrados, você pode exibir uma mensagem de erro
            flash('Nota fiscal não encontrada.')

    elif 'bt_criar_certificado' in request.form:
        # Código para criar o PDF
        if 'dados_pdf' in session:
            resultado = session['dados_pdf']
            return redirect(url_for('gerar_pdf'))
        else:
            # Se os dados não estiverem na sessão, você pode exibir uma mensagem de erro
            flash('Os dados para criar o PDF não estão disponíveis.')
            return redirect(url_for('gerar_pdf'))  # Redirecionar para uma página apropriada em caso de erro

    return render_template('criar_certificado.html', resultado=resultado)  # Defina resultado como parte do contexto de renderização


@app.route('/gerar_pdf', methods=['POST'])
def gerar_pdf():
    # Recuperando os dados da sessão
    dados_pdf = session.get('dados_pdf')

    # Verifica se os dados necessários estão presentes
    if dados_pdf:
        criar_desc_material = request.form.get('criar_desc_material', 'Não informado')
        criar_codigo_fornecedor = request.form.get('criar_codigo_fornecedor', 'Não informado')
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

        # Verifica se há dados na tabela 'comp_quimica'
        tem_dados_comp_quimica = dados_pdf.get('comp_quimica') and any(dados_pdf['comp_quimica'].values())
        # Verifica se há dados na tabela 'prop_mecanicas'
        tem_dados_prop_mecanicas = dados_pdf.get('prop_mecanicas') and any(dados_pdf['prop_mecanicas'].values())
        # Verifica se há dados na tabela 'tratamentos'
        tem_dados_tratamentos = dados_pdf.get('tratamentos') and any(dados_pdf['tratamentos'].values())
        # Verifica se há dados na tabela 'ad_porcas'
        tem_dados_ad_porcas = dados_pdf.get('ad_porcas') and any(dados_pdf['ad_porcas'].values())
        # Verifica se há dados na tabela 'ad_pinos'
        tem_dados_ad_pinos = dados_pdf.get('ad_pinos') and any(dados_pdf['ad_pinos'].values())
        # Verifica se há dados na tabela 'ad_parafusos'
        tem_dados_ad_parafusos = dados_pdf.get('ad_parafusos') and any(dados_pdf['ad_parafusos'].values())
        # Verifica se há dados na tabela 'ad_grampos'
        tem_dados_ad_grampos = dados_pdf.get('ad_grampos') and any(dados_pdf['ad_grampos'].values())
        # Verifica se há dados na tabela 'ad_arruelas'
        tem_dados_ad_arruelas = dados_pdf.get('ad_arruelas') and any(dados_pdf['ad_arruelas'].values())
        # Verifica se há dados na tabela 'ad_anel'
        tem_dados_ad_anel = dados_pdf.get('ad_anel') and any(dados_pdf['ad_anel'].values())

        # Acessando o valor de 'cc_numero_nota'
        numero_nota = dados_pdf.get('cadastro_certificados', {}).get('cc_numero_nota', 'Não informado')
        comp_quimica = dados_pdf.get('comp_quimica', {}.get('cc_c', ''))

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
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # Alinhar todo o texto à esquerda
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
            dureza = dados_pdf['prop_mecanicas'].get('cc_dureza', '')
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
                 Paragraph("Dureza<br/>Hardness", estilo_centralizado),
                 Paragraph("Prova de Carga<br/>Load Proof", estilo_centralizado)],
                [escoamento, tracao, reducao, alongamento, dureza, carga]
            ]
            prop_mecanicas_table = Table(data, colWidths=effective_page_width / 6)

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
                [revenimento, termico, superficial, macrografia,observacao]
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
            altura = dados_pdf['ad_porcas'].get('cc_adporcas_altura', '')
            chave = dados_pdf['ad_porcas'].get('cc_adporcas_chave', '')
            diametro = dados_pdf['ad_porcas'].get('cc_adporcas_diametro', '')
            diametro_estrutura = dados_pdf['ad_porcas'].get('cc_adporcas_diametro_estrutura', '')
            diametro_interno = dados_pdf['ad_porcas'].get('cc_adporcas_diamentro_interno', '')
            diametro_externo = dados_pdf['ad_porcas'].get('cc_adporcas_diametro_externo', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Estrutural<br/>Structura Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado)],
                [altura, chave, diametro, diametro_estrutura, diametro_interno, diametro_externo]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adporcas_table = Table(data, colWidths=effective_page_width / 6)
            adporcas_table.setStyle(TableStyle(cell_styles))

            elements.append(adporcas_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_pinos:
            espessura = dados_pdf['ad_pinos'].get('cc_adpinos_espeddura', '')
            comprimento = dados_pdf['ad_pinos'].get('cc_adpinos_comprimento', '')
            diametro = dados_pdf['ad_pinos'].get('cc_adpinos_diametro', '')
            diametro_cabeca = dados_pdf['ad_pinos'].get('cc_adpinos_diametro_cabeca', '')
            diametro_interno = dados_pdf['ad_pinos'].get('cc_adpinos_', '')
            diametro_externo = dados_pdf['ad_pinos'].get('cc_adpinos_', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Espessura<br/>Thickness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Length", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Cabeça<br/>Head Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado)],
                [espessura, comprimento, diametro, diametro_cabeca, diametro_interno, diametro_externo]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adpinos_table = Table(data, colWidths=effective_page_width / 6)
            adpinos_table.setStyle(TableStyle(cell_styles))

            elements.append(adpinos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_parafusos:
            altura = dados_pdf['ad_parafusos'].get('cc_adparafusos_altura', "")
            chave = dados_pdf['ad_parafusos'].get('cc_adparafusos_chave', "")
            comprimento = dados_pdf['ad_parafusos'].get('cc_adparafusos_comprimento', "")
            diametro = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro', "")
            diametro_cabeca = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro_cabeca', "")
            comprimento_rosca = dados_pdf['ad_parafusos'].get('cc_adparafusos_comprimento_rosca', "")
            diametro_ponta = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro_ponta', "")

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado)],
                [altura, chave, comprimento,diametro],
                [Paragraph("Diâmetro Cabeça/Corpo<br/>Head/Body Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Diâmetro Ponta<br/>Tip Diameter", estilo_centralizado), ""],
                [diametro_cabeca, comprimento_rosca, diametro_ponta, ""]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adparafusos_table = Table(data, colWidths=effective_page_width / 4)
            adparafusos_table.setStyle(TableStyle(cell_styles))

            elements.append(adparafusos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_grampos:
            comprimento = dados_pdf['ad_grampos'].get('cc_adgrampos_comprimento', '')
            diametro = dados_pdf['ad_grampos'].get('cc_adgrampos_diametro', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado)],
                [comprimento, diametro]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adgrampos_table = Table(data, colWidths=effective_page_width / 2)
            adgrampos_table.setStyle(TableStyle(cell_styles))

            elements.append(adgrampos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_arruelas:
            altura = dados_pdf['ad_arruelas'].get('cc_adarruelas_altura', '')
            diametro_interno = dados_pdf['ad_arruelas'].get('cc_adarruelas_diametro_interno', '')
            diametro_externo = dados_pdf['ad_arruelas'].get('cc_adarruelas_diametro_externo', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado)],
                [altura, diametro_interno, diametro_externo]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adarruelas_table = Table(data, colWidths=effective_page_width / 2)
            adarruelas_table.setStyle(TableStyle(cell_styles))

            elements.append(adarruelas_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_anel:
            altura = dados_pdf['ad_anel'].get('cc_adanel_altura', '')
            diametro_interno = dados_pdf['ad_anel'].get('cc_adanel_diametro_interno', '')
            diametro_externo = dados_pdf['ad_anel'].get('cc_adanel_diametro_externo', '')

            # Texto dentro da tabela
            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            # Cria o parágrafo do texto com o estilo personalizado
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            # Defina o tamanho da fonte que você deseja para as células da tabela
            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado)],
                [altura, diametro_interno, diametro_externo]
            ]

            # Crie uma lista de estilos de célula com o tamanho da fonte definido
            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centraliza o texto
                ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Adiciona linhas de grade
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),  # Escolha a fonte desejada (no exemplo, usei Helvetica)
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),  # Defina o tamanho da fonte
            ]

            adanel_table = Table(data, colWidths=effective_page_width / 2)
            adanel_table.setStyle(TableStyle(cell_styles))

            elements.append(adanel_table)
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
                       "product is in according with reference standards.", estilo_centralizado),
             Paragraph(f"Atenciosamente,<br/>{nome_assinatura}<br/><b>{setor_assinatura}</b><br/>"
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
        # Retorna o PDF como resposta
        buffer.seek(0)
        return Response(buffer.getvalue(), mimetype='application/pdf',
                        headers={"Content-Disposition": "attachment;filename=certificado.pdf"})

    else:
        flash("Dados necessários para gerar o PDF não foram encontrados.")
        return redirect(url_for('criar_certificado'))

def buscar_certificado_nota(numero_nota):
    connection = conectar_db()
    try:
        resultado = {}

        with connection.cursor() as cursor:
            # Busca na tabela de cadastro de certificados
            sql = "SELECT * FROM cadastro_certificados WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            cadastro_certificados = cursor.fetchone()

            # Verifica se o registro foi encontrado
            if cadastro_certificados:
                resultado['cadastro_certificados'] = cadastro_certificados

                # Verifica se o arquivo existe
                if cadastro_certificados['cc_arquivo']:
                    resultado['arquivo'] = cadastro_certificados['cc_arquivo']
                else:
                    resultado['arquivo'] = None
            else:
                resultado['cadastro_certificados'] = None
                resultado['arquivo'] = None

            sql = "SELECT * FROM comp_quimica WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['comp_quimica'] = cursor.fetchone()

            sql = "SELECT * FROM prop_mecanicas WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['prop_mecanicas'] = cursor.fetchone()

            sql = "SELECT * FROM tratamentos WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['tratamentos'] = cursor.fetchone()

            sql = "SELECT * FROM ad_porcas WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['ad_porcas'] = cursor.fetchone()

            sql = "SELECT * FROM ad_pinos WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['ad_pinos'] = cursor.fetchone()

            sql = "SELECT * FROM ad_parafusos WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['ad_parafusos'] = cursor.fetchone()

            sql = "SELECT * FROM ad_grampos WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['ad_grampos'] = cursor.fetchone()

            sql = "SELECT * FROM ad_arruelas WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['ad_arruelas'] = cursor.fetchone()

            sql = "SELECT * FROM ad_anel WHERE cc_numero_nota = %s"
            cursor.execute(sql, (numero_nota,))
            resultado['ad_anel'] = cursor.fetchone()


    except Exception as e:
        print(f"1 Erro ao buscar certificado por nota: {e}")
        resultado = None
    finally:
        connection.close()

    return resultado

@app.route('/download_arquivo/<numero_nota>')
def download_arquivo(numero_nota):
    resultado = buscar_certificado_nota(numero_nota)

    # Verifica se um arquivo foi encontrado
    if resultado and resultado['arquivo']:
        arquivo_binario = resultado['arquivo']
        nome_arquivo = f"certificado_{numero_nota}.pdf"
        file_like = io.BytesIO(arquivo_binario)

        response = make_response(file_like.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
        response.mimetype = 'application/pdf'
        return response
    else:
        return "Arquivo não encontrado", 404

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

    # print("Resultados encontrados:", resultados_agrupados)  # Para depuração
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
        # Verificação de existência
        if verificar_existencia_nota(nota_fiscal):
            flash('Número da nota já cadastrado no sistema.')
            return redirect(url_for('cadastro_certificados'))
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
            # print("Tipo de Análise:", tipo_analise)
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

def verificar_existencia_nota(nota_fiscal):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(1) FROM cadastro_certificados WHERE cc_numero_nota = %s"
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
            sql = """
            INSERT INTO cadastro_certificados 
            (cc_numero_nota, cc_descricao, cc_cod_fornecedor, cc_cod_produto, cc_corrida, cc_data, cc_cq, cc_qtd_pedidos, cc_arquivo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
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
        print(f"Ocorreu um erro: {e}")
    finally:
        connection.close()

def inserir_cadastro_composicao_quimica(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO comp_quimica
            (cc_numero_nota, cc_c, cc_mn, cc_p, cc_s, cc_si, cc_ni, cc_cr, cc_b, cc_cu, cc_mo, cc_co, cc_fe, cc_sn, cc_al, cc_n, cc_nb)
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
                dados['fe'],
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
