"""
painel_triagem.py — Sistema de Triagem v2.0
Janela principal que integra todos os painéis e serviços.
"""

import threading
import os
import re
import customtkinter as ctk
from autocorrect import Speller

import config as cfg_module
from motores import ios, android, fastboot, radar_usb
from servicos import api_client
from servicos.impressao import (
    construir_imagem_etiqueta, imprimir_imagem_win32,
    WIN32_DISPONIVEL, listar_impressoras
)
from ui.painel_hardware import PainelHardware
from ui.painel_inspecao import PainelInspecao
from ui.painel_log import PainelLog
from ui.barra_acoes import BarraAcoes
from ui.janela_etiqueta import JanelaEtiqueta

# Configuração do Tema Visual
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Corretor ortográfico (carrega em background)
corretor_pt = lambda x: x

def _inicializar_speller():
    global corretor_pt
    try:
        s = Speller(lang='pt')
        corretor_pt = s
    except Exception:
        pass

threading.Thread(target=_inicializar_speller, daemon=True).start()


class SistemaTriagem(ctk.CTk):

    def __init__(self):
        super().__init__()

        self._cfg = cfg_module.carregar()
        self.title(self._cfg["app_titulo"])
        self.geometry(self._cfg["app_geometria"])
        self.after(100, lambda: self.state("zoomed"))

        # Layout principal: 3 colunas
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Cabeçalho ---
        self._criar_cabecalho()

        # --- Painéis ---
        self.painel_hw = PainelHardware(
            self,
            callbacks={
                "ler_ios": self._iniciar_leitura_ios,
                "ler_android": self._iniciar_leitura_android,
                "ler_fastboot": self._iniciar_leitura_fastboot,
                "marca_selecionada": self._carregar_modelos,
                "modelo_selecionado": self._carregar_modelos_fisicos,
                "modo_manual": self._alternar_modo_manual,
            }
        )
        self.painel_hw.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        self.painel_insp = PainelInspecao(
            self,
            callbacks={
                "cadastrar_avaria": self._cadastrar_nova_avaria,
            }
        )
        self.painel_insp.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")

        self.painel_log = PainelLog(self)
        self.painel_log.grid(row=2, column=2, rowspan=2, padx=10, pady=5, sticky="nsew")

        # --- Rodapé ---
        self.barra = BarraAcoes(
            self,
            patrimonio_num=self._cfg.get("patrimonio_num", 10),
            callbacks={
                "limpar": self._limpar_tela,
                "copiar_excel": self._exportar_para_clipboard,
                "salvar_api": self._enviar_para_api,
                "editar_etiqueta": self._abrir_janela_editar_etiqueta,
                "calibrar": self._abrir_calibracao,
            }
        )
        self.barra.grid(row=3, column=0, columnspan=2, sticky="ew")

        # --- Atalhos de teclado ---
        self._configurar_atalhos()

        # --- Inicialização ---
        self._status("Sistema iniciado. Aguardando conexão USB.", "gray")
        self._iniciar_radar_usb()
        self._carregar_dominios()

    # =================================================================
    #  CABEÇALHO
    # =================================================================
    def _criar_cabecalho(self):
        try:
            from PIL import Image
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_hq_cropped.png")
            logo_img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(312, 80)
            )
            self.lbl_titulo = ctk.CTkLabel(self, image=logo_img, text="")
        except Exception:
            self.lbl_titulo = ctk.CTkLabel(
                self, text="Auditoria e Triagem de Dispositivos",
                font=ctk.CTkFont(size=24, weight="bold")
            )
        self.lbl_titulo.grid(row=0, column=0, columnspan=3, pady=(15, 5))

        self.lbl_status = ctk.CTkLabel(
            self, text="Inicializando motor de triagem...",
            text_color="gray", font=ctk.CTkFont(size=14)
        )
        self.lbl_status.grid(row=1, column=0, columnspan=3, pady=(0, 10))

        # Botão atualizar listas (canto superior direito)
        self.btn_atualizar = ctk.CTkButton(
            self, text="🔄 Atualizar Listas", width=140, height=32,
            fg_color="#444444", hover_color="#555555",
            font=ctk.CTkFont(weight="bold"),
            command=self._carregar_dominios
        )
        self.btn_atualizar.place(relx=0.98, rely=0.02, anchor="ne")

        # Botão voltar ao hub (canto superior esquerdo)
        self.btn_sair = ctk.CTkButton(
            self, text="🔙 Voltar ao Hub", width=140, height=32,
            fg_color="#8A1111", hover_color="#5C0B0B",
            font=ctk.CTkFont(weight="bold"),
            command=self.destroy
        )
        self.btn_sair.place(relx=0.02, rely=0.02, anchor="nw")

        self.bind("<F5>", lambda e: self._carregar_dominios())

    # =================================================================
    #  STATUS / LOG
    # =================================================================
    def _status(self, mensagem, cor="gray"):
        """Atualiza a barra de status e registra no log."""
        self.lbl_status.configure(text=mensagem, text_color=cor)
        self.painel_log.adicionar(mensagem)

    def _status_thread(self, mensagem, cor="gray"):
        """Versão thread-safe do _status — usa self.after()."""
        self.after(0, lambda: self._status(mensagem, cor))

    # =================================================================
    #  RADAR USB
    # =================================================================
    def _iniciar_radar_usb(self):
        threading.Thread(
            target=radar_usb.monitorar,
            args=(self._status_thread,),
            daemon=True
        ).start()

    # =================================================================
    #  LEITURA DE DISPOSITIVOS
    # =================================================================
    def _iniciar_leitura_ios(self):
        self._status("Iniciando varredura profunda no iOS...", "yellow")
        threading.Thread(target=self._extrair_ios, daemon=True).start()

    def _extrair_ios(self):
        try:
            self._status_thread("Extraindo dicionário de Hardware (Dump Completo)...", "yellow")
            dados = ios.extrair()
            self._status_thread("Calculando capacidade de disco rígido...", "yellow")
            self.after(0, lambda: self.painel_hw.preencher_dados(dados))
            self._status_thread("Leitura concluída com sucesso.", "#00FF00")
        except FileNotFoundError:
            self._status_thread("Falha Crítica: Motor ideviceinfo ausente no PATH.", "red")
        except Exception:
            self._status_thread("Falha de Comunicação: Dispositivo bloqueado ou cabo com defeito.", "red")

    def _iniciar_leitura_android(self):
        self._status("Iniciando requisição de interface ADB...", "yellow")
        threading.Thread(target=self._extrair_android, daemon=True).start()

    def _extrair_android(self):
        try:
            self._status_thread("Acessando propriedades do sistema (getprop)...", "yellow")
            dados = android.extrair()

            if dados.get("imei_encontrado"):
                status_msg = f"Leitura ADB concluída: {dados['marca']} {dados['modelo']}"
                cor = "#00FF00"
            else:
                status_msg = f"Leitura parcial ({dados['marca']} {dados['modelo']}): IMEI bloqueado pelo Android 10+"
                cor = "yellow"

            self.after(0, lambda: self.painel_hw.preencher_dados(dados))
            self._status_thread(status_msg, cor)
        except Exception:
            self._status_thread("Falha de Comunicação: Aparelho offline ou Depuração desligada.", "red")

    def _iniciar_leitura_fastboot(self):
        self._status("Iniciando requisição Fastboot...", "yellow")
        threading.Thread(target=self._extrair_fastboot, daemon=True).start()

    def _extrair_fastboot(self):
        try:
            self._status_thread("Acessando variáveis de hardware (fastboot getvar all)...", "yellow")
            dados = fastboot.extrair()

            if dados.get("imei_encontrado"):
                self._status_thread("Leitura Fastboot concluída com sucesso.", "#00FF00")
            else:
                self._status_thread("Leitura Fastboot concluída, mas sem IMEI no log.", "yellow")

            self.after(0, lambda: self.painel_hw.preencher_dados(dados))
        except FileNotFoundError:
            self._status_thread("Falha Crítica: fastboot.exe ausente na pasta platform-tools.", "red")
        except ConnectionError as e:
            self._status_thread(str(e), "red")
        except Exception:
            self._status_thread("Falha de Comunicação Fastboot.", "red")

    # =================================================================
    #  MODO MANUAL
    # =================================================================
    def _alternar_modo_manual(self, ativado: bool):
        self.painel_hw.set_modo_manual(ativado)
        if ativado:
            self._status("Modo Manual: Identificadores liberados para leitor de código.", "yellow")
            self.painel_hw.campo_marca.focus()
        else:
            self._status("Modo Manual Desativado. Todos os campos blindados.", "gray")

    # =================================================================
    #  CARREGAR DADOS DA API
    # =================================================================
    def _carregar_dominios(self):
        self._status("Carregando domínios da API...", "yellow")

        def request():
            try:
                dominios = api_client.carregar_dominios(self._cfg["api_url"])
                self.after(0, lambda: self._aplicar_dominios(dominios))
                self._status_thread("Domínios carregados com sucesso.", "gray")
            except Exception as e:
                self._status_thread(f"Aviso: Falha ao carregar domínios da API. Erro: {e}", "red")

        threading.Thread(target=request, daemon=True).start()

    def _aplicar_dominios(self, dominios: dict):
        """Aplica os domínios a todos os painéis."""
        self.painel_hw.campo_marca.set_values(dominios.get("marcas", []))
        self.painel_hw.campo_nome_comercial.set_values(dominios.get("modelos", []))
        self.painel_insp.popular_dominios(dominios)

    def _carregar_modelos(self, marca):
        if not marca or marca == "Carregando...":
            return
        self._status(f"Buscando modelos para a marca: {marca}...", "yellow")

        def request():
            try:
                modelos = api_client.carregar_modelos(self._cfg["api_url"], marca)
                if not modelos:
                    modelos = [""]
                self.after(0, lambda: self.painel_hw.campo_nome_comercial.set_values(modelos))
                self._status_thread(f"Modelos de {marca} carregados.", "gray")
            except Exception as e:
                print(f"Erro ao buscar modelos: {e}")
                self.after(0, lambda: self.painel_hw.campo_nome_comercial.set_values([""]))

        threading.Thread(target=request, daemon=True).start()

    def _carregar_modelos_fisicos(self, modelo):
        if not modelo or modelo == "Selecione uma Marca":
            return
        self._status(f"Buscando modelos físicos para: {modelo}...", "yellow")

        # --- Inferir Quantidade de Chips Aceitos ---
        marca = self.painel_hw.campo_marca.get().lower()
        modelo_lower = modelo.lower()
        qnt_chips = "2"  # Padrão para quase todos os smartphones modernos (Físico + eSIM)

        if "apple" in marca:
            # Modelos antigos da Apple que só suportam 1 chip (antes do iPhone XR/XS que trouxeram eSIM)
            # O iPhone X original também só tinha 1 chip, mas para manter a regra que você pediu (do X pra cima = 2):
            antigos = ["iphone 5", "iphone 6", "iphone 7", "iphone 8", "iphone se (1", "iphone se 1"]
            if any(antigo in modelo_lower for antigo in antigos):
                qnt_chips = "1"
        
        self.painel_insp.input_qnt_chips.delete(0, 'end')
        self.painel_insp.input_qnt_chips.insert(0, qnt_chips)
        # -------------------------------------------

        def request():
            try:
                modelos_fisicos = api_client.carregar_modelos_fisicos(self._cfg["api_url"], modelo)
                
                # Limpa sujeiras do banco de dados
                modelos_limpos = [m for m in modelos_fisicos if m.strip().upper() not in ("", "N/A", "CARREGANDO...")]
                
                if not modelos_limpos:
                    modelos_limpos = ["N/A"]
                    
                self.after(0, lambda: self.painel_hw.campo_modelo.set_values(modelos_limpos))
                
                # Para agilizar o Modo Manual, vamos sempre auto-selecionar o primeiro modelo físico válido
                # (ex: se tiver iPhone9,2 e iPhone9,4, ele preenche o primeiro sozinho sem travar o usuário)
                self.after(0, lambda: self.painel_hw.campo_modelo.set(modelos_limpos[0]))
                
                self._status_thread("Modelos físicos carregados.", "gray")
            except Exception as e:
                print(f"Erro ao buscar modelos físicos: {e}")
                self.after(0, lambda: self.painel_hw.campo_modelo.set_values(["N/A"]))

        threading.Thread(target=request, daemon=True).start()

    # =================================================================
    #  LIMPAR CAMPOS
    # =================================================================
    def _limpar_tela(self):
        self.painel_hw.limpar()
        self.painel_insp.limpar()
        self._status("Painel de digitação e extração limpo.", "gray")

    # =================================================================
    #  EXPORTAR PARA EXCEL
    # =================================================================
    def _exportar_para_clipboard(self):
        hw = self.painel_hw.obter_dados()
        insp = self.painel_insp.obter_dados()

        tipo = "CELULAR"
        marca = hw["marca"].upper()
        modelo = hw["modelo"].upper()
        nome_comercial = hw["nome_comercial"].upper()
        cor = insp["cor"].upper()
        imei1 = hw["imei1"]
        imei2 = hw["imei2"]

        meid = hw["meid"]
        serie = hw["serie"].upper()
        qnt_chips = insp["qnt_chips"]
        chips_inst = insp["chips_inst"]
        estado = insp["estado"].upper()

        # Avarias selecionadas
        avarias_selecionadas = [a.upper() for a in insp["avarias"]]
        texto_avarias = ", ".join(avarias_selecionadas)

        # Observações com autocorreção
        obs_crua = insp["obs"].lower()
        if obs_crua.strip():
            dicionario_triagem = {
                "arranhoes": "arranhões", "arranhao": "arranhão",
                "carcaca": "carcaça", "botao": "botão", "botoes": "botões",
                "camera": "câmera", "modulo": "módulo", "avaria": "avaria"
            }
            for errado, certo in dicionario_triagem.items():
                obs_crua = obs_crua.replace(errado, certo)
            obs_formatada = corretor_pt(obs_crua).upper()
        else:
            obs_formatada = ""

        obs_final = texto_avarias
        if obs_formatada:
            obs_final = f"{texto_avarias} - {obs_formatada}" if texto_avarias else obs_formatada

        condicao = insp["condicao"].upper()
        peso = insp["peso"]

        linha = f"{tipo}\t{marca}\t{modelo}\t{nome_comercial}\t{cor}\t{imei1}\t{imei2}\t{meid}\t\t{serie}\t{qnt_chips}\t{chips_inst}\t{estado}\t{obs_final}\t{condicao}\t{peso}"

        self.clipboard_clear()
        self.clipboard_append(linha)
        self._status(f"Dados exportados p/ Excel ({modelo})", "#00FF00")

    # =================================================================
    #  SALVAR NA API
    # =================================================================
    def _enviar_para_api(self):
        self._status("Enviando dados para a API...", "yellow")
        hw = self.painel_hw.obter_dados()
        insp = self.painel_insp.obter_dados()

        peso_match = re.search(r'\d+', insp["peso"])
        peso = int(peso_match.group()) if peso_match else 0

        arm_match = re.search(r'\d+', hw["armazenamento"])
        capacidade = int(arm_match.group()) if arm_match else 0

        chips_inst = int(insp["chips_inst"]) if insp["chips_inst"].isdigit() else 0
        chips_aceitos = int(insp["qnt_chips"]) if insp["qnt_chips"].isdigit() else 0

        avarias_lista = [{"nome": a} for a in insp["avarias"]]

        ram_match = re.search(r'\d+', hw["ram"])
        capacidade_ram = int(ram_match.group()) if ram_match else None

        id_tecnico_texto = insp["id_tecnico"].strip()
        id_responsavel = int(id_tecnico_texto) if id_tecnico_texto.isdigit() else 1

        def limpar_id(valor):
            texto = valor.strip()
            return "" if texto == "N/A" else texto

        payload = {
            "caixaRecebimento": {"nome": insp["caixa"]},
            "modelo": {
                "marca": {"nome": hw["marca"]},
                "tipoEquipamento": {"nome": "Smartphone"},
                "modelo": {"nome": hw["nome_comercial"]},
                "modeloFisico": {"nome": hw["modelo"]},
            },
            "numeroSerie": limpar_id(hw["serie"]),
            "idResponsavelTecnico": id_responsavel,
            "imei1": limpar_id(hw["imei1"]),
            "imei2": limpar_id(hw["imei2"]),
            "meid": limpar_id(hw["meid"]),
            "eid": "",
            "capacidadeArmazenamentoGb": capacidade,
            "capacidadeRamGb": capacidade_ram,
            "cor": {"nome": insp["cor"]},
            "qtdChipsInstalados": chips_inst,
            "qtdChipsAceitos": chips_aceitos,
            "estadoFisico": {"nome": insp["estado"]},
            "estadoAcesso": {"nome": insp["acesso"]},
            "condicaoFuncionamento": {"nome": insp["condicao"]},
            "avarias": avarias_lista,
            "pesoGramas": peso,
            "observacoes": insp["obs"],
        }

        def request():
            try:
                dados = api_client.salvar_triagem(self._cfg["api_url"], payload)
                id_estoque = dados.get("idItemEstoque")

                def sucesso():
                    self._status(f"Triagem Salva! ID Estoque: {id_estoque}. Gerando etiqueta...", "#00FF00")
                    self.barra.patrimonio_num = int(id_estoque)
                    self._gerar_etiqueta()

                self.after(0, sucesso)
            except Exception as e:
                self._status_thread(f"Erro na API: {e}", "red")

        threading.Thread(target=request, daemon=True).start()

    # =================================================================
    #  ETIQUETA
    # =================================================================
    def _gerar_etiqueta(self):
        hw = self.painel_hw.obter_dados()
        imei = hw["imei1"].strip()
        if not imei or imei == "N/A":
            self._status("Erro: É necessário um IMEI válido para gerar a etiqueta.", "red")
            return

        patrimonio = self.barra.get_patrimonio_texto()
        escala = float(self._cfg.get("escala_conteudo", 1.0))

        img = construir_imagem_etiqueta(
            id_telefone=self.barra.patrimonio_num,
            patrimonio=patrimonio,
            marca=hw["marca"],
            modelo=hw["nome_comercial"],
            arm=hw["armazenamento"],
            serie=hw["serie"],
            estado=self.painel_insp.combo_estado.get(),
            escala=escala
        )

        os.makedirs("etiquetas", exist_ok=True)
        nome_base = patrimonio.replace(" ", "_").replace("-", "_")
        arquivo_png = os.path.join("etiquetas", f"{nome_base}.png")
        img.save(arquivo_png, dpi=(203, 203))

        nome_impressora = self._cfg["impressora"]
        if WIN32_DISPONIVEL:
            threading.Thread(
                target=self._imprimir_thread,
                args=(img, nome_impressora, patrimonio),
                daemon=True
            ).start()
        else:
            self._status("win32print não disponível — abra o PNG e imprima manualmente.", "yellow")
            os.startfile(arquivo_png)

    def _imprimir_thread(self, img, nome_impressora, patrimonio):
        try:
            imprimir_imagem_win32(img, nome_impressora, patrimonio, self._cfg)
            self._status_thread(f"Etiqueta [{patrimonio}] enviada para impressora!", "#00FF00")
            self.after(0, lambda: setattr(self.barra, 'patrimonio_num', self.barra.patrimonio_num + 1))
        except Exception as e:
            self._status_thread(f"Erro ao imprimir: {e}", "red")

    def _abrir_janela_editar_etiqueta(self):
        avarias = list(self.painel_insp.vars_avarias.keys())
        JanelaEtiqueta(self, self._cfg, avarias_conhecidas=avarias)

    # =================================================================
    #  CALIBRAÇÃO
    # =================================================================
    def _abrir_calibracao(self):
        win = ctk.CTkToplevel(self)
        win.title("⚙  Calibrar Impressão Térmica")
        win.geometry("460x460")
        win.resizable(False, False)
        win.grab_set()

        ctk.CTkLabel(win, text="Calibrar Dimensões da Etiqueta",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(18, 4))
        ctk.CTkLabel(win,
            text="Ajuste os valores abaixo até a etiqueta sair no tamanho correto.\n"
                 "Salve e teste até ficar perfeito.",
            text_color="gray", font=ctk.CTkFont(size=12)).pack(pady=(0, 14))

        frame = ctk.CTkFrame(win)
        frame.pack(fill="x", padx=30)

        def campo(label, valor_atual):
            row = ctk.CTkFrame(frame)
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=180, anchor="w").pack(side="left")
            e = ctk.CTkEntry(row, width=150, justify="center")
            e.insert(0, str(valor_atual))
            e.pack(side="left", padx=8)
            return e

        e_impressora = campo("Nome da impressora:", self._cfg["impressora"])
        e_largura = campo("Largura da etiqueta (mm):", self._cfg["largura_mm"])
        e_altura = campo("Altura da etiqueta (mm):", self._cfg["altura_mm"])
        e_offset_x = campo("Ajuste Horizontal X (mm):", self._cfg.get("offset_x_mm", 0.0))
        e_offset_y = campo("Ajuste Vertical Y (mm):", self._cfg.get("offset_y_mm", 0.0))
        e_escala = campo("Escala Conteúdo (1.0 = 100%):", self._cfg.get("escala_conteudo", 1.0))

        if WIN32_DISPONIVEL:
            impressoras = listar_impressoras()
            if impressoras:
                ctk.CTkLabel(win,
                    text="Impressoras disponíveis: " + ", ".join(impressoras),
                    text_color="#888", font=ctk.CTkFont(size=10), wraplength=400
                ).pack(pady=(6, 0), padx=20)

        def salvar():
            try:
                self._cfg["impressora"] = e_impressora.get().strip()
                self._cfg["largura_mm"] = float(e_largura.get().replace(",", "."))
                self._cfg["altura_mm"] = float(e_altura.get().replace(",", "."))
                self._cfg["offset_x_mm"] = float(e_offset_x.get().replace(",", "."))
                self._cfg["offset_y_mm"] = float(e_offset_y.get().replace(",", "."))
                self._cfg["escala_conteudo"] = float(e_escala.get().replace(",", "."))
                cfg_module.salvar(self._cfg)
                self._status(
                    f"Config salva: {self._cfg['largura_mm']}x{self._cfg['altura_mm']} mm — "
                    f"Impressora: {self._cfg['impressora']}", "#00FF00")
                win.destroy()
            except ValueError:
                self._status("Valores inválidos — use números como 58.6 e 40.0", "red")

        ctk.CTkButton(win, text="💾  Salvar e Fechar", fg_color="#1f6aa5",
                      hover_color="#144870", command=salvar).pack(pady=18)

    # =================================================================
    #  CADASTRAR AVARIA
    # =================================================================
    def _cadastrar_nova_avaria(self):
        nova_avaria = self.painel_insp.input_busca_avaria.get().strip()
        if not nova_avaria:
            self._status("Aviso: Digite o nome da avaria no campo de pesquisa antes de adicionar.", "yellow")
            return

        self._status(f"Cadastrando nova avaria: '{nova_avaria}'...", "yellow")

        def request():
            try:
                api_client.cadastrar_avaria(self._cfg["api_url"], nova_avaria)
                self._status_thread(f"Avaria '{nova_avaria}' adicionada com sucesso!", "#00FF00")
                self.after(0, lambda: self.painel_insp.input_busca_avaria.delete(0, 'end'))
                self.after(0, self.painel_insp._filtrar_avarias)
                self.after(0, self._carregar_dominios)
            except Exception as e:
                self._status_thread(f"Erro ao cadastrar avaria: {e}", "red")

        threading.Thread(target=request, daemon=True).start()

    # =================================================================
    #  ATALHOS DE TECLADO
    # =================================================================
    def _configurar_atalhos(self):
        # Navegação entre campos de hardware (Enter avança)
        self.painel_hw.campo_imei1.bind_entry("<Return>", lambda e: self.painel_hw.campo_imei2.focus())
        self.painel_hw.campo_imei2.bind_entry("<Return>", lambda e: self.painel_hw.campo_meid.focus())
        self.painel_hw.campo_meid.bind_entry("<Return>", lambda e: self.painel_insp.combo_cor.focus())

        # Selecionar tudo ao focar nos campos de hardware
        campos_hw = [self.painel_hw.campo_imei1,
                     self.painel_hw.campo_imei2, self.painel_hw.campo_meid]
        for campo in campos_hw:
            campo.bind_entry("<FocusIn>", lambda e, c=campo: c._entry.after(10, lambda: c.select_all()))

        # Ctrl+P para imprimir
        self.bind("<Control-p>", lambda e: self._abrir_janela_editar_etiqueta())


if __name__ == "__main__":
    app = SistemaTriagem()
    app.mainloop()