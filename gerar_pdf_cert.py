import pygame
import time
import random

# Inicializa o pygame
pygame.init()

# Definições básicas
branco = (255, 255, 255)
preto = (0, 0, 0)
vermelho = (213, 50, 80)
verde = (0, 255, 0)

largura_tela = 800
altura_tela = 600

display = pygame.display.set_mode((largura_tela, altura_tela))
pygame.display.set_caption('Jogo da Cobrinha')

clock = pygame.time.Clock()

tamanho_bloco = 10
font_style = pygame.font.SysFont("bahnschrift", 25)
score_font = pygame.font.SysFont("comicsansms", 35)

def pontuacao(score):
    valor = score_font.render("Pontuação: " + str(score), True, verde)
    display.blit(valor, [0, 0])

def cobra(tamanho_bloco, lista_cobra):
    for x in lista_cobra:
        pygame.draw.rect(display, preto, [x[0], x[1], tamanho_bloco, tamanho_bloco])

def mensagem(msg, cor):
    mesg = font_style.render(msg, True, cor)
    display.blit(mesg, [largura_tela / 6, altura_tela / 3])

def jogo():
    fim_jogo = False
    fim_jogo_encerrado = False

    x1 = largura_tela / 2
    y1 = altura_tela / 2

    x1_mudanca = 0
    y1_mudanca = 0

    lista_cobra = []
    comprimento_cobra = 1

    velocidade_cobrinha = 15

    comida_x = round(random.randrange(0, largura_tela - tamanho_bloco) / 10.0) * 10.0
    comida_y = round(random.randrange(0, altura_tela - tamanho_bloco) / 10.0) * 10.0

    while not fim_jogo:

        while fim_jogo_encerrado == True:
            display.fill(branco)
            mensagem("Você perdeu! Pressione C para jogar novamente ou Q para sair", vermelho)
            pontuacao(comprimento_cobra - 1)
            pygame.display.update()

            for evento in pygame.event.get():
                if evento.type == pygame.KEYDOWN:
                    if evento.key == pygame.K_q:
                        fim_jogo = True
                        fim_jogo_encerrado = False
                    if evento.key == pygame.K_c:
                        jogo()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                fim_jogo = True
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_LEFT:
                    x1_mudanca = -tamanho_bloco
                    y1_mudanca = 0
                elif evento.key == pygame.K_RIGHT:
                    x1_mudanca = tamanho_bloco
                    y1_mudanca = 0
                elif evento.key == pygame.K_UP:
                    y1_mudanca = -tamanho_bloco
                    x1_mudanca = 0
                elif evento.key == pygame.K_DOWN:
                    y1_mudanca = tamanho_bloco
                    x1_mudanca = 0

        if x1 >= largura_tela or x1 < 0 or y1 >= altura_tela or y1 < 0:
            fim_jogo_encerrado = True
        x1 += x1_mudanca
        y1 += y1_mudanca
        display.fill(branco)
        pygame.draw.rect(display, verde, [comida_x, comida_y, tamanho_bloco, tamanho_bloco])
        lista_cobra.append([x1, y1])
        if len(lista_cobra) > comprimento_cobra:
            del lista_cobra[0]

        for x in lista_cobra[:-1]:
            if x == [x1, y1]:
                fim_jogo_encerrado = True

        cobra(tamanho_bloco, lista_cobra)
        pontuacao(comprimento_cobra - 1)

        pygame.display.update()

        if x1 == comida_x and y1 == comida_y:
            comida_x = round(random.randrange(0, largura_tela - tamanho_bloco) / 10.0) * 10.0
            comida_y = round(random.randrange(0, altura_tela - tamanho_bloco) / 10.0) * 10.0
            comprimento_cobra += 1
            velocidade_cobrinha += 1  # Aumenta a velocidade da cobrinha

        clock.tick(velocidade_cobrinha)

    pygame.quit()
    quit()

jogo()
