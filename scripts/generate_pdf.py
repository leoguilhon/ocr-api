from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

c = canvas.Canvas("samples/documento.pdf", pagesize=A4)

texts = [
    "RELATORIO FINANCEIRO\nTOTAL FATURADO: R$ 12.500,00\nDATA: 20/02/2026",
    "DETALHAMENTO\nSERVICO A: R$ 5.000,00\nSERVICO B: R$ 7.500,00"
]

for text in texts:
    c.setFont("Helvetica", 14)
    y = 800
    for line in text.split("\n"):
        c.drawString(50, y, line)
        y -= 30
    c.showPage()

c.save()
print("PDF criado com sucesso.")