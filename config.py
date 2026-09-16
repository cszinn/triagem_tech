"""
config.py — Gerenciador centralizado do config.json.
Carrega, mescla com valores padrão e salva configurações do sistema.
"""

import os
import json

_CONFIG_PATH = "config.json"

CONFIG_PADRAO = {
    # Impressora
    "impressora": "4BARCODE 4B-2054L",
    "largura_mm": 58.6,
    "altura_mm": 40.0,
    "offset_x_mm": 0.0,
    "offset_y_mm": 2.0,
    "patrimonio_num": 10,
    "escala_conteudo": 1.2,

    # Rede / API
    "api_url": "https://useful-gecko-present.ngrok-free.app/api",

    # Janela / UI
    "app_titulo": "Instituto ITI - Triagem Receita Federal",
    "app_geometria": "1920x1080",
}


def carregar() -> dict:
    """Carrega config.json e mescla com os padrões."""
    try:
        if os.path.exists(_CONFIG_PATH):
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return {**CONFIG_PADRAO, **dados}
    except Exception:
        pass
    return dict(CONFIG_PADRAO)


def salvar(cfg: dict):
    """Salva o dicionário de configuração no config.json."""
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
