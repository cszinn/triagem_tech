import customtkinter as ctk
import subprocess
import threading
import time
import os
import io
import json
import qrcode
import re
import unicodedata
import difflib


from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.graphics.barcode import code128
from autocorrect import Speller
from datetime import datetime
import requests 


# Impressão direta via Windows GDI
try:
    import win32print
    import win32ui
    import win32con
    import win32gui
    from PIL import ImageWin
    WIN32_DISPONIVEL = True
except ImportError:
    WIN32_DISPONIVEL = False

# Corretor ortográfico inicializado em background para não travar o app
corretor_pt = lambda x: x  # passthrough até o dicionário carregar

def _inicializar_speller():
    global corretor_pt
    try:
        s = Speller(lang='pt')
        corretor_pt = s
    except Exception:
        pass  # mantém o passthrough se falhar

threading.Thread(target=_inicializar_speller, daemon=True).start()


DIRETORIO_ATUAL = os.getcwd()
PASTA_TOOLS = os.path.join(DIRETORIO_ATUAL, "platform-tools")

# Define o caminho exato dos executáveis
CAMINHO_ADB = os.path.join(PASTA_TOOLS, "adb.exe")
CAMINHO_IDEVICEINFO = os.path.join(PASTA_TOOLS, "ideviceinfo.exe")
CAMINHO_IDEVICEID = os.path.join(PASTA_TOOLS, "idevice_id.exe")



# Configuração do Tema Visual
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
# ctk.deactivate_automatic_dpi_awareness()

class SistemaTriagem(ctk.CTk):
    
    # --- CONFIGURAÇÕES DE IMPRESSÃO ---
    
    _CONFIG_PATH = "config.json"
    # 1. Concentre TODAS as constantes aqui
    _CONFIG_PADRAO = {
        # Configurações da Impressora
        "impressora": "4BARCODE 4B-2054L",
        "largura_mm": 58.6,
        "altura_mm": 40.0,
        "offset_x_mm": 0.0,
        "offset_y_mm": 2.0,
        "patrimonio_num": 10,
        "escala_conteudo": 1.2,
        
        # Configurações de Rede / API
        "api_url": "https://useful-gecko-present.ngrok-free.app/api",
        
        # Configurações da Janela / UI
        "app_titulo": "Instituto ITI - Triagem Receita Federal",
        "app_geometria": "1920x1080"
    }
        
    def __init__(self):
        super().__init__()

        self._cfg = self._carregar_config()

        # 3. Aplica as configurações diretamente do dicionário
        self.title(self._cfg["app_titulo"])
        self.geometry(self._cfg["app_geometria"])
        self.after(100, lambda: self.state("zoomed"))
        # Número de patrimônio (recuperado do arquivo ou default 75)
        self._patrimonio_num = self._cfg.get("patrimonio_num", 75)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        self.criar_cabecalho()
        self.criar_painel_extracao()
        self.criar_painel_manual()
        self.criar_painel_log() 
        self.criar_rodape()
        
        self.configurar_atalhos()
        
        self.atualizar_status("Sistema iniciado. Aguardando conexão USB.", "gray")
        self.iniciar_radar_usb()
        self.carregar_dominios()

    def criar_cabecalho(self):
        try:
            from PIL import Image
            import os
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_hq_cropped.png")
            logo_img = ctk.CTkImage(light_image=Image.open(logo_path),
                                    dark_image=Image.open(logo_path),
                                    size=(312, 80))
            self.lbl_titulo = ctk.CTkLabel(self, image=logo_img, text="")
        except Exception as e:
            self.lbl_titulo = ctk.CTkLabel(self, text="Auditoria e Triagem de Dispositivos", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_titulo.grid(row=0, column=0, columnspan=3, pady=(15, 5))
        
        self.lbl_status = ctk.CTkLabel(self, text="Inicializando motor de triagem...", text_color="gray", font=ctk.CTkFont(size=14))
        self.lbl_status.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        self.btn_atualizar_dados = ctk.CTkButton(
            self, 
            text="🔄 Atualizar Listas", 
            width=140, 
            height=32,
            fg_color="#444444", 
            hover_color="#555555", 
            font=ctk.CTkFont(weight="bold"),
            command=self.carregar_dominios
        )
        self.btn_atualizar_dados.place(relx=0.98, rely=0.02, anchor="ne")
        
        self.btn_sair = ctk.CTkButton(
            self, 
            text="🔙 Voltar ao Hub", 
            width=140, 
            height=32,
            fg_color="#8A1111", 
            hover_color="#5C0B0B", 
            font=ctk.CTkFont(weight="bold"),
            command=self.destroy
        )
        self.btn_sair.place(relx=0.02, rely=0.02, anchor="nw")
        self.bind("<F5>", lambda e: self.carregar_dominios())
    
    def criar_combo_leitura(self, parent, texto, comando_selecao=None):
        lbl = ctk.CTkLabel(parent, text=texto)
        lbl.pack(anchor="w", padx=20, pady=(2,0)) 
        
        combo = ctk.CTkComboBox(
            parent, 
            values=["Carregando..."], 
            state="disabled", 
            text_color="#00FF00", 
            font=ctk.CTkFont(weight="bold"), 
            command=comando_selecao # Dispara se ele clicar na lista
        )
        combo.pack(fill="x", padx=20, pady=(0, 2))
        
        # Dispara também se o usuário digitar livremente e sair do campo
        if comando_selecao:
            combo._entry.bind("<FocusOut>", lambda e: comando_selecao(combo.get()))
            combo._entry.bind("<Return>", lambda e: comando_selecao(combo.get()))
        self.aplicar_filtro_dropdown(combo)
        return combo

    def criar_painel_extracao(self):
        frame_auto = ctk.CTkFrame(self)
        frame_auto.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        lbl_sec = ctk.CTkLabel(frame_auto, text="Leitura USB (Hardware)", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_sec.pack(pady=10)

        self.btn_ios = ctk.CTkButton(frame_auto, text="Ler Aparelho (iPhone / iOS)", fg_color="#4B4B4B", hover_color="#333333", command=self.iniciar_leitura_ios)
        self.btn_ios.pack(pady=5, padx=20, fill="x")

        self.btn_android = ctk.CTkButton(frame_auto, text="Ler Aparelho (Android ADB)", fg_color="#1f6aa5", command=self.iniciar_leitura_android)
        self.btn_android.pack(pady=5, padx=20, fill="x")

        self.switch_manual = ctk.CTkSwitch(frame_auto, text="Modo Manual (Habilitar Leitor de Código)", command=self.alternar_modo_manual)
        self.switch_manual.pack(pady=(15, 5), padx=20, anchor="w")

        self.campo_marca = self.criar_combo_leitura(
            frame_auto, 
            "Marca:", 
            comando_selecao=self.carregar_modelos
        )
        
        # Quando o Nome Comercial for escolhido, dispara a busca de Modelos Físicos
        self.campo_nome_comercial = self.criar_combo_leitura(frame_auto, "Nome Comercial:", comando_selecao=self.carregar_modelos_fisicos)
        
        self.campo_modelo = self.criar_combo_leitura(frame_auto, "Modelo Físico (Hardware ID):")
        
        # --- Modificação: Armazenamento e RAM Lado a Lado ---
        frame_arm_ram = ctk.CTkFrame(frame_auto)
        frame_arm_ram.pack(fill="x", padx=20, pady=(2, 0))
        frame_arm_ram.grid_columnconfigure(0, weight=1)
        frame_arm_ram.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame_arm_ram, text="Armazenamento:").grid(row=0, column=0, sticky="w")
        self.campo_armazenamento = ctk.CTkEntry(frame_arm_ram, state="disabled", text_color="#00FF00", font=ctk.CTkFont(weight="bold"))
        self.campo_armazenamento.grid(row=1, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkLabel(frame_arm_ram, text="Memória RAM:").grid(row=0, column=1, sticky="w")
        self.campo_ram = ctk.CTkEntry(frame_arm_ram, state="disabled", text_color="#00FF00", font=ctk.CTkFont(weight="bold"))
        self.campo_ram.grid(row=1, column=1, sticky="ew", padx=(5, 0))
        # ----------------------------------------------------

        self.campo_eid = self.criar_campo_leitura(frame_auto, "EID (eSIM):")
        self.campo_imei1 = self.criar_campo_leitura(frame_auto, "IMEI 1:")
        self.campo_imei2 = self.criar_campo_leitura(frame_auto, "IMEI 2:")
        self.campo_meid = self.criar_campo_leitura(frame_auto, "MEID:")
        self.campo_serie = self.criar_campo_leitura(frame_auto, "Número de Série (S/N):")

    def criar_painel_manual(self):
        frame_manual = ctk.CTkScrollableFrame(self)
        frame_manual.grid(row=2, column=1, padx=10, pady=5, sticky="nsew")

        lbl_sec = ctk.CTkLabel(frame_manual, text="Inspeção Física", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_sec.pack(pady=10)

        # --- ID do Responsável Técnico ---
        self.input_id_tecnico = self.criar_campo_entrada(frame_manual, "ID Responsável Técnico:")
        self.input_id_tecnico.insert(0, "1")
        
        lbl_caixa = ctk.CTkLabel(frame_manual, text="Caixa de Recebimento:")
        lbl_caixa.pack(anchor="w", padx=20, pady=(5,0))
        self.combo_caixa = ctk.CTkComboBox(frame_manual, values=["Carregando..."]) 
        self.combo_caixa.pack(fill="x", padx=20, pady=(0, 5))

        lbl_cor = ctk.CTkLabel(frame_manual, text="Cor do Aparelho:")
        lbl_cor.pack(anchor="w", padx=20, pady=(5,0))
        self.combo_cor = ctk.CTkComboBox(frame_manual, values=["Carregando..."])
        self.combo_cor.pack(fill="x", padx=20, pady=(0, 5))
        
        # --- Chips e Peso Lado a Lado ---
        frame_chips_peso = ctk.CTkFrame(frame_manual)
        frame_chips_peso.pack(fill="x", padx=20, pady=(5, 5))
        frame_chips_peso.grid_columnconfigure(0, weight=1)
        frame_chips_peso.grid_columnconfigure(1, weight=1)
        frame_chips_peso.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(frame_chips_peso, text="Chips Aceit.:").grid(row=0, column=0, sticky="w")
        self.input_qnt_chips = ctk.CTkEntry(frame_chips_peso)
        self.input_qnt_chips.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        ctk.CTkLabel(frame_chips_peso, text="Chips Inst.:").grid(row=0, column=1, sticky="w")
        self.input_chips_inst = ctk.CTkEntry(frame_chips_peso)
        self.input_chips_inst.grid(row=1, column=1, sticky="ew", padx=(4, 4))

        ctk.CTkLabel(frame_chips_peso, text="Peso (g):").grid(row=0, column=2, sticky="w")
        self.input_peso = ctk.CTkEntry(frame_chips_peso)
        self.input_peso.grid(row=1, column=2, sticky="ew", padx=(4, 0))
        
        lbl_estado = ctk.CTkLabel(frame_manual, text="Estado Físico:")
        lbl_estado.pack(anchor="w", padx=20, pady=(5,0))
        self.combo_estado = ctk.CTkComboBox(frame_manual, values=["Carregando..."])
        self.combo_estado.pack(fill="x", padx=20, pady=(0, 5))
        
        # --- Condição e Acesso Lado a Lado ---
        frame_cond_acesso = ctk.CTkFrame(frame_manual)
        frame_cond_acesso.pack(fill="x", padx=20, pady=(5, 5))
        frame_cond_acesso.grid_columnconfigure(0, weight=1)
        frame_cond_acesso.grid_columnconfigure(1, weight=1)

        lbl_condicao = ctk.CTkLabel(frame_cond_acesso, text="Condição de Func.:")
        lbl_condicao.grid(row=0, column=0, sticky="w")
        self.combo_condicao = ctk.CTkComboBox(frame_cond_acesso, values=["Carregando..."])
        self.combo_condicao.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        lbl_acesso = ctk.CTkLabel(frame_cond_acesso, text="Estado de Acesso:")
        lbl_acesso.grid(row=0, column=1, sticky="w")
        self.combo_acesso = ctk.CTkComboBox(frame_cond_acesso, values=["Carregando..."])
        self.combo_acesso.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        # --- Observações Adicionais ---
        self.input_obs = self.criar_campo_entrada(frame_manual, "Observações Adicionais:")

        # --- Avarias Identificadas ---
        lbl_avarias = ctk.CTkLabel(frame_manual, text="Avarias Identificadas:")
        lbl_avarias.pack(anchor="w", padx=20, pady=(10,0))
        
        # NOVO: Frame para abrigar a busca e o botão lado a lado
        frame_busca_avaria = ctk.CTkFrame(frame_manual)
        frame_busca_avaria.pack(fill="x", padx=20, pady=(0, 5))
        frame_busca_avaria.grid_columnconfigure(0, weight=1) # O campo de texto estica
        frame_busca_avaria.grid_columnconfigure(1, weight=0) # O botão usa só o necessário
        
        self.input_busca_avaria = ctk.CTkEntry(frame_busca_avaria, placeholder_text="Pesquisar ou adicionar (ex: conector)...")
        self.input_busca_avaria.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.input_busca_avaria.bind("<KeyRelease>", self.filtrar_avarias)
        
        self.btn_add_avaria = ctk.CTkButton(
            frame_busca_avaria, text="+", width=30,
            fg_color="#1f6aa5", hover_color="#144870",
            font=ctk.CTkFont(weight="bold", size=16),
            command=self.cadastrar_nova_avaria # Aciona a nova função
        )
        self.btn_add_avaria.grid(row=0, column=1, sticky="e")
        
        self.frame_avarias = ctk.CTkScrollableFrame(frame_manual, height=60)
        self.frame_avarias.pack(fill="x", padx=20, pady=(0, 5))
        self.vars_avarias = {}
        self.widgets_avarias = {}
        combos_manuais = [self.combo_caixa, self.combo_cor, self.combo_estado, self.combo_condicao, self.combo_acesso]
        for c in combos_manuais:
            self.aplicar_filtro_dropdown(c)
           
    def criar_painel_log(self):
        frame_log = ctk.CTkFrame(self)
        frame_log.grid(row=2, column=2, rowspan=2, padx=10, pady=5, sticky="nsew")
        
        lbl_sec = ctk.CTkLabel(frame_log, text="Log de Operação", font=ctk.CTkFont(size=18, weight="bold"))
        lbl_sec.pack(pady=10)

        self.caixa_log = ctk.CTkTextbox(frame_log, state="disabled", wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.caixa_log.pack(expand=True, fill="both", padx=10, pady=(0, 10))

    def criar_rodape(self):
            # 1. Cria um frame invisível para abrigar os 4 botões na mesma linha
            frame_botoes = ctk.CTkFrame(self)
            frame_botoes.grid(row=3, column=0, columnspan=3, pady=(10, 5), padx=10, sticky="ew")
            
            # 2. Configura 4 colunas com pesos iguais dentro deste frame
            for i in range(4):
                frame_botoes.grid_columnconfigure(i, weight=1)

            self.btn_limpar = ctk.CTkButton(frame_botoes, text="Limpar Campos", fg_color="#8A1111", hover_color="#5C0B0B", command=self.limpar_tela)
            self.btn_limpar.grid(row=0, column=0, padx=10, sticky="ew")

            self.btn_copiar = ctk.CTkButton(frame_botoes, text="COPIAR PARA EXCEL", font=ctk.CTkFont(size=16, weight="bold"), height=40, fg_color="#2FA572", hover_color="#248259", command=self.exportar_para_clipboard)
            self.btn_copiar.grid(row=0, column=1, padx=10, sticky="ew")

            # --- O NOVO BOTÃO DE SALVAR AQUI! ---
            self.btn_salvar = ctk.CTkButton(frame_botoes, text="SALVAR NO SISTEMA", font=ctk.CTkFont(size=16, weight="bold"), height=40, fg_color="#A52A2A", hover_color="#8B2222", command=self.enviar_para_api)
            self.btn_salvar.grid(row=0, column=2, padx=10, sticky="ew")
            
            self.btn_imprimir = ctk.CTkButton(frame_botoes, text="GERAR ETIQUETA", font=ctk.CTkFont(size=16, weight="bold"), height=40, fg_color="#1f6aa5", hover_color="#144870", command=self.gerar_etiqueta_pdf)
            self.btn_imprimir.grid(row=0, column=3, padx=(10, 60), sticky="ew") # Margem direita para não encavalar na engrenagem

            self.btn_calibrar = ctk.CTkButton(frame_botoes, text="⚙", width=40, height=40,
                font=ctk.CTkFont(size=20), fg_color="#444", hover_color="#666",
                command=self.abrir_calibracao)
            self.btn_calibrar.grid(row=0, column=3, padx=(0, 10), sticky="e")
            
            # --- Controle de Nº de Patrimônio (Mantido Exatamente Igual) ---
            frame_pat = ctk.CTkFrame(self)
            frame_pat.grid(row=4, column=0, columnspan=3, pady=(0, 12), padx=20, sticky="ew")
            frame_pat.grid_columnconfigure(0, weight=1)
            frame_pat.grid_columnconfigure(1, weight=0)
            frame_pat.grid_columnconfigure(2, weight=0)
            frame_pat.grid_columnconfigure(3, weight=0)
            frame_pat.grid_columnconfigure(4, weight=1)
            
            lbl_pat = ctk.CTkLabel(frame_pat, text="Nº de Patrimônio:", font=ctk.CTkFont(size=14, weight="bold"))
            lbl_pat.grid(row=0, column=0, sticky="e", padx=(0, 8))
            
            self.btn_pat_menos = ctk.CTkButton(
                frame_pat, text="−", width=36, height=36,
                font=ctk.CTkFont(size=20, weight="bold"),
                fg_color="#3a3a3a", hover_color="#555555",
                command=self._patrimonio_decrementar
            )
            self.btn_pat_menos.grid(row=0, column=1, padx=(0, 4))
            
            self.entry_patrimonio = ctk.CTkEntry(
                frame_pat, width=130, height=36,
                font=ctk.CTkFont(size=15, weight="bold"),
                justify="center"
            )
            self.entry_patrimonio.grid(row=0, column=2, padx=4)
            self.entry_patrimonio.insert(0, f"ITI TECH-{self._patrimonio_num:03d}")
            self.entry_patrimonio.bind("<Up>",    lambda e: self._patrimonio_incrementar())
            self.entry_patrimonio.bind("<Down>",  lambda e: self._patrimonio_decrementar())
            self.entry_patrimonio.bind("<FocusOut>", self._patrimonio_validar_entrada)
            self.entry_patrimonio.bind("<Return>", self._patrimonio_validar_entrada)
            
            self.btn_pat_mais = ctk.CTkButton(
                frame_pat, text="+", width=36, height=36,
                font=ctk.CTkFont(size=20, weight="bold"),
                fg_color="#1f6aa5", hover_color="#144870",
                command=self._patrimonio_incrementar
            )
            self.btn_pat_mais.grid(row=0, column=3, padx=(4, 0))
            
            lbl_pat_info = ctk.CTkLabel(
                frame_pat, 
                text="Use +/−, setas ↑↓ ou digite diretamente (prefixo \"ITI TECH-\" é fixo)",
                font=ctk.CTkFont(size=11), text_color="gray"
            )
            lbl_pat_info.grid(row=0, column=4, sticky="w", padx=(12, 0))
    
    def _carregar_config(self) -> dict:
            try:
                if os.path.exists(self._CONFIG_PATH):
                    with open(self._CONFIG_PATH, "r", encoding="utf-8") as f:
                        dados = json.load(f)
                        # Mescla os padrões com o que veio do arquivo JSON
                        return {**self._CONFIG_PADRAO, **dados}
            except Exception:
                pass
            return dict(self._CONFIG_PADRAO)

    def _salvar_config_impressora(self):
        try:
            with open(self._CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.atualizar_status(f"Erro ao salvar config: {e}", "red")

    def abrir_calibracao(self):
        """Abre janela de calibração das dimensões de impressão."""
        win = ctk.CTkToplevel(self)
        win.title("⚙  Calibrar Impressão Térmica")
        win.geometry("460x460")
        win.resizable(False, False)
        win.grab_set()  # modal

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
        e_largura    = campo("Largura da etiqueta (mm):", self._cfg["largura_mm"])
        e_altura     = campo("Altura da etiqueta (mm):", self._cfg["altura_mm"])
        e_offset_x   = campo("Ajuste Horizontal X (mm):", self._cfg.get("offset_x_mm", 0.0))
        e_offset_y   = campo("Ajuste Vertical Y (mm):", self._cfg.get("offset_y_mm", 0.0))
        e_escala     = campo("Escala Conteúdo (1.0 = 100%):", self._cfg.get("escala_conteudo", 1.0))

        def _listar_impressoras():
            try:
                nomes = [p[2] for p in win32print.EnumPrinters(
                    win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
                return "\n".join(nomes)
            except Exception:
                return "(win32print indisponível)"

        if WIN32_DISPONIVEL:
            ctk.CTkLabel(win,
                text="Impressoras disponíveis: " + ", ".join(
                    p[2] for p in win32print.EnumPrinters(
                        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)),
                text_color="#888", font=ctk.CTkFont(size=10), wraplength=400
            ).pack(pady=(6, 0), padx=20)

        def salvar():
            try:
                self._cfg["impressora"]  = e_impressora.get().strip()
                self._cfg["largura_mm"]  = float(e_largura.get().replace(",", "."))
                self._cfg["altura_mm"]   = float(e_altura.get().replace(",", "."))
                self._cfg["offset_x_mm"] = float(e_offset_x.get().replace(",", "."))
                self._cfg["offset_y_mm"] = float(e_offset_y.get().replace(",", "."))
                self._cfg["escala_conteudo"] = float(e_escala.get().replace(",", "."))
                self._salvar_config_impressora()
                self.atualizar_status(
                    f"Config salva: {self._cfg['largura_mm']}x{self._cfg['altura_mm']} mm — "
                    f"Impressora: {self._cfg['impressora']}", "#00FF00")
                win.destroy()
            except ValueError:
                self.atualizar_status("Valores inválidos — use números como 58.6 e 40.0", "red")

        ctk.CTkButton(win, text="💾  Salvar e Fechar", fg_color="#1f6aa5",
                      hover_color="#144870", command=salvar).pack(pady=18)

    # --- CONTROLE DE PATRIMÔNIO ---
    
    def _patrimonio_atualizar_display(self):
        """Atualiza o campo de entrada e salva o estado no config."""
        self.entry_patrimonio.delete(0, 'end')
        self.entry_patrimonio.insert(0, f"ITI TECH-{self._patrimonio_num:03d}")
        
        # Salva o novo número de patrimônio
        if self._cfg.get("patrimonio_num") != self._patrimonio_num:
            self._cfg["patrimonio_num"] = self._patrimonio_num
            self._salvar_config_impressora()
    
    def _patrimonio_incrementar(self):
        self._patrimonio_num += 1
        self._patrimonio_atualizar_display()
    
    def _patrimonio_decrementar(self):
        if self._patrimonio_num > 1:
            self._patrimonio_num -= 1
            self._patrimonio_atualizar_display()
    
    def _patrimonio_validar_entrada(self, event=None):
        """Tenta extrair apenas o número digitado (com ou sem o prefixo)."""
        texto = self.entry_patrimonio.get().strip()
        prefixo = "ITI TECH-"
        
        # Aceita digitação com ou sem o prefixo
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
            pass  # mantém o valor anterior se inválido
        
        self._patrimonio_atualizar_display()

    def ciclar_combobox(self, combo, direcao):
        valores = combo.cget("values")
        atual = combo.get()
        
        try:
            idx = valores.index(atual)
        except ValueError:
            idx = 0
            
        if direcao == "up":
            novo_idx = max(0, idx - 1)
        else:
            novo_idx = min(len(valores) - 1, idx + 1)
            
        combo.set(valores[novo_idx])

    def configurar_atalhos(self):
            self.campo_eid.bind("<Return>", lambda e: self.campo_imei1.focus())
            self.campo_imei1.bind("<Return>", lambda e: self.campo_imei2.focus())
            self.campo_imei2.bind("<Return>", lambda e: self.campo_meid.focus())
            
            # ATUALIZADO: Envia o foco para o combo_cor ao dar enter no MEID
            self.campo_meid.bind("<Return>", lambda e: self.combo_cor.focus())
            
            # ATUALIZADO: Usa o _entry para capturar o "Enter" no ComboBox de cor
            self.combo_cor._entry.bind("<Return>", lambda e: self.input_chips_inst.focus())
            
            self.input_chips_inst.bind("<Return>", lambda e: self.combo_estado.focus())

            campos_hardware = [self.campo_eid, self.campo_imei1, self.campo_imei2, self.campo_meid]
            for campo in campos_hardware:
                campo.bind("<FocusIn>", lambda e, c=campo: c.after(10, lambda: c.select_range(0, 'end')))

            # Atalhos para ciclar as opções dos ComboBoxes com as setas para cima/baixo
            self.combo_estado._entry.bind("<Up>", lambda e: self.ciclar_combobox(self.combo_estado, "up"))
            self.combo_estado._entry.bind("<Down>", lambda e: self.ciclar_combobox(self.combo_estado, "down"))
            
            self.combo_condicao._entry.bind("<Up>", lambda e: self.ciclar_combobox(self.combo_condicao, "up"))
            self.combo_condicao._entry.bind("<Down>", lambda e: self.ciclar_combobox(self.combo_condicao, "down"))

            # NOVO: Atalhos para o novo combo de estado de acesso (opcional, mas mantém a fluidez da UI)
            self.combo_acesso._entry.bind("<Up>", lambda e: self.ciclar_combobox(self.combo_acesso, "up"))
            self.combo_acesso._entry.bind("<Down>", lambda e: self.ciclar_combobox(self.combo_acesso, "down"))
            
            self.bind("<Control-p>", lambda e: self.gerar_etiqueta_pdf())
        # --- RADAR DE DISPOSITIVOS USB ---

    def iniciar_radar_usb(self):
        thread_radar = threading.Thread(target=self.monitorar_usb, daemon=True)
        thread_radar.start()

    def monitorar_usb(self):
        dispositivos_android = set()
        dispositivos_ios = set()

        while True:
            time.sleep(1.5)

            try:
                out_ios = subprocess.check_output([CAMINHO_IDEVICEID, '-l'], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip().split('\n')
                ios_atuais = set([d for d in out_ios if d])
            except Exception:
                ios_atuais = set()

            novos_ios = ios_atuais - dispositivos_ios
            removidos_ios = dispositivos_ios - ios_atuais

            for d in novos_ios:
                self.atualizar_status(f"Aparelho Apple detectado na porta USB.", "#00FFFF")
            for d in removidos_ios:
                self.atualizar_status(f"Aparelho Apple desconectado.", "#8B8B8B")

            dispositivos_ios = ios_atuais

            try:
                out_android = subprocess.check_output([CAMINHO_ADB, 'devices'], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip().split('\n')
                android_atuais = set()
                for linha in out_android[1:]: 
                    if '\t' in linha:
                        android_atuais.add(linha.split('\t')[0])
            except Exception:
                android_atuais = set()

            novos_android = android_atuais - dispositivos_android
            removidos_android = dispositivos_android - android_atuais

            for d in novos_android:
                self.atualizar_status(f"Aparelho Android detectado (Acesso ADB liberado).", "#00FFFF")
            for d in removidos_android:
                self.atualizar_status(f"Aparelho Android desconectado.", "#8B8B8B")

            dispositivos_android = android_atuais

    # --- FUNÇÕES DE LÓGICA E INTERFACE ---

    def atualizar_status(self, mensagem, cor="gray"):
        self.lbl_status.configure(text=mensagem, text_color=cor)
        
        agora = datetime.now().strftime("%H:%M:%S")
        linha_log = f"[{agora}] {mensagem}\n"
        
        self.caixa_log.configure(state="normal")
        self.caixa_log.insert("end", linha_log)
        self.caixa_log.see("end") 
        self.caixa_log.configure(state="disabled")

    def criar_campo_leitura(self, parent, texto):
        lbl = ctk.CTkLabel(parent, text=texto)
        lbl.pack(anchor="w", padx=20, pady=(2,0)) 
        entry = ctk.CTkEntry(parent, state="disabled", text_color="#00FF00", font=ctk.CTkFont(weight="bold"))
        entry.pack(fill="x", padx=20, pady=(0, 2))
        return entry
        
    def criar_campo_entrada(self, parent, texto):
        lbl = ctk.CTkLabel(parent, text=texto)
        lbl.pack(anchor="w", padx=20, pady=(5,0))
        entry = ctk.CTkEntry(parent)
        entry.pack(fill="x", padx=20, pady=(0, 5))
        return entry

    def alternar_modo_manual(self):
        modo_ligado = self.switch_manual.get() == 1
        estado = "normal" if modo_ligado else "disabled"
        cor_texto = "#FFFFFF" if modo_ligado else "#00FF00"
        
        campos_identificadores = [self.campo_armazenamento,self.campo_eid, self.campo_imei1, self.campo_imei2, self.campo_meid]
        
        for campo in campos_identificadores:
            campo.configure(state=estado, text_color=cor_texto)
            
        if modo_ligado:
            self.atualizar_status("Modo Manual: Identificadores liberados para leitor de código.", "yellow")
            self.campo_eid.focus()
        else:
            self.atualizar_status("Modo Manual Desativado. Todos os campos blindados.", "gray")

    def preencher_dados_tela(self, marca, modelo, nome_comercial, armazenamento, ram, eid, imei1, imei2, meid, serie):
        # Campos de Texto Normal (Entry)
        campos_identificadores = [
            (self.campo_armazenamento, armazenamento), (self.campo_ram, ram),
            (self.campo_eid, eid), (self.campo_imei1, imei1), 
            (self.campo_imei2, imei2), (self.campo_meid, meid),
            (self.campo_serie, serie) # Série movida pra cá, pois é Entry
        ]
        
        # Campos Dropdown (ComboBox)
        campos_combos = [
            (self.campo_marca, marca),
            (self.campo_nome_comercial, nome_comercial),
            (self.campo_modelo, modelo) # Hardware ID
        ]
        
        modo_manual = self.switch_manual.get() == 1
        
        # Preenche os combos
        for combo, valor in campos_combos:
            combo.configure(state="normal")
            combo.set(valor)
            if not modo_manual: 
                combo.configure(state="disabled")
            else:
                combo.configure(text_color="#FFFFFF")
                
        # Preenche os entries
        for campo, valor in campos_identificadores:
            campo.configure(state="normal")
            campo.delete(0, 'end')
            campo.insert(0, valor)
            if not modo_manual: 
                campo.configure(state="disabled")
            else: 
                campo.configure(text_color="#FFFFFF") 

        if hasattr(self, 'combo_cor'): self.combo_cor.set("")
        self.input_qnt_chips.delete(0, 'end')
        self.input_qnt_chips.insert(0, "2")
        self.input_chips_inst.delete(0, 'end')

    def alternar_modo_manual(self):
        modo_ligado = self.switch_manual.get() == 1
        estado = "normal" if modo_ligado else "disabled"
        cor_texto = "#FFFFFF" if modo_ligado else "#00FF00"
        
        # Agora os combos de modelo também devem destravar no modo manual!
        campos_liberaveis = [
            self.campo_marca, self.campo_nome_comercial, self.campo_modelo,
            self.campo_armazenamento, self.campo_ram, self.campo_eid, 
            self.campo_imei1, self.campo_imei2, self.campo_meid, self.campo_serie
        ]
        
        for campo in campos_liberaveis:
            campo.configure(state=estado, text_color=cor_texto)
            
        if modo_ligado:
            self.atualizar_status("Modo Manual: Identificadores liberados para leitor de código.", "yellow")
            self.campo_marca.focus() # Manda o foco para o primeiro campo
        else:
            self.atualizar_status("Modo Manual Desativado. Todos os campos blindados.", "gray")

    def limpar_tela(self):
        # Agora são 10 argumentos vazios (adicionado a RAM)
        self.preencher_dados_tela("", "", "", "", "", "", "", "", "", "")
        
        self.input_qnt_chips.delete(0, 'end')
        self.input_chips_inst.delete(0, 'end')
        self.input_obs.delete(0, 'end')
        self.input_peso.delete(0, 'end')
        
        if hasattr(self, 'combo_estado'): self.combo_estado.set("")
        if hasattr(self, 'combo_condicao'): self.combo_condicao.set("")
        if hasattr(self, 'combo_cor'): self.combo_cor.set("")
        if hasattr(self, 'combo_acesso'): self.combo_acesso.set("")
        
        if hasattr(self, 'vars_avarias'):
            for var in self.vars_avarias.values(): var.set("")
                
        self.atualizar_status("Painel de digitação e extração limpo.", "gray")

    # --- EXPORTAÇÃO EXCEL ---

    def exportar_para_clipboard(self):
        # Textos padronizados em MAIÚSCULO para a planilha
        tipo = "CELULAR"
        
        marca = self.campo_marca.get().upper()
        modelo = self.campo_modelo.get().upper()
        nome_comercial = self.campo_nome_comercial.get().upper()
        
        # --- CORREÇÃO AQUI: Mudou de input_cor para combo_cor ---
        cor = self.combo_cor.get().upper() if hasattr(self, 'combo_cor') else ""
        
        imei1 = self.campo_imei1.get()
        imei2 = self.campo_imei2.get()
        
        eid_raw = self.campo_eid.get()
        eid = f"'{eid_raw}" if eid_raw.strip() != "" and eid_raw != "N/A" else eid_raw
        
        meid = self.campo_meid.get()
        serie = self.campo_serie.get().upper()
        
        qnt_chips = self.input_qnt_chips.get()
        chips_inst = self.input_chips_inst.get() 
        estado = self.combo_estado.get().upper()
        
        # --- NOVO: Pega as avarias selecionadas nos CheckBoxes ---
        texto_avarias = ""
        if hasattr(self, 'vars_avarias'):
            avarias_selecionadas = [var.get().upper() for var in self.vars_avarias.values() if var.get() != ""]
            texto_avarias = ", ".join(avarias_selecionadas)
        
        obs_crua = self.input_obs.get().lower()
        if obs_crua.strip() != "":
            dicionario_triagem = {
                "arranhoes": "arranhões", "arranhao": "arranhão",
                "carcaca": "carcaça", "botao": "botão", "botoes": "botões",
                "camera": "câmera", "modulo": "módulo", "avaria": "avaria"
            }
            for errado, certo in dicionario_triagem.items():
                obs_crua = obs_crua.replace(errado, certo)
                
            obs_formatada = corretor_pt(obs_crua).upper()
            self.input_obs.delete(0, 'end')
            self.input_obs.insert(0, obs_formatada)
        else:
            obs_formatada = ""
            
        # Junta as avarias marcadas com as observações digitadas para ir para o Excel
        obs_final = texto_avarias
        if obs_formatada:
            obs_final = f"{texto_avarias} - {obs_formatada}" if texto_avarias else obs_formatada
            
        condicao = self.combo_condicao.get().upper()
        peso = self.input_peso.get()

        # Sequência exata: Tipo, Marca, Modelo, Nome Comercial, Cor, IMEI1, IMEI2, MEID, EID, Série, Qnt Chips, Chips Inst, Estado, Obs, Condição, Peso
        linha_tabulada = f"{tipo}\t{marca}\t{modelo}\t{nome_comercial}\t{cor}\t{imei1}\t{imei2}\t{meid}\t{eid}\t{serie}\t{qnt_chips}\t{chips_inst}\t{estado}\t{obs_final}\t{condicao}\t{peso}"
        
        self.clipboard_clear()
        self.clipboard_append(linha_tabulada)
        
        self.atualizar_status(f"Dados exportados p/ Excel ({modelo})", "#00FF00")

    # --- GERAÇÃO E IMPRESSÃO DIRETA DE ETIQUETA ---

    def _construir_imagem_etiqueta(self,idTelefone ,patrimonio, marca, modelo, arm, serie, estado):
        """
        Constrói a etiqueta como imagem PIL no tamanho exato da etiqueta física
        (58,6 mm x 40 mm) na resolução de 203 DPI da impressora MDK-2054L.
        Retorna um objeto PIL.Image.
        """
        DPI = 203
        MM_POR_POLEGADA = 25.4

        largura_px = int(round(58.6 / MM_POR_POLEGADA * DPI))  # ≈ 468 px
        altura_px  = int(round(40.0 / MM_POR_POLEGADA * DPI))  # ≈ 320 px

        img = Image.new("L", (largura_px, altura_px), 255)  # branco, escala de cinza
        draw = ImageDraw.Draw(img)

        # Pega a escala definida nas configurações
        escala = float(self._cfg.get("escala_conteudo", 1.0))

        # --- Fontes (usa a fonte embutida do Pillow se não tiver TrueType) ---
        def _fonte(tamanho):
            try:
                caminho = os.path.join(os.environ.get("SystemRoot", "C:/Windows"), "Fonts", "arialbd.ttf")
                if os.path.exists(caminho):
                    return ImageFont.truetype(caminho, tamanho)
                return ImageFont.truetype("arial.ttf", tamanho)
            except Exception:
                return ImageFont.load_default()

        fonte_titulo  = _fonte(int(22 * escala))
        fonte_normal  = _fonte(int(17 * escala))
        fonte_pequena = _fonte(int(15 * escala))
        fonte_pat     = _fonte(int(19 * escala))

        def centralizar_texto(texto, y, fonte):
            bbox = draw.textbbox((0, 0), texto, font=fonte)
            w = bbox[2] - bbox[0]
            x = (largura_px - w) // 2
            draw.text((x, y), texto, font=fonte, fill=0)

        # --- 1. Cabeçalho ---
        centralizar_texto("Instituto ITI - Triagem", int(4 * escala), fonte_titulo)

        # --- 2. Aparelho ---
        if marca and not modelo.lower().startswith(marca.lower()):
            txt_aparelho = f"{marca} {modelo}".strip()
        else:
            txt_aparelho = modelo if modelo else marca
        centralizar_texto(txt_aparelho, int(32 * escala), fonte_normal)

        # --- 3. Capacidade ---
        txt_cap = f"Capacidade: {arm}" if arm and arm != "N/A" else "Capacidade: N/A"
        centralizar_texto(txt_cap, int(54 * escala), fonte_pequena)

        # --- 4. S/N e Estado ---
        txt_sn = f"S/N: {serie or 'N/A'} | Est: {estado or 'N/A'}"
        centralizar_texto(txt_sn, int(73 * escala), fonte_pequena)

        # --- 5. QR Code ---
        qr = qrcode.QRCode(version=2, box_size=4, border=1,
                           error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(idTelefone)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("L")

        # Redimensiona para caber (máx ~130 px de altura, deixando espaço para texto)
        qr_alvo = int(116 * escala)
        qr_img = qr_img.resize((qr_alvo, qr_alvo), Image.LANCZOS)

        qr_x = (largura_px - qr_alvo) // 2
        qr_y = int(96 * escala)
        img.paste(qr_img, (qr_x, qr_y))

        # --- 6. Nº de Patrimônio ---
        centralizar_texto(patrimonio, int(218 * escala), fonte_pat)

        return img

    def gerar_etiqueta_pdf(self, event=None):
        imei = self.campo_imei1.get().strip()
        if not imei or imei == "N/A" or imei == "":
            self.atualizar_status("Erro: É necessário um IMEI válido para gerar a etiqueta.", "red")
            return

        # Valida e captura o patrimônio atual
        self._patrimonio_validar_entrada()
        patrimonio = f"ITI TECH-{self._patrimonio_num:03d}"

        marca  = self.campo_marca.get().strip()
        modelo = self.campo_nome_comercial.get().strip()
        arm    = self.campo_armazenamento.get().strip()
        serie  = self.campo_serie.get().strip()
        estado = self.combo_estado.get().strip()

        # --- Garante pasta de saída ---
        pasta = "etiquetas"
        os.makedirs(pasta, exist_ok=True)

        # --- Constrói a imagem ---
        img_etiqueta = self._construir_imagem_etiqueta(self._patrimonio_num, patrimonio, marca, modelo, arm, serie, estado)

        # Salva PNG de referência
        nome_base = patrimonio.replace(" ", "_").replace("-", "_")
        arquivo_png = os.path.join(pasta, f"{nome_base}.png")
        img_etiqueta.save(arquivo_png, dpi=(203, 203))

        # --- Impressão direta via Windows GDI ---
        NOME_IMPRESSORA = "4BARCODE 4B-2054L"

        if WIN32_DISPONIVEL:
            threading.Thread(
                target=self._imprimir_imagem_win32,
                args=(img_etiqueta, NOME_IMPRESSORA, patrimonio),
                daemon=True
            ).start()
        else:
            # Fallback: abre o PNG para impressão manual
            self.atualizar_status("win32print não disponível — abra o PNG e imprima manualmente.", "yellow")
            os.startfile(arquivo_png)

    def _imprimir_imagem_win32(self, img: Image.Image, nome_impressora: str, patrimonio: str):
        """Envia a imagem PIL diretamente para a impressora via Windows GDI."""
        try:
            # Verifica se a impressora existe; usa a padrão como fallback
            nomes_disponiveis = [p[2] for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            if nome_impressora not in nomes_disponiveis:
                nome_impressora = win32print.GetDefaultPrinter()

            # 1. Obtém o DEVMODE padrão configurado no Painel de Controle
            hprinter = win32print.OpenPrinter(nome_impressora)
            printer_info = win32print.GetPrinter(hprinter, 2)
            devmode = printer_info["pDevMode"]
            
            # NÃO modificamos o devmode. O usuário já configurou no driver.
            
            # 2. Cria contexto de dispositivo usando as configs nativas do driver
            hdc_gui = win32gui.CreateDC("WINSPOOL", nome_impressora, devmode)
            hdc = win32ui.CreateDCFromHandle(hdc_gui)

            # Obtém a área de impressão real que o driver definiu
            dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX)
            dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY)
            imp_w = hdc.GetDeviceCaps(win32con.HORZRES)
            imp_h = hdc.GetDeviceCaps(win32con.VERTRES)

            MM = 25.4
            
            # Calcula o deslocamento (offset) definido no nosso app
            offset_x_mm = self._cfg.get("offset_x_mm", 0.0)
            offset_y_mm = self._cfg.get("offset_y_mm", 0.0)
            offset_x_px = int(round(offset_x_mm / MM * dpi_x))
            offset_y_px = int(round(offset_y_mm / MM * dpi_y))

            # Redimensiona a imagem PIL
            alvo_w = int(round(self._cfg["largura_mm"] / MM * dpi_x))
            alvo_h = int(round(self._cfg["altura_mm"] / MM * dpi_y))
            img_impressao = img.resize((alvo_w, alvo_h), Image.LANCZOS).convert("RGB")

            # Corta a imagem caso o offset faça ela vazar para fora da página (evita pular páginas extras)
            if offset_x_px < 0:
                img_impressao = img_impressao.crop((-offset_x_px, 0, alvo_w, alvo_h))
                alvo_w += offset_x_px
                offset_x_px = 0
            if offset_y_px < 0:
                img_impressao = img_impressao.crop((0, -offset_y_px, alvo_w, alvo_h))
                alvo_h += offset_y_px
                offset_y_px = 0
                
            crop_w = min(alvo_w, imp_w - offset_x_px)
            crop_h = min(alvo_h, imp_h - offset_y_px)
            if crop_w < alvo_w or crop_h < alvo_h:
                img_impressao = img_impressao.crop((0, 0, crop_w, crop_h))

            hdc.StartDoc(f"Etiqueta {patrimonio}")
            hdc.StartPage()

            # Desenha a área da etiqueta rigorosamente dentro dos limites
            dib = ImageWin.Dib(img_impressao)
            x2 = offset_x_px + crop_w
            y2 = offset_y_px + crop_h
            
            dib.draw(hdc.GetHandleAttrib(), (offset_x_px, offset_y_px, x2, y2))

            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            win32print.ClosePrinter(hprinter)

            self.after(0, lambda: self.atualizar_status(
                f"Etiqueta [{patrimonio}] enviada para impressora!", "#00FF00"))

            # Incrementa para o próximo
            self.after(0, self._patrimonio_incrementar)

        except Exception as e:
            self.after(0, lambda: self.atualizar_status(
                f"Erro ao imprimir: {e}", "red"))

    # --- MOTORES DE EXTRAÇÃO ---

    def iniciar_leitura_ios(self):
        self.atualizar_status("Iniciando varredura profunda no iOS...", "yellow")
        threading.Thread(target=self.extrair_dados_ios).start()

    def extrair_dados_ios(self):
        try:
            tabela_iphones = {
                "iPhone7,1": "iPhone 6 Plus", "iPhone7,2": "iPhone 6",
                "iPhone8,1": "iPhone 6s", "iPhone8,2": "iPhone 6s Plus", "iPhone8,4": "iPhone SE (1ª Ger)",
                "iPhone9,1": "iPhone 7", "iPhone9,3": "iPhone 7",
                "iPhone9,2": "iPhone 7 Plus", "iPhone9,4": "iPhone 7 Plus",
                "iPhone10,1": "iPhone 8", "iPhone10,4": "iPhone 8",
                "iPhone10,2": "iPhone 8 Plus", "iPhone10,5": "iPhone 8 Plus",
                "iPhone10,3": "iPhone X", "iPhone10,6": "iPhone X",
                "iPhone11,2": "iPhone XS", "iPhone11,4": "iPhone XS Max", "iPhone11,6": "iPhone XS Max",
                "iPhone11,8": "iPhone XR",
                "iPhone12,1": "iPhone 11", "iPhone12,3": "iPhone 11 Pro", "iPhone12,5": "iPhone 11 Pro Max",
                "iPhone12,8": "iPhone SE (2ª Ger)",
                "iPhone13,1": "iPhone 12 mini", "iPhone13,2": "iPhone 12", "iPhone13,3": "iPhone 12 Pro", "iPhone13,4": "iPhone 12 Pro Max",
                "iPhone14,4": "iPhone 13 mini", "iPhone14,5": "iPhone 13", "iPhone14,2": "iPhone 13 Pro", "iPhone14,3": "iPhone 13 Pro Max",
                "iPhone14,6": "iPhone SE (3ª Ger)",
                "iPhone14,7": "iPhone 14", "iPhone14,8": "iPhone 14 Plus",
                "iPhone15,2": "iPhone 14 Pro", "iPhone15,3": "iPhone 14 Pro Max",
                "iPhone15,4": "iPhone 15", "iPhone15,5": "iPhone 15 Plus",
                "iPhone16,1": "iPhone 15 Pro", "iPhone16,2": "iPhone 15 Pro Max",
                "iPhone17,1": "iPhone 16 Pro", "iPhone17,2": "iPhone 16 Pro Max", "iPhone17,3": "iPhone 16", "iPhone17,4": "iPhone 16 Plus",
                "iPhone18,1": "iPhone 17 Pro", "iPhone18,2": "iPhone 17 Pro Max", "iPhone18,3": "iPhone 17", "iPhone18,4": "iPhone 17 Plus"
            }
            
            self.atualizar_status("Extraindo dicionário de Hardware (Dump Completo)...", "yellow")
            
            raw_info = subprocess.check_output([CAMINHO_IDEVICEINFO], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            info_dict = {}
            for linha in raw_info.split('\n'):
                if ': ' in linha:
                    chave, valor = linha.split(': ', 1)
                    info_dict[chave.strip()] = valor.strip()
            
            marca = "Apple"
            modelo = info_dict.get('ProductType', 'Desconhecido')
            nome_comercial = tabela_iphones.get(modelo, modelo)
            
            serie = info_dict.get('SerialNumber', 'N/A')
            imei1 = info_dict.get('InternationalMobileEquipmentIdentity', 'N/A')
            
            imei2 = info_dict.get('InternationalMobileEquipmentIdentity2', info_dict.get('InternationalMobileSubscriberIdentity', 'N/A'))
            if imei2 == imei1: 
                imei2 = "N/A"
                
            meid  = info_dict.get('MobileEquipmentIdentifier', 'N/A')
            eid = "N/A" 
            
            self.atualizar_status("Calculando capacidade de disco rígido...", "yellow")
            try:
                bytes_raw = subprocess.check_output([CAMINHO_IDEVICEINFO, '-q', 'com.apple.disk_usage', '-k', 'TotalDiskCapacity'], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
                gb_calculado = int(bytes_raw) / (1000 ** 3)
                tamanhos_mercado = [8, 16, 32, 64, 128, 256, 512, 1024]
                tamanho_real = min(tamanhos_mercado, key=lambda x: abs(x - gb_calculado))
                armazenamento_final = f"{tamanho_real} GB"
            except Exception:
                armazenamento_final = "N/A"
            
            ram_final = "N/A" # A Apple esconde a RAM de comandos nativos do terminal
            
            self.preencher_dados_tela(marca, modelo, nome_comercial, armazenamento_final, ram_final, eid, imei1, imei2, meid, serie)
            self.atualizar_status(f"Leitura concluída com sucesso.", "#00FF00")
            
        except FileNotFoundError:
            self.atualizar_status("Falha Crítica: Motor ideviceinfo ausente no PATH.", "red")
        except subprocess.CalledProcessError:
            self.atualizar_status("Falha de Comunicação: Dispositivo bloqueado ou cabo com defeito.", "red")

    def iniciar_leitura_android(self):
        self.atualizar_status("Iniciando requisição de interface ADB...", "yellow")
        threading.Thread(target=self.extrair_dados_android).start()

    def extrair_dados_android(self):
        try:
            self.atualizar_status("Acessando propriedades do sistema (getprop)...", "yellow")
            
            marca_raw = subprocess.check_output([CAMINHO_ADB, 'shell', 'getprop', 'ro.product.brand'], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            marca = marca_raw.capitalize() if marca_raw else "N/A"
            
            modelo = subprocess.check_output([CAMINHO_ADB, 'shell', 'getprop', 'ro.product.model'], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()
            
            nome_comercial = modelo 
            
            serie = subprocess.check_output([CAMINHO_ADB, 'shell', 'getprop', 'ro.serialno'], text=True, creationflags=subprocess.CREATE_NO_WINDOW).strip()

            self.atualizar_status("Bypass em andamento para extração de IMEI...", "yellow")
            # Note o uso do f-string e das aspas duplas em volta do {CAMINHO_ADB} caso o caminho tenha espaços
            imei_cru = subprocess.getoutput('"' + CAMINHO_ADB + '" shell "service call iphonesubinfo 1 | grep -o \'[0-9a-f]\\{8\\} \' | tail -n+3 | tr -d \' \\n\'"').strip()

            if len(imei_cru) > 8 and "Exception" not in imei_cru:
                imei1 = imei_cru
                imei2 = "N/A" 
                eid = "N/A"
                meid = "N/A"
                status_final = f"Leitura ADB concluída: {marca} {modelo}"
                cor_final = "#00FF00"
            else:
                imei1 = "N/A"
                imei2 = "N/A"
                eid = "N/A"
                meid = "N/A"
                status_final = f"Leitura parcial ({marca} {modelo}): IMEI bloqueado pelo Android 10+"
                cor_final = "yellow"
            
            # ... dentro do try de extrair_dados_android, logo após checar o IMEI ...
            
            self.atualizar_status("Calculando capacidade de RAM (MemTotal)...", "yellow")
            try:
                ram_raw = subprocess.check_output([CAMINHO_ADB, 'shell', 'cat /proc/meminfo'], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                # Procura por "MemTotal:      8192000 kB"
                kb_match = re.search(r'MemTotal:\s+(\d+)\s+kB', ram_raw)
                if kb_match:
                    gb_ram = round(int(kb_match.group(1)) / (1024 * 1024))
                    # Ajusta para tamanhos comerciais
                    tamanhos_ram = [1, 2, 3, 4, 6, 8, 12, 16, 24]
                    gb_calculado = min(tamanhos_ram, key=lambda x: abs(x - gb_ram))
                    ram_final = f"{gb_calculado} GB"
                else:
                    ram_final = "N/A"
            except Exception:
                ram_final = "N/A"

            self.preencher_dados_tela(marca, modelo, nome_comercial, "N/A", ram_final, eid, imei1, imei2, meid, serie)
            self.atualizar_status(status_final, cor_final)
            
        except Exception as e:
            self.atualizar_status("Falha de Comunicação: Aparelho offline ou Depuração desligada.", "red")
            
    def carregar_modelos(self, marca_digitada):
        texto = marca_digitada.strip()
        if not texto or texto == "Carregando...":
            return
            
        self.atualizar_status(f"Buscando modelos para a marca: {texto}...", "yellow")
        
        def realizar_request():
            try:
                url = f"{self._cfg.get('api_url', 'http://localhost:5000/api')}/triagem/marcas/{texto}/modelos"
                response = requests.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    dados = response.json()
                    
                    if isinstance(dados, dict):
                        lista_real = dados.get("value", dados.get("data", []))
                    else:
                        lista_real = dados

                    nomes_modelos = [item.get("nome", "") for item in lista_real if isinstance(item, dict)]
                    
                    if not nomes_modelos:
                        nomes_modelos = [""]
                        
                    # --- AQUI ESTÁ A MUDANÇA PRINCIPAL ---
                    self.after(0, lambda: self.atualizar_valores_combo(self.campo_nome_comercial, nomes_modelos))
                    
                    atual = self.campo_nome_comercial.get()
                    if atual == "Selecione uma Marca" or atual == "":
                         if nomes_modelos[0]:
                             self.after(0, lambda: self.campo_nome_comercial.set(nomes_modelos[0]))
                             
                    self.after(0, lambda: self.atualizar_status(f"Modelos de {texto} carregados.", "gray"))
                else:
                    # --- E AQUI (FALLBACK) ---
                    self.after(0, lambda: self.atualizar_valores_combo(self.campo_nome_comercial, [""]))
            except Exception as e:
                print(f"Erro ao buscar modelos: {e}") 
                # --- E AQUI (FALLBACK EM CASO DE EXCEPTION) ---
                self.after(0, lambda: self.atualizar_valores_combo(self.campo_nome_comercial, [""]))

        threading.Thread(target=realizar_request, daemon=True).start()
    
    def carregar_modelos_fisicos(self, modelo_digitado):
        texto = modelo_digitado.strip()
        if not texto or texto == "Selecione uma Marca":
            return
            
        self.atualizar_status(f"Buscando modelos físicos para: {texto}...", "yellow")
        
        def realizar_request():
            try:
                url = f"{self._cfg.get('api_url', 'http://localhost:5000/api')}/triagem/modelos/{texto}/modelos-fisicos"
                response = requests.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    dados = response.json()
                    
                    if isinstance(dados, dict):
                        lista_real = dados.get("value", dados.get("data", []))
                    else:
                        lista_real = dados

                    modelos_fisicos = [item.get("nome", "") for item in lista_real if isinstance(item, dict)]
                    
                    if not modelos_fisicos:
                        modelos_fisicos = ["N/A"]
                        
                    # --- AQUI ESTÁ A MUDANÇA PRINCIPAL ---
                    self.after(0, lambda: self.atualizar_valores_combo(self.campo_modelo, modelos_fisicos))
                    
                    atual = self.campo_modelo.get()
                    if atual == "Selecione um Modelo" or atual == "":
                        self.after(0, lambda: self.campo_modelo.set(modelos_fisicos[0]))
                        
                    self.after(0, lambda: self.atualizar_status(f"Modelos físicos carregados.", "gray"))
                else:
                    # --- E AQUI (FALLBACK) ---
                    self.after(0, lambda: self.atualizar_valores_combo(self.campo_modelo, ["N/A"]))
            except Exception as e:
                print(f"Erro ao buscar modelos físicos: {e}") 
                # --- E AQUI (FALLBACK EM CASO DE EXCEPTION) ---
                self.after(0, lambda: self.atualizar_valores_combo(self.campo_modelo, ["N/A"]))

        threading.Thread(target=realizar_request, daemon=True).start()      
    
    def carregar_dominios(self):
        self.atualizar_status("Carregando domínios da API...", "yellow")
        
        def realizar_request():
            try:
                url = f"{self._cfg.get('api_url', 'http://localhost:5000/api')}/triagem/dominios"
                print(url)
                response = requests.get(url, timeout=5, verify=False)
                if response.status_code == 200:
                    dados = response.json()
                    
                    # Novas listas extraídas:
                    marcas = [item["nome"] for item in dados.get("marcas", [])]
                    modelos = [item["nome"] for item in dados.get("modelos", [])]
                    
                    # Extrações originais:
                    cores = [item["nome"] for item in dados.get("cores", [])]
                    estados = [item["nome"] for item in dados.get("estadosFisicos", [])]
                    condicoes = [item["nome"] for item in dados.get("condicoesFuncionamento", [])]
                    acessos = [item["nome"] for item in dados.get("estadosAcesso", [])]
                    avarias = [item["nome"] for item in dados.get("avarias", [])]
                    caixas = [item["nome"] for item in dados.get("caixasRecebimentos", [])]
                    
                    # --- AQUI OCORRE A GRANDE SUBSTITUIÇÃO DOS .configure ---
                    self.after(0, lambda: self.atualizar_valores_combo(self.campo_marca, marcas))
                    self.after(0, lambda: self.atualizar_valores_combo(self.campo_nome_comercial, modelos))

                    self.after(0, lambda: self.atualizar_valores_combo(self.combo_cor, cores))
                    self.after(0, lambda: self.atualizar_valores_combo(self.combo_estado, estados))
                    self.after(0, lambda: self.atualizar_valores_combo(self.combo_condicao, condicoes))
                    self.after(0, lambda: self.atualizar_valores_combo(self.combo_acesso, acessos))
                    self.after(0, lambda: self.atualizar_valores_combo(self.combo_caixa, caixas))
                    # ---------------------------------------------------------
                    
                    def renderizar_avarias():
                        for widget in self.frame_avarias.winfo_children():
                            widget.destroy()
                        self.vars_avarias.clear()
                        
                        if hasattr(self, 'widgets_avarias'):
                            self.widgets_avarias.clear()
                        
                        for avaria in avarias:
                            var = ctk.StringVar(value="")
                            chk = ctk.CTkCheckBox(self.frame_avarias, text=avaria, variable=var, onvalue=avaria, offvalue="")
                            chk.pack(anchor="w", pady=2)
                            self.vars_avarias[avaria] = var
                            
                            if hasattr(self, 'widgets_avarias'):
                                self.widgets_avarias[avaria] = chk
                            
                    self.after(0, renderizar_avarias)
                    self.after(0, lambda: self.atualizar_status("Domínios carregados com sucesso.", "gray"))
            except Exception as e:
                mensagem = f"Aviso: Falha ao carregar domínios da API. Erro: {e}"
                self.after(0, lambda msg=mensagem: self.atualizar_status(msg, "red"))

        threading.Thread(target=realizar_request, daemon=True).start()
    
    def enviar_para_api(self):
        self.atualizar_status("Enviando dados para a API...", "yellow")
        
        peso_match = re.search(r'\d+', self.input_peso.get())
        peso = int(peso_match.group()) if peso_match else 0
        
        arm_match = re.search(r'\d+', self.campo_armazenamento.get())
        capacidade = int(arm_match.group()) if arm_match else 0
        
        chips_text = self.input_chips_inst.get()
        chips_inst = int(chips_text) if chips_text.isdigit() else 0

        chips_aceitos_text = self.input_qnt_chips.get()
        chips_aceitos = int(chips_aceitos_text) if chips_aceitos_text.isdigit() else 0

        avarias_lista = [{"nome": var.get()} for var in self.vars_avarias.values() if var.get() != ""]

        ram_match = re.search(r'\d+', self.campo_ram.get())
        capacidade_ram = int(ram_match.group()) if ram_match else None
        
        id_tecnico_texto = self.input_id_tecnico.get().strip()
        id_responsavel = int(id_tecnico_texto) if id_tecnico_texto.isdigit() else 1
        
        def limpar_identificador(valor):
            texto = valor.strip()
            return "" if texto == "N/A" else texto

        payload = {
            "caixaRecebimento": { "nome": self.combo_caixa.get() },
            "modelo": {
                "marca": { "nome": self.campo_marca.get() },
                "tipoEquipamento": { "nome": "Smartphone" }, 
                "modelo": { "nome": self.campo_nome_comercial.get() },
                "modeloFisico": { "nome": self.campo_modelo.get() }
            },
            "numeroSerie": limpar_identificador(self.campo_serie.get()),
            "idResponsavelTecnico": id_responsavel, 
            "imei1": limpar_identificador(self.campo_imei1.get()),
            "imei2": limpar_identificador(self.campo_imei2.get()),
            "meid": limpar_identificador(self.campo_meid.get()),
            "eid": limpar_identificador(self.campo_eid.get()),
            "capacidadeArmazenamentoGb": capacidade,
            "capacidadeRamGb": capacidade_ram, 
            "cor": { "nome": self.combo_cor.get() }, 
            "qtdChipsInstalados": chips_inst,
            "qtdChipsAceitos": chips_aceitos, 
            "estadoFisico": { "nome": self.combo_estado.get() },
            "estadoAcesso": { "nome": self.combo_acesso.get() }, 
            "condicaoFuncionamento": { "nome": self.combo_condicao.get() },
            "avarias": avarias_lista,
            "pesoGramas": peso,
            "observacoes": self.input_obs.get()
        }

        def realizar_request():
            url = f"{self._cfg.get('api_url', 'http://localhost:5000/api')}/triagem/triagem"
            try:
                response = requests.post(url, json=payload, timeout=10, verify=False)
                if response.status_code == 200:
                    dados = response.json()
                    id_estoque = dados.get("idItemEstoque")
                    
                    def sucesso_na_ui():
                        self.atualizar_status(f"Triagem Salva! ID Estoque: {id_estoque}. Gerando etiqueta...", "#00FF00")
                        self._patrimonio_num = int(id_estoque)
                        self._patrimonio_atualizar_display()
                        self.gerar_etiqueta_pdf()

                    self.after(0, sucesso_na_ui)
                else:
                    self.after(0, lambda: self.atualizar_status(f"Erro na API: {response.text}", "red"))
            except requests.exceptions.RequestException as e:
                mensagem_erro = f"Erro de conexão com o servidor: {e}"
                self.after(0, lambda msg=mensagem_erro: self.atualizar_status(msg, "red"))

        threading.Thread(target=realizar_request, daemon=True).start()           
                
    def filtrar_avarias(self, event=None):
        termo = self.input_busca_avaria.get()
        
        # Remove acentos e converte para minúsculo
        termo_norm = unicodedata.normalize('NFKD', termo).encode('ASCII', 'ignore').decode('utf-8').lower()

        for avaria, chk in self.widgets_avarias.items():
            avaria_norm = unicodedata.normalize('NFKD', avaria).encode('ASCII', 'ignore').decode('utf-8').lower()
            
            # Se o campo de busca estiver vazio, mostra tudo
            if not termo_norm:
                chk.pack(anchor="w", pady=2)
                continue

            # 1ª Tentativa: Contém o texto exato (ex: digita "tela" e acha "Arranhão na Tela")
            if termo_norm in avaria_norm:
                chk.pack(anchor="w", pady=2)
            else:
                # 2ª Tentativa: Busca similar/aproximada (ex: digita "aranhao" com erro ortográfico)
                match_aproximado = False
                for palavra in avaria_norm.split():
                    # Calcula % de semelhança entre o que foi digitado e as palavras da avaria
                    if difflib.SequenceMatcher(None, termo_norm, palavra).ratio() > 0.7:
                        match_aproximado = True
                        break
                
                if match_aproximado:
                    chk.pack(anchor="w", pady=2)
                else:
                    chk.pack_forget() # Esconde a opção se não bater com nada           
    
    def cadastrar_nova_avaria(self):
        nova_avaria = self.input_busca_avaria.get().strip()
        
        if not nova_avaria:
            self.atualizar_status("Aviso: Digite o nome da avaria no campo de pesquisa antes de adicionar.", "yellow")
            return
            
        self.atualizar_status(f"Cadastrando nova avaria: '{nova_avaria}'...", "yellow")
        
        def realizar_request():
            try:
                # Monta a URL baseando-se na configuração (ex: /api/triagem/avarias)
                url = f"{self._cfg.get('api_url', 'http://localhost:5000/api')}/triagem/avarias"
                payload = {"nome": nova_avaria}
                
                response = requests.post(url, json=payload, timeout=5, verify=False)
                
                if response.status_code == 200:
                    self.after(0, lambda: self.atualizar_status(f"Avaria '{nova_avaria}' adicionada com sucesso!", "#00FF00"))
                    # 2. Limpa o campo de pesquisa
                    self.after(0, lambda: self.input_busca_avaria.delete(0, 'end'))
                    
                    # 3. Força a limpeza do filtro visual (para mostrar tudo)
                    self.after(0, self.filtrar_avarias)
                    
                    # 4. Atualiza as listas com a API
                    self.after(0, self.carregar_dominios)
                else:
                    # Tenta extrair a mensagem de erro que você configurou no C# (resultado.Errors)
                    erro_msg = response.text
                    try:
                        erro_json = response.json()
                        erro_msg = erro_json.get("mensagem", erro_msg)
                    except:
                        pass
                    self.after(0, lambda msg=f"Erro ao cadastrar avaria: {erro_msg}": self.atualizar_status(msg, "red"))
                    
            except Exception as e:
                self.after(0, lambda msg=f"Falha de conexão: {e}": self.atualizar_status(msg, "red"))

        threading.Thread(target=realizar_request, daemon=True).start()
                  
    def aplicar_filtro_dropdown(self, combo):
        """Adiciona o evento de digitação para filtrar o combobox usando busca fuzzy."""
        # Salva os valores iniciais (vazios ou 'Carregando...')
        combo._valores_originais = combo.cget("values")
        
        def on_keyrelease(event):
            # Ignora setas do teclado, Tab e Enter para não atrapalhar a navegação
            if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Return', 'Tab']:
                return
                
            termo = combo.get()
            termo_norm = unicodedata.normalize('NFKD', termo).encode('ASCII', 'ignore').decode('utf-8').lower()
            
            # Pega a lista original salva em background no próprio widget
            originais = getattr(combo, '_valores_originais', [])
            
            # Se a caixa de texto estiver vazia, volta a lista inteira
            if not termo_norm or termo == "Carregando..." or termo == "Selecione uma Marca":
                combo.configure(values=originais)
                if hasattr(combo, "_open_dropdown_menu"):
                    combo._open_dropdown_menu()
                return
                
            filtrados = []
            for valor in originais:
                valor_str = str(valor)
                valor_norm = unicodedata.normalize('NFKD', valor_str).encode('ASCII', 'ignore').decode('utf-8').lower()
                
                # Regra 1: O termo digitado faz parte da palavra exata?
                if termo_norm in valor_norm:
                    filtrados.append(valor_str)
                else:
                    # Regra 2: Busca aproximada (tolerância a erros de digitação)
                    for palavra in valor_norm.split():
                        if difflib.SequenceMatcher(None, termo_norm, palavra).ratio() > 0.7:
                            filtrados.append(valor_str)
                            break
                            
            # Atualiza o dropdown apenas com as opções válidas
            combo.configure(values=filtrados if filtrados else [""])
            if hasattr(combo, "_open_dropdown_menu"):
                combo._open_dropdown_menu()

        # O 'add="+"' garante que não vamos sobrescrever os atalhos de <Return> que você já criou
        combo._entry.bind("<KeyRelease>", on_keyrelease, add="+")

    def atualizar_valores_combo(self, combo, valores):
        """Sempre que a API retornar dados novos, usamos essa função para salvar a lista original."""
        combo.configure(values=valores)
        combo._valores_originais = valores
        if combo.get() == "Carregando...":
            combo.set("")
                    
                
if __name__ == "__main__":
    app = SistemaTriagem()
    app.mainloop()