import base64
import datetime
import json
import tempfile

import pyodbc
import logging
from datetime import timedelta
from PyPDF2 import PdfMerger
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response, jsonify
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from werkzeug.utils import secure_filename
from flask_session import Session
from flask import send_file, Response
import os
import io
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import Image
from reportlab.platypus import Spacer
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from collections import defaultdict
from io import BytesIO
import pdfplumber
import re
import zipfile

import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine


#from pyzbar import pyzbar
import numpy as np
#import cv2

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Configuração da extensão Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Substitua 'DATABASE_URL' pela URL do seu banco de dados
DATABASE_URL = 'mssql+pyodbc://Qualidade:y2%:ff4G4A>7@172.16.2.27:1433/dbQualidade?driver=ODBC+Driver+17+for+SQL+Server'

# Crie o engine
engine = create_engine(DATABASE_URL)

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


def is_logged_in():
    """Verifica se o utilizador está logado."""
    return 'logged_in' in session


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['usuario']
        password = request.form['senha']

        try:
            connection = conectar_db()
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM dbo.usuarios WHERE nome_usuario = ? AND senha_usuario = ?',
                           (username, password))
            user = cursor.fetchone()

            if user:
                session['logged_in'] = True
                session['username'] = username

                session['privilegio'] = user.privilegio

                # Armazenando informações adicionais na sessão
                session['nome_assinatura'] = user.nome_assinatura
                session['setor_assinatura'] = user.setor_assinatura
                session['telefone_assinatura'] = user.telefone_assinatura
                session['email_assinatura'] = user.email_assinatura

                username = session['username']
                print(f"Ação realizada por: {username}, Logou")
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
    username = session['username']
    print(f"Ação realizada por: {username}, Deslogou")
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('privilegio', None)
    session.pop('nome_assinatura', None)
    session.pop('setor_assinatura', None)
    session.pop('telefone_assinatura', None)
    session.pop('email_assinatura', None)
    flash('Você saiu com sucesso.')
    return redirect(url_for('login'))


@app.context_processor
def inject_aviso():
    connection = conectar_db()
    cursor = connection.cursor()
    mensagens_aviso = []

    try:
        cursor.execute("SELECT numero_instrumento, equipamento, ultima_calibracao, intervalo "
                       "FROM dbo.cadastro_equipamento")
        mensagens_db = cursor.fetchall()

        for numero_instrumento, equipamento, ultima_calibracao, intervalo in mensagens_db:
            data_calibracao_dt = datetime.datetime.strptime(ultima_calibracao, "%Y-%m-%d").date()
            data_vencimento = datetime.date(data_calibracao_dt.year + int(intervalo), data_calibracao_dt.month,
                                            data_calibracao_dt.day)
            hoje = datetime.date.today()
            dias_para_vencimento = (data_vencimento - hoje).days
            data_vencimento_formatada = data_vencimento.strftime("%d/%m/%Y")
            if dias_para_vencimento <= 60 and dias_para_vencimento >= 0:
                aviso = f"{numero_instrumento} - {equipamento} - Vencimento em {data_vencimento_formatada} - Faltam {dias_para_vencimento} dias"
                mensagens_aviso.append(aviso)
            elif dias_para_vencimento < 0:
                dias_apos_vencimento = abs(dias_para_vencimento)
                aviso = f"{numero_instrumento} - {equipamento} - Venceu em {data_vencimento_formatada} - Vencido há {dias_apos_vencimento} dias"
                mensagens_aviso.append(aviso)

    except Exception as e:
        print(f"Erro ao buscar mensagens de aviso: {e}")
    finally:
        cursor.close()
        connection.close()

    return dict(mensagens_aviso=mensagens_aviso)


@app.route('/')
def home():
    if not is_logged_in():
        return redirect(url_for('login'))
    username = session['username']
    privilegio = session['privilegio']
    if privilegio == 1:
        print(f"Ação realizada por: {username}, Clicou Home_recebimento")
        return render_template('home_recebimento.html')
    elif privilegio == 2:
        print(f"Ação realizada por: {username}, Clicou Home")
        return render_template('home_recebimento_concluido.html')
    elif privilegio == 3:
        print(f"Ação realizada por: {username}, Clicou Home")
        return render_template('home_zincagem.html')
    elif privilegio == 9:
        print(f"Ação realizada por: {username}, Clicou Home")
        return render_template('home.html')


@app.route('/home_recebimento')
def home_recebimento():
    if not is_logged_in():
        return redirect(url_for('login'))
    username = session['username']
    print(f"Ação realizada por: {username}, Clicou Home")
    return render_template('home_recebimento.html')


@app.route('/home_recebimento_concluido')
def home_recebimento_concluido():
    if not is_logged_in():
        return redirect(url_for('login'))
    username = session['username']
    print(f"Ação realizada por: {username}, Clicou Home")
    return render_template('home_recebimento_concluido.html')


@app.route('/home_zincagem')
def home_zincagem():
    if not is_logged_in():
        return redirect(url_for('login'))
    username = session['username']
    print(f"Ação realizada por: {username}, Clicou Home")
    return render_template('home_zincagem.html')


@app.route('/relatorio_teste')
def relatorio_teste():
    return render_template('/relatorio_teste.html')


@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    def add_header(p):
        logo_path = "static/images/LogoCertificado.png"
        p.drawImage(logo_path, 30, height - 80, width=150, height=60)
        p.setFont("Helvetica-Bold", 30)
        p.drawString(225, height - 55, "Relatório de Torque")

        p.setFont("Helvetica-Bold", 10)
        p.drawString(30, height - 100, f"Cliente: {cliente}")
        p.drawString(30, height - 115, f"Pedido: {pedido}")
        p.drawString(300, height - 115, f"Data: {data_relatorio}")
        p.drawString(30, height - 130, f"OBS: {obs}")

    def draw_images(p):
        styles = getSampleStyleSheet()
        centered_style = styles['Normal']
        centered_style.alignment = 1  # Center alignment

        image_texts = [
            request.form.get('relatorio_texto_imagem1', ''),
            request.form.get('relatorio_texto_imagem2', ''),
            request.form.get('relatorio_texto_imagem3', ''),
            request.form.get('relatorio_texto_imagem4', ''),
            request.form.get('relatorio_texto_imagem5', ''),
            request.form.get('relatorio_texto_imagem6', '')
        ]
        image_files = [
            request.files.get('imagem1'),
            request.files.get('imagem2'),
            request.files.get('imagem3'),
            request.files.get('imagem4'),
            request.files.get('imagem5'),
            request.files.get('imagem6')
        ]

        table_data = []
        for i in range(0, 6, 3):
            row = []
            for j in range(3):
                index = i + j
                if index < len(image_texts):
                    text = image_texts[index]
                    image_file = image_files[index]
                    if image_file:
                        image_buffer = BytesIO(image_file.read())
                        img = Image(image_buffer, width=2 * inch, height=1.5 * inch)
                        paragraph = Paragraph(text, centered_style)
                        cell_content = [paragraph, Spacer(1, 10), img]
                        row.append(cell_content)
                    else:
                        row.append([Paragraph("", centered_style), Spacer(1, 12), Paragraph("", centered_style)])
                else:
                    row.append([Paragraph("", centered_style), Spacer(1, 12), Paragraph("", centered_style)])
            table_data.append(row)

        table = Table(table_data, colWidths=[2.5 * inch, 2.5 * inch, 2.5 * inch], rowHeights=[2.5 * inch, 2.5 * inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))

        table.wrapOn(p, width, height)
        table.drawOn(p, 30, height - 500)

        # Add observation below images
        obs_final = request.form.get('relatorio_obs_final', '')
        obs_y_position = height - 520

        p.drawString(30, obs_y_position, "Observação:")
        p.drawString(100, obs_y_position, obs_final)

    # Draw the form fields data
    cliente = request.form.get('relatorio_cliente', '')
    pedido = request.form.get('relatorio_pedido', '')
    data_relatorio = request.form.get('relatorio_data', '')
    obs = request.form.get('relatorio_obs', '')

    table_types = json.loads(request.form.get('table_types', '[]'))
    tables_data = []

    for table_id in table_types:
        table_type = request.form.get(f'table_type_{table_id}')
        table_header = request.form.get(f'table_header_{table_id}')
        rows = []

        if table_type == '1':
            rows = [
                ["DIMENSIONAL DE PARTIDA", request.form.get(f'dimensional_partida_{table_id}_1', ''), request.form.get(f'dimensional_partida_{table_id}_2', ''), request.form.get(f'dimensional_partida_{table_id}_3', '')],
                ["TORQUE 136 Nm (CONF.TABELA)", request.form.get(f'torque_136_{table_id}_1', ''), request.form.get(f'torque_136_{table_id}_2', ''), request.form.get(f'torque_136_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_136_{table_id}_1', ''), request.form.get(f'alongamento_136_{table_id}_2', ''), request.form.get(f'alongamento_136_{table_id}_3', '')],
                ["TORQUE 149,6 Nm (10% A MAIS TABELA)", request.form.get(f'torque_1496_{table_id}_1', ''), request.form.get(f'torque_1496_{table_id}_2', ''), request.form.get(f'torque_1496_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_1496_{table_id}_1', ''), request.form.get(f'alongamento_1496_{table_id}_2', ''), request.form.get(f'alongamento_1496_{table_id}_3', '')],
                ["TORQUE 163,2 Nm (20% A MAIS TABELA)", request.form.get(f'torque_1632_{table_id}_1', ''), request.form.get(f'torque_1632_{table_id}_2', ''), request.form.get(f'torque_1632_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_1632_{table_id}_1', ''), request.form.get(f'alongamento_1632_{table_id}_2', ''), request.form.get(f'alongamento_1632_{table_id}_3', '')],
                ["TORQUE 176,8 Nm (30% A MAIS TABELA)", request.form.get(f'torque_1768_{table_id}_1', ''), request.form.get(f'torque_1768_{table_id}_2', ''), request.form.get(f'torque_1768_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_1768_{table_id}_1', ''), request.form.get(f'alongamento_1768_{table_id}_2', ''), request.form.get(f'alongamento_1768_{table_id}_3', '')]
            ]
        elif table_type == '2':
            rows = [
                ["DIMENSIONAL DE PARTIDA", request.form.get(f'dimensional_partida_{table_id}_1', ''), request.form.get(f'dimensional_partida_{table_id}_2', ''), request.form.get(f'dimensional_partida_{table_id}_3', '')],
                ["TORQUE 271 Nm (CONF.TABELA)", request.form.get(f'torque_271_{table_id}_1', ''), request.form.get(f'torque_271_{table_id}_2', ''), request.form.get(f'torque_271_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_271_{table_id}_1', ''), request.form.get(f'alongamento_271_{table_id}_2', ''), request.form.get(f'alongamento_271_{table_id}_3', '')],
                ["TORQUE 298,1 Nm (10% A MAIS TABELA)", request.form.get(f'torque_298_{table_id}_1', ''), request.form.get(f'torque_298_{table_id}_2', ''), request.form.get(f'torque_298_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_298_{table_id}_1', ''), request.form.get(f'alongamento_298_{table_id}_2', ''), request.form.get(f'alongamento_298_{table_id}_3', '')],
                ["TORQUE 318,1 Nm (20% A MAIS TABELA)", request.form.get(f'torque_318_{table_id}_1', ''), request.form.get(f'torque_318_{table_id}_2', ''), request.form.get(f'torque_318_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_318_{table_id}_1', ''), request.form.get(f'alongamento_318_{table_id}_2', ''), request.form.get(f'alongamento_318_{table_id}_3', '')],
                ["TORQUE 338,1 Nm (30% A MAIS TABELA)", request.form.get(f'torque_338_{table_id}_1', ''), request.form.get(f'torque_338_{table_id}_2', ''), request.form.get(f'torque_338_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_338_{table_id}_1', ''), request.form.get(f'alongamento_338_{table_id}_2', ''), request.form.get(f'alongamento_338_{table_id}_3', '')]
            ]
        elif table_type == '3':
            rows = [
                ["DIMENSIONAL DE PARTIDA", request.form.get(f'dimensional_partida_{table_id}_1', ''), request.form.get(f'dimensional_partida_{table_id}_2', ''), request.form.get(f'dimensional_partida_{table_id}_3', '')],
                ["TORQUE 422 Nm (CONF.TABELA)", request.form.get(f'torque_422_{table_id}_1', ''), request.form.get(f'torque_422_{table_id}_2', ''), request.form.get(f'torque_422_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_422_{table_id}_1', ''), request.form.get(f'alongamento_422_{table_id}_2', ''), request.form.get(f'alongamento_422_{table_id}_3', '')],
                ["TORQUE 464,2 Nm (10% A MAIS TABELA)", request.form.get(f'torque_464_{table_id}_1', ''), request.form.get(f'torque_464_{table_id}_2', ''), request.form.get(f'torque_464_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_464_{table_id}_1', ''), request.form.get(f'alongamento_464_{table_id}_2', ''), request.form.get(f'alongamento_464_{table_id}_3', '')],
                ["TORQUE 510,62 Nm (20% A MAIS TABELA)", request.form.get(f'torque_510_{table_id}_1', ''), request.form.get(f'torque_510_{table_id}_2', ''), request.form.get(f'torque_510_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_510_{table_id}_1', ''), request.form.get(f'alongamento_510_{table_id}_2', ''), request.form.get(f'alongamento_510_{table_id}_3', '')],
                ["TORQUE 561,66 Nm (30% A MAIS TABELA)", request.form.get(f'torque_561_{table_id}_1', ''), request.form.get(f'torque_561_{table_id}_2', ''), request.form.get(f'torque_561_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_561_{table_id}_1', ''), request.form.get(f'alongamento_561_{table_id}_2', ''), request.form.get(f'alongamento_561_{table_id}_3', '')]
            ]
        elif table_type == '4':
            rows = [
                ["DIMENSIONAL DE PARTIDA", request.form.get(f'dimensional_partida_{table_id}_1', ''), request.form.get(f'dimensional_partida_{table_id}_2', ''), request.form.get(f'dimensional_partida_{table_id}_3', '')],
                ["TORQUE 741 Nm (CONF.TABELA)", request.form.get(f'torque_741_{table_id}_1', ''), request.form.get(f'torque_741_{table_id}_2', ''), request.form.get(f'torque_741_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_741_{table_id}_1', ''), request.form.get(f'alongamento_741_{table_id}_2', ''), request.form.get(f'alongamento_741_{table_id}_3', '')],
                ["TORQUE 815,1 Nm (10% A MAIS TABELA)", request.form.get(f'torque_815_{table_id}_1', ''), request.form.get(f'torque_815_{table_id}_2', ''), request.form.get(f'torque_815_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_815_{table_id}_1', ''), request.form.get(f'alongamento_815_{table_id}_2', ''), request.form.get(f'alongamento_815_{table_id}_3', '')],
                ["TORQUE 896,61 Nm (20% A MAIS TABELA)", request.form.get(f'torque_896_{table_id}_1', ''), request.form.get(f'torque_896_{table_id}_2', ''), request.form.get(f'torque_896_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_896_{table_id}_1', ''), request.form.get(f'alongamento_896_{table_id}_2', ''), request.form.get(f'alongamento_896_{table_id}_3', '')],
                ["TORQUE 986,27 Nm (30% A MAIS TABELA)", request.form.get(f'torque_986_{table_id}_1', ''), request.form.get(f'torque_986_{table_id}_2', ''), request.form.get(f'torque_986_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_986_{table_id}_1', ''), request.form.get(f'alongamento_986_{table_id}_2', ''), request.form.get(f'alongamento_986_{table_id}_3', '')]
            ]
        elif table_type == '5':
            rows = [
                ["DIMENSIONAL DE PARTIDA", request.form.get(f'dimensional_partida_{table_id}_1', ''), request.form.get(f'dimensional_partida_{table_id}_2', ''), request.form.get(f'dimensional_partida_{table_id}_3', '')],
                ["TORQUE 1071 Nm (CONF.TABELA)", request.form.get(f'torque_1071_{table_id}_1', ''), request.form.get(f'torque_1071_{table_id}_2', ''), request.form.get(f'torque_1071_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_1071_{table_id}_1', ''), request.form.get(f'alongamento_1071_{table_id}_2', ''), request.form.get(f'alongamento_1071_{table_id}_3', '')],
                ["TORQUE 1091 Nm (10% A MAIS TABELA)", request.form.get(f'torque_1091_{table_id}_1', ''), request.form.get(f'torque_1091_{table_id}_2', ''), request.form.get(f'torque_1091_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_1091_{table_id}_1', ''), request.form.get(f'alongamento_1091_{table_id}_2', ''), request.form.get(f'alongamento_1091_{table_id}_3', '')],
                ["TORQUE 1111 Nm (20% A MAIS TABELA)", request.form.get(f'torque_1111_{table_id}_1', ''), request.form.get(f'torque_1111_{table_id}_2', ''), request.form.get(f'torque_1111_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_1111_{table_id}_1', ''), request.form.get(f'alongamento_1111_{table_id}_2', ''), request.form.get(f'alongamento_1111_{table_id}_3', '')],
                ["TORQUE 1131 Nm (30% A MAIS TABELA)", request.form.get(f'torque_1131_{table_id}_1', ''), request.form.get(f'torque_1131_{table_id}_2', ''), request.form.get(f'torque_1131_{table_id}_3', '')],
                ["% DE ALONGAMENTO", request.form.get(f'alongamento_1131_{table_id}_1', ''), request.form.get(f'alongamento_1131_{table_id}_2', ''), request.form.get(f'alongamento_1131_{table_id}_3', '')]
            ]
        tables_data.append((table_header, rows))

    add_header(p)
    draw_images(p)

    username = session.get('username', 'N/A')
    nome_assinatura = session.get('nome_assinatura', 'N/A')
    setor_assinatura = session.get('setor_assinatura', 'N/A')
    telefone_assinatura = session.get('telefone_assinatura', 'N/A')
    email_assinatura = session.get('email_assinatura', 'N/A')

    user_info = [
        f"Nome: {nome_assinatura}",
        f"Setor: {setor_assinatura}",
        f"{telefone_assinatura}",
        f"{email_assinatura}"
    ]

    p.setFont("Helvetica", 10)
    text_y = 100
    for info in user_info:
        p.drawRightString(width - 30, text_y, info)
        text_y -= 12

    p.showPage()

    add_header(p)
    # Draw tables in the PDF
    y_position = height - 150
    for table_header, rows in tables_data:
        data = [[f"Ø {table_header}", "1", "2", "3"]]
        data.extend(rows)

        row_heights = [0.25 * inch] * len(data)

        t = Table(data, colWidths=[2.0 * inch, 1 * inch, 1 * inch, 1 * inch], rowHeights=row_heights)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        t.setStyle(style)

        table_width, table_height = t.wrap(0, height)

        if y_position - table_height < 0:
            p.showPage()
            add_header(p)
            y_position = height - 150

        t.drawOn(p, 125, y_position - table_height)
        y_position -= table_height + 10  # Espaço entre as tabelas

    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='relatorio_torque.pdf', mimetype='application/pdf')


@app.route('/download_certificado', methods=['GET', 'POST'])
def download_certificado():
    return render_template('download_certificado.html')


@app.route('/cadastro_equipamento', methods=['GET', 'POST'])
def cadastro_equipamento():
    if not is_logged_in():
        return redirect(url_for('login'))

    username = session['username']
    print(f"Ação realizada por: {username}, Entrou em Cadastro de Equipamento")
    numeros_instrumentos = []
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            # Busca todos os números de instrumentos existentes
            cursor.execute("SELECT DISTINCT numero_instrumento FROM dbo.cadastro_equipamento ORDER BY numero_instrumento ASC")
            numeros_instrumentos = [row[0] for row in cursor.fetchall()]

    except Exception as e:
        print(f"Erro ao buscar números de instrumentos: {e}")

    if request.method == 'POST':
        numero_instrumento = request.form.get('cad_numero_instrumento')
        equipamento = request.form.get('cad_equipamento')
        ultima_calibracao = request.form.get('cad_ultima_calibracao')
        intervalo = request.form.get('cad_intervalo')

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM dbo.cadastro_equipamento WHERE numero_instrumento = ?", (numero_instrumento,))
                (count,) = cursor.fetchone()
                if count > 0:
                    sql_update = ("UPDATE dbo.cadastro_equipamento SET equipamento = ?, ultima_calibracao = ?, intervalo = ? "
                                  "WHERE numero_instrumento = ?")
                    cursor.execute(sql_update, (equipamento, ultima_calibracao, intervalo, numero_instrumento))
                    print(f"Ação realizada por: {username}, Atualizou: {equipamento}")
                    flash('Atualização de equipamento com sucesso!')
                else:
                    sql_insert = ("INSERT INTO dbo.cadastro_equipamento (numero_instrumento, equipamento, "
                                  "ultima_calibracao, intervalo) VALUES (?, ?, ?, ?)")
                    cursor.execute(sql_insert, (numero_instrumento, equipamento, ultima_calibracao, intervalo))
                    print(f"Ação realizada por: {username}, Cadastrou: {equipamento}")
                    flash('Cadastro de equipamento com sucesso!')
                connection.commit()

        except Exception as e:
            print(f"Erro ao buscar números de instrumentos ou ao cadastrar/atualizar equipamento: {e}")
            flash('Ocorreu um erro ao processar sua solicitação.', 'error')
            return render_template('cadastro_equipamento.html', numeros_instrumentos=numeros_instrumentos), 500

        finally:
            if connection:
                connection.close()

    return render_template('cadastro_equipamento.html', numeros_instrumentos=numeros_instrumentos)


@app.route('/buscar_dados_instrumento/<numero_instrumento>')
def buscar_dados_instrumento(numero_instrumento):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT equipamento, ultima_calibracao, intervalo FROM dbo.cadastro_equipamento WHERE numero_instrumento = ?", (numero_instrumento,))
            resultado = cursor.fetchone()
            if resultado:
                return jsonify({
                    "equipamento": resultado[0],
                    "ultima_calibracao": resultado[1] if resultado[1] else '',
                    "intervalo": resultado[2]
                })
            else:
                return jsonify({}), 404
    except Exception as e:
        print(f"Erro ao buscar dados do instrumento: {e}")
        return "Erro ao buscar dados", 500
    finally:
        if connection:
            connection.close()


@app.route('/baixar_certificado_por_id', methods=['POST'])
def baixar_certificado_por_id():
    if not is_logged_in():
        return redirect(url_for('login'))

    numero_certificado = request.form.get('dc_numero_certificado')
    nota_saida = request.form.get('dc_nota_saida')

    connection = conectar_db()
    cursor = connection.cursor()

    try:
        arquivos = None
        if numero_certificado:
            cursor.execute("SELECT arquivo FROM dbo.certificados_gerados WHERE id = ?", (numero_certificado,))
            arquivos = cursor.fetchall()
        elif nota_saida:
            cursor.execute("SELECT arquivo FROM dbo.certificados_gerados WHERE numero_nota = ?", (nota_saida,))
            arquivos = cursor.fetchall()

        if arquivos:
            if len(arquivos) == 1:
                # Se apenas um arquivo, envie diretamente
                response = make_response(arquivos[0][0])
                content_filename = f'certificado_{numero_certificado}.pdf' if numero_certificado else f'certificados_nota_{nota_saida}.pdf'
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename={content_filename}'
                return response
            else:
                # Se múltiplos arquivos, crie um zip com eles individualmente
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zf:
                    for i, arquivo in enumerate(arquivos):
                        pdf_filename = f'certificado_{i + 1}.pdf'
                        zf.writestr(pdf_filename, arquivo[0])

                zip_buffer.seek(0)
                response = make_response(zip_buffer.read())
                content_filename = f'certificados_nota_{nota_saida}.zip'

                response.headers['Content-Type'] = 'application/zip'
                response.headers['Content-Disposition'] = f'attachment; filename={content_filename}'
                return response
        else:
            return "Certificado não encontrado.", 404
    except Exception as e:
        print(f"Erro ao buscar o certificado: {e}")
        return "Ocorreu um erro ao processar sua solicitação.", 500
    finally:
        username = session.get('username', 'unknown user')
        print(f"Ação realizada por: {username}, Baixar Certificado NF:{numero_certificado} - NS:{nota_saida}")
        cursor.close()
        connection.close()


@app.route('/criar_certificado')
def criar_certificado():
    if not is_logged_in():
        return redirect(url_for('login'))

    return render_template('criar_certificado.html')


@app.route('/cadastro_fornecedor', methods=['GET', 'POST'])
def cadastro_fornecedor():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome_fornecedor = request.form['cad_nome_fornecedor']
        dados_complementares = request.form['cad_dados_fornecedor']

        connection = conectar_db()
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO dbo.cadastro_fornecedor (nome_fornecedor) VALUES (?)"
                cursor.execute(sql, nome_fornecedor)
                connection.commit()
            flash('Formulário enviado com sucesso!')
            username = session['username']
            print(f"Ação realizada por: {username}, Cadastro Fornecedor Nome:{nome_fornecedor}")
            return redirect(url_for('cadastro_fornecedor'))
        except Exception as e:
            print(f"Erro ao inserir o fornecedor no banco de dados: {e}")
            flash(f"Erro ao inserir o fornecedor no banco de dados: {e}")
            return redirect(url_for('cadastro_fornecedor'))
        finally:
            connection.close()
    else:
        return render_template('cadastro_fornecedor.html')


@app.route('/avaliacao_diaria.html', methods=['GET', 'POST'])
def avaliacao_diaria():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    fornecedores = []
    try:
        with connection.cursor() as cursor:
            if request.method == 'POST':
                data = request.form['ad_data']
                id_fornecedor = request.form['fornecedor']
                nao_conformidade = request.form['ad_nao_conformidade']
                atraso_entrega = request.form['ad_atraso_entrega']
                observacao = request.form['ad_observacao']

                sql_verifica = "SELECT COUNT(*) FROM dbo.avaliacao_diaria WHERE id_fornecedor = ? AND data = ?"
                cursor.execute(sql_verifica, (id_fornecedor, data))
                if cursor.fetchone()[0] > 0:
                    # Se já existe, apague o registro existente
                    sql_delete = "DELETE FROM dbo.avaliacao_diaria WHERE id_fornecedor = ? AND data = ?"
                    cursor.execute(sql_delete, (id_fornecedor, data))
                    flash('Avaliação substituida.')
                    print(f"Registro apagado.")

                sql_insert = """
                    INSERT INTO dbo.avaliacao_diaria (id_fornecedor, data, nao_conformidade, atraso_entrega, 
                    observacao)
                    VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(sql_insert, (id_fornecedor, data, nao_conformidade, atraso_entrega, observacao))
                connection.commit()

                username = session['username']
                print(
                    f"Ação realizada por: {username}, Avaliação Diária Data: {data} - ID:{id_fornecedor}"
                    f" - NC:{nao_conformidade} - AE:{atraso_entrega}")
                flash('Registro inserido com sucesso!')
                return redirect(url_for('avaliacao_diaria'))

            else:
                # Se o método não for POST, apenas mostre a página com os fornecedores
                sql_fornecedores = ("SELECT id, nome_fornecedor FROM dbo.cadastro_fornecedor "
                                    "ORDER BY nome_fornecedor ASC")
                cursor.execute(sql_fornecedores)
                fornecedores = cursor.fetchall()
    except Exception as e:
        print(f"Erro: {e}")
        flash(f"Erro: {e}")
    finally:
        connection.close()

    return render_template('avaliacao_diaria.html', fornecedores=fornecedores)


@app.route('/pesquisar_avaliacao_diaria.html', methods=['GET', 'POST'])
def pesquisar_avaliacao_diaria():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    fornecedores = []
    dados_organizados = {}
    resumo_trimestral = defaultdict(lambda: defaultdict(dict))
    resumo_por_trimestre = {1: [], 2: [], 3: [], 4: []}
    pesquisa_realizada = False
    fornecedor_escolhido = None
    id_fornecedor = None

    try:
        with connection.cursor() as cursor:
            # Busca fornecedores para o <select>
            sql_fornecedores = "SELECT id, nome_fornecedor FROM dbo.cadastro_fornecedor ORDER BY nome_fornecedor ASC"
            cursor.execute(sql_fornecedores)
            fornecedores = cursor.fetchall()

            if request.method == 'POST':
                pesquisa_realizada = True
                id_fornecedor = request.form['fornecedor']
                ano = request.form['ano']

                # Obtém o nome do fornecedor escolhido
                cursor.execute("SELECT nome_fornecedor FROM dbo.cadastro_fornecedor WHERE id = ?", (id_fornecedor,))
                fornecedor_escolhido = cursor.fetchone()[0]

                # Formata a pesquisa para capturar os registros de um ano específico
                cursor.execute("""
                SELECT * FROM dbo.avaliacao_diaria
                WHERE id_fornecedor = ? AND CONVERT(VARCHAR, data, 23) LIKE ?
                """, (id_fornecedor, f"{ano}%"))

                resultado = fetch_dict(cursor)
                while resultado:
                    data_obj = datetime.datetime.strptime(resultado['data'], '%Y-%m-%d')
                    mes = data_obj.month
                    dia = data_obj.day

                    if mes not in dados_organizados:
                        dados_organizados[mes] = {}

                    # Diretamente atribui o resultado ao dia específico
                    dados_organizados[mes][dia] = resultado

                    resultado = fetch_dict(cursor)

        # Cálculo do resumo trimestral após todos os dados serem organizados
        for mes, dias in dados_organizados.items():
            soma_nao_conformidade = sum(dia.get('nao_conformidade', 0) for dia in dias.values())
            soma_atraso_entrega = sum(dia.get('atraso_entrega', 0) for dia in dias.values())
            qtd_dias_com_valor = sum(1 for dia in dias.values())

            resumo_trimestral[mes] = {'soma_nao_conformidade': soma_nao_conformidade,
                                      'soma_atraso_entrega': soma_atraso_entrega,
                                      'qtd_dias_com_valor': qtd_dias_com_valor
                                      }

        # Agrupa os dados por trimestre e calcula o valor final para cada mês
        for mes, dados in resumo_trimestral.items():
            trimestre = (mes - 1) // 3 + 1
            dados['valor_final'] = ((dados['soma_nao_conformidade'] + dados['soma_atraso_entrega']) / max(
                dados['qtd_dias_com_valor'], 2)) * 5
            resumo_por_trimestre[trimestre].append((mes, dados))

        notas_finais_trimestres = {}
        for trimestre, meses in resumo_por_trimestre.items():
            total_valor_final = sum(dados['valor_final'] for _, dados in meses if 'valor_final' in dados)
            total_meses_com_dados = sum(1 for _, dados in meses if 'valor_final' in dados and dados['valor_final'] > 0)
            # Calcula a nota final apenas se houver meses com dados
            nota_final_trimestre = total_valor_final / total_meses_com_dados if total_meses_com_dados else 0
            notas_finais_trimestres[trimestre] = round(nota_final_trimestre, 2)

    except Exception as e:
        print(f"Erro: {e}")
        flash(f"Erro ao processar a pesquisa: {e}")
    finally:
        connection.close()

    meses_ordenados = sorted(dados_organizados.items(), key=lambda x: x[0], reverse=True)
    username = session['username']
    print(f"Ação realizada por: {username}, fornecedor escolhido: {fornecedor_escolhido}, id:{id_fornecedor}")

    return render_template('pesquisar_avaliacao_diaria.html',
                           fornecedores=fornecedores,
                           resultados=meses_ordenados,
                           resumo_por_trimestre=resumo_por_trimestre,
                           notas_finais_trimestres=notas_finais_trimestres,
                           pesquisa_realizada=pesquisa_realizada,
                           fornecedor_escolhido=fornecedor_escolhido)



@app.route('/lista_norma')
def lista_norma():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT norma, descricao FROM dbo.imagem_norma")
            normas = cursor.fetchall()
            # Separar normas em numéricas e alfabéticas
            normas_numericas = [n for n in normas if n[0].split('-')[0].isdigit()]
            normas_alfabeticas = [n for n in normas if not n[0].split('-')[0].isdigit()]
            # Ordenar cada lista separadamente
            normas_numericas.sort(key=lambda x: int(x[0].split('-')[0]))
            normas_alfabeticas.sort(key=lambda x: x[0])
            # Concatenar as listas
            normas = normas_numericas + normas_alfabeticas
    except Exception as e:
        print(f"Erro ao buscar normas: {e}")
        normas = []
    finally:
        connection.close()

    username = session['username']
    print(f"Ação realizada por: {username}, Lista Norma")

    return render_template('lista_norma.html', normas=normas)


@app.route('/plano_controle_inspecao', methods=['GET', 'POST'])
def plano_controle_inspecao():
    if not is_logged_in():
        return redirect(url_for('login'))

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

            username = session['username']
            print(f"Ação realizada por: {username}, Plano Controle:{numero}")
            return redirect(url_for('plano_controle_inspecao'))
        else:
            print("Controle número: ", numero, "ERRO ao cadastrar.")
            return redirect(url_for('cadastro_norma'))

    # Para o GET, vamos buscar todas as imagens no banco de dados
    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT numero, imagem FROM dbo.plano_controle_inspecao ORDER BY CAST(numero AS INT) ASC")
    imagens_db = cursor.fetchall()
    connection.close()

    # Converter imagens para base64 para serem exibidas no HTML
    imagens = [{'numero': img[0], 'imagem': base64.b64encode(img[1]).decode('utf-8')} for img in imagens_db]
    username = session['username']
    print(f"Ação realizada por: {username}, Plano Controle Imagens")

    return render_template('plano_controle_inspecao.html', imagens=imagens)


@app.route('/base')
def base():
    return render_template('base.html')


@app.route('/pesquisar_certificado', methods=['GET', 'POST'])
def pesquisar_certificado():
    if not is_logged_in():
        return redirect(url_for('login'))


    resultados = None
    if request.method == 'POST':
        numero_nota = request.form.get('pc_numero_nota')
        codigo_produto = request.form.get('pc_cod_produto')
        resultados = buscar_certificados(numero_nota, codigo_produto)
        username = session['username']
        print(f"Ação realizada por: {username}, Pesquisar Certificado NF:{numero_nota} CP:{codigo_produto}")

    return render_template('pesquisar_certificado.html', resultados=resultados)


@app.route('/criar_certificado', methods=['POST'])
def tratar_formulario():
    if not is_logged_in():
        return redirect(url_for('login'))

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
            else:
                flash('Nota fiscal e código não encontrados.')

    elif 'bt_criar_certificado' in request.form:
        if 'dados_pdf' in session and session['dados_pdf']:
            # Se os dados estão na sessão e não são None, prossegue para gerar o PDF
            username = session['username']
            print(f"Ação realizada por: {username}, Criar Certificado")
            return redirect(url_for('gerar_pdf'))
        else:
            # Se os dados não estão disponíveis, fornecer opinião e não redireciona para 'gerar_pdf'
            flash('Os dados para criar o PDF não estão disponíveis. Por favor, procure a nota fiscal novamente.')
            return redirect(url_for(
                'criar_certificado'))

    # Buscar o último ID na tabela e sugerir o próximo número do certificado
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(id) AS ultimo_id FROM dbo.certificados_gerados")
            ultimo_id = cursor.fetchone()[0] or 0
            proximo_numero_certificado = ultimo_id + 1
    except Exception as e:
        print(f"Erro ao buscar o último ID: {e}")
    finally:
        connection.close()

    return render_template('criar_certificado.html', resultado=session.get('dados_pdf', {}),
                           proximo_numero_certificado=proximo_numero_certificado)


@app.route('/gerar_pdf', methods=['POST'])
def gerar_pdf():
    dados_pdf = session.get('dados_pdf')
    imagens = []

    if 'imagem1' in request.files:
        imagem1 = request.files['imagem1']
        if imagem1.filename != '':
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(imagem1.filename)[1])
            imagem1.save(temp_file.name)
            imagens.append(temp_file.name)

    if 'imagem2' in request.files:
        imagem2 = request.files['imagem2']
        if imagem2.filename != '':
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(imagem2.filename)[1])
            imagem2.save(temp_file.name)
            imagens.append(temp_file.name)

    if dados_pdf:

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
        nota_saida = request.form.get('nota_saida', 'Não informado')
        cc_revenimento = request.form.get('cc_revenimento', '')
        cc_termico = request.form.get('cc_termico', '')
        cc_superficial = request.form.get('cc_superficial', '')
        cc_macrografia = request.form.get('cc_macrografia', '')
        cc_observacao = request.form.get('cc_observacao', '')

        tem_dados_comp_quimica = dados_pdf.get('comp_quimica') and any(dados_pdf['comp_quimica'].values())
        tem_dados_prop_mecanicas = dados_pdf.get('prop_mecanicas') and any(dados_pdf['prop_mecanicas'].values())
        tem_dados_tratamentos = dados_pdf.get('tratamentos') and any(dados_pdf['tratamentos'].values())
        tem_dados_ad_porcas = dados_pdf.get('ad_porcas') and any(dados_pdf['ad_porcas'].values())
        tem_dados_ad_pinos = dados_pdf.get('ad_pinos') and any(dados_pdf['ad_pinos'].values())
        tem_dados_ad_parafusos = dados_pdf.get('ad_parafusos') and any(dados_pdf['ad_parafusos'].values())
        tem_dados_ad_grampos = dados_pdf.get('ad_grampos') and any(dados_pdf['ad_grampos'].values())
        tem_dados_ad_arruelas = dados_pdf.get('ad_arruelas') and any(dados_pdf['ad_arruelas'].values())
        tem_dados_ad_anel = dados_pdf.get('ad_anel') and any(dados_pdf['ad_anel'].values())
        tem_dados_ad_prisioneiro_estojo = dados_pdf.get('ad_prisioneiro_estojo') and any(
            dados_pdf['ad_prisioneiro_estojo'].values())
        tem_dados_ad_chumbador = dados_pdf.get('ad_chumbador') and any(dados_pdf['ad_chumbador'].values())
        tem_dados_ad_rebite = dados_pdf.get('ad_rebite') and any(dados_pdf['ad_rebite'].values())
        tem_dados_ad_chaveta = dados_pdf.get('ad_chaveta') and any(dados_pdf['ad_chaveta'].values())
        tem_dados_ad_contrapino = dados_pdf.get('ad_contrapino') and any(dados_pdf['ad_contrapino'].values())
        tem_dados_ad_especial = dados_pdf.get('ad_especial') and any(dados_pdf['ad_especial'].values())

        # Cria um arquivo PDF na memória
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        page_width, page_height = letter

        # Estilo personalizado para parágrafos centralizados
        estilo_centralizado = ParagraphStyle(name='Centralizado', alignment=TA_CENTER, fontSize=8)

        # Defina as margens da página
        left_margin = 0.4 * inch
        right_margin = 0.4 * inch
        top_margin = 0.4 * inch
        bottom_margin = 0.4 * inch

        # Remove cabeçalho e rodapé
        doc.topMargin = top_margin
        doc.bottomMargin = bottom_margin

        # Defina a largura e altura efetivas da página
        effective_page_width = page_width - left_margin - right_margin
        effective_page_height = page_height - top_margin - bottom_margin

        elements = []

        # Estilo para o título
        texto_style1 = ParagraphStyle(name='TextoStyle1', fontSize=14, alignment=1, leading=22)
        texto_style2 = ParagraphStyle(name='TextoStyle2', fontSize=12, alignment=1, leading=14)
        texto_style3 = ParagraphStyle(name='TextoStyle3', fontSize=8, alignment=1, leading=14)

        # Texto dentro da tabela
        texto_certificado = "Certificado de Qualidade / Quality Certificate"
        texto_numero_certificado = f"Nº: {numero_certificado}"

        # Cria os parágrafos dos textos com os estilos personalizados
        texto_certificado_paragraph = Paragraph(texto_certificado, texto_style1)
        texto_numero_certificado_paragraph = Paragraph(texto_numero_certificado, texto_style1)

        # Caminho para a imagem
        image_path = os.path.join(app.static_folder, 'images', 'LogoCertificado.png')

        # Cria a tabela com a imagem e os textos
        data = [
            [Image(image_path, width=108, height=54), texto_certificado_paragraph, texto_numero_certificado_paragraph]
        ]

        table = Table(data, colWidths=[1.5 * inch, 4.5 * inch, 1.5 * inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),  # Alinha a imagem à esquerda
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Alinha o texto certificado ao centro
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),  # Alinha o número do certificado à direita
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        elements.append(Spacer(0.1, 0.1 * inch))

        styles = getSampleStyleSheet()
        normal_style = styles['Normal']

        data = [
            ["Av. Queirós dos Santos 690 - Centro - CEP: 09015-310 - Fone: (11) 4469-3000"]
        ]

        table = Table(data, colWidths=[6 * inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Alinha todas as colunas à esquerda
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        elements.append(Spacer(0.1, 0.1 * inch))

        data = [
            [Paragraph(f"<font size='6'>Cliente<br/>Customer: </font><font size='10'>{criar_cliente}</font>",
                    getSampleStyleSheet()['Normal']),
             Paragraph(f"<font size='6'>Pedido<br/>Customer Order: </font><font size='10'>{criar_pedido}</font>",
                    getSampleStyleSheet()['Normal'])],
            [Paragraph(
                f"<font size='6'>Nº Certificado do Fabricante<br/>Nº Certificate Supplier:      </font><font size='10'>{criar_numero_fabricante}</font>",
                getSampleStyleSheet()['Normal']),
                Paragraph(f"<font size='6'>Pedido ARS<br/>ARS Order:     </font><font size='10'>{criar_pedido_ars}</font>",
                    getSampleStyleSheet()['Normal'])],
            [Paragraph(
                f"<font size='6'>Descrição do Material<br/>Description of Material: </font><font size='10'>{criar_desc_material}</font>",
                getSampleStyleSheet()['Normal']),
                Paragraph(
                    f"<font size='6'>Nota de Saída<br/>Exit Note: </font><font size='10'>{nota_saida}</font>",
                    getSampleStyleSheet()['Normal'])],
            [Paragraph(
                f"<font size='6'>Material<br/>Material: </font><font size='10'>{criar_material}</font>",
                getSampleStyleSheet()['Normal']),
                Paragraph(
                    f"<font size='6'>Quantidade de Peças<br/>Quantity of Parts: </font><font size='10'>{criar_quantidade}</font>",
                    getSampleStyleSheet()['Normal'])],
            [Paragraph(
                f"<font size='6'>Lote<br/>Lote: </font><font size='10'>{criar_lote}</font>",
                getSampleStyleSheet()['Normal']),
                Paragraph(
                    f"<font size='6'>Cod. For.<br/>Code: </font><font size='10'>{criar_codigo_fornecedor}</font>",
                    getSampleStyleSheet()['Normal'])],

        ]

        colWidths = [(2 / 3) * effective_page_width, (1 / 3) * effective_page_width]

        table = Table(data, colWidths=colWidths)

        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        elements.append(table)

        elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_comp_quimica:
            c = dados_pdf['comp_quimica'].get('cc_c', '') or '---'
            mn = dados_pdf['comp_quimica'].get('cc_mn', '') or '---'
            p = dados_pdf['comp_quimica'].get('cc_p', '') or '---'
            s = dados_pdf['comp_quimica'].get('cc_s', '') or '---'
            si = dados_pdf['comp_quimica'].get('cc_si', '') or '---'
            ni = dados_pdf['comp_quimica'].get('cc_ni', '') or '---'
            cr = dados_pdf['comp_quimica'].get('cc_cr', '') or '---'
            b = dados_pdf['comp_quimica'].get('cc_b', '') or '---'
            cu = dados_pdf['comp_quimica'].get('cc_cu', '') or '---'
            mo = dados_pdf['comp_quimica'].get('cc_mo', '') or '---'
            co = dados_pdf['comp_quimica'].get('cc_co', '') or '---'
            fe = dados_pdf['comp_quimica'].get('cc_fe', '') or '---'
            sn = dados_pdf['comp_quimica'].get('cc_sn', '') or '---'
            al = dados_pdf['comp_quimica'].get('cc_al', '') or '---'
            n = dados_pdf['comp_quimica'].get('cc_n', '') or '---'
            nb = dados_pdf['comp_quimica'].get('cc_nb', '') or '---'

            texto_subtitulo = "Composição Química / Chemical Analysis"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            data = [
                [f"C: {c}", f"Mn: {mn}", f"P: {p}", f"S: {s}", f"Si: {si}", f"Ni: {ni}", f"Cr: {cr}", f"B: {b}"],
                [f"Cu: {cu}", f"Mo: {mo}", f"Co: {co}", f"Fe: {fe}", f"Al: {al}", f"N: {n}", f"Nb: {nb}", f"Sn: {sn}"]
            ]
            comp_quimica_table = Table(data, colWidths=effective_page_width / 8)

            comp_quimica_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            elements.append(comp_quimica_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_prop_mecanicas:
            escoamento = dados_pdf['prop_mecanicas'].get('cc_escoamento', '') or '---'
            tracao = dados_pdf['prop_mecanicas'].get('cc_tracao', '') or '---'
            reducao = dados_pdf['prop_mecanicas'].get('cc_reducao', '') or '---'
            alongamento = dados_pdf['prop_mecanicas'].get('cc_alongamento', '') or '---'
            carga = dados_pdf['prop_mecanicas'].get('cc_carga', '') or '---'
            dureza_1 = '---'

            if tem_dados_ad_porcas:
                dureza_1 = dados_pdf['ad_porcas'].get('cc_adporcas_dureza', '') or '---'
            elif tem_dados_ad_pinos:
                dureza_1 = dados_pdf['ad_pinos'].get('cc_adpinos_dureza', '') or '---'
            elif tem_dados_ad_parafusos:
                dureza_1 = dados_pdf['ad_parafusos'].get('cc_adparafusos_dureza', "") or '---'
            elif tem_dados_ad_grampos:
                dureza_1 = dados_pdf['ad_grampos'].get('cc_adgrampos_dureza', '') or '---'
            elif tem_dados_ad_arruelas:
                dureza_1 = dados_pdf['ad_arruelas'].get('cc_adarruelas_dureza', '') or '---'
            elif tem_dados_ad_anel:
                dureza_1 = dados_pdf['ad_anel'].get('cc_adanel_dureza', '') or '---'
            elif tem_dados_ad_prisioneiro_estojo:
                dureza_1 = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_dureza', '') or '---'
            elif tem_dados_ad_especial:
                dureza_1 = dados_pdf['ad_especial'].get('cc_adespecial_dureza', '') or '---'
            elif tem_dados_ad_chumbador:
                dureza_1 = dados_pdf['ad_chumbador'].get('cc_adchumbador_dureza', '') or '---'
            elif tem_dados_ad_rebite:
                dureza_1 = dados_pdf['ad_rebite'].get('cc_adrebite_dureza', '') or '---'
            elif tem_dados_ad_chaveta:
                dureza_1 = dados_pdf['ad_chaveta'].get('cc_adchaveta_dureza', '') or '---'
            elif tem_dados_ad_contrapino:
                dureza_1 = dados_pdf['ad_contrapino'].get('cc_adcontrapino_dureza', '') or '---'


            texto_subtitulo = "Propriedades Mecânicas / Mechanical Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            data = [
                [Paragraph("Escoamento<br/>Yield Strenght", estilo_centralizado),
                 Paragraph("Resistência Tração<br/>Tensile Strenght", estilo_centralizado),
                 Paragraph("Redução de Área<br/>Reduction of Area", estilo_centralizado),
                 Paragraph("Alongamento<br/>Elongation", estilo_centralizado),
                 Paragraph("Prova de Carga<br/>Load Proof", estilo_centralizado),
                 Paragraph("Dureza<br/>Hardness", estilo_centralizado),],

                [escoamento, tracao, reducao, alongamento, carga, dureza_1]
            ]
            prop_mecanicas_table = Table(data, colWidths=effective_page_width / 6)

            prop_mecanicas_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
            ]))
            elements.append(prop_mecanicas_table)
            elements.append(Spacer(0.1, 0.1 * inch))


        revenimento = cc_revenimento or '---'
        termico = cc_termico or '---'
        superficial = cc_superficial or '---'
        macrografia = cc_macrografia or '---'
        observacao = cc_observacao or '---'

        texto_subtitulo = "Tratamentos / Treatments"
        texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
        elements.append(texto_paragraph)
        elements.append(Spacer(0.05, 0.05 * inch))

        tamanho_da_fonte = 8

        data = [
            [Paragraph("Temperatura Revenimento<br/>Tempering Temperatura", estilo_centralizado),
             Paragraph("Tratamento Térmico<br/>Thermal Treatment", estilo_centralizado),
             Paragraph("Tratamento Superficial<br/>Surface Treatment", estilo_centralizado),
             Paragraph("Macrografia<br/>Macrography", estilo_centralizado),
             Paragraph("Observação<br/>Comments", estilo_centralizado)],
            [Paragraph(revenimento, estilo_centralizado), Paragraph(termico, estilo_centralizado),
             Paragraph(superficial, estilo_centralizado),
             Paragraph(macrografia, estilo_centralizado), Paragraph(observacao, estilo_centralizado)]
        ]

        cell_styles = [
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
        ]

        tratamentos_table = Table(data, colWidths=effective_page_width / 5)
        tratamentos_table.setStyle(TableStyle(cell_styles))

        elements.append(tratamentos_table)
        elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_porcas:
            dureza = dados_pdf['ad_porcas'].get('cc_adporcas_dureza', '') or '---'
            altura = dados_pdf['ad_porcas'].get('cc_adporcas_altura', '') or '---'
            chave = dados_pdf['ad_porcas'].get('cc_adporcas_chave', '') or '---'
            diametro = dados_pdf['ad_porcas'].get('cc_adporcas_diametro', '') or '---'
            diametro_estrutura = dados_pdf['ad_porcas'].get('cc_adporcas_diametro_estrutura', '') or '---'
            diametro_interno = dados_pdf['ad_porcas'].get('cc_adporcas_diamentro_interno', '') or '---'
            diametro_externo = dados_pdf['ad_porcas'].get('cc_adporcas_diametro_externo', '') or '---'
            norma = dados_pdf['ad_porcas'].get('cc_adporcas_norma', '') or '---'

            texto_subtitulo = "Dimensionais / Dimensional"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Estrutural<br/>Structural Diameter", estilo_centralizado)],
                [Paragraph(altura, estilo_centralizado),
                 Paragraph(chave, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                 Paragraph(diametro_estrutura, estilo_centralizado)],
                [Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adporcas_table = Table(data, colWidths=effective_page_width / 4)
            adporcas_table.setStyle(TableStyle(cell_styles))

            elements.append(adporcas_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_pinos:
            dureza = dados_pdf['ad_pinos'].get('cc_adpinos_dureza', '') or '---'
            espessura = dados_pdf['ad_pinos'].get('cc_adpinos_espeddura', '') or '---'
            comprimento = dados_pdf['ad_pinos'].get('cc_adpinos_comprimento', '') or '---'
            diametro = dados_pdf['ad_pinos'].get('cc_adpinos_diametro', '') or '---'
            diametro_cabeca = dados_pdf['ad_pinos'].get('cc_adpinos_diametro_cabeca', '') or '---'
            diametro_interno = dados_pdf['ad_pinos'].get('cc_adpinos_diametro_interno', '') or '---'
            diametro_externo = dados_pdf['ad_pinos'].get('cc_adpinos_diametro_externo', '') or '---'
            norma = dados_pdf['ad_pinos'].get('cc_adpinos_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Espessura<br/>Thickness", estilo_centralizado),
                 Paragraph("Comprimento<br/>Length", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Cabeça<br/>Head Diameter", estilo_centralizado)],
                [Paragraph(espessura, estilo_centralizado),
                 Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                Paragraph(diametro_cabeca, estilo_centralizado)],
                [
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adpinos_table = Table(data, colWidths=effective_page_width / 4)
            adpinos_table.setStyle(TableStyle(cell_styles))

            elements.append(adpinos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_parafusos:
            dureza = dados_pdf['ad_parafusos'].get('cc_adparafusos_dureza', "") or '---'
            altura = dados_pdf['ad_parafusos'].get('cc_adparafusos_altura', "") or '---'
            chave = dados_pdf['ad_parafusos'].get('cc_adparafusos_chave', "") or '---'
            comprimento = dados_pdf['ad_parafusos'].get('cc_adparafusos_comprimento', "") or '---'
            diametro = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro', "") or '---'
            diametro_cabeca = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro_cabeca', "") or '---'
            comprimento_rosca = dados_pdf['ad_parafusos'].get('cc_adparafusos_comprimento_rosca', "") or '---'
            diametro_ponta = dados_pdf['ad_parafusos'].get('cc_adparafusos_diametro_ponta', "") or '---'
            norma = dados_pdf['ad_parafusos'].get('cc_adparafusos_norma', "") or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado)],
                [Paragraph(altura, estilo_centralizado),
                 Paragraph(chave, estilo_centralizado),
                 Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado)],
                [Paragraph("Diâmetro Cabeça/Corpo<br/>Head/Body Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Diâmetro Ponta<br/>Tip Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(diametro_cabeca, estilo_centralizado),
                 Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(diametro_ponta, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adparafusos_table = Table(data, colWidths=effective_page_width / 4)
            adparafusos_table.setStyle(TableStyle(cell_styles))

            elements.append(adparafusos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_grampos:
            dureza = dados_pdf['ad_grampos'].get('cc_adgrampos_dureza', '') or '---'
            comprimento = dados_pdf['ad_grampos'].get('cc_adgrampos_comprimento', '') or '---'
            diametro = dados_pdf['ad_grampos'].get('cc_adgrampos_diametro', '') or '---'
            comprimento_rosca = dados_pdf['ad_grampos'].get('cc_adgrampos_comprimento_rosca', '') or '---'
            diametro_interno = dados_pdf['ad_grampos'].get('cc_adgrampos_diametro_interno', '') or '---'
            norma = dados_pdf['ad_grampos'].get('cc_adgrampos_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                 Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adgrampos_table = Table(data, colWidths=effective_page_width / 5)
            adgrampos_table.setStyle(TableStyle(cell_styles))

            elements.append(adgrampos_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_arruelas:
            dureza = dados_pdf['ad_arruelas'].get('cc_adarruelas_dureza', '') or '---'
            altura = dados_pdf['ad_arruelas'].get('cc_adarruelas_altura', '') or '---'
            diametro_interno = dados_pdf['ad_arruelas'].get('cc_adarruelas_diametro_interno', '') or '---'
            diametro_externo = dados_pdf['ad_arruelas'].get('cc_adarruelas_diametro_externo', '') or '---'
            norma = dados_pdf['ad_arruelas'].get('cc_adarruelas_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(altura, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adarruelas_table = Table(data, colWidths=effective_page_width / 4)
            adarruelas_table.setStyle(TableStyle(cell_styles))

            elements.append(adarruelas_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_anel:
            dureza = dados_pdf['ad_anel'].get('cc_adanel_dureza', '') or '---'
            altura = dados_pdf['ad_anel'].get('cc_adanel_altura', '') or '---'
            diametro_interno = dados_pdf['ad_anel'].get('cc_adanel_diametro_interno', '') or '---'
            diametro_externo = dados_pdf['ad_anel'].get('cc_adanel_diametro_externo', '') or '---'
            norma = dados_pdf['ad_anel'].get('cc_adanel_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(altura, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adanel_table = Table(data, colWidths=effective_page_width / 4)
            adanel_table.setStyle(TableStyle(cell_styles))

            elements.append(adanel_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_prisioneiro_estojo:
            dureza = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_dureza', '') or '---'
            comprimento = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_comprimento', '') or '---'
            diametro = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_diametro', '') or '---'
            comprimento_rosca = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_comprimento_rosca', '') or '---'
            norma = dados_pdf['ad_prisioneiro_estojo'].get('cc_adprisioneiroestojo_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                 Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adprisioneiroestojo_table = Table(data, colWidths=effective_page_width / 4)
            adprisioneiroestojo_table.setStyle(TableStyle(cell_styles))

            elements.append(adprisioneiroestojo_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_especial:
            dureza = dados_pdf['ad_especial'].get('cc_adespecial_dureza', '') or '---'
            altura = dados_pdf['ad_especial'].get('cc_adespecial_altura', '') or '---'
            chave = dados_pdf['ad_especial'].get('cc_adespecial_chave', '') or '---'
            comprimento = dados_pdf['ad_especial'].get('cc_adespecial_comprimento', '') or '---'
            diametro = dados_pdf['ad_especial'].get('cc_adespecial_diametro', '') or '---'
            diametro_cabeca = dados_pdf['ad_especial'].get('cc_adespecial_diametro_cabeca', '') or '---'
            comprimento_rosca = dados_pdf['ad_especial'].get('cc_adespecial_comprimento_rosca', '') or '---'
            diametro_interno = dados_pdf['ad_especial'].get('cc_adespecial_diametro_interno', '') or '---'
            diametro_externo = dados_pdf['ad_especial'].get('cc_adespecial_diametro_externo', '') or '---'
            norma = dados_pdf['ad_especial'].get('cc_adespecial_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Chave<br/>Key", estilo_centralizado),
                 Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Cabeça<br/>Head Diameter", estilo_centralizado)],
                [Paragraph(altura, estilo_centralizado),
                 Paragraph(chave, estilo_centralizado),
                 Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                 Paragraph(diametro_cabeca, estilo_centralizado)],
                [
                 Paragraph("Comprimento Rosca<br/>Thread Lenght", estilo_centralizado),
                 Paragraph("Diâmetro Interno<br/>Inner Diameter", estilo_centralizado),
                 Paragraph("Diâmetro Externo<br/>Outer Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(comprimento_rosca, estilo_centralizado),
                 Paragraph(diametro_interno, estilo_centralizado),
                 Paragraph(diametro_externo, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adespecial_table = Table(data, colWidths=effective_page_width / 5)
            adespecial_table.setStyle(TableStyle(cell_styles))

            elements.append(adespecial_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_chumbador:
            dureza = dados_pdf['ad_chumbador'].get('cc_adchumbador_dureza', '') or '---'
            comprimento = dados_pdf['ad_chumbador'].get('cc_adchumbador_comprimento', '') or '---'
            bitola = dados_pdf['ad_chumbador'].get('cc_adchumbador_bitola', '') or '---'
            norma = dados_pdf['ad_chumbador'].get('cc_adchumbador_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Bitola<br/>Gauge", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(comprimento, estilo_centralizado),
                 Paragraph(bitola, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adchumbador_table = Table(data, colWidths=effective_page_width / 3)
            adchumbador_table.setStyle(TableStyle(cell_styles))

            elements.append(adchumbador_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_rebite:
            dureza = dados_pdf['ad_rebite'].get('cc_adrebite_dureza', '') or '---'
            comprimento = dados_pdf['ad_rebite'].get('cc_adrebite_comprimento', '') or '---'
            bitola = dados_pdf['ad_rebite'].get('cc_adrebite_bitola', '') or '---'
            diametro_cabeca = dados_pdf['ad_rebite'].get('cc_adrebite_diametro_cabeca', '') or '---'
            norma = dados_pdf['ad_rebite'].get('cc_adrebite_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Bitola<br/>Gauge", estilo_centralizado),
                 Paragraph("Diâmetro Cabeça<br/>Head Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(comprimento, estilo_centralizado),
                 Paragraph(bitola, estilo_centralizado), Paragraph(diametro_cabeca, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adrebite_table = Table(data, colWidths=effective_page_width / 4)
            adrebite_table.setStyle(TableStyle(cell_styles))

            elements.append(adrebite_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_chaveta:
            dureza = dados_pdf['ad_chaveta'].get('cc_adchaveta_dureza', '') or '---'
            comprimento = dados_pdf['ad_chaveta'].get('cc_adchaveta_comprimento', '') or '---'
            diametro = dados_pdf['ad_chaveta'].get('cc_adchaveta_diametro', '') or '---'
            altura = dados_pdf['ad_chaveta'].get('cc_adchaveta_altura', '') or '---'
            norma = dados_pdf['ad_chaveta'].get('cc_adchaveta_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Altura<br/>Height", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                 Paragraph(altura, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adchaveta_table = Table(data, colWidths=effective_page_width / 4)
            adchaveta_table.setStyle(TableStyle(cell_styles))

            elements.append(adchaveta_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if tem_dados_ad_contrapino:
            dureza = dados_pdf['ad_contrapino'].get('cc_adcontrapino_dureza', '') or '---'
            comprimento = dados_pdf['ad_contrapino'].get('cc_adcontrapino_comprimento', '') or '---'
            diametro = dados_pdf['ad_contrapino'].get('cc_adcontrapino_diametro', '') or '---'
            norma = dados_pdf['ad_contrapino'].get('cc_adcontrapino_norma', '') or '---'

            texto_subtitulo = "Propriedades Dimensionais / Dimensional Properties"
            texto_paragraph = Paragraph(texto_subtitulo, texto_style2)
            elements.append(texto_paragraph)
            elements.append(Spacer(0.05, 0.05 * inch))

            tamanho_da_fonte = 8

            data = [
                [Paragraph("Comprimento<br/>Lenght", estilo_centralizado),
                 Paragraph("Diâmetro<br/>Diameter", estilo_centralizado),
                 Paragraph("Norma<br/>Norm", estilo_centralizado)],
                [Paragraph(comprimento, estilo_centralizado),
                 Paragraph(diametro, estilo_centralizado),
                 Paragraph(norma, estilo_centralizado)]
            ]

            cell_styles = [
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
            ]

            adcontrapino_table = Table(data, colWidths=effective_page_width / 3)
            adcontrapino_table.setStyle(TableStyle(cell_styles))

            elements.append(adcontrapino_table)
            elements.append(Spacer(0.1, 0.1 * inch))

        if imagens:
            imagem_cells = []

            for imagem_path in imagens:
                imagem_cells.append(Image(imagem_path, 2 * inch, 1 * inch))

            imagem_table = Table([imagem_cells], colWidths=effective_page_width / 2)

            imagem_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                ('BOX', (0, 0), (-1, -1), 0, colors.white),
            ]))

            elements.append(imagem_table)

        nome_assinatura = session.get('nome_assinatura')
        setor_assinatura = session.get('setor_assinatura')
        telefone_assinatura = session.get('telefone_assinatura')
        email_assinatura = session.get('email_assinatura')

        tamanho_da_fonte = 8

        data = [
            ["Observação - Comments", f"Visto - Signs / Data - Date: {criar_data}"],
            [Paragraph("* Com base nos resultados obtidos, certificamos<br/>"
                       "que o produto encontra-se dentro das normas citadas.<br/>"
                       "* In according with test results, we certify that the<br/>"
                       "product is in according with reference standards.<br/> ", estilo_centralizado),
             Paragraph(f"{nome_assinatura}<br/><b>{setor_assinatura}</b><br/>"
                       f"{telefone_assinatura}<br/>{email_assinatura}", estilo_centralizado)
             ]
        ]

        cell_styles = [
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), tamanho_da_fonte),
        ]

        rodape_table = Table(data, colWidths=effective_page_width / 2)
        rodape_table.setStyle(TableStyle(cell_styles))

        elements.append(rodape_table)
        elements.append(Spacer(0.1, 0.1 * inch))

        doc.build(elements)

        session.pop('dados_pdf', None)

        inserir_certificado_gerado(buffer, nota_saida, cod_produto)

        # Define o nome do arquivo PDF
        nome_arquivo_pdf = f"{numero_certificado}-{criar_desc_material}.pdf"

        buffer.seek(0)
        return Response(buffer.getvalue(), mimetype='application/pdf',
                        headers={"Content-Disposition": f"attachment;filename={nome_arquivo_pdf}"})

    else:
        flash("Dados necessários para gerar o PDF não foram encontrados.")
        return redirect(url_for('criar_certificado'))


def inserir_certificado_gerado(arquivo_pdf, nota_saida, cod_produto):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            # Convertendo o arquivo PDF para um objeto Binary para inserção no SQL
            arquivo_binario = arquivo_pdf.getvalue()

            sql = "INSERT INTO dbo.certificados_gerados (arquivo, numero_nota, cod_produto) VALUES (?, ?, ?)"
            cursor.execute(sql, (arquivo_binario, nota_saida, cod_produto))
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

                sql_ad_porcas = ("SELECT * FROM dbo.ad_porcas WHERE cc_numero_nota = ? "
                                 "AND cc_cod_produto = ? AND cc_pedido_compra = ?")
                cursor.execute(sql_ad_porcas, (numero_nota, cod_produto, pedido_compra))
                ad_porcas = fetch_dict(cursor)
                resultado['ad_porcas'] = ad_porcas if ad_porcas else None

                sql = ("SELECT * FROM dbo.ad_pinos WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_pinos = fetch_dict(cursor)
                resultado['ad_pinos'] = ad_pinos if ad_pinos else None

                sql = ("SELECT * FROM dbo.ad_parafusos WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_parafusos = fetch_dict(cursor)
                resultado['ad_parafusos'] = ad_parafusos if ad_parafusos else None

                sql = ("SELECT * FROM dbo.ad_grampos WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_grampos = fetch_dict(cursor)
                resultado['ad_grampos'] = ad_grampos if ad_grampos else None

                sql = ("SELECT * FROM dbo.ad_arruelas WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_arruelas = fetch_dict(cursor)
                resultado['ad_arruelas'] = ad_arruelas if ad_arruelas else None

                sql = ("SELECT * FROM dbo.ad_anel WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_anel = fetch_dict(cursor)
                resultado['ad_anel'] = ad_anel if ad_anel else None

                sql = ("SELECT * FROM dbo.ad_prisioneiro_estojo WHERE cc_numero_nota = ? "
                       "AND cc_cod_produto = ? AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_prisioneiro_estojo = fetch_dict(cursor)
                resultado['ad_prisioneiro_estojo'] = ad_prisioneiro_estojo if ad_prisioneiro_estojo else None

                sql = ("SELECT * FROM dbo.ad_chumbador WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_chumbador = fetch_dict(cursor)
                resultado['ad_chumbador'] = ad_chumbador if ad_chumbador else None

                sql = ("SELECT * FROM dbo.ad_rebite WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_rebite = fetch_dict(cursor)
                resultado['ad_rebite'] = ad_rebite if ad_rebite else None

                sql = ("SELECT * FROM dbo.ad_chaveta WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_chaveta = fetch_dict(cursor)
                resultado['ad_chaveta'] = ad_chaveta if ad_chaveta else None

                sql = ("SELECT * FROM dbo.ad_contrapino WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
                cursor.execute(sql, (numero_nota, cod_produto, pedido_compra))
                ad_contrapino = fetch_dict(cursor)
                resultado['ad_contrapino'] = ad_contrapino if ad_contrapino else None

                sql = ("SELECT * FROM dbo.ad_especial WHERE cc_numero_nota = ? AND cc_cod_produto = ? "
                       "AND cc_pedido_compra = ?")
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


def buscar_certificados(numero_nota, codigo_produto):
    connection = conectar_db()
    cursor = None
    try:
        resultados_agrupados = {}
        cursor = connection.cursor()

        # Modificada para buscar registros que correspondam ao número da nota OU código do produto
        sql = """
                SELECT cc_numero_nota, cc_descricao, cc_cod_fornecedor, cc_cod_produto, 
                cc_corrida, cc_data, cc_cq, cc_qtd_pedidos FROM dbo.cadastro_certificados 
                WHERE cc_numero_nota = ? OR cc_cod_produto = ?
              """
        cursor.execute(sql, (numero_nota, codigo_produto))
        cadastros = cursor.fetchall()

        # Converte manualmente cada linha do resultado em um dicionário
        cadastros = [dict_factory(cursor, cadastro) for cadastro in cadastros]

        for cadastro in cadastros:
            chave = f"{cadastro['cc_numero_nota']}-{cadastro['cc_cod_produto']}"
            resultados_agrupados[chave] = {'cadastro_certificados': cadastro}
            for tipo in ('comp_quimica', 'prop_mecanicas', 'tratamentos', 'ad_porcas', 'ad_pinos',
                         'ad_parafusos', 'ad_grampos', 'ad_rebite', 'ad_prisioneiro_estojo',
                         'ad_chumbador', 'ad_chaveta', 'ad_arruelas', 'ad_anel', 'ad_contrapino',
                         'ad_especial'):
                resultados_agrupados[chave][tipo] = []

        tipos_relacionados = {
            'comp_quimica': "SELECT * FROM dbo.comp_quimica WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'prop_mecanicas': "SELECT * FROM dbo.prop_mecanicas WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'tratamentos': "SELECT * FROM dbo.tratamentos WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_porcas': "SELECT * FROM dbo.ad_porcas WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_pinos': "SELECT * FROM dbo.ad_pinos WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_parafusos': "SELECT * FROM dbo.ad_parafusos WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_grampos': "SELECT * FROM dbo.ad_grampos WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_rebite': "SELECT * FROM dbo.ad_rebite WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_prisioneiro_estojo': "SELECT * FROM dbo.ad_prisioneiro_estojo WHERE cc_numero_nota = ? AND "
                                     "cc_cod_produto = ?",
            'ad_chumbador': "SELECT * FROM dbo.ad_chumbador WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_chaveta': "SELECT * FROM dbo.ad_chaveta WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_arruelas': "SELECT * FROM dbo.ad_arruelas WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_anel': "SELECT * FROM dbo.ad_anel WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_contrapino': "SELECT * FROM dbo.ad_contrapino WHERE cc_numero_nota = ? AND cc_cod_produto = ?",
            'ad_especial': "SELECT * FROM dbo.ad_especial WHERE cc_numero_nota = ? AND cc_cod_produto = ?"
        }

        # Ajuste nas consultas relacionadas para usar tanto número da nota quanto código do produto
        for chave, dados in resultados_agrupados.items():
            numero_nota, codigo_produto = chave.split('-')
            for tipo, sql in tipos_relacionados.items():
                # Ajuste na query para incluir o código do produto na condição
                sql_ajustada = sql.replace("WHERE cc_numero_nota IN (?)",
                                           "WHERE cc_numero_nota = ? AND cc_cod_produto = ?")
                cursor.execute(sql_ajustada, (numero_nota, codigo_produto))
                itens_relacionados = cursor.fetchall()
                itens_relacionados = [dict_factory(cursor, item) for item in itens_relacionados]

                for item in itens_relacionados:
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
        ri_cod_produto = request.form.get('pc_cod_produto')

        # Função que busca os dados pelos parâmetros fornecidos
        resultados = buscar_registro_inspecao(numero_nota, ri_data, ri_cod_produto)

    username = session['username']
    print(f"Ação realizada por: {username}, Entrou Pesquisa Registro Inspeção")
    return render_template('pesquisar_registro_inspecao.html', resultados=resultados)



def buscar_registro_inspecao(numero_nota, ri_data, ri_cod_produto):
    connection = conectar_db()
    try:
        resultados_agrupados = {}
        cursor = connection.cursor()

        # Verifica quais campos foram preenchidos e ajusta a consulta SQL
        sql = "SELECT * FROM dbo.registro_inspecao WHERE 1=1"
        params = []

        if numero_nota:
            sql += " AND ri_numero_nota = ?"
            params.append(numero_nota)
        if ri_data:
            sql += " AND ri_data = ?"
            params.append(ri_data)
        if ri_cod_produto:
            sql += " AND ri_cod_produto = ?"
            params.append(ri_cod_produto)

        cursor.execute(sql, params)
        cadastros = cursor.fetchall()

        # Converte manualmente cada linha do resultado em um dicionário
        cadastros_dict = [dict_factory(cursor, cadastro) for cadastro in cadastros]

        for cadastro in cadastros_dict:
            chave = f"{cadastro['ri_numero_nota']}-{cadastro['ri_cod_produto']}-{cadastro['ri_pedido_compra']}"
            if chave not in resultados_agrupados:
                resultados_agrupados[chave] = {'registro_inspecao': cadastro}

                # Inicializa listas para cada tipo de informação relacionada
                for tipo in ('ad_porcas', 'ad_pinos', 'ad_parafusos', 'ad_grampos', 'ad_rebite',
                             'ad_prisioneiro_estojo', 'ad_chumbador', 'ad_chaveta', 'ad_arruelas',
                             'ad_anel', 'ad_contrapino', 'ad_especial'):
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

    # Ordenar os resultados agrupados por data de entrada
    resultados_ordenados = sorted(resultados_agrupados.values(), key=lambda x: x['registro_inspecao']['ri_data'],
                                  reverse=True)

    username = session['username']
    print(f"Ação realizada por: {username}, Buscou Registro Inspecao NF:{numero_nota} - Data:{ri_data} -"
          f" Cod: {ri_cod_produto}")
    return resultados_ordenados




@app.route('/cadastro_certificados', methods=['GET', 'POST'])
def cadastro_certificados():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Verificar qual botão foi clicado
        if 'bt_registrar_certificado' in request.form:
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

            arquivo = request.files['arquivo']

            if arquivo:
                arquivo_binario = arquivo.read()
            else:
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
                'arquivo': arquivo_binario
            }

            inserir_cadastro_certificados(dados_certificado)

            # Composição Química
            comp_quimica = request.form.get('comp_quimica') == 'on'
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
            username = session['username']
            print(f"Ação realizada por: {username}, Cadastro Certificado NF:{nota_fiscal} - CP:{cod_produto}")
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
                        # Verificar se o arquivo foi enviado
                        arquivo = request.files['arquivo']
                        if arquivo:
                            arquivo_binario = arquivo.read()
                            extracted_data = extract_data_from_pdf(arquivo_binario)
                            if extracted_data and (extracted_data['is_belenus'] or extracted_data['is_metalbo']):
                                # Redirecionar para a página com os campos preenchidos
                                return render_template('cadastro_certificados.html',
                                                       cc_numero_nota=nota_fiscal,
                                                       cc_cod_produto=cod_produto,
                                                       extracted_data=extracted_data,
                                                       arquivo=secure_filename(arquivo.filename))
                            else:
                                flash('O arquivo anexado não é um certificado válido.')

                    else:
                        # Se nenhum registro correspondente foi encontrado
                        flash('Erro, não foi feito registro de inspeção. Verifique os valores inseridos.')

            except Exception as e:
                print(f"Ocorreu um erro bt_procurar_nota: {e}")
            finally:
                connection.close()

    return render_template('cadastro_certificados.html')


def verificar_existencia_nota(nota_fiscal):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT COUNT(1) FROM dbo.cadastro_certificados WHERE cc_numero_nota = ?"
            cursor.execute(sql, (nota_fiscal,))
            resultado = cursor.fetchone()
            return resultado['COUNT(1)'] > 0
    except Exception as e:
        print(f"Erro ao verificar existência da nota: {e}")
    finally:
        connection.close()
    return False


def inserir_cadastro_certificados(dados):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = """INSERT INTO dbo.cadastro_certificados 
                     (cc_numero_nota, cc_descricao, cc_cod_fornecedor, cc_cod_produto, cc_corrida, 
                     cc_data, cc_cq, cc_qtd_pedidos, cc_arquivo)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adparafusos_dureza, cc_adparafusos_altura, 
            cc_adparafusos_chave, cc_adparafusos_comprimento, cc_adparafusos_diametro, 
            cc_adparafusos_diametro_cabeca, cc_adparafusos_comprimento_rosca, 
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adporcas_dureza, cc_adporcas_altura, 
            cc_adporcas_chave, cc_adporcas_diametro, cc_adporcas_diametro_estrutura, 
            cc_adporcas_diametro_interno, cc_adporcas_diametro_externo, cc_adporcas_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adarruelas_dureza, cc_adarruelas_altura, 
            cc_adarruelas_diametro_interno, cc_adarruelas_diametro_externo, cc_adarruelas_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adanel_dureza, cc_adanel_altura, 
            cc_adanel_diametro_interno, cc_adanel_diametro_externo, cc_adanel_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adgrampos_dureza, cc_adgrampos_comprimento, 
            cc_adgrampos_diametro, cc_adgrampos_comprimento_rosca, cc_adgrampos_diametro_interno, 
            cc_adgrampos_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adpinos_dureza, cc_adpinos_espessura, 
            cc_adpinos_comprimento, cc_adpinos_diametro, cc_adpinos_diametro_cabeca, 
            cc_adpinos_diametro_interno, cc_adpinos_diametro_externo, cc_adpinos_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adprisioneiroestojo_dureza, 
            cc_adprisioneiroestojo_comprimento, cc_adprisioneiroestojo_diametro, 
            cc_adprisioneiroestojo_comprimento_rosca, cc_adprisioneiroestojo_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adespecial_dureza, 
            cc_adespecial_altura, cc_adespecial_chave, cc_adespecial_comprimento, 
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adcontrapino_dureza, 
            cc_adcontrapino_comprimento, cc_adcontrapino_diametro, cc_adcontrapino_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adchaveta_dureza, cc_adchaveta_comprimento, 
            cc_adchaveta_diametro, cc_adchaveta_altura, cc_adchaveta_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adrebite_dureza, cc_adrebite_comprimento, 
            cc_adrebite_bitola, cc_adrebite_diametro_cabeca, cc_adrebite_norma)
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
            (cc_numero_nota, cc_cod_produto, cc_pedido_compra, cc_adchumbador_dureza, 
            cc_adchumbador_comprimento, cc_adchumbador_bitola, cc_adchumbador_norma)
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
                              WHERE ri_cod_produto = ? AND ri_opcao = 'Reprovado'""", codProduto)
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
    connection = conectar_db()
    cursor = connection.cursor()

    cursor.execute("""SELECT imagem, extensao FROM dbo.imagem_norma WHERE norma = ?""", (norma,))
    row = cursor.fetchone()
    if row:
        imagem, formato_imagem = row
        mime_type = EXTENSION_TO_MIME_TYPE.get(formato_imagem.lower(), 'application/octet-stream')
        return send_file(io.BytesIO(imagem), mimetype=mime_type)
    else:
        return 'Imagem não encontrada', 404


@app.route('/cadastro_norma', methods=['GET', 'POST'])
def cadastro_norma():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        numero_norma = request.form['cad_numero_norma']
        imagem = request.files['imagem_norma']
        descricao_norma = request.form['cad_descricao_norma']

        if imagem and allowed_file(imagem.filename):
            filename = secure_filename(imagem.filename)
            extensao = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''  # Extrai a extensão do arquivo
            imagem_data = imagem.read()

            connection = conectar_db()
            cursor = connection.cursor()
            cursor.execute("""INSERT INTO dbo.imagem_norma (norma, imagem, extensao, descricao) VALUES (?, ?, ?, ?)""",
                           (numero_norma, imagem_data, extensao, descricao_norma))
            connection.commit()
            connection.close()

            flash('Norma cadastrada com sucesso!')
            username = session['username']
            print(f"Ação realizada por: {username}, Cadastro Norma:{numero_norma}")
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

    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT norma FROM dbo.imagem_norma")
            normas = [row[0] for row in cursor.fetchall()]  # Ajustado aqui para pegar só a string
            # Separar normas em numéricas e alfabéticas
            normas_numericas = [n for n in normas if n.split('-')[0].isdigit()]
            normas_alfabeticas = [n for n in normas if not n.split('-')[0].isdigit()]
            # Ordenar cada lista separadamente
            normas_numericas.sort(key=lambda x: int(x.split('-')[0]))
            normas_alfabeticas.sort(key=lambda x: x)
            # Concatenar as listas
            normas = normas_numericas + normas_alfabeticas
    except Exception as e:
        print(f"Erro ao buscar normas: {e}")
        normas = []

    finally:
        connection.close()

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
        ri_item = request.form.get('ri_item')
        print(ri_opcao)
        resp_inspecao = request.form.get('ri_resp_inspecao')
        data = request.form.get('ri_data')
        data_inspecao = datetime.date.today()
        ri_observacao = request.form.get('ri_observacao')

        connection = conectar_db()
        try:
            with connection.cursor() as cursor:
                # Verifica se já existe um registro
                if verificar_existencia_registro(nota_fiscal, cod_produto, pedido_compra):
                    # Se existe, deleta o antigo
                    cursor.execute(
                        "DELETE FROM dbo.registro_inspecao WHERE ri_numero_nota = ? AND ri_cod_produto = ? "
                        "AND ri_pedido_compra = ?",
                        (nota_fiscal, cod_produto, pedido_compra))
                    flash('Registro existente será substituído pelo novo.', 'warning')

            sql = """INSERT INTO dbo.registro_inspecao (ri_numero_nota, ri_cod_produto,
            ri_fornecedor, ri_pedido_compra, ri_quantidade_total, ri_volume, 
            ri_desenho, ri_acabamento, ri_opcao, ri_resp_inspecao, ri_data, 
            ri_data_inspecao, ri_item, ri_observacao) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
            cursor.execute(sql, (nota_fiscal, cod_produto, fornecedor, pedido_compra, quantidade_total,
                                 volume, desenho, acabamento, ri_opcao, resp_inspecao, data, data_inspecao,
                                 ri_item, ri_observacao))

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

        username = session['username']
        print(f"Ação realizada por: {username}, registro inspeção NF:{nota_fiscal} - CP:{cod_produto}")
        flash('Registro de Inspeção criado com sucesso!')
        return redirect(url_for('registro_inspecao'))

    return render_template('registro_inspecao.html', normas=normas)


def verificar_existencia_registro(nota_fiscal, cod_produto, pedido_compra):
    connection = conectar_db()
    try:
        with connection.cursor() as cursor:
            sql = ("SELECT COUNT(1) FROM dbo.registro_inspecao WHERE ri_numero_nota = ? AND ri_cod_produto = ? "
                   "AND ri_pedido_compra = ?")
            cursor.execute(sql, (nota_fiscal, cod_produto, pedido_compra))
            resultado = cursor.fetchone()
            if resultado and resultado[0] > 0:
                return True
            return False
    except Exception as e:
        print(f"Erro ao verificar existência do registro de inspeção: {e}")
    finally:
        connection.close()


def allowed_file_pdf(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


logging.basicConfig(level=logging.DEBUG)


@app.route('/rncf', methods=['GET', 'POST'])
def rncf():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        rncf_numero_relatorio = request.form.get('rncf_numero_relatorio')
        rncf_fornecedor = request.form['rncf_fornecedor']
        rncf_nota_fiscal = request.form['rncf_nota_fiscal']
        rncf_descricao_material = request.form['rncf_descricao_material']
        rncf_data_notificacao = request.form['rncf_data_notificacao']
        rncf_prazo_responder = request.form['rncf_prazo_responder']
        rncf_tratativa_final = request.form['rncf_tratativa_final']
        rncf_status = request.form['rncf_status']
        rncf_relatorio_pdf = request.files['rncf_relatorio_pdf']

        logging.debug(f"Received POST data: {request.form}")

        connection = conectar_db()
        cursor = connection.cursor()

        if rncf_status == "Finalizado":
            rncf_data_finalizado = datetime.datetime.now()
        else:
            rncf_data_finalizado = None

        cursor.execute("SELECT * FROM dbo.rncf WHERE rncf_numero = ?", (rncf_numero_relatorio,))
        existing_report = cursor.fetchone()

        if existing_report:
            logging.debug(f"Existing report found: {existing_report}")
            if rncf_relatorio_pdf and allowed_file_pdf(rncf_relatorio_pdf.filename):
                relatorio_pdf_data = rncf_relatorio_pdf.read()
                cursor.execute("""
                    UPDATE dbo.rncf SET
                        rncf_fornecedor = ?, rncf_nota_fiscal = ?, rncf_descricao_material = ?,
                        rncf_data_notificacao = ?, rncf_prazo = ?, rncf_tratativa_final = ?, rncf_status = ?, rncf_relatorio_pdf = ?, rncf_data_finalizado = ?
                    WHERE rncf_numero = ?
                """, (
                    rncf_fornecedor, rncf_nota_fiscal, rncf_descricao_material,
                    rncf_data_notificacao, rncf_prazo_responder, rncf_tratativa_final, rncf_status, relatorio_pdf_data,
                    rncf_data_finalizado, rncf_numero_relatorio
                ))
            else:
                cursor.execute("""
                    UPDATE dbo.rncf SET
                        rncf_fornecedor = ?, rncf_nota_fiscal = ?, rncf_descricao_material = ?,
                        rncf_data_notificacao = ?, rncf_prazo = ?, rncf_tratativa_final = ?, rncf_status = ?, rncf_data_finalizado = ?
                    WHERE rncf_numero = ?
                """, (
                    rncf_fornecedor, rncf_nota_fiscal, rncf_descricao_material,
                    rncf_data_notificacao, rncf_prazo_responder, rncf_tratativa_final, rncf_status,
                    rncf_data_finalizado, rncf_numero_relatorio
                ))
            connection.commit()
            connection.close()

            flash('Relatório atualizado com sucesso!')
        else:
            #cursor.execute("SELECT COALESCE(MAX(rncf_numero), 0) + 1 FROM dbo.rncf")
            #rncf_numero_relatorio = cursor.fetchone()[0]

            if rncf_relatorio_pdf and allowed_file_pdf(rncf_relatorio_pdf.filename):
                relatorio_pdf_data = rncf_relatorio_pdf.read()
                cursor.execute("""
                    INSERT INTO dbo.rncf (
                        rncf_numero, rncf_fornecedor, rncf_nota_fiscal,
                        rncf_descricao_material, rncf_data_notificacao,
                        rncf_prazo, rncf_tratativa_final, rncf_status, rncf_relatorio_pdf, rncf_data_finalizado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rncf_numero_relatorio, rncf_fornecedor, rncf_nota_fiscal,
                    rncf_descricao_material, rncf_data_notificacao,
                    rncf_prazo_responder, rncf_tratativa_final, rncf_status, relatorio_pdf_data, rncf_data_finalizado
                ))
            else:
                cursor.execute("""
                    INSERT INTO dbo.rncf (
                        rncf_numero, rncf_fornecedor, rncf_nota_fiscal,
                        rncf_descricao_material, rncf_data_notificacao,
                        rncf_prazo, rncf_tratativa_final, rncf_status, rncf_data_finalizado
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rncf_numero_relatorio, rncf_fornecedor, rncf_nota_fiscal,
                    rncf_descricao_material, rncf_data_notificacao,
                    rncf_prazo_responder, rncf_tratativa_final, rncf_status, rncf_data_finalizado
                ))

            connection.commit()
            connection.close()

            flash('Relatório cadastrado com sucesso!')
        return redirect(url_for('rncf'))

    return render_template('rncf.html')


@app.route('/get_rncf_data', methods=['POST'])
def get_rncf_data():
    if not is_logged_in():
        return redirect(url_for('login'))

    rncf_numero_relatorio = request.json.get('rncf_numero_relatorio')
    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM dbo.rncf WHERE rncf_numero = ?", (rncf_numero_relatorio,))
    existing_report = cursor.fetchone()
    connection.close()

    if existing_report:
        return {
            'rncf_numero_relatorio': existing_report.rncf_numero,
            'rncf_fornecedor': existing_report.rncf_fornecedor,
            'rncf_nota_fiscal': existing_report.rncf_nota_fiscal,
            'rncf_descricao_material': existing_report.rncf_descricao_material,
            'rncf_data_notificacao': existing_report.rncf_data_notificacao.strftime('%Y-%m-%d'),
            'rncf_prazo_responder': existing_report.rncf_prazo,
            'rncf_tratativa_final': existing_report.rncf_tratativa_final,
            'rncf_status': existing_report.rncf_status
        }
    else:
        return {}, 404


@app.route('/rncf_records', methods=['GET'])
def rncf_records():
    if not is_logged_in():
        return redirect(url_for('login'))

    fornecedor = request.args.get('fornecedor')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))

    connection = conectar_db()
    cursor = connection.cursor()

    query = """
        SELECT rncf_numero, rncf_fornecedor, rncf_nota_fiscal, rncf_descricao_material,
               rncf_data_notificacao, rncf_prazo, rncf_tratativa_final, rncf_status, rncf_data_finalizado
        FROM dbo.rncf WHERE 1=1
    """
    count_query = "SELECT COUNT(*) FROM dbo.rncf WHERE 1=1"

    params = []
    if fornecedor:
        query += " AND rncf_fornecedor LIKE ?"
        count_query += " AND rncf_fornecedor LIKE ?"
        params.append(f"%{fornecedor}%")
    if data_inicio:
        query += " AND rncf_data_notificacao >= ?"
        count_query += " AND rncf_data_notificacao >= ?"
        params.append(data_inicio)
    if data_fim:
        query += " AND rncf_data_notificacao <= ?"
        count_query += " AND rncf_data_notificacao <= ?"
        params.append(data_fim)

    # Executar a consulta de contagem
    cursor.execute(count_query, params)
    total_records = cursor.fetchone()[0]

    # Adicionar ordenação e limitação para paginação
    query += """
            ORDER BY 
                CASE 
                    WHEN rncf_status = 'Pendente' THEN 1 
                    WHEN rncf_status = 'Finalizado' THEN 2 
                    ELSE 3 
                END,
                rncf_data_notificacao DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
    params.append((page - 1) * per_page)
    params.append(per_page)

    cursor.execute(query, params)
    records = cursor.fetchall()
    connection.close()

    records_list = []
    for record in records:
        data_notificacao = record.rncf_data_notificacao
        prazo = record.rncf_prazo
        data_final = data_notificacao + datetime.timedelta(days=prazo)
        records_list.append({
            'rncf_numero': record.rncf_numero,
            'rncf_fornecedor': record.rncf_fornecedor,
            'rncf_nota_fiscal': record.rncf_nota_fiscal,
            'rncf_descricao_material': record.rncf_descricao_material,
            'rncf_data_notificacao': data_notificacao.strftime('%d-%m-%Y'),
            'rncf_prazo': prazo,
            'rncf_tratativa_final': record.rncf_tratativa_final,
            'rncf_status': record.rncf_status,
            'rncf_data_final': data_final.strftime('%d-%m-%Y'),
            'rncf_data_finalizado': record.rncf_data_finalizado.strftime('%d-%m-%Y') if record.rncf_data_finalizado else None
        })

    return jsonify({
        'records': records_list,
        'total': total_records
    })


@app.route('/get_next_rncf_numero', methods=['GET'])
def get_next_rncf_numero():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT COALESCE(MAX(rncf_numero), 0) + 1 FROM dbo.rncf")
    next_numero = cursor.fetchone()[0]
    connection.close()

    return jsonify({'next_numero': next_numero})


@app.route('/download_pdf/<rncf_numero>')
def download_pdf(rncf_numero):
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT rncf_relatorio_pdf FROM dbo.rncf WHERE rncf_numero = ?", (rncf_numero,))
    record = cursor.fetchone()
    connection.close()

    if record and record.rncf_relatorio_pdf:
        return send_file(
            io.BytesIO(record.rncf_relatorio_pdf),
            download_name=f'relatorio_{rncf_numero}.pdf',
            as_attachment=True
        )
    else:
        flash('Arquivo PDF não encontrado.')
        return redirect(url_for('rncf'))


@app.route('/supplier_report')
def supplier_report():
    if not is_logged_in():
        return redirect(url_for('login'))
    return render_template('supplier_report.html')


@app.route('/generate_supplier_report', methods=['POST'])
def generate_supplier_report():
    if not is_logged_in():
        return redirect(url_for('login'))

    data = request.json
    fornecedor = data.get('fornecedor')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    connection = conectar_db()
    cursor = connection.cursor()

    if start_date and end_date:
        query = """
            SELECT rncf_data_notificacao, rncf_data_finalizado, rncf_status
            FROM dbo.rncf 
            WHERE rncf_fornecedor = ? AND rncf_data_notificacao BETWEEN ? AND ?
        """
        cursor.execute(query, (fornecedor, start_date, end_date))
    else:
        query = """
            SELECT rncf_data_notificacao, rncf_data_finalizado, rncf_status
            FROM dbo.rncf 
            WHERE rncf_fornecedor = ?
        """
        cursor.execute(query, (fornecedor,))

    results = cursor.fetchall()
    connection.close()

    dates = []
    times = []
    statuses = []

    for result in results:
        data_notificacao = result.rncf_data_notificacao
        data_finalizado = result.rncf_data_finalizado
        status = result.rncf_status

        dates.append(data_notificacao)
        if status == 'Finalizado':
            resolution_time = (data_finalizado - data_notificacao).days
        else:
            resolution_time = None

        times.append(resolution_time)
        statuses.append(status)

    return jsonify({'dates': dates, 'times': times, 'statuses': statuses})


@app.route('/api/fornecedores', methods=['GET'])
def get_fornecedores():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()

    query = "SELECT DISTINCT rncf_fornecedor FROM dbo.rncf"
    cursor.execute(query)
    fornecedores = cursor.fetchall()
    connection.close()

    fornecedores_list = [{'id': index, 'nome': fornecedor[0]} for index, fornecedor in enumerate(fornecedores)]
    return jsonify(fornecedores_list)


def extract_data_from_pdf(pdf_binary):
    with pdfplumber.open(io.BytesIO(pdf_binary)) as pdf:
        lines = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend(text.split('\n'))

    with pdfplumber.open(io.BytesIO(pdf_binary)) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            full_text += text

    # Verificar se o PDF é da Belenus, Metalbo ou REX
    is_belenus = False
    is_metalbo = False
    is_rex = False
    if lines:
        if "www.belenus.com.br" in lines[-1].strip():
            is_belenus = True
        elif "www.metalbo.com.br" in lines[-1].strip():
            is_metalbo = True
        elif "Industrial Rex Ltda" in lines[0].strip():
            is_rex = True

    if is_belenus:
        return extract_belenus_data(lines, full_text)
    elif is_metalbo:
        return extract_metalbo_data(lines, full_text)
    elif is_rex:
        return extract_rex_data(lines, full_text)
    else:
        return None

def extract_belenus_data(lines, full_text):
    # Expressões regulares para os diferentes dados que precisamos extrair
    cq_pattern = r'CQ Nº:\s*([A-Z0-9-]+)'
    heat_pattern = r'Corrida / Heat:\s*([A-Z0-9]+)'

    # Encontrar os dados usando expressões regulares
    cq_match = re.search(cq_pattern, full_text)
    heat_match = re.search(heat_pattern, full_text)

    # Armazenar os dados extraídos em variáveis
    cq_value = cq_match.group(1) if cq_match else None

    heat_value = None
    if heat_match:
        # Encontrar a linha contendo "Corrida / Heat:"
        for i, line in enumerate(lines):
            if "Corrida / Heat:" in line:
                # A linha seguinte contém o valor correto
                heat_value_line = lines[i + 1].strip()
                heat_value = heat_value_line.split()[-1]  # Último elemento da linha
                break

    elements_values = {}

    # Rastrear a Análise Química
    for i, line in enumerate(lines):
        if "Análise Química" in line:
            elements_line = lines[i + 2].split()  # linha abaixo de "Análise Química"
            values_line = lines[i + 3].split()  # próxima linha contém os valores
            for element, value in zip(elements_line, values_line):
                elements_values[element] = value.replace(',', '.')
            break

    # Inicializar dicionário para armazenar propriedades mecânicas
    mechanical_properties = {
        "tensile_strength": None,
        "yield_strength": None,
        "elongation": None,
        "reduction_of_area": None,
        "proof_load": None
    }

    # Função para extrair o penúltimo e último elementos
    def extract_penultimate_and_last_elements(line):
        parts = line.split()
        if len(parts) >= 3:
            return f"{parts[-1]} {parts[-3]}"
        return None

    # Rastrear e extrair propriedades mecânicas
    for line in lines:
        if "RESISTENCIA À TRAÇÃO" in line:
            mechanical_properties["tensile_strength"] = extract_penultimate_and_last_elements(line)
        elif "LIMITE DE ESCOAMENTO" in line:
            mechanical_properties["yield_strength"] = extract_penultimate_and_last_elements(line)
        elif "ALONGAMENTO" in line:
            mechanical_properties["elongation"] = extract_penultimate_and_last_elements(line)
        elif "ESTRICÇÃO" in line:
            mechanical_properties["reduction_of_area"] = extract_penultimate_and_last_elements(line)
        elif "CARGA DE PROVA" in line:
            mechanical_properties["proof_load"] = extract_penultimate_and_last_elements(line)

    print(elements_values)
    return {
        "cq_value": cq_value,
        "heat_value": heat_value,
        "elements_values": elements_values,
        "mechanical_properties": mechanical_properties,
        "is_belenus": True,
        "is_metalbo": False
    }

def extract_metalbo_data(lines, full_text):
    # Expressões regulares para os diferentes dados que precisamos extrair
    heat_pattern = r'Corrida - Heat:\s*([A-Z0-9]+)'

    # Encontrar os dados usando expressões regulares
    heat_match = re.search(heat_pattern, full_text)

    # Armazenar os dados extraídos em variáveis
    heat_value = None
    if heat_match:
        # Encontrar a linha contendo "Corrida - Heat:"
        for i, line in enumerate(lines):
            if "Corrida - Heat:" in line:
                # A linha contém o valor correto após "Corrida - Heat:"
                heat_value_line = line.strip()
                heat_value = heat_value_line.split()[-1]  # Último elemento da linha
                break

    elements_values = {}

    # Rastrear a Composição Química
    for i, line in enumerate(lines):
        if "Test results" in line:
            i += 1  # Move para a linha dos elementos
            while i < len(lines) and "ENSAIOS / INSPEÇÃO" not in lines[i]:
                parts = lines[i].split()
                if len(parts) >= 2:
                    element = parts[-2]
                    print("Penultimo: ",element)
                    value = parts[-1].replace(',', '.')
                    elements_values[element] = value
                i += 1
            break

    # Inicializar dicionário para armazenar propriedades mecânicas
    mechanical_properties = {
        "tensile_strength": None,
        "yield_strength": None,
        "elongation": None,
        "reduction_of_area": None,
        "proof_load": None
    }

    # Função para extrair o último elemento
    def extract_last_elements_with_unit(line, unit):
        parts = line.split()
        if len(parts) >= 1:
            return f"{parts[-1]} {unit}"
        return None

    # Rastrear e extrair propriedades mecânicas
    for line in lines:
        if "ESCOAMENTO - PSI" in line:
            mechanical_properties["yield_strength"] = extract_last_elements_with_unit(line, "PSI")
        elif "LIMITE ESCOAMENTO PERMANENTE - N/MM²" in line:
            mechanical_properties["yield_strength"] = extract_last_elements_with_unit(line, "N/mm²")
        elif "RESISTÊNCIA A TRAÇÃO - PSI" in line:
            mechanical_properties["tensile_strength"] = extract_last_elements_with_unit(line, "PSI")
        elif "RESISTÊNCIA A TRAÇÃO - N/MM²" in line:
            mechanical_properties["tensile_strength"] = extract_last_elements_with_unit(line, "N/mm²")
        elif "ESTRICÇÃO (%)" in line:
            mechanical_properties["reduction_of_area"] = extract_last_elements_with_unit(line, "%")
        elif "ALONGAMENTO (%)" in line:
            mechanical_properties["elongation"] = extract_last_elements_with_unit(line, "%")
        elif "RUPTURA - LBF" in line:
            mechanical_properties["proof_load"] = extract_last_elements_with_unit(line, "LBF")
        elif "RUPTURA - NEWTON" in line:
            mechanical_properties["proof_load"] = extract_last_elements_with_unit(line, "N")
        elif "CARGA DE PROVA - KGF" in line:
            mechanical_properties["proof_load"] = extract_last_elements_with_unit(line, "KGF")

    print(elements_values)
    return {
        "heat_value": heat_value,
        "elements_values": elements_values,
        "mechanical_properties": mechanical_properties,
        "is_belenus": False,
        "is_metalbo": True
    }


def extract_rex_data(lines, full_text):
    # Função para extrair o penúltimo e último elementos com a unidade
    def extract_penultimate_and_last_elements(line):
        parts = line.split()
        if len(parts) >= 3:
            return f"{parts[-1]} {parts[3]}"
        return None
    def extract_penultimate_and_last_elements_escoamento(line):
        parts = line.split()
        if len(parts) >= 6:
            return f"{parts[-1]} {parts[6]}"
        return None
    def extract_penultimate_and_last_elements_carga(line):
        parts = line.split()
        if len(parts) >= 6:
            return f"{parts[-1]} {parts[6]}"
        return None
    def extract_penultimate_and_last_elements_reducao(line):
        parts = line.split()
        if len(parts) >= 7:
            return f"{parts[-1]} {parts[7]}"
        return None

    # Padrão para reconhecer a análise química
    composition_pattern = re.compile(
        r"(C:\d+,\d+|Mn:\d+,\d+|P:\d+,\d+|S:\d+,\d+|Si:\d+,\d+|Ni:\d+,\d+|Cr:\d+,\d+|B:\d+,\d+|Cu:\d+,\d+|Mo:\d+,\d+|Co:\d+,\d+|Fe:\d+,\d+|Sn:\d+,\d+|Al:\d+,\d+|N:\d+,\d+|Nb:\d+,\d+)"
    )

    heat_data = []
    composition_data = []
    elements_values = {}

    # Encontrar a composição química e o valor da corrida
    for line in lines:
        first_composition_match = composition_pattern.search(line)
        if first_composition_match:
            heat_value = line[:first_composition_match.start()].strip().split()[-1]
            heat_data.append(heat_value)

            composition_matches = composition_pattern.findall(line)
            if composition_matches:
                for match in composition_matches:
                    element, value = match.split(":")
                    elements_values[element] = value.replace(',', '.')
                composition_data.append(' '.join(composition_matches))

    # Inicializar dicionário para armazenar propriedades mecânicas
    mechanical_properties = {
        "tensile_strength": None,
        "yield_strength": None,
        "elongation": None,
        "reduction_of_area": None,
        "proof_load": None
    }

    # Padrões para propriedades mecânicas
    property_patterns = {
        "tensile_strength": r"Tração - Tension",
        "yield_strength": r"Limite de Escoamento - Yield Strength",
        "elongation": r"Alongamento - Elongation",
        "reduction_of_area": r"Redução de Área - Reduction of Area",
        "proof_load": r"Carga de Prova - Proof Load"
    }

    # Rastrear e extrair propriedades mecânicas
    for line in lines:
        for key, pattern in property_patterns.items():
            if pattern in line:
                if pattern == "Limite de Escoamento - Yield Strength":
                    mechanical_properties[key] = extract_penultimate_and_last_elements_escoamento(line)
                elif pattern == "Carga de Prova - Proof Load":
                    mechanical_properties[key] = extract_penultimate_and_last_elements_carga(line)
                elif pattern == "Redução de Área - Reduction of Area":
                    mechanical_properties[key] = extract_penultimate_and_last_elements_reducao(line)
                else:
                    mechanical_properties[key] = extract_penultimate_and_last_elements(line)
                break

    print(elements_values)
    return {
        "heat_value": heat_data[0],
        "elements_values": elements_values,
        "mechanical_properties": mechanical_properties,
        "is_belenus": False,
        "is_metalbo": True
    }


@app.route('/cadastro_recebimento_concluido', methods=['GET', 'POST'])
def cadastro_recebimento_concluido():
    if not is_logged_in():
        return redirect(url_for('login'))

    if request.method == 'POST':
        data_entrada = request.form['cr_data']
        nota_fiscal = request.form['cr_nota_fiscal']
        ordem_compra = request.form['cr_ordem_compra']
        pedido = request.form['cr_pedido']
        responsavel = request.form['ri_resp_inspecao']
        data_cadastro = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Define a data de cadastro como a data e hora atual

        connection = conectar_db()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO dbo.cadastro_recebimento_concluido (
                data_entrada, nota_fiscal, ordem_compra, data_cadastro, responsavel, pedido
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (data_entrada, nota_fiscal, ordem_compra, data_cadastro, responsavel, pedido))
        connection.commit()
        connection.close()

        flash('Recebimento cadastrado com sucesso!')
        username = session['username']
        print(f"Ação realizada por: {username}, Cadastro Recebimento Concluído: Nota Fiscal {nota_fiscal}")
        return redirect(url_for('cadastro_recebimento_concluido'))

    return render_template('cadastro_recebimento_concluido.html')


@app.route('/pesquisar_recebimento_concluido', methods=['GET', 'POST'])
def pesquisar_recebimento_concluido():
    if not is_logged_in():
        return redirect(url_for('login'))

    results = []
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    if request.method == 'POST':
        data_entrada = request.form.get('cr_data')
        nota_fiscal = request.form.get('cr_nota_fiscal')
        ordem_compra = request.form.get('cr_ordem_compra')
        pedido = request.form.get('cr_pedido')

        query = "SELECT * FROM dbo.cadastro_recebimento_concluido WHERE 1=1"
        params = []

        if data_entrada:
            query += " AND data_entrada = ?"
            params.append(data_entrada)
        if nota_fiscal:
            query += " AND nota_fiscal LIKE ?"
            params.append(f"%{nota_fiscal}%")
        if ordem_compra:
            query += " AND ordem_compra LIKE ?"
            params.append(f"%{ordem_compra}%")
        if pedido:
            query += " AND pedido LIKE ?"
            params.append(f"%{pedido}%")

        connection = conectar_db()
        cursor = connection.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        connection.close()
    else:
        # Busca os registros do dia atual se não for uma requisição POST
        query = "SELECT * FROM dbo.cadastro_recebimento_concluido WHERE data_entrada = ?"
        params = [today]

        connection = conectar_db()
        cursor = connection.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        connection.close()

    # Formatar datas para o padrão brasileiro
    formatted_results = []
    for row in results:
        formatted_row = list(row)
        # Formatar data de entrada
        if isinstance(formatted_row[1], datetime.date):
            formatted_row[1] = formatted_row[1].strftime('%d/%m/%Y')
        elif isinstance(formatted_row[1], str):
            try:
                formatted_row[1] = datetime.datetime.strptime(formatted_row[1], '%Y-%m-%d').strftime('%d/%m/%Y')
            except ValueError:
                pass  # Mantém a string original se a conversão falhar
        # Formatar data de cadastro (data e hora)
        if isinstance(formatted_row[4], datetime.datetime):
            formatted_row[4] = formatted_row[4].strftime('%d/%m/%Y')
        elif isinstance(formatted_row[4], str):
            try:
                formatted_row[4] = datetime.datetime.strptime(formatted_row[4], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
            except ValueError:
                pass  # Mantém a string original se a conversão falhar
        formatted_results.append(formatted_row)

    return render_template('pesquisar_recebimento_concluido.html', results=formatted_results)


@app.route('/resumo_trimestral.html', methods=['GET', 'POST'])
def resumo_trimestral():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    fornecedores = []
    dados_organizados = defaultdict(lambda: defaultdict(dict))
    resumo_trimestral = defaultdict(lambda: defaultdict(lambda: {'soma_nao_conformidade': 0, 'soma_atraso_entrega': 0, 'qtd_dias_com_valor': 0}))
    notas_finais_trimestres = defaultdict(lambda: defaultdict(float))
    anos_disponiveis = [2024, 2025, 2026, 2027]
    ano_selecionado = 2024  # Padrão

    if request.method == 'POST':
        ano_selecionado = int(request.form['ano'])

    try:
        with connection.cursor() as cursor:
            # Busca todos os fornecedores
            sql_fornecedores = "SELECT id, nome_fornecedor, campo1, campo2, pdf_fornecedor FROM dbo.cadastro_fornecedor ORDER BY nome_fornecedor ASC"
            cursor.execute(sql_fornecedores)
            fornecedores = cursor.fetchall()

            # Para cada fornecedor, buscar os dados de avaliação do ano selecionado
            for fornecedor in fornecedores:
                id_fornecedor = fornecedor[0]
                cursor.execute("""
                SELECT * FROM dbo.avaliacao_diaria WHERE id_fornecedor = ? AND CONVERT(VARCHAR, data, 23) LIKE ?
                """, (id_fornecedor, f"{ano_selecionado}%"))

                resultado = fetch_dictn(cursor)
                while resultado:
                    data_obj = datetime.datetime.strptime(resultado['data'], '%Y-%m-%d')
                    mes = data_obj.month
                    dia = data_obj.day

                    if id_fornecedor not in dados_organizados:
                        dados_organizados[id_fornecedor] = defaultdict(lambda: defaultdict(dict))

                    dados_organizados[id_fornecedor][mes][dia] = resultado
                    resultado = fetch_dictn(cursor)

            # Calcular o resumo trimestral para cada fornecedor
            for id_fornecedor, meses in dados_organizados.items():
                for mes, dias in meses.items():
                    soma_nao_conformidade = sum(dia.get('nao_conformidade', 0) for dia in dias.values())
                    soma_atraso_entrega = sum(dia.get('atraso_entrega', 0) for dia in dias.values())
                    qtd_dias_com_valor = sum(1 for dia in dias.values())

                    trimestre = (mes - 1) // 3 + 1
                    resumo_trimestral[id_fornecedor][trimestre]['soma_nao_conformidade'] += soma_nao_conformidade
                    resumo_trimestral[id_fornecedor][trimestre]['soma_atraso_entrega'] += soma_atraso_entrega
                    resumo_trimestral[id_fornecedor][trimestre]['qtd_dias_com_valor'] += qtd_dias_com_valor

            # Calcular as notas finais trimestrais para cada fornecedor
            for id_fornecedor, trimestres in resumo_trimestral.items():

                for trimestre, dados in trimestres.items():
                    if dados['qtd_dias_com_valor'] > 0:
                        dados['valor_final'] = (((dados['soma_nao_conformidade'] + dados['soma_atraso_entrega']) / dados['qtd_dias_com_valor']) * 5)
                    else:
                        dados['valor_final'] = 0

                    notas_finais_trimestres[id_fornecedor][trimestre] = dados['valor_final']

    except Exception as e:
        print(f"Erro: {e}")
        flash(f"Erro ao processar o resumo: {e}")
    finally:
        connection.close()

    return render_template('resumo_trimestral.html',
                           fornecedores=fornecedores,
                           resumo_trimestral=resumo_trimestral,
                           notas_finais_trimestres=notas_finais_trimestres,
                           anos_disponiveis=anos_disponiveis,
                           ano_selecionado=ano_selecionado)


@app.route('/salvar_fornecedores', methods=['POST'])
def salvar_fornecedores():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()

    try:
        with connection.cursor() as cursor:
            fornecedor_id = request.form.get('salvar_fornecedor_id')
            if fornecedor_id:
                campo1 = request.form.get('campo1')
                campo2 = request.form.get('campo2')

                # Garantir que campo2 não é None antes de dividir
                if not campo2:
                    campo2 = ""

                # Verificar se todos os dados necessários estão presentes
                if campo1 is not None and campo2 is not None:
                    # Declaração preparada para evitar SQL injection
                    sql_update = """
                        UPDATE dbo.cadastro_fornecedor
                        SET campo1 = ?, campo2 = ?
                        WHERE id = ?
                    """
                    cursor.execute(sql_update, (campo1, campo2, fornecedor_id))

                if 'pdf' in request.files:
                    pdf_file = request.files['pdf']
                    if pdf_file.filename != '':
                        pdf_data = pdf_file.read()
                        # Declaração preparada para dados do PDF
                        sql_update_pdf = """
                            UPDATE dbo.cadastro_fornecedor
                            SET pdf_fornecedor = ?
                            WHERE id = ?
                        """
                        cursor.execute(sql_update_pdf, (pdf_data, fornecedor_id))

            connection.commit()
        flash("Modificações salvas com sucesso!", "success")
    except Exception as e:
        print(f"Erro ao salvar modificações: {e}")
        flash(f"Erro ao salvar modificações: {e}", "danger")
    finally:
        connection.close()

    return redirect(url_for('resumo_trimestral'))


@app.route('/download_pdf_trimestral/<int:fornecedor_id>')
def download_pdf_trimestral(fornecedor_id):
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    pdf_path = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pdf_fornecedor FROM dbo.cadastro_fornecedor WHERE id = ?", (fornecedor_id,))
            pdf_data = cursor.fetchone()[0]

            if pdf_data:
                if not os.path.exists('temp'):
                    os.makedirs('temp')
                pdf_path = f"temp/{fornecedor_id}.pdf"
                with open(pdf_path, "wb") as f:
                    f.write(pdf_data)

                response = send_file(pdf_path, as_attachment=True)

                # Remover o arquivo após o envio da resposta
                @response.call_on_close
                def remove_file():
                    try:
                        os.remove(pdf_path)
                    except Exception as e:
                        print(f"Erro ao remover arquivo: {e}")

                return response
            else:
                flash("PDF não encontrado!", "warning")
                return redirect(url_for('resumo_trimestral'))
    except Exception as e:
        print(f"Erro: {e} do download pdf")
        flash(f"Erro ao baixar PDF: {e}", "danger")
        return redirect(url_for('resumo_trimestral'))
    finally:
        connection.close()


def fetch_dictn(cursor):
    columns = [column[0] for column in cursor.description]
    row = cursor.fetchone()
    if row:
        result = dict(zip(columns, row))
        return result
    else:
        return None


@app.route('/quantidade_inspecao', methods=['GET', 'POST'])
def get_quantidade_inspecao():
    if not is_logged_in():
        return redirect(url_for('login'))

    ano = request.form.get('ano')
    mes = request.form.get('mes')
    dia = request.form.get('dia')
    responsavel = request.form.get('responsavel')

    connection = conectar_db()
    cursor = connection.cursor()

    query = """
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN ri_opcao = 'Reprovado' THEN 1 ELSE 0 END) AS reprovados,
            SUM(CASE WHEN ri_opcao != 'Reprovado' THEN 1 ELSE 0 END) AS aprovados
        FROM dbo.registro_inspecao
        WHERE 
            TRY_CONVERT(date, ri_data) IS NOT NULL
            AND ri_data <> '' -- Ignora datas vazias
            AND (? IS NULL OR YEAR(TRY_CONVERT(date, ri_data)) = ?)
            AND (? IS NULL OR MONTH(TRY_CONVERT(date, ri_data)) = ?)
            AND (? IS NULL OR DAY(TRY_CONVERT(date, ri_data)) = ?)
            AND (? IS NULL OR ri_resp_inspecao = ?)
    """

    parameters = [
        ano if ano else None,
        ano if ano else 0,
        mes if mes else None,
        mes if mes else 0,
        dia if dia else None,
        dia if dia else 0,
        responsavel if responsavel else None,
        responsavel if responsavel else ''
    ]

    cursor.execute(query, parameters)
    result = cursor.fetchone()

    total = result[0]
    reprovados = result[1]
    aprovados = result[2]

    # Obter lista de responsáveis
    cursor.execute("SELECT DISTINCT ri_resp_inspecao FROM dbo.registro_inspecao ORDER BY ri_resp_inspecao")
    responsaveis = cursor.fetchall()

    # Obter lista de anos, meses e dias disponíveis
    cursor.execute("SELECT DISTINCT YEAR(TRY_CONVERT(date, ri_data)) AS ano FROM dbo.registro_inspecao WHERE TRY_CONVERT(date, ri_data) IS NOT NULL AND ri_data <> '' ORDER BY ano")
    anos_disponiveis = cursor.fetchall()

    cursor.execute("SELECT DISTINCT MONTH(TRY_CONVERT(date, ri_data)) AS mes FROM dbo.registro_inspecao WHERE TRY_CONVERT(date, ri_data) IS NOT NULL AND ri_data <> '' ORDER BY mes")
    meses_disponiveis = cursor.fetchall()

    cursor.execute("SELECT DISTINCT DAY(TRY_CONVERT(date, ri_data)) AS dia FROM dbo.registro_inspecao WHERE TRY_CONVERT(date, ri_data) IS NOT NULL AND ri_data <> '' ORDER BY dia")
    dias_disponiveis = cursor.fetchall()

    connection.close()

    return render_template('quantidade_inspecao.html',
                           total=total,
                           reprovados=reprovados,
                           aprovados=aprovados,
                           anos_disponiveis=anos_disponiveis,
                           meses_disponiveis=meses_disponiveis,
                           dias_disponiveis=dias_disponiveis,
                           responsaveis=responsaveis)


app.jinja_env.globals.update(max=max, min=min)


@app.route('/cadastro_itens_ars', methods=['GET', 'POST'])
def cadastro_itens_ars():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()

    if request.method == 'POST':
        codigo = request.form['cad_itens_ars']
        descricao = request.form['cad_desc_itens']

        cursor.execute("""
            INSERT INTO dbo.cadastro_itens (
                cod_item, descricao_item
            ) VALUES (?, ?)
        """, (codigo, descricao))
        connection.commit()
        flash('Item cadastrado com sucesso!')
        connection.close()
        return redirect(url_for('cadastro_itens_ars'))  # Redireciona para evitar reenvio do formulário

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    if search_query:
        cursor.execute("""
            SELECT id, cod_item, descricao_item
            FROM dbo.cadastro_itens
            WHERE cod_item LIKE ? OR descricao_item LIKE ?
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, ('%' + search_query + '%', '%' + search_query + '%', offset, per_page))
        itens = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.cadastro_itens
            WHERE cod_item LIKE ? OR descricao_item LIKE ?
        """, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("""
            SELECT id, cod_item, descricao_item
            FROM dbo.cadastro_itens
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, per_page))
        itens = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM dbo.cadastro_itens")

    total_row = cursor.fetchone()
    total = total_row[0] if total_row else 0

    connection.close()

    return render_template('cadastro_itens_ars.html', itens=itens, page=page, total=total, per_page=per_page, search_query=search_query)


@app.route('/cadastro_separador', methods=['GET', 'POST'])
def cadastro_separador():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()

    if request.method == 'POST':
        num_separador = request.form['cad_numero_separador']
        nome_separador = request.form['cad_nome_separador']
        status_separador = 'Desativado'

        cursor.execute("""
            INSERT INTO dbo.cadastro_separador (
                num_separador, nome_separador, status_separador
            ) VALUES (?, ?, ?)
        """, (num_separador, nome_separador, status_separador))
        connection.commit()
        flash('Separador cadastrado com sucesso!')
        connection.close()
        return redirect(url_for('cadastro_separador'))  # Redireciona para evitar reenvio do formulário

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    if search_query:
        cursor.execute("""
            SELECT id, num_separador, nome_separador, status_separador
            FROM dbo.cadastro_separador
            WHERE num_separador LIKE ? OR nome_separador LIKE ?
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, ('%' + search_query + '%', '%' + search_query + '%', offset, per_page))
        separadores = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.cadastro_separador
            WHERE num_separador LIKE ? OR nome_separador LIKE ?
        """, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("""
            SELECT id, num_separador, nome_separador, status_separador
            FROM dbo.cadastro_separador
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, per_page))
        separadores = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM dbo.cadastro_separador")

    total_row = cursor.fetchone()
    total = total_row[0] if total_row else 0

    connection.close()

    return render_template('cadastro_separador.html', separadores=separadores, page=page, total=total, per_page=per_page, search_query=search_query)


@app.route('/cadastro_picker', methods=['GET', 'POST'])
def cadastro_picker():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()

    if request.method == 'POST':
        num_picker = request.form['cad_numero_picker']
        nome_picker = request.form['cad_nome_picker']
        status_picker = 'Desativado'

        cursor.execute("""
            INSERT INTO dbo.cadastro_picker (
                num_picker, nome_picker, status_picker
            ) VALUES (?, ?, ?)
        """, (num_picker, nome_picker, status_picker))
        connection.commit()
        flash('Picker cadastrado com sucesso!')
        connection.close()
        return redirect(url_for('cadastro_picker'))  # Redireciona para evitar reenvio do formulário

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    if search_query:
        cursor.execute("""
            SELECT id, num_picker, nome_picker, status_picker
            FROM dbo.cadastro_picker
            WHERE num_picker LIKE ? OR nome_picker LIKE ?
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, ('%' + search_query + '%', '%' + search_query + '%', offset, per_page))
        pickers = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.cadastro_picker
            WHERE num_picker LIKE ? OR nome_picker LIKE ?
        """, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("""
            SELECT id, num_picker, nome_picker, status_picker
            FROM dbo.cadastro_picker
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, per_page))
        pickers = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM dbo.cadastro_picker")

    total_row = cursor.fetchone()
    total = total_row[0] if total_row else 0

    connection.close()

    return render_template('cadastro_picker.html', pickers=pickers, page=page, total=total, per_page=per_page, search_query=search_query)


@app.route('/cadastro_recusa', methods=['GET', 'POST'])
def cadastro_recusa():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()

    if request.method == 'POST':
        cod_recusa = request.form['cad_cod_recusa']
        desc_recusa = request.form['cad_desc_recusa']

        cursor.execute("""
            INSERT INTO dbo.cadastro_reprova (
                cod_reprova, descricao_reprova
            ) VALUES (?, ?)
        """, (cod_recusa, desc_recusa))
        connection.commit()
        flash('Recusa cadastrada com sucesso!')
        connection.close()
        return redirect(url_for('cadastro_recusa'))  # Redireciona para evitar reenvio do formulário

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    if search_query:
        cursor.execute("""
            SELECT id, cod_reprova, descricao_reprova
            FROM dbo.cadastro_reprova
            WHERE cod_reprova LIKE ? OR descricao_reprova LIKE ?
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, ('%' + search_query + '%', '%' + search_query + '%', offset, per_page))
        recusas = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.cadastro_reprova
            WHERE cod_reprova LIKE ? OR descricao_reprova LIKE ?
        """, ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("""
            SELECT id, cod_reprova, descricao_reprova
            FROM dbo.cadastro_reprova
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, per_page))
        recusas = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM dbo.cadastro_reprova")

    total_row = cursor.fetchone()
    total = total_row[0] if total_row else 0

    connection.close()

    return render_template('cadastro_recusa.html', recusas=recusas, page=page, total=total, per_page=per_page, search_query=search_query)


from flask import Flask, render_template, redirect, url_for, flash, jsonify, session, request
import datetime

@app.route('/reprova_inspecao', methods=['GET', 'POST'])
def reprova_inspecao():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()

    if request.method == 'POST':
        #data = datetime.datetime.now().strftime('%Y-%m-%d')
        data = request.form['rep_data']
        num_pedido = request.form['rep_num_pedido']
        cod_item_ars = request.form['rep_cod_item_ars']
        desc_item_ars = request.form['rep_desc_item_ars']
        quantidade = request.form['rep_quantidade']
        cod_separador = request.form['rep_cod_separador']
        separador = request.form['rep_separador']
        cod_picker = request.form['rep_cod_picker']
        picker = request.form['rep_picker']
        cod_reprova = request.form['rep_cod_reprova']
        desc_reprova = request.form['rep_motivo_reprova']
        observacao = request.form['rep_observacao']
        responsavel = session['username']

        cursor.execute("""
            INSERT INTO dbo.registro_reprova (
                data, num_pedido, cod_item_ars, desc_item_ars, quantidade,
                cod_separador, separador, cod_picker, picker, cod_reprova,
                desc_reprova, observacao, responsavel
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data, num_pedido, cod_item_ars, desc_item_ars, quantidade, cod_separador, separador,
              cod_picker, picker, cod_reprova, desc_reprova, observacao, responsavel))
        connection.commit()
        flash('Reprova registrada com sucesso!')
        connection.close()
        return redirect(url_for('reprova_inspecao'))  # Redireciona para evitar reenvio do formulário

    return render_template('reprova_inspecao.html', today_date=datetime.date.today())


@app.route('/get_item_desc/<cod_item>')
def get_item_desc(cod_item):
    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT descricao_item FROM dbo.cadastro_itens WHERE cod_item = ?", (cod_item,))
    item = cursor.fetchone()
    connection.close()
    if item:
        return jsonify(descricao=item[0])
    return jsonify(error='Item não encontrado')


@app.route('/get_separador_desc/<num_separador>')
def get_separador_desc(num_separador):
    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT nome_separador FROM dbo.cadastro_separador WHERE num_separador = ?", (num_separador,))
    separador = cursor.fetchone()
    connection.close()
    if separador:
        return jsonify(nome=separador[0])
    return jsonify(error='Separador não encontrado')


@app.route('/get_picker_desc/<num_picker>')
def get_picker_desc(num_picker):
    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT nome_picker FROM dbo.cadastro_picker WHERE num_picker = ?", (num_picker,))
    picker = cursor.fetchone()
    connection.close()
    if picker:
        return jsonify(nome=picker[0])
    return jsonify(error='Picker não encontrado')


@app.route('/get_reprova_desc/<cod_reprova>')
def get_reprova_desc(cod_reprova):
    connection = conectar_db()
    cursor = connection.cursor()
    cursor.execute("SELECT descricao_reprova FROM dbo.cadastro_reprova WHERE cod_reprova = ?", (cod_reprova,))
    reprova = cursor.fetchone()
    connection.close()
    if reprova:
        return jsonify(descricao=reprova[0])
    return jsonify(error='Reprova não encontrada')


@app.route('/pesquisar_reprova_inspecao', methods=['GET'])
def pesquisar_reprova_inspecao():
    if not is_logged_in():
        return redirect(url_for('login'))

    connection = conectar_db()
    cursor = connection.cursor()

    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    if search_query:
        cursor.execute("""
            SELECT id, data, num_pedido, cod_item_ars, desc_item_ars, quantidade,
                   cod_separador, separador, cod_picker, picker, cod_reprova,
                   desc_reprova, observacao, responsavel
            FROM dbo.registro_reprova
            WHERE num_pedido LIKE ? OR cod_item_ars LIKE ? OR desc_item_ars LIKE ?
               OR cod_separador LIKE ? OR separador LIKE ? OR cod_picker LIKE ?
               OR picker LIKE ? OR cod_reprova LIKE ? OR desc_reprova LIKE ?
               OR observacao LIKE ? OR responsavel LIKE ?
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%',
              '%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%',
              '%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%',
              '%' + search_query + '%', '%' + search_query + '%', offset, per_page))
        registros = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*)
            FROM dbo.registro_reprova
            WHERE num_pedido LIKE ? OR cod_item_ars LIKE ? OR desc_item_ars LIKE ?
               OR cod_separador LIKE ? OR separador LIKE ? OR cod_picker LIKE ?
               OR picker LIKE ? OR cod_reprova LIKE ? OR desc_reprova LIKE ?
               OR observacao LIKE ? OR responsavel LIKE ?
        """, ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%',
              '%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%',
              '%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%',
              '%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("""
            SELECT id, data, num_pedido, cod_item_ars, desc_item_ars, quantidade,
                   cod_separador, separador, cod_picker, picker, cod_reprova,
                   desc_reprova, observacao, responsavel
            FROM dbo.registro_reprova
            ORDER BY id DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """, (offset, per_page))
        registros = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) FROM dbo.registro_reprova")

    total_row = cursor.fetchone()
    total = total_row[0] if total_row else 0

    connection.close()

    return render_template('pesquisar_reprova_inspecao.html', registros=registros, page=page, total=total, per_page=per_page, search_query=search_query)


def obter_dados_reprovas():
    query = """
    SELECT data, num_pedido, cod_item_ars, desc_item_ars, quantidade,
           cod_separador, separador, cod_picker, picker, cod_reprova,
           desc_reprova, observacao, responsavel
    FROM dbo.registro_reprova
    """
    df = pd.read_sql_query(query, engine)
    return df


def gerar_grafico_quantidade_reprovas_por_ano(df):
    df['data'] = pd.to_datetime(df['data'])
    df['ano'] = df['data'].dt.year
    reprovas_por_ano = df.groupby('ano').size()

    fig, ax = plt.subplots()
    reprovas_por_ano.plot(kind='bar', ax=ax, color='skyblue')
    ax.set_title('Quantidade de Reprovas por Ano')
    ax.set_xlabel('Ano')
    ax.set_ylabel('Quantidade de Reprovas')

    return salvar_grafico(fig)


def gerar_grafico_reprovas_por_picker(df):
    reprovas_por_picker = df.groupby('picker').size()

    fig, ax = plt.subplots()
    reprovas_por_picker.plot(kind='bar', ax=ax, color='skyblue')
    ax.set_title('Quantidade de Reprovas por Picker')
    ax.set_xlabel('Picker')
    ax.set_ylabel('Quantidade de Reprovas')

    return salvar_grafico(fig)


def gerar_grafico_reprovas_por_separador(df):
    reprovas_por_separador = df.groupby('separador').size()

    fig, ax = plt.subplots()
    reprovas_por_separador.plot(kind='bar', ax=ax, color='skyblue')
    ax.set_title('Quantidade de Reprovas por Separador')
    ax.set_xlabel('Separador')
    ax.set_ylabel('Quantidade de Reprovas')

    return salvar_grafico(fig)


def gerar_grafico_ranking_reprova(df):
    ranking_reprova = df['desc_reprova'].value_counts()

    fig, ax = plt.subplots()
    ranking_reprova.plot(kind='bar', ax=ax, color='skyblue')
    ax.set_title('Ranking de Motivos de Reprova')
    ax.set_xlabel('Motivo de Reprova')
    ax.set_ylabel('Quantidade')

    return salvar_grafico(fig)


def salvar_grafico(fig):
    img = BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    base64_img = base64.b64encode(img.getvalue()).decode('utf-8')
    plt.close(fig)
    return base64_img


@app.route('/relatorio_reprovados', methods=['GET', 'POST'])
def relatorio_reprovados():
    if not is_logged_in():
        return redirect(url_for('login'))

    df = obter_dados_reprovas()
    grafico_ano = gerar_grafico_quantidade_reprovas_por_ano(df)
    grafico_picker = gerar_grafico_reprovas_por_picker(df)
    grafico_separador = gerar_grafico_reprovas_por_separador(df)
    grafico_ranking = gerar_grafico_ranking_reprova(df)

    return render_template('relatorio_reprovados.html', grafico_ano=grafico_ano, grafico_picker=grafico_picker, grafico_separador=grafico_separador, grafico_ranking=grafico_ranking)


@app.route('/dados_grafico')
def dados_grafico():
    if not is_logged_in():
        return redirect(url_for('login'))

    tipo = request.args.get('tipo')
    df = obter_dados_reprovas()

    if tipo == 'ano':
        df['data'] = pd.to_datetime(df['data'])
        df['ano'] = df['data'].dt.year
        dados = df.groupby('ano').size()
        return jsonify({
            'labels': dados.index.tolist(),
            'values': dados.values.tolist(),
            'label': 'Quantidade de Reprovas por Ano'
        })
    elif tipo == 'picker':
        dados = df.groupby('picker').size()
        return jsonify({
            'labels': dados.index.tolist(),
            'values': dados.values.tolist(),
            'label': 'Quantidade de Reprovas por Picker'
        })
    elif tipo == 'separador':
        dados = df.groupby('separador').size()
        return jsonify({
            'labels': dados.index.tolist(),
            'values': dados.values.tolist(),
            'label': 'Quantidade de Reprovas por Separador'
        })
    elif tipo == 'ranking':
        dados = df['desc_reprova'].value_counts()
        return jsonify({
            'labels': dados.index.tolist(),
            'values': dados.values.tolist(),
            'label': 'Ranking de Motivos de Reprova'
        })
    else:
        return jsonify({'labels': [], 'values': [], 'label': 'Dados não encontrados'})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
