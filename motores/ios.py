"""
motores/ios.py — Motor de extração de dados de iPhones via ideviceinfo.
Extrai IMEI, série, modelo, armazenamento e demais identificadores.
"""

import os
import subprocess
import re

DIRETORIO_ATUAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_TOOLS = os.path.join(DIRETORIO_ATUAL, "platform-tools")
CAMINHO_IDEVICEINFO = os.path.join(PASTA_TOOLS, "ideviceinfo.exe")

# Mapeamento Hardware ID → Nome Comercial
TABELA_IPHONES = {
    # iPhone 5, 5c, 5s
    "iPhone5,1": "iPhone 5", "iPhone5,2": "iPhone 5",
    "iPhone5,3": "iPhone 5c", "iPhone5,4": "iPhone 5c",
    "iPhone6,1": "iPhone 5s", "iPhone6,2": "iPhone 5s",
    # iPhone 6, 6 Plus
    "iPhone7,1": "iPhone 6 Plus", "iPhone7,2": "iPhone 6",
    # iPhone 6s, 6s Plus, SE 1ª Ger
    "iPhone8,1": "iPhone 6s", "iPhone8,2": "iPhone 6s Plus", "iPhone8,4": "iPhone SE (1ª Ger)",
    # iPhone 7, 7 Plus
    "iPhone9,1": "iPhone 7", "iPhone9,3": "iPhone 7",
    "iPhone9,2": "iPhone 7 Plus", "iPhone9,4": "iPhone 7 Plus",
    # iPhone 8, 8 Plus, X
    "iPhone10,1": "iPhone 8", "iPhone10,4": "iPhone 8",
    "iPhone10,2": "iPhone 8 Plus", "iPhone10,5": "iPhone 8 Plus",
    "iPhone10,3": "iPhone X", "iPhone10,6": "iPhone X",
    # iPhone XS, XS Max, XR
    "iPhone11,2": "iPhone XS", "iPhone11,4": "iPhone XS Max", "iPhone11,6": "iPhone XS Max",
    "iPhone11,8": "iPhone XR",
    # iPhone 11 series, SE 2ª Ger
    "iPhone12,1": "iPhone 11", "iPhone12,3": "iPhone 11 Pro", "iPhone12,5": "iPhone 11 Pro Max",
    "iPhone12,8": "iPhone SE (2ª Ger)",
    # iPhone 12 series
    "iPhone13,1": "iPhone 12 mini", "iPhone13,2": "iPhone 12", "iPhone13,3": "iPhone 12 Pro", "iPhone13,4": "iPhone 12 Pro Max",
    # iPhone 13 series, SE 3ª Ger
    "iPhone14,4": "iPhone 13 mini", "iPhone14,5": "iPhone 13", "iPhone14,2": "iPhone 13 Pro", "iPhone14,3": "iPhone 13 Pro Max",
    "iPhone14,6": "iPhone SE (3ª Ger)",
    # iPhone 14 series
    "iPhone14,7": "iPhone 14", "iPhone14,8": "iPhone 14 Plus",
    "iPhone15,2": "iPhone 14 Pro", "iPhone15,3": "iPhone 14 Pro Max",
    # iPhone 15 series
    "iPhone15,4": "iPhone 15", "iPhone15,5": "iPhone 15 Plus",
    "iPhone16,1": "iPhone 15 Pro", "iPhone16,2": "iPhone 15 Pro Max",
    # iPhone 16 series
    "iPhone17,1": "iPhone 16 Pro", "iPhone17,2": "iPhone 16 Pro Max", "iPhone17,3": "iPhone 16", "iPhone17,4": "iPhone 16 Plus",
    # iPhone 17 series
    "iPhone18,1": "iPhone 17 Pro", "iPhone18,2": "iPhone 17 Pro Max", "iPhone18,3": "iPhone 17", "iPhone18,4": "iPhone 17 Plus",
    # iPhone 18 series
    "iPhone19,1": "iPhone 18 Pro", "iPhone19,2": "iPhone 18 Pro Max", "iPhone19,3": "iPhone 18", "iPhone19,4": "iPhone 18 Plus",
}


def extrair() -> dict:
    """
    Executa ideviceinfo e retorna um dicionário com os dados do aparelho.
    Lança FileNotFoundError se o executável não existir.
    Lança subprocess.CalledProcessError se a comunicação falhar.
    """
    raw_info = subprocess.check_output(
        [CAMINHO_IDEVICEINFO], text=True,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    info_dict = {}
    for linha in raw_info.split('\n'):
        if ': ' in linha:
            chave, valor = linha.split(': ', 1)
            info_dict[chave.strip()] = valor.strip()

    marca = "Apple"
    modelo = info_dict.get('ProductType', 'Desconhecido')
    nome_comercial = TABELA_IPHONES.get(modelo, modelo)

    serie = info_dict.get('SerialNumber', 'N/A')
    imei1 = info_dict.get('InternationalMobileEquipmentIdentity', 'N/A')

    imei2 = info_dict.get(
        'InternationalMobileEquipmentIdentity2',
        info_dict.get('InternationalMobileSubscriberIdentity', 'N/A')
    )
    if imei2 == imei1:
        imei2 = "N/A"

    meid = info_dict.get('MobileEquipmentIdentifier', 'N/A')
    eid = "N/A"

    # Capacidade de armazenamento
    armazenamento = "N/A"
    try:
        bytes_raw = subprocess.check_output(
            [CAMINHO_IDEVICEINFO, '-q', 'com.apple.disk_usage', '-k', 'TotalDiskCapacity'],
            text=True, creationflags=subprocess.CREATE_NO_WINDOW
        ).strip()
        gb_calculado = int(bytes_raw) / (1000 ** 3)
        tamanhos_mercado = [8, 16, 32, 64, 128, 256, 512, 1024]
        tamanho_real = min(tamanhos_mercado, key=lambda x: abs(x - gb_calculado))
        armazenamento = f"{tamanho_real} GB"
    except Exception:
        pass

    ram = "N/A"  # A Apple não expõe a RAM via terminal

    return {
        "marca": marca,
        "modelo": modelo,
        "nome_comercial": nome_comercial,
        "armazenamento": armazenamento,
        "ram": ram,
        "eid": eid,
        "imei1": imei1,
        "imei2": imei2,
        "meid": meid,
        "serie": serie,
    }
