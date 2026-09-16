"""
motores/android.py — Motor de extração de dados de Androids via ADB.
Extrai IMEI (com bypass), série, modelo, armazenamento e RAM.
"""

import os
import subprocess
import re

DIRETORIO_ATUAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_TOOLS = os.path.join(DIRETORIO_ATUAL, "platform-tools")
CAMINHO_ADB = os.path.join(PASTA_TOOLS, "adb.exe")


def _getprop(prop: str) -> str:
    """Executa adb shell getprop e retorna o valor."""
    try:
        return subprocess.check_output(
            [CAMINHO_ADB, 'shell', 'getprop', prop],
            text=True, creationflags=subprocess.CREATE_NO_WINDOW
        ).strip()
    except Exception:
        return ""


def _extrair_imeis_meids() -> dict:
    """Tenta extrair IMEIs e MEID via service call e getprop."""
    imeis_meids = set()

    # Método 1: service call iphonesubinfo (bypass)
    for i in range(1, 6):
        for slot in [0, 1]:
            try:
                cmd = f'"{CAMINHO_ADB}" shell "service call iphonesubinfo {i} i32 {slot}"'
                out = subprocess.getoutput(cmd)
                if 'Parcel' in out:
                    parts = re.findall(r"'(.*?)'", out)
                    clean_str = "".join(parts).replace('.', '').replace(' ', '').strip()
                    if len(clean_str) >= 14 and clean_str.isalnum():
                        imeis_meids.add(clean_str)
            except Exception:
                pass

    # Método 2: getprop grep imei
    try:
        prop_imeis = subprocess.getoutput(f'"{CAMINHO_ADB}" shell "getprop | grep -i imei"')
        for match in re.findall(r'\[(.*?)\]:\s*\[(.*?)\]', prop_imeis):
            val = match[1].strip()
            if len(val) >= 14 and val.isalnum():
                imeis_meids.add(val)
    except Exception:
        pass

    # Classificar
    ids_lista = sorted(list(imeis_meids))
    imei1 = "N/A"
    imei2 = "N/A"
    meid = "N/A"

    for ident in ids_lista:
        if len(ident) == 14:
            meid = ident
        elif len(ident) >= 15:
            if imei1 == "N/A":
                imei1 = ident
            elif imei2 == "N/A" and ident != imei1:
                imei2 = ident

    return {"imei1": imei1, "imei2": imei2, "meid": meid}


def _extrair_eid() -> str:
    """Tenta extrair o EID (eSIM) via getprop."""
    try:
        prop_eid = subprocess.getoutput(f'"{CAMINHO_ADB}" shell "getprop | grep -i eid"')
        for match in re.findall(r'\[(.*?)\]:\s*\[(.*?)\]', prop_eid):
            val = match[1].strip()
            if len(val) == 32 and val.isdigit() and val.startswith("89"):
                return val
    except Exception:
        pass
    return "N/A"


def _extrair_armazenamento() -> str:
    """Calcula o armazenamento a partir do df."""
    try:
        df_out = subprocess.check_output(
            [CAMINHO_ADB, 'shell', 'df'], text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).strip()
        for linha in df_out.split('\n'):
            if '/data' in linha:
                partes = linha.split()
                if len(partes) >= 4:
                    if partes[0].startswith('/'):
                        tamanho_str = partes[1]
                    elif partes[0][0].isdigit():
                        tamanho_str = partes[0]
                    else:
                        tamanho_str = partes[1]

                    tamanho_str = tamanho_str.upper()
                    match = re.search(r'([\d\.]+)', tamanho_str)
                    if match:
                        val = float(match.group(1))
                        if 'G' in tamanho_str:
                            gb = val
                        elif 'M' in tamanho_str:
                            gb = val / 1024
                        elif 'K' in tamanho_str:
                            gb = val / (1024 * 1024)
                        else:
                            gb = val / (1024 * 1024)

                        if gb > 0:
                            tamanhos_mercado = [8, 16, 32, 64, 128, 256, 512, 1024]
                            tamanho_real = next((t for t in tamanhos_mercado if t >= gb), tamanhos_mercado[-1])
                            return f"{tamanho_real} GB"
    except Exception:
        pass
    return "N/A"


def _extrair_ram() -> str:
    """Calcula a RAM a partir do /proc/meminfo."""
    try:
        ram_raw = subprocess.check_output(
            [CAMINHO_ADB, 'shell', 'cat /proc/meminfo'],
            text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        kb_match = re.search(r'MemTotal:\s+(\d+)\s+kB', ram_raw, re.IGNORECASE)
        if kb_match:
            gb_ram_float = int(kb_match.group(1)) / (1024 * 1024)
            tamanhos_ram = [1, 2, 3, 4, 6, 8, 12, 16, 24]
            gb_calculado = next((t for t in tamanhos_ram if t >= gb_ram_float), tamanhos_ram[-1])
            return f"{gb_calculado} GB"
    except Exception:
        pass
    return "N/A"


def extrair() -> dict:
    """
    Executa ADB e retorna um dicionário com os dados do aparelho Android.
    Lança Exception se a comunicação falhar.
    """
    marca_raw = _getprop('ro.product.brand')
    marca = marca_raw.capitalize() if marca_raw else "N/A"

    modelo = _getprop('ro.product.model') or "Desconhecido"

    mercado_raw = _getprop('ro.product.marketname')
    nome_comercial = mercado_raw if mercado_raw else modelo

    # Número de série — tenta múltiplas fontes
    serie = "N/A"
    try:
        serie_psno = _getprop('ro.ril.oem.psno')
        serie_gsm = _getprop('vendor.gsm.serial')
        serie_boot = _getprop('ro.boot.serialno')
        serie_normal = _getprop('ro.serialno')

        if serie_psno and len(serie_psno) > 4:
            serie = serie_psno
        elif serie_normal and serie_normal not in ("N/A", "unknown"):
            serie = serie_normal
        elif serie_gsm and len(serie_gsm) > 4:
            serie = serie_gsm
        else:
            serie = serie_boot or "N/A"
    except Exception:
        pass

    ids = _extrair_imeis_meids()
    eid = _extrair_eid()
    armazenamento = _extrair_armazenamento()
    ram = _extrair_ram()

    # Determinar se a leitura foi parcial (IMEI bloqueado no Android 10+)
    imei_encontrado = ids["imei1"] != "N/A" or ids["imei2"] != "N/A"

    return {
        "marca": marca,
        "modelo": modelo,
        "nome_comercial": nome_comercial,
        "armazenamento": armazenamento,
        "ram": ram,
        "eid": eid,
        "imei1": ids["imei1"],
        "imei2": ids["imei2"],
        "meid": ids["meid"],
        "serie": serie,
        "imei_encontrado": imei_encontrado,
    }
