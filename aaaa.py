import base64
import json
from PIL import Image
import io

# Carregar os dados do arquivo JSON
with open('json/STA1000242024-06-13_14_00_00_0735_1_NEW2023.json', 'r') as file:
    data = json.load(file)

# Extrair informações do JSON
equipamento = data.get('equipamento')
data_evento = data.get('data')
hora = data.get('hora')
faixa = data.get('faixa')
placa = data.get('placa')
tag = data.get('tag')
imagem_base64 = data.get('imagemBase64')
latitude = data.get('latitude')
longitude = data.get('longtitude')

# Decodificar a imagem Base64
image_data = base64.b64decode(imagem_base64)
image = Image.open(io.BytesIO(image_data))

# Mostrar a imagem
image.show()

# Salvar a imagem (opcional)
image.save("imagem_decodificada.png")

# Mostrar as informações
print(f"Equipamento: {equipamento}")
print(f"Data: {data_evento}")
print(f"Hora: {hora}")
print(f"Faixa: {faixa}")
print(f"Placa: {placa}")
print(f"Tag: {tag}")
print(f"Latitude: {latitude}")
print(f"Longitude: {longitude}")
