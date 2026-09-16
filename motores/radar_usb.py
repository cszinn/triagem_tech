"""
motores/radar_usb.py — Monitor contínuo de dispositivos USB (iOS e Android).
Detecta conexões e desconexões, disparando callbacks para a UI.
"""

import os
import subprocess
import time

DIRETORIO_ATUAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_TOOLS = os.path.join(DIRETORIO_ATUAL, "platform-tools")
CAMINHO_ADB = os.path.join(PASTA_TOOLS, "adb.exe")
CAMINHO_IDEVICEID = os.path.join(PASTA_TOOLS, "idevice_id.exe")


def monitorar(callback):
    """
    Loop infinito que detecta dispositivos conectados/desconectados.
    
    Args:
        callback: função(mensagem: str, cor: str) chamada a cada evento.
                  Deve ser thread-safe (usar self.after() se for Tkinter).
    """
    dispositivos_android = set()
    dispositivos_ios = set()

    while True:
        time.sleep(1.5)

        # --- iOS ---
        try:
            out_ios = subprocess.check_output(
                [CAMINHO_IDEVICEID, '-l'], text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            ).strip().split('\n')
            ios_atuais = set(d for d in out_ios if d)
        except Exception:
            ios_atuais = set()

        novos_ios = ios_atuais - dispositivos_ios
        removidos_ios = dispositivos_ios - ios_atuais

        for _ in novos_ios:
            callback("Aparelho Apple detectado na porta USB.", "#00FFFF")
        for _ in removidos_ios:
            callback("Aparelho Apple desconectado.", "#8B8B8B")

        dispositivos_ios = ios_atuais

        # --- Android ---
        try:
            out_android = subprocess.check_output(
                [CAMINHO_ADB, 'devices'], text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            ).strip().split('\n')
            android_atuais = set()
            for linha in out_android[1:]:
                if '\t' in linha:
                    android_atuais.add(linha.split('\t')[0])
        except Exception:
            android_atuais = set()

        novos_android = android_atuais - dispositivos_android
        removidos_android = dispositivos_android - android_atuais

        for _ in novos_android:
            callback("Aparelho Android detectado (Acesso ADB liberado).", "#00FFFF")
        for _ in removidos_android:
            callback("Aparelho Android desconectado.", "#8B8B8B")

        dispositivos_android = android_atuais
