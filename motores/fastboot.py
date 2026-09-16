"""
motores/fastboot.py — Motor de extração de dados via Fastboot.
Usado para aparelhos que estão em modo bootloader.
"""

import os
import subprocess
import re

DIRETORIO_ATUAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_TOOLS = os.path.join(DIRETORIO_ATUAL, "platform-tools")
CAMINHO_FASTBOOT = os.path.join(PASTA_TOOLS, "fastboot.exe")


def extrair() -> dict:
    """
    Executa fastboot getvar all e retorna um dicionário com os dados extraídos.
    Lança FileNotFoundError se fastboot.exe não existir.
    """
    result = subprocess.run(
        [CAMINHO_FASTBOOT, 'getvar', 'all'],
        capture_output=True, text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    output = result.stderr + "\n" + result.stdout

    if "waiting for any device" in output.lower() or not output.strip() or "FAILED" in output:
        raise ConnectionError("Nenhum aparelho em modo Fastboot detectado.")

    info_dict = {}
    for linha in output.split('\n'):
        if ':' in linha:
            partes = linha.split(':', 1)
            chave = partes[0].replace('(bootloader)', '').strip().lower()
            valor = partes[1].strip()
            info_dict[chave] = valor

    imei1 = info_dict.get('imei', 'N/A')
    imei2 = info_dict.get('imei2', 'N/A')
    serie = info_dict.get('serialno', 'N/A')

    ram_raw = info_dict.get('ro.ramsize', info_dict.get('ram', 'N/A'))
    armazenamento_raw = info_dict.get('ro.emmc_size', info_dict.get('ro.ufs_size', 'N/A'))

    ram = "N/A"
    if ram_raw != "N/A" and 'GB' in ram_raw.upper():
        ram = ram_raw.upper().replace(' ', '')

    armazenamento = "N/A"
    if armazenamento_raw != "N/A" and 'GB' in armazenamento_raw.upper():
        armazenamento = armazenamento_raw.upper().replace(' ', '')

    marca = "N/A"
    modelo = info_dict.get('product', info_dict.get('hw.board', 'Desconhecido'))

    if 'moto' in modelo.lower() or 'motorola' in output.lower():
        marca = "Motorola"
    elif 'xiaomi' in output.lower() or 'poco' in output.lower():
        marca = "Xiaomi"

    return {
        "marca": marca,
        "modelo": modelo,
        "nome_comercial": modelo,
        "armazenamento": armazenamento,
        "ram": ram,
        "eid": "N/A",
        "imei1": imei1,
        "imei2": imei2,
        "meid": "N/A",
        "serie": serie,
        "imei_encontrado": imei1 != "N/A",
    }
