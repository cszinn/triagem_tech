"""
servicos/impressao.py — Geração de etiquetas térmicas e impressão direta via Windows GDI.
"""

import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

# Impressão direta via Windows GDI
try:
    import win32print
    import win32ui
    import win32con
    import win32gui
    from PIL import ImageWin
    WIN32_DISPONIVEL = True
except ImportError:
    WIN32_DISPONIVEL = False


def construir_imagem_etiqueta(id_telefone, patrimonio, marca, modelo, arm, serie, estado, escala=1.0):
    """
    Constrói a etiqueta como imagem PIL no tamanho exato da etiqueta física
    (58,6 mm x 40 mm) na resolução de 203 DPI.
    Retorna um objeto PIL.Image.
    """
    DPI = 203
    MM_POR_POLEGADA = 25.4

    largura_px = int(round(58.6 / MM_POR_POLEGADA * DPI))
    altura_px = int(round(40.0 / MM_POR_POLEGADA * DPI))

    img = Image.new("L", (largura_px, altura_px), 255)
    draw = ImageDraw.Draw(img)

    def _fonte(tamanho):
        try:
            caminho = os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Fonts", "arialbd.ttf")
            if os.path.exists(caminho):
                return ImageFont.truetype(caminho, tamanho)
            return ImageFont.truetype("arial.ttf", tamanho)
        except Exception:
            return ImageFont.load_default()

    fonte_titulo = _fonte(int(22 * escala))
    fonte_normal = _fonte(int(17 * escala))
    fonte_pequena = _fonte(int(15 * escala))
    fonte_pat = _fonte(int(19 * escala))

    def centralizar_texto(texto, y, fonte):
        bbox = draw.textbbox((0, 0), texto, font=fonte)
        w = bbox[2] - bbox[0]
        x = (largura_px - w) // 2
        draw.text((x, y), texto, font=fonte, fill=0)

    # 1. Cabeçalho
    centralizar_texto("Instituto ITI - Triagem", int(4 * escala), fonte_titulo)

    # 2. Aparelho
    if marca and not modelo.lower().startswith(marca.lower()):
        txt_aparelho = f"{marca} {modelo}".strip()
    else:
        txt_aparelho = modelo if modelo else marca
    centralizar_texto(txt_aparelho, int(32 * escala), fonte_normal)

    # 3. Capacidade
    txt_cap = f"Capacidade: {arm}" if arm and arm != "N/A" else "Capacidade: N/A"
    centralizar_texto(txt_cap, int(54 * escala), fonte_pequena)

    # 4. S/N e Estado
    txt_sn = f"S/N: {serie or 'N/A'} | Est: {estado or 'N/A'}"
    centralizar_texto(txt_sn, int(73 * escala), fonte_pequena)

    # 5. QR Code
    qr = qrcode.QRCode(version=2, box_size=4, border=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data(id_telefone)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")

    qr_alvo = int(116 * escala)
    qr_img = qr_img.resize((qr_alvo, qr_alvo), Image.LANCZOS)

    qr_x = (largura_px - qr_alvo) // 2
    qr_y = int(96 * escala)
    img.paste(qr_img, (qr_x, qr_y))

    # 6. Nº de Patrimônio
    centralizar_texto(patrimonio, int(218 * escala), fonte_pat)

    return img


def imprimir_imagem_win32(img: Image.Image, nome_impressora: str, patrimonio: str, cfg: dict):
    """Envia a imagem PIL diretamente para a impressora via Windows GDI."""
    if not WIN32_DISPONIVEL:
        raise RuntimeError("win32print não disponível.")

    # Verifica se a impressora existe
    nomes_disponiveis = [p[2] for p in win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
    if nome_impressora not in nomes_disponiveis:
        nome_impressora = win32print.GetDefaultPrinter()

    hprinter = win32print.OpenPrinter(nome_impressora)
    printer_info = win32print.GetPrinter(hprinter, 2)
    devmode = printer_info["pDevMode"]

    hdc_gui = win32gui.CreateDC("WINSPOOL", nome_impressora, devmode)
    hdc = win32ui.CreateDCFromHandle(hdc_gui)

    dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
    dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)
    imp_w = hdc.GetDeviceCaps(win32con.HORZRES)
    imp_h = hdc.GetDeviceCaps(win32con.VERTRES)

    MM = 25.4

    offset_x_mm = cfg.get("offset_x_mm", 0.0)
    offset_y_mm = cfg.get("offset_y_mm", 0.0)
    offset_x_px = int(round(offset_x_mm / MM * dpi_x))
    offset_y_px = int(round(offset_y_mm / MM * dpi_y))

    alvo_w = int(round(cfg["largura_mm"] / MM * dpi_x))
    alvo_h = int(round(cfg["altura_mm"] / MM * dpi_y))
    img_impressao = img.resize((alvo_w, alvo_h), Image.LANCZOS).convert("RGB")

    if offset_x_px < 0:
        img_impressao = img_impressao.crop((-offset_x_px, 0, alvo_w, alvo_h))
        alvo_w += offset_x_px
        offset_x_px = 0
    if offset_y_px < 0:
        img_impressao = img_impressao.crop((0, -offset_y_px, alvo_w, alvo_h))
        alvo_h += offset_y_px
        offset_y_px = 0

    crop_w = min(alvo_w, imp_w - offset_x_px)
    crop_h = min(alvo_h, imp_h - offset_y_px)
    if crop_w < alvo_w or crop_h < alvo_h:
        img_impressao = img_impressao.crop((0, 0, crop_w, crop_h))

    hdc.StartDoc(f"Etiqueta {patrimonio}")
    hdc.StartPage()

    dib = ImageWin.Dib(img_impressao)
    x2 = offset_x_px + crop_w
    y2 = offset_y_px + crop_h
    dib.draw(hdc.GetHandleAttrib(), (offset_x_px, offset_y_px, x2, y2))

    hdc.EndPage()
    hdc.EndDoc()
    hdc.DeleteDC()
    win32print.ClosePrinter(hprinter)


def listar_impressoras() -> list:
    """Retorna os nomes de todas as impressoras disponíveis no Windows."""
    if not WIN32_DISPONIVEL:
        return []
    return [p[2] for p in win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
