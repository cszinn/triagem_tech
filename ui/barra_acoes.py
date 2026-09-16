"""
ui/barra_acoes.py — Rodapé: botões de ação e controle de patrimônio.
Atualizado com ícones e design moderno.
"""

import customtkinter as ctk
from servicos.impressao import WIN32_DISPONIVEL, listar_impressoras
import config as cfg_module


class BarraAcoes(ctk.CTkFrame):
    """Rodapé com botões de ação e controle de Nº de Patrimônio."""

    def __init__(self, master, patrimonio_num=10, callbacks=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._callbacks = callbacks or {}
        self._patrimonio_num = patrimonio_num

        # --- Linha de botões ---
        frame_botoes = ctk.CTkFrame(self)
        frame_botoes.pack(fill="x", padx=10, pady=(10, 5))
        for i in range(4):
            frame_botoes.grid_columnconfigure(i, weight=1)

        self.btn_limpar = ctk.CTkButton(
            frame_botoes, text="🗑️ Limpar Campos",
            font=ctk.CTkFont("Segoe UI", 16, "bold"), height=45,
            fg_color="#8A1111", hover_color="#5C0B0B",
            command=self._callbacks.get("limpar")
        )
        self.btn_limpar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.btn_copiar = ctk.CTkButton(
            frame_botoes, text="📋 COPIAR P/ EXCEL",
            font=ctk.CTkFont("Segoe UI", 16, "bold"), height=45,
            fg_color="#2FA572", hover_color="#248259",
            command=self._callbacks.get("copiar_excel")
        )
        self.btn_copiar.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.btn_salvar = ctk.CTkButton(
            frame_botoes, text="💾 SALVAR NO SISTEMA",
            font=ctk.CTkFont("Segoe UI", 16, "bold"), height=45,
            fg_color="#A52A2A", hover_color="#8B2222",
            command=self._callbacks.get("salvar_api")
        )
        self.btn_salvar.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        self.btn_imprimir = ctk.CTkButton(
            frame_botoes, text="🖨️ EDITAR/EXPORTAR ETIQUETA",
            font=ctk.CTkFont("Segoe UI", 16, "bold"), height=45,
            fg_color="#1f6aa5", hover_color="#144870",
            command=self._callbacks.get("editar_etiqueta")
        )
        self.btn_imprimir.grid(row=0, column=3, padx=(10, 60), pady=10, sticky="ew")

        self.btn_calibrar = ctk.CTkButton(
            frame_botoes, text="⚙️", width=45, height=45,
            font=ctk.CTkFont(size=22), fg_color="#444", hover_color="#666",
            command=self._callbacks.get("calibrar")
        )
        self.btn_calibrar.grid(row=0, column=3, padx=(0, 10), pady=10, sticky="e")

        # --- Controle de Nº de Patrimônio ---
        frame_pat = ctk.CTkFrame(self, fg_color="transparent")
        frame_pat.pack(fill="x", padx=20, pady=(0, 15))
        frame_pat.grid_columnconfigure(0, weight=1)
        frame_pat.grid_columnconfigure(1, weight=0)
        frame_pat.grid_columnconfigure(2, weight=0)
        frame_pat.grid_columnconfigure(3, weight=0)
        frame_pat.grid_columnconfigure(4, weight=1)

        lbl_pat = ctk.CTkLabel(frame_pat, text="🏷️ Nº de Patrimônio Próximo:",
                               font=ctk.CTkFont("Segoe UI", 15, "bold"))
        lbl_pat.grid(row=0, column=0, sticky="e", padx=(0, 12))

        self.btn_pat_menos = ctk.CTkButton(
            frame_pat, text="−", width=40, height=40,
            font=ctk.CTkFont(size=22, weight="bold"),
            fg_color="#3a3a3a", hover_color="#555555",
            command=self._decrementar
        )
        self.btn_pat_menos.grid(row=0, column=1, padx=(0, 4))

        self.entry_patrimonio = ctk.CTkEntry(
            frame_pat, width=150, height=40,
            font=ctk.CTkFont("Segoe UI", 16, "bold"),
            justify="center"
        )
        self.entry_patrimonio.grid(row=0, column=2, padx=4)
        self.entry_patrimonio.insert(0, f"ITI TECH-{self._patrimonio_num:03d}")
        self.entry_patrimonio.bind("<Up>", lambda e: self._incrementar())
        self.entry_patrimonio.bind("<Down>", lambda e: self._decrementar())
        self.entry_patrimonio.bind("<FocusOut>", self._validar_entrada)
        self.entry_patrimonio.bind("<Return>", self._validar_entrada)

        self.btn_pat_mais = ctk.CTkButton(
            frame_pat, text="+", width=40, height=40,
            font=ctk.CTkFont(size=22, weight="bold"),
            fg_color="#1f6aa5", hover_color="#144870",
            command=self._incrementar
        )
        self.btn_pat_mais.grid(row=0, column=3, padx=(4, 0))

        lbl_pat_info = ctk.CTkLabel(
            frame_pat,
            text='Use +/−, setas ↑↓ ou digite diretamente',
            font=ctk.CTkFont("Segoe UI", 12), text_color="gray"
        )
        lbl_pat_info.grid(row=0, column=4, sticky="w", padx=(12, 0))

    def _atualizar_display(self):
        self.entry_patrimonio.delete(0, 'end')
        self.entry_patrimonio.insert(0, f"ITI TECH-{self._patrimonio_num:03d}")

    def _incrementar(self):
        self._patrimonio_num += 1
        self._atualizar_display()
        self._salvar_patrimonio()

    def _decrementar(self):
        if self._patrimonio_num > 1:
            self._patrimonio_num -= 1
            self._atualizar_display()
            self._salvar_patrimonio()

    def _validar_entrada(self, event=None):
        texto = self.entry_patrimonio.get().strip()
        prefixo = "ITI TECH-"

        if texto.upper().startswith(prefixo):
            numero_str = texto[len(prefixo):].strip()
        else:
            numero_str = texto

        try:
            num = int(numero_str)
            if num < 1:
                num = 1
            self._patrimonio_num = num
        except ValueError:
            pass

        self._atualizar_display()
        self._salvar_patrimonio()

    def _salvar_patrimonio(self):
        """Salva o número de patrimônio no config.json."""
        try:
            cfg = cfg_module.carregar()
            if cfg.get("patrimonio_num") != self._patrimonio_num:
                cfg["patrimonio_num"] = self._patrimonio_num
                cfg_module.salvar(cfg)
        except Exception:
            pass

    @property
    def patrimonio_num(self):
        return self._patrimonio_num

    @patrimonio_num.setter
    def patrimonio_num(self, valor):
        self._patrimonio_num = valor
        self._atualizar_display()
        self._salvar_patrimonio()

    def get_patrimonio_texto(self) -> str:
        return f"ITI TECH-{self._patrimonio_num:03d}"
