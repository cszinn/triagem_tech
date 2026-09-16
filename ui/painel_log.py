"""
ui/painel_log.py — Coluna direita: log de operação.
Atualizado com visual moderno.
"""

import customtkinter as ctk
from datetime import datetime


class PainelLog(ctk.CTkFrame):
    """Painel de log de operação (coluna direita)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        lbl_sec = ctk.CTkLabel(self, text="📜 Log de Operação",
                               font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        lbl_sec.pack(pady=(15, 20))

        self.caixa_log = ctk.CTkTextbox(
            self, state="disabled", wrap="word",
            font=ctk.CTkFont(family="Consolas", size=13),
            fg_color="#1E1E1E", text_color="#E0E0E0"
        )
        self.caixa_log.pack(expand=True, fill="both", padx=15, pady=(0, 15))

    def adicionar(self, mensagem: str):
        """Adiciona uma linha com timestamp ao log."""
        agora = datetime.now().strftime("%H:%M:%S")
        linha_log = f"[{agora}] {mensagem}\n"

        self.caixa_log.configure(state="normal")
        self.caixa_log.insert("end", linha_log)
        self.caixa_log.see("end")
        self.caixa_log.configure(state="disabled")
