import asyncio
import time

import pyautogui
from concurrent.futures import ThreadPoolExecutor

# Função para realizar os cliques
def click_task():
    for _ in range(100):
        pyautogui.click(clicks=100)

# Função assíncrona para rodar múltiplas tarefas de clique
async def run_click_tasks():
    with ThreadPoolExecutor() as executor:
        # Executa 5 tarefas simultâneas
        tasks = [asyncio.get_event_loop().run_in_executor(executor, click_task) for _ in range(10)]
        await asyncio.gather(*tasks)

# Executa o loop de eventos asyncio
time.sleep(4)
asyncio.run(run_click_tasks())
