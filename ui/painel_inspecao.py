"""
ui/painel_inspecao.py — Coluna central: inspeção física e avarias.
Modificado para usar AutocompleteEntry em todos os campos de lista,
permitindo digitação livre irrestrita conforme pedido pelo usuário.
"""

import unicodedata
import difflib
import customtkinter as ctk
from ui.componentes import LabeledEntry, AutocompleteEntry


class PainelInspecao(ctk.CTkFrame):
    """Painel de inspeção física (coluna central)."""

    def __init__(self, master, callbacks=None, **kwargs):
        super().__init__(master, **kwargs)
        self._callbacks = callbacks or {}

        lbl_sec = ctk.CTkLabel(self, text="🛠️ Inspeção Física",
                               font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"))
        lbl_sec.pack(pady=(15, 20))

        # ID e Caixa lado a lado
        frame_id_caixa = ctk.CTkFrame(self, fg_color="transparent")
        frame_id_caixa.pack(fill="x", padx=20, pady=(5, 10))
        frame_id_caixa.grid_columnconfigure(0, weight=1)
        frame_id_caixa.grid_columnconfigure(1, weight=2) # Caixa costuma ser texto maior

        self.input_id_tecnico = LabeledEntry(frame_id_caixa, "ID Responsável Técnico:")
        self.input_id_tecnico.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.input_id_tecnico.set("1")

        self.combo_caixa = AutocompleteEntry(frame_id_caixa, "📦 Caixa de Recebimento:")
        self.combo_caixa.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Cor do Aparelho
        self.combo_cor = AutocompleteEntry(self, "🎨 Cor do Aparelho:")
        self.combo_cor.pack(fill="x", padx=20, pady=(5, 10))

        # Chips e Peso lado a lado
        frame_chips_peso = ctk.CTkFrame(self, fg_color="transparent")
        frame_chips_peso.pack(fill="x", padx=20, pady=(5, 10))
        frame_chips_peso.grid_columnconfigure(0, weight=1)
        frame_chips_peso.grid_columnconfigure(1, weight=1)
        frame_chips_peso.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(frame_chips_peso, text="Chips Aceit.:", font=ctk.CTkFont("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        self.input_qnt_chips = ctk.CTkEntry(frame_chips_peso, height=35)
        self.input_qnt_chips.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkLabel(frame_chips_peso, text="Chips Inst.:", font=ctk.CTkFont("Segoe UI", 13, "bold")).grid(row=0, column=1, sticky="w")
        self.input_chips_inst = ctk.CTkEntry(frame_chips_peso, height=35)
        self.input_chips_inst.grid(row=1, column=1, sticky="ew", padx=(4, 4))

        ctk.CTkLabel(frame_chips_peso, text="Peso (g):", font=ctk.CTkFont("Segoe UI", 13, "bold")).grid(row=0, column=2, sticky="w")
        self.input_peso = ctk.CTkEntry(frame_chips_peso, height=35)
        self.input_peso.grid(row=1, column=2, sticky="ew", padx=(4, 0))

        # Estado Físico, Condição e Acesso lado a lado (3 colunas)
        frame_estados = ctk.CTkFrame(self, fg_color="transparent")
        frame_estados.pack(fill="x", padx=20, pady=(5, 10))
        frame_estados.grid_columnconfigure(0, weight=1)
        frame_estados.grid_columnconfigure(1, weight=1)
        frame_estados.grid_columnconfigure(2, weight=1)

        self.combo_estado = AutocompleteEntry(frame_estados, "📱 Estado Físico:")
        self.combo_estado.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.combo_condicao = AutocompleteEntry(frame_estados, "⚙️ Condição de Func.:")
        self.combo_condicao.grid(row=0, column=1, sticky="ew", padx=(4, 4))

        self.combo_acesso = AutocompleteEntry(frame_estados, "🔓 Estado de Acesso:")
        self.combo_acesso.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        # Observações
        self.input_obs = LabeledEntry(self, "📝 Observações Adicionais:")
        self.input_obs.pack(fill="x", padx=20, pady=(5, 15))

        # Avarias e Checkbox de filtro
        frame_titulo_avarias = ctk.CTkFrame(self, fg_color="transparent")
        frame_titulo_avarias.pack(fill="x", padx=20, pady=(10, 5))
        frame_titulo_avarias.grid_columnconfigure(0, weight=1)
        
        lbl_avarias = ctk.CTkLabel(frame_titulo_avarias, text="⚠️ Avarias Identificadas:", font=ctk.CTkFont("Segoe UI", 14, "bold"))
        lbl_avarias.grid(row=0, column=0, sticky="w")
        
        self.var_mostrar_selecionadas = ctk.BooleanVar(value=False)
        self.chk_mostrar_selecionadas = ctk.CTkCheckBox(
            frame_titulo_avarias, text="Ver só marcadas",
            variable=self.var_mostrar_selecionadas,
            command=self._filtrar_avarias,
            font=ctk.CTkFont("Segoe UI", 12)
        )
        self.chk_mostrar_selecionadas.grid(row=0, column=1, sticky="e")

        # Busca + botão adicionar avaria
        frame_busca_avaria = ctk.CTkFrame(self, fg_color="transparent")
        frame_busca_avaria.pack(fill="x", padx=20, pady=(0, 5))
        frame_busca_avaria.grid_columnconfigure(0, weight=1)
        frame_busca_avaria.grid_columnconfigure(1, weight=0)

        self.input_busca_avaria = ctk.CTkEntry(
            frame_busca_avaria, height=35,
            placeholder_text="Pesquisar ou adicionar (ex: conector)...",
            font=ctk.CTkFont("Segoe UI", 13)
        )
        self.input_busca_avaria.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.input_busca_avaria.bind("<KeyRelease>", self._filtrar_avarias)

        self.btn_add_avaria = ctk.CTkButton(
            frame_busca_avaria, text="➕ Adicionar", width=90, height=35,
            fg_color="#2F80ED", hover_color="#1F61B8",
            font=ctk.CTkFont("Segoe UI", 13, "bold"),
            command=lambda: self._callbacks.get("cadastrar_avaria", lambda: None)()
        )
        self.btn_add_avaria.grid(row=0, column=1, sticky="e")

        # Frame scrollável de checkboxes de avarias
        self.frame_avarias = ctk.CTkScrollableFrame(self, height=120, fg_color="#1E1E1E")
        self.frame_avarias.pack(fill="x", padx=20, pady=(0, 15))

        self.vars_avarias = {}
        self.widgets_avarias = {}

    def popular_dominios(self, dominios: dict):
        """Popula todos os AutocompleteEntry com os dados da API."""
        self.combo_caixa.set_values(dominios.get("caixas", []))
        self.combo_cor.set_values(dominios.get("cores", []))
        self.combo_estado.set_values(dominios.get("estados_fisicos", []))
        self.combo_condicao.set_values(dominios.get("condicoes", []))
        self.combo_acesso.set_values(dominios.get("acessos", []))

        # Renderizar avarias
        for widget in self.frame_avarias.winfo_children():
            widget.destroy()
        self.vars_avarias.clear()
        self.widgets_avarias.clear()

        for avaria in dominios.get("avarias", []):
            var = ctk.StringVar(value="")
            chk = ctk.CTkCheckBox(
                self.frame_avarias, text=avaria,
                variable=var, onvalue=avaria, offvalue="",
                font=ctk.CTkFont("Segoe UI", 13),
                command=self._ao_clicar_avaria
            )
            chk.pack(anchor="w", pady=4)
            self.vars_avarias[avaria] = var
            self.widgets_avarias[avaria] = chk

    def _ao_clicar_avaria(self):
        # Se estiver no modo "só marcadas", ao desmarcar o item some na hora
        if self.var_mostrar_selecionadas.get():
            self._filtrar_avarias()

    def _filtrar_avarias(self, event=None):
        termo = self.input_busca_avaria.get()
        termo_norm = unicodedata.normalize('NFKD', termo).encode('ASCII', 'ignore').decode('utf-8').lower()
        so_marcadas = self.var_mostrar_selecionadas.get()

        for avaria, chk in self.widgets_avarias.items():
            var_associada = self.vars_avarias[avaria]
            
            # Filtro principal: ver só as marcadas
            if so_marcadas and var_associada.get() == "":
                chk.pack_forget()
                continue

            avaria_norm = unicodedata.normalize('NFKD', avaria).encode('ASCII', 'ignore').decode('utf-8').lower()

            if not termo_norm:
                chk.pack(anchor="w", pady=4)
                continue

            if termo_norm in avaria_norm:
                chk.pack(anchor="w", pady=4)
            else:
                match_aproximado = False
                for palavra in avaria_norm.split():
                    if difflib.SequenceMatcher(None, termo_norm, palavra).ratio() > 0.7:
                        match_aproximado = True
                        break

                if match_aproximado:
                    chk.pack(anchor="w", pady=4)
                else:
                    chk.pack_forget()

    def obter_avarias_selecionadas(self) -> list:
        """Retorna lista de nomes de avarias marcadas."""
        return [var.get() for var in self.vars_avarias.values() if var.get() != ""]

    def limpar(self):
        self.input_qnt_chips.delete(0, 'end')
        self.input_chips_inst.delete(0, 'end')
        self.input_obs.clear()
        self.input_peso.delete(0, 'end')

        self.combo_estado.set("")
        self.combo_condicao.set("")
        self.combo_cor.set("")
        self.combo_acesso.set("")
        self.combo_caixa.set("")

        for var in self.vars_avarias.values():
            var.set("")

    def obter_dados(self) -> dict:
        """Retorna todos os dados de inspeção como dicionário."""
        return {
            "id_tecnico": self.input_id_tecnico.get(),
            "caixa": self.combo_caixa.get(),
            "cor": self.combo_cor.get(),
            "qnt_chips": self.input_qnt_chips.get(),
            "chips_inst": self.input_chips_inst.get(),
            "peso": self.input_peso.get(),
            "estado": self.combo_estado.get(),
            "condicao": self.combo_condicao.get(),
            "acesso": self.combo_acesso.get(),
            "obs": self.input_obs.get(),
            "avarias": self.obter_avarias_selecionadas(),
        }
