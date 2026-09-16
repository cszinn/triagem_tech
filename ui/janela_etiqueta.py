"""
ui/janela_etiqueta.py — Toplevel para editar/exportar etiquetas existentes.
"""

import os
import re
import threading
import customtkinter as ctk

from servicos import api_client
from servicos.impressao import construir_imagem_etiqueta, imprimir_imagem_win32, WIN32_DISPONIVEL


class JanelaEtiqueta(ctk.CTkToplevel):
    """Janela modal para buscar, editar e reimprimir etiquetas antigas."""

    def __init__(self, master, cfg, avarias_conhecidas=None, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Editar / Exportar Etiqueta Antiga")
        self.geometry("700x800")
        self.attributes("-topmost", True)
        self.focus_force()

        self._cfg = cfg
        self._etiqueta_em_edicao = None

        # --- Busca ---
        frame_busca = ctk.CTkFrame(self)
        frame_busca.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(frame_busca, text="ID da Etiqueta (ex: 100):").pack(side="left", padx=10)
        self._entry_id = ctk.CTkEntry(frame_busca, width=150)
        self._entry_id.pack(side="left", padx=10)

        btn_buscar = ctk.CTkButton(frame_busca, text="Buscar", width=100,
                                    command=self._buscar_dados)
        btn_buscar.pack(side="left", padx=10)

        self._lbl_status = ctk.CTkLabel(frame_busca, text="", text_color="yellow")
        self._lbl_status.pack(side="left", padx=10)

        # --- Formulário ---
        form_scroll = ctk.CTkScrollableFrame(self)
        form_scroll.pack(fill="both", expand=True, padx=20, pady=5)

        ctk.CTkLabel(form_scroll, text="Dados do Aparelho (Leitura/Hardware)",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5), anchor="w")

        def campo(parent, texto):
            ctk.CTkLabel(parent, text=texto).pack(anchor="w", pady=(5, 0))
            e = ctk.CTkEntry(parent)
            e.pack(fill="x", pady=(0, 5))
            return e

        self._e_marca = campo(form_scroll, "Marca:")
        self._e_modelo = campo(form_scroll, "Nome Comercial:")
        self._e_modelo_fisico = campo(form_scroll, "Modelo Físico (Hardware ID):")

        frame_arm = ctk.CTkFrame(form_scroll, fg_color="transparent")
        frame_arm.pack(fill="x", pady=(2, 0))
        frame_arm.grid_columnconfigure(0, weight=1)
        frame_arm.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame_arm, text="Armazenamento:").grid(row=0, column=0, sticky="w")
        self._e_arm = ctk.CTkEntry(frame_arm)
        self._e_arm.grid(row=1, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkLabel(frame_arm, text="Memória RAM:").grid(row=0, column=1, sticky="w")
        self._e_ram = ctk.CTkEntry(frame_arm)
        self._e_ram.grid(row=1, column=1, sticky="ew", padx=(5, 0))

        self._e_imei = campo(form_scroll, "IMEI 1:")
        self._e_imei2 = campo(form_scroll, "IMEI 2:")
        self._e_meid = campo(form_scroll, "MEID:")
        self._e_serie = campo(form_scroll, "Número de Série:")

        ctk.CTkLabel(form_scroll, text="Inspeção Física",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 5), anchor="w")

        self._e_tecnico = campo(form_scroll, "ID Responsável Técnico:")
        self._e_caixa = campo(form_scroll, "Caixa de Recebimento:")
        self._e_cor = campo(form_scroll, "Cor do Aparelho:")

        frame_chips = ctk.CTkFrame(form_scroll, fg_color="transparent")
        frame_chips.pack(fill="x", pady=(5, 5))
        frame_chips.grid_columnconfigure(0, weight=1)
        frame_chips.grid_columnconfigure(1, weight=1)
        frame_chips.grid_columnconfigure(2, weight=1)
        ctk.CTkLabel(frame_chips, text="Chips Aceit.:").grid(row=0, column=0, sticky="w")
        self._e_chips_aceitos = ctk.CTkEntry(frame_chips)
        self._e_chips_aceitos.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkLabel(frame_chips, text="Chips Inst.:").grid(row=0, column=1, sticky="w")
        self._e_chips_inst = ctk.CTkEntry(frame_chips)
        self._e_chips_inst.grid(row=1, column=1, sticky="ew", padx=(4, 4))
        ctk.CTkLabel(frame_chips, text="Peso (g):").grid(row=0, column=2, sticky="w")
        self._e_peso = ctk.CTkEntry(frame_chips)
        self._e_peso.grid(row=1, column=2, sticky="ew", padx=(4, 0))

        self._e_estado = campo(form_scroll, "Estado Físico:")

        frame_ca = ctk.CTkFrame(form_scroll, fg_color="transparent")
        frame_ca.pack(fill="x", pady=(5, 5))
        frame_ca.grid_columnconfigure(0, weight=1)
        frame_ca.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame_ca, text="Condição de Func.:").grid(row=0, column=0, sticky="w")
        self._e_condicao = ctk.CTkEntry(frame_ca)
        self._e_condicao.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkLabel(frame_ca, text="Estado de Acesso:").grid(row=0, column=1, sticky="w")
        self._e_acesso = ctk.CTkEntry(frame_ca)
        self._e_acesso.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        self._e_obs = campo(form_scroll, "Observações Adicionais:")

        # Avarias
        ctk.CTkLabel(form_scroll, text="Avarias Identificadas:").pack(anchor="w", pady=(10, 0))
        self._frame_avarias = ctk.CTkScrollableFrame(form_scroll, height=100)
        self._frame_avarias.pack(fill="x", pady=(0, 5))

        self._vars_avarias = {}
        if avarias_conhecidas:
            for avaria in avarias_conhecidas:
                var = ctk.StringVar(value="")
                chk = ctk.CTkCheckBox(self._frame_avarias, text=avaria,
                                       variable=var, onvalue=avaria, offvalue="")
                chk.pack(anchor="w", pady=2)
                self._vars_avarias[avaria] = var

        # --- Botões de ação ---
        frame_actions = ctk.CTkFrame(self, fg_color="transparent")
        frame_actions.pack(fill="x", padx=20, pady=20)

        btn_salvar = ctk.CTkButton(frame_actions, text="Salvar Alterações",
                                    fg_color="green", hover_color="darkgreen",
                                    command=self._salvar_alteracoes)
        btn_salvar.pack(side="left", expand=True, padx=10)

        btn_imprimir = ctk.CTkButton(frame_actions, text="Imprimir Etiqueta",
                                      fg_color="#1f6aa5", hover_color="#144870",
                                      command=self._imprimir_agora)
        btn_imprimir.pack(side="left", expand=True, padx=10)

    def _preencher(self, entry, valor):
        entry.delete(0, 'end')
        if valor is not None:
            entry.insert(0, str(valor))

    def _buscar_dados(self):
        texto_id = self._entry_id.get().strip()
        match = re.search(r'\d+', texto_id)
        if not match:
            self._lbl_status.configure(text="ID inválido.", text_color="red")
            return

        id_num = int(match.group())
        self._lbl_status.configure(text="Buscando...", text_color="yellow")

        def request_thread():
            try:
                dados = api_client.buscar_triagem(self._cfg["api_url"], id_num)
                self._etiqueta_em_edicao = dados

                def update_ui():
                    self._preencher(self._e_marca, dados.get("marca", ""))
                    self._preencher(self._e_modelo, dados.get("modelo", ""))
                    self._preencher(self._e_modelo_fisico, dados.get("modeloFisico", ""))
                    self._preencher(self._e_arm, dados.get("capacidadeArmazenamentoGb", ""))
                    self._preencher(self._e_ram, dados.get("capacidadeRamGb", ""))
                    self._preencher(self._e_imei, dados.get("imei1", ""))
                    self._preencher(self._e_imei2, dados.get("imei2", ""))
                    self._preencher(self._e_meid, dados.get("meid", ""))
                    self._preencher(self._e_serie, dados.get("numeroSerie", ""))
                    self._preencher(self._e_tecnico, dados.get("idResponsavelTecnico", ""))
                    self._preencher(self._e_caixa, dados.get("caixaRecebimento", ""))
                    self._preencher(self._e_cor, dados.get("cor", ""))
                    self._preencher(self._e_chips_aceitos, dados.get("qtdChipsAceitos", ""))
                    self._preencher(self._e_chips_inst, dados.get("qtdChipsInstalados", ""))
                    self._preencher(self._e_peso, dados.get("pesoGramas", ""))
                    self._preencher(self._e_estado, dados.get("estadoFisico", ""))
                    self._preencher(self._e_condicao, dados.get("condicaoFuncionamento", ""))
                    self._preencher(self._e_acesso, dados.get("estadoAcesso", ""))
                    self._preencher(self._e_obs, dados.get("observacoes", ""))

                    for var in self._vars_avarias.values():
                        var.set("")
                    avs = dados.get("avarias", [])
                    if isinstance(avs, list):
                        for av in avs:
                            if av in self._vars_avarias:
                                self._vars_avarias[av].set(av)
                            else:
                                var = ctk.StringVar(value=av)
                                chk = ctk.CTkCheckBox(self._frame_avarias, text=av,
                                                       variable=var, onvalue=av, offvalue="")
                                chk.pack(anchor="w", pady=2)
                                self._vars_avarias[av] = var

                    self._lbl_status.configure(text="Encontrado!", text_color="#00FF00")

                self.after(0, update_ui)
            except Exception as e:
                self.after(0, lambda msg=str(e): self._lbl_status.configure(
                    text=msg if len(msg) < 80 else msg[:80] + "...", text_color="red"))

        threading.Thread(target=request_thread, daemon=True).start()

    def _salvar_alteracoes(self):
        if not self._etiqueta_em_edicao:
            self._lbl_status.configure(text="Busque um ID primeiro.", text_color="red")
            return

        texto_id = self._entry_id.get().strip()
        match = re.search(r'\d+', texto_id)
        id_num = int(match.group())

        def int_or_none(valor):
            try:
                return int(valor) if valor.strip() else None
            except ValueError:
                return None

        avarias_selecionadas = [{"nome": var.get()} for var in self._vars_avarias.values() if var.get() != ""]

        payload = {
            "id": id_num,
            "caixaRecebimento": {"nome": self._e_caixa.get().strip()},
            "modelo": {
                "marca": {"nome": self._e_marca.get().strip()},
                "tipoEquipamento": {"nome": "Smartphone"},
                "modelo": {"nome": self._e_modelo.get().strip()},
                "modeloFisico": {"nome": self._e_modelo_fisico.get().strip()},
            },
            "numeroSerie": self._e_serie.get().strip(),
            "idResponsavelTecnico": int_or_none(self._e_tecnico.get()),
            "imei1": self._e_imei.get().strip(),
            "imei2": self._e_imei2.get().strip(),
            "meid": self._e_meid.get().strip(),
            "eid": "",
            "capacidadeArmazenamentoGb": int_or_none(self._e_arm.get()),
            "capacidadeRamGb": int_or_none(self._e_ram.get()),
            "cor": {"nome": self._e_cor.get().strip()},
            "qtdChipsInstalados": int_or_none(self._e_chips_inst.get()),
            "qtdChipsAceitos": int_or_none(self._e_chips_aceitos.get()),
            "pesoGramas": int_or_none(self._e_peso.get()),
            "estadoFisico": {"nome": self._e_estado.get().strip()},
            "condicaoFuncionamento": {"nome": self._e_condicao.get().strip()},
            "estadoAcesso": {"nome": self._e_acesso.get().strip()},
            "observacoes": self._e_obs.get().strip(),
            "avarias": avarias_selecionadas,
        }

        self._lbl_status.configure(text="Salvando...", text_color="yellow")

        def request_thread():
            try:
                api_client.atualizar_triagem(self._cfg["api_url"], id_num, payload)
                self.after(0, lambda: self._lbl_status.configure(
                    text="Alterações salvas!", text_color="#00FF00"))
            except Exception as e:
                self.after(0, lambda msg=str(e): self._lbl_status.configure(
                    text=f"Erro: {msg}" if len(msg) < 80 else f"Erro: {msg[:80]}...", text_color="red"))

        threading.Thread(target=request_thread, daemon=True).start()

    def _imprimir_agora(self):
        if not self._etiqueta_em_edicao:
            self._lbl_status.configure(text="Busque um ID primeiro.", text_color="red")
            return

        texto_id = self._entry_id.get().strip()
        match = re.search(r'\d+', texto_id)
        id_num = match.group()
        patrimonio = f"ITI TECH-{int(id_num):03d}"
        escala = float(self._cfg.get("escala_conteudo", 1.0))

        img_etiqueta = construir_imagem_etiqueta(
            id_telefone=id_num,
            patrimonio=patrimonio,
            marca=self._e_marca.get(),
            modelo=self._e_modelo.get(),
            arm=self._e_arm.get(),
            serie=self._e_serie.get(),
            estado=self._e_estado.get(),
            escala=escala
        )

        os.makedirs("etiquetas", exist_ok=True)
        arquivo_png = os.path.join("etiquetas", f"etiqueta_{patrimonio}.png")
        img_etiqueta.save(arquivo_png, dpi=(203, 203))

        if WIN32_DISPONIVEL:
            try:
                imprimir_imagem_win32(img_etiqueta, self._cfg["impressora"], patrimonio, self._cfg)
                self._lbl_status.configure(text="Etiqueta impressa!", text_color="#00FF00")
            except Exception as e:
                self._lbl_status.configure(
                    text=f"Salvo em {arquivo_png}, falha: {e}", text_color="orange")
        else:
            self._lbl_status.configure(
                text=f"Salvo em {arquivo_png} (impressão manual)", text_color="orange")
