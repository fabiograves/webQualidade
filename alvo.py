import pygame
import random
import time

# Inicializa o pygame
pygame.init()

# Definições básicas
largura_tela = 800
altura_tela = 600
branco = (255, 255, 255)
vermelho = (255, 0, 0)
preto = (0, 0, 0)

display = pygame.display.set_mode((largura_tela, altura_tela))
pygame.display.set_caption('Jogo de Tiro ao Alvo')

clock = pygame.time.Clock()
fonte_pontuacao = pygame.font.SysFont(None, 35)
fonte_tempo = pygame.font.SysFont(None, 50)

def mostrar_tempo(tempo):
    text = fonte_tempo.render("Tempo: {:.2f} segundos".format(tempo), True, preto)
    display.blit(text, [largura_tela // 4, altura_tela // 2])

def mostrar_acertos(clicks, total_alvos):
    precisao = round((100 / (clicks / total_alvos)),2)
    text = fonte_tempo.render(f"Tentativas: {clicks}, Precisao: {precisao}%", True, preto)
    display.blit(text, [largura_tela // 6, altura_tela // 3])

def pontuacao(alvos_restantes):
    text = fonte_pontuacao.render("Alvos restantes: " + str(alvos_restantes), True, preto)
    display.blit(text, [10, 10])

def jogo():
    fim_jogo = False
    alvos_acertados = 0
    total_alvos = 50
    alvo_tamanho = 60
    clicks = 0
    alvo_x = random.randint(0, largura_tela - alvo_tamanho)
    alvo_y = random.randint(0, altura_tela - alvo_tamanho)
    tempo_inicial = time.time()

    while not fim_jogo and alvos_acertados < total_alvos:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                fim_jogo = True
            if evento.type == pygame.MOUSEBUTTONDOWN:
                clicks += 1
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if alvo_x < mouse_x < alvo_x + alvo_tamanho and alvo_y < mouse_y < alvo_y + alvo_tamanho:
                    alvos_acertados += 1
                    if alvos_acertados < total_alvos:
                        alvo_x = random.randint(0, largura_tela - alvo_tamanho)
                        alvo_y = random.randint(0, altura_tela - alvo_tamanho)

        display.fill(branco)
        pygame.draw.rect(display, vermelho, [alvo_x, alvo_y, alvo_tamanho, alvo_tamanho])
        pontuacao(total_alvos - alvos_acertados)

        pygame.display.update()
        clock.tick(60)

    tempo_final = time.time()
    tempo_total = tempo_final - tempo_inicial

    display.fill(branco)
    mostrar_tempo(tempo_total)
    mostrar_acertos(clicks, total_alvos)
    pygame.display.update()

    time.sleep(5)
    pygame.quit()
    quit()

jogo()
