import pyttsx3

engine = pyttsx3.init()

# Configura velocidade e volume
engine.setProperty('rate', 150)
engine.setProperty('volume', 0.9)

# Lista as vozes disponíveis
voices = engine.getProperty('voices')
for index, voice in enumerate(voices):
    print(f"Voice {index}: {voice.name}")

# Escolhe a voz desejada (por exemplo, 0 ou 1, dependendo das vozes disponíveis)
voice_index = int(input("Digite o índice da voz desejada: "))
engine.setProperty('voice', voices[voice_index].id)

texto = input("Digite o texto que você quer que o programa fale: ")

# Converte o texto em fala
engine.say(texto)
engine.runAndWait()
