from PIL import Image, ImageDraw, ImageFont

def create_image(path, text):
    img = Image.new("RGB", (900, 500), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except:
        font = ImageFont.load_default()

    draw.text((50, 50), text, fill="black", font=font)
    img.save(path)

text = """
SUPERMERCADO BOM PRECO
CNPJ: 12.345.678/0001-99
DATA: 21/02/2026

ARROZ 5KG ........ R$ 29,90
FEIJAO 1KG ....... R$ 9,50
CARNE ........... R$ 42,00

TOTAL: R$ 81,40
"""

create_image("samples/nota.png", text)
create_image("samples/nota.jpg", text)

print("Imagens PNG e JPG criadas com sucesso.")