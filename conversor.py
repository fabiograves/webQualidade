import speech_recognition as sr
import os
from pydub import AudioSegment

def transcrever_audio_wav_por_pedacos(nome_arquivo):
    # Caminho do arquivo WAV dentro da pasta static
    caminho_wav = os.path.join("static", nome_arquivo)

    # Carregar o áudio
    audio = AudioSegment.from_wav(caminho_wav)

    # Definir o tamanho do segmento (em milissegundos)
    tamanho_segmento = 30000  # 30 segundos por segmento

    # Inicializar o reconhecedor de fala
    reconhecedor = sr.Recognizer()

    # Caminho do arquivo de transcrição
    nome_arquivo_txt = os.path.splitext(nome_arquivo)[0] + "_transcricao.txt"
    caminho_txt = os.path.join("static", nome_arquivo_txt)

    # Abrir o arquivo de texto no modo append (acrescentar texto)
    with open(caminho_txt, "a") as arquivo_txt:
        # Transcrever cada pedaço e salvar em um arquivo de texto
        for i, pedaco in enumerate(range(0, len(audio), tamanho_segmento)):
            audio_pedaco = audio[pedaco:pedaco + tamanho_segmento]
            arquivo_temp = f"temp_pedaco_{i}.wav"
            audio_pedaco.export(arquivo_temp, format="wav")

            with sr.AudioFile(arquivo_temp) as source:
                audio_data = reconhecedor.record(source)

            try:
                texto = reconhecedor.recognize_google(audio_data, language="pt-BR")
                arquivo_txt.write(texto + " ")
                print(f"Transcrição do pedaço {i} concluída.")
                print(f"Texto: {texto}")
            except sr.UnknownValueError:
                print(f"Não foi possível entender o áudio no pedaço {i}.")
                arquivo_txt.write(f"[Erro: Pedaço {i} não compreendido]\n")
            except sr.RequestError as e:
                print(f"Erro no serviço de reconhecimento: {e}")
                arquivo_txt.write(f"[Erro no serviço de reconhecimento: {e}]\n")

            os.remove(arquivo_temp)  # Remove o arquivo temporário após uso

    print(f"Transcrição completa salva em: {caminho_txt}")
    return caminho_txt

# Exemplo de uso
#transcrever_audio_wav_por_pedacos("nome_arquivo232.wav")
