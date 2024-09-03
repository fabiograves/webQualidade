import barcode
from barcode.writer import ImageWriter

# Defina o número do código de barras
codigo = "S0001"

# Escolha o tipo de código de barras (neste exemplo, Code128)
barcode_class = barcode.get_barcode_class('code128')

# Crie o código de barras
codigo_barras = barcode_class(codigo, writer=ImageWriter())

# Salve a imagem do código de barras
filename = codigo_barras.save("codigo_barras_S0001")

print(f"Código de barras salvo como {filename}.png")
