"""
ui/painel_hardware.py — Coluna esquerda: leitura USB e dados do aparelho.
Atualizado com UI moderna, fontes grandes e suporte nativo ao AutocompleteEntry modificado.
"""

import customtkinter as ctk
from ui.componentes import ReadOnlyField, AutocompleteEntry


class PainelHardware(ctk.CTkScrollableFrame):
    """Painel de leitura USB (coluna esquerda)."""

    def __init__(self, master, callbacks=None, **kwargs):
        super().__init__(master, **kwargs)
        self._callbacks = callbacks or {}

        lbl_sec = ctk.CTkLabel(self, text="🔌 Leitura USB (Hardware)",
                               font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        lbl_sec.pack(pady=(15, 20))

        # Botões de leitura
        self.btn_ios = ctk.CTkButton(
            self, text="Ler Aparelho (iPhone / iOS)", height=40,
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            fg_color="#4B4B4B", hover_color="#333333",
            command=self._callbacks.get("ler_ios")
        )
        self.btn_ios.pack(pady=6, padx=20, fill="x")

        self.btn_android = ctk.CTkButton(
            self, text="Ler Aparelho (Android ADB)", height=40,
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            fg_color="#2F80ED", hover_color="#1F61B8",
            command=self._callbacks.get("ler_android")
        )
        self.btn_android.pack(pady=6, padx=20, fill="x")

        self.btn_fastboot = ctk.CTkButton(
            self, text="Ler Aparelho (Fastboot)", height=40,
            font=ctk.CTkFont("Segoe UI", 15, "bold"),
            fg_color="#F2994A", hover_color="#E07A2B",
            command=self._callbacks.get("ler_fastboot")
        )
        self.btn_fastboot.pack(pady=6, padx=20, fill="x")

        # Switch modo manual
        self.switch_manual = ctk.CTkSwitch(
            self, text="Liberar digitação (Modo Manual)",
            font=ctk.CTkFont("Segoe UI", 14),
            progress_color="#F2994A",
            command=self._on_switch_manual
        )
        self.switch_manual.pack(pady=(20, 10), padx=20, anchor="w")

        # Campos de modelo (com autocomplete/busca - ESTILO HW ligado)
        self.campo_marca = AutocompleteEntry(
            self, "🏷️ Marca:", estilo_hw=True,
            command=self._callbacks.get("marca_selecionada")
        )
        self.campo_marca.pack(fill="x", padx=20, pady=(4, 0))

        self.campo_nome_comercial = AutocompleteEntry(
            self, "📱 Nome Comercial:", estilo_hw=True,
            command=self._callbacks.get("modelo_selecionado")
        )
        self.campo_nome_comercial.pack(fill="x", padx=20, pady=(4, 0))

        self.campo_modelo = AutocompleteEntry(self, "⚙️ Modelo Físico (Hardware ID):", estilo_hw=True)
        self.campo_modelo.pack(fill="x", padx=20, pady=(4, 0))

        # Armazenamento e RAM lado a lado
        frame_arm_ram = ctk.CTkFrame(self, fg_color="transparent")
        frame_arm_ram.pack(fill="x", padx=20, pady=(4, 0))
        frame_arm_ram.grid_columnconfigure(0, weight=1)
        frame_arm_ram.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_arm_ram, text="💾 Armazenamento:", font=ctk.CTkFont("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        self.campo_armazenamento = ctk.CTkEntry(
            frame_arm_ram, state="disabled", height=35,
            text_color="#00FF00", font=ctk.CTkFont("Segoe UI", 14, "bold")
        )
        self.campo_armazenamento.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkLabel(frame_arm_ram, text="🧠 Memória RAM:", font=ctk.CTkFont("Segoe UI", 13, "bold")).grid(row=0, column=1, sticky="w")
        self.campo_ram = ctk.CTkEntry(
            frame_arm_ram, state="disabled", height=35,
            text_color="#00FF00", font=ctk.CTkFont("Segoe UI", 14, "bold")
        )
        self.campo_ram.grid(row=1, column=1, sticky="ew", padx=(5, 0))

        # Identificadores

        self.campo_imei1 = ReadOnlyField(self, "📶 IMEI 1:")
        self.campo_imei1.pack(fill="x", padx=20, pady=(4, 0))

        self.campo_imei2 = ReadOnlyField(self, "📶 IMEI 2:")
        self.campo_imei2.pack(fill="x", padx=20, pady=(4, 0))

        self.campo_meid = ReadOnlyField(self, "📳 MEID:")
        self.campo_meid.pack(fill="x", padx=20, pady=(4, 0))

        self.campo_serie = ReadOnlyField(self, "🔢 Número de Série (S/N):")
        self.campo_serie.pack(fill="x", padx=20, pady=(4, 0))

    def _on_switch_manual(self):
        cb = self._callbacks.get("modo_manual")
        if cb:
            cb(self.switch_manual.get() == 1)

    def preencher_dados(self, dados: dict, modo_manual=False):
        """Preenche todos os campos com um dicionário de dados."""
        self.campo_marca.set(dados.get("marca", ""), modo_manual)
        self.campo_nome_comercial.set(dados.get("nome_comercial", ""), modo_manual)
        self.campo_modelo.set(dados.get("modelo", ""), modo_manual)

        # Armazenamento e RAM
        for campo, chave in [(self.campo_armazenamento, "armazenamento"), (self.campo_ram, "ram")]:
            campo.configure(state="normal")
            campo.delete(0, 'end')
            if dados.get(chave):
                campo.insert(0, str(dados.get(chave, "")))
            if not modo_manual:
                campo.configure(state="disabled", text_color="#00FF00")
            else:
                campo.configure(text_color="#FFFFFF")

        # Identificadores
        self.campo_imei1.set(dados.get("imei1", ""), modo_manual)
        self.campo_imei2.set(dados.get("imei2", ""), modo_manual)
        self.campo_meid.set(dados.get("meid", ""), modo_manual)
        self.campo_serie.set(dados.get("serie", ""), modo_manual)

    def limpar(self):
        dados_vazio = {k: "" for k in ["marca", "nome_comercial", "modelo", "armazenamento",
                                         "ram", "imei1", "imei2", "meid", "serie"]}
        self.preencher_dados(dados_vazio)

    def set_modo_manual(self, ativado: bool):
        """Alterna todos os campos entre editável e read-only."""
        campos = [self.campo_marca, self.campo_nome_comercial, self.campo_modelo,
                  self.campo_imei1, self.campo_imei2,
                  self.campo_meid, self.campo_serie]
        for campo in campos:
            campo.set_editavel(ativado)

        # Armazenamento e RAM
        for campo in [self.campo_armazenamento, self.campo_ram]:
            if ativado:
                campo.configure(state="normal", text_color="#FFFFFF")
            else:
                campo.configure(state="disabled", text_color="#00FF00")

    def obter_dados(self) -> dict:
        """Retorna todos os dados dos campos como dicionário."""
        return {
            "marca": self.campo_marca.get(),
            "nome_comercial": self.campo_nome_comercial.get(),
            "modelo": self.campo_modelo.get(),
            "armazenamento": self.campo_armazenamento.get(),
            "ram": self.campo_ram.get(),
            "imei1": self.campo_imei1.get(),
            "imei2": self.campo_imei2.get(),
            "meid": self.campo_meid.get(),
            "serie": self.campo_serie.get(),
        }
