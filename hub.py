import sys
import os
import subprocess
import threading
import json
import customtkinter as ctk
import config as cfg_module
from servicos import api_client

# Configuração visual base
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class HubApplication(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self._cfg = cfg_module.carregar()
        self.usuario_id = "1"
        self.usuario_nome = "Operador"

        # --- Responsividade para Telas de Notebook (ex: 1366x768) ---
        altura_tela = self.winfo_screenheight()
        if altura_tela <= 800:
            ctk.set_window_scaling(0.85)
            ctk.set_widget_scaling(0.85)

        self.title("ITI TECH - Hub Central")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Centraliza o conteúdo na tela
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Cabeçalho
        self.frame_top = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_top.grid(row=0, column=0, sticky="nsew", pady=(30, 0))
        
        try:
            from PIL import Image
            logo_img = ctk.CTkImage(light_image=Image.open("logo_hq_cropped.png"),
                                    dark_image=Image.open("logo_hq_cropped.png"),
                                    size=(312, 80))
            self.lbl_title = ctk.CTkLabel(self.frame_top, image=logo_img, text="")
        except Exception as e:
            print("Logo não encontrada:", e)
            self.lbl_title = ctk.CTkLabel(self.frame_top, text="ITI TECH", font=ctk.CTkFont(size=36, weight="bold"))
        
        self.lbl_title.pack(pady=(0, 10))
        
        self.lbl_subtitle = ctk.CTkLabel(self.frame_top, text="Faça login para acessar os módulos.", text_color="gray", font=ctk.CTkFont(size=16))
        self.lbl_subtitle.pack(pady=(10, 0))

        # ----------------------------------------------------
        # 1. BOTÃO DE LOGIN WEB (Exibido primeiro)
        # ----------------------------------------------------
        self.frame_login = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_login.grid(row=1, column=0, padx=40, pady=20)
        
        lbl_instrucao = ctk.CTkLabel(self.frame_login, text="Autenticação Requerida", font=ctk.CTkFont(size=20, weight="bold"))
        lbl_instrucao.pack(pady=(10, 20))
        
        self.btn_login = ctk.CTkButton(
            self.frame_login, text="🌐 ABRIR JANELA DE LOGIN", height=50, width=350,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2F80ED", hover_color="#1F61B8",
            command=self._iniciar_login_web
        )
        self.btn_login.pack(pady=10)
        
        self.lbl_status_login = ctk.CTkLabel(self.frame_login, text="O login abrirá em uma nova janela interna.", text_color="gray", font=ctk.CTkFont(size=13))
        self.lbl_status_login.pack(pady=10)

        # ----------------------------------------------------
        # 2. FRAME DE CARDS DOS MÓDULOS (Escondido inicialmente)
        # ----------------------------------------------------
        self.frame_cards = ctk.CTkFrame(self, fg_color="transparent")
        
        # Grid para os cards
        self.frame_cards.grid_columnconfigure(0, weight=1)
        self.frame_cards.grid_columnconfigure(1, weight=1)
        
        # Botão de Logout (Sair) - Ficará no canto da tela
        self.btn_logout = ctk.CTkButton(
            self, text="Sair (Logout)", fg_color="#444444", hover_color="#FF4C4C",
            width=120, height=30, font=ctk.CTkFont(size=12, weight="bold"),
            command=self.fazer_logout
        )
        
        # Criação dos Cards
        self.criar_card(
            parent=self.frame_cards,
            row=0, col=0,
            titulo="📦 Painel de Triagem",
            descricao="Módulo físico para auditoria, triagem e impressão de etiquetas térmicas.",
            cor_botao="#1f6aa5",
            comando=self.abrir_triagem
        )

        self.criar_card(
            parent=self.frame_cards,
            row=0, col=1,
            titulo="🔍 Consulta Web",
            descricao="Consultar dados de aparelhos já triados na base de dados.",
            cor_botao="#444444",
            comando=self.abrir_consulta
        )

        self.criar_card(
            parent=self.frame_cards,
            row=1, col=0,
            titulo="🗄️ Banco de Dados",
            descricao="Acesso direto à interface administrativa do Banco de Dados via Ngrok.",
            cor_botao="#248753",
            comando=self.abrir_banco_dados
        )

        self.criar_card(
            parent=self.frame_cards,
            row=1, col=1,
            titulo="🔒 Módulo Futuro",
            descricao="Espaço reservado para futuras implementações no sistema.",
            cor_botao="#333333",
            comando=None,
            estado="disabled"
        )

        # Rodapé
        self.lbl_rodape = ctk.CTkLabel(self, text="Instituto ITI - Versão 2.0.1", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_rodape.grid(row=2, column=0, sticky="s", pady=20)
        
        # Tenta logar automaticamente ao iniciar
        self.after(500, self.tentar_auto_login)

    def criar_card(self, parent, row, col, titulo, descricao, cor_botao, comando, estado="normal"):
        """Cria um cartão clicável para um módulo do sistema."""
        frame_card = ctk.CTkFrame(parent, width=350, height=180, corner_radius=15)
        frame_card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
        frame_card.grid_propagate(False) # Mantém tamanho fixo

        lbl_titulo = ctk.CTkLabel(frame_card, text=titulo, font=ctk.CTkFont(size=20, weight="bold"))
        lbl_titulo.pack(pady=(20, 5), padx=20, anchor="w")

        lbl_desc = ctk.CTkLabel(frame_card, text=descricao, font=ctk.CTkFont(size=12), text_color="gray", wraplength=300, justify="left")
        lbl_desc.pack(pady=(5, 15), padx=20, anchor="w", fill="x", expand=True)

        if estado == "normal":
            btn = ctk.CTkButton(frame_card, text="Acessar Módulo", fg_color=cor_botao, command=comando)
            btn.pack(pady=(0, 20), padx=20, anchor="e")
        else:
            btn = ctk.CTkButton(frame_card, text="Em Breve", fg_color=cor_botao, state="disabled")
            btn.pack(pady=(0, 20), padx=20, anchor="e")

    # --- Lógica de Login Web (Extração e Cache de Cookies) ---
    
    def arquivo_sessao(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sessao.json")
    
    def salvar_sessao(self):
        dados = {
            "usuario_id": self.usuario_id,
            "usuario_nome": self.usuario_nome,
            "cookies": getattr(self, "cookies", {})
        }
        try:
            with open(self.arquivo_sessao(), "w", encoding="utf-8") as f:
                json.dump(dados, f)
        except Exception as e:
            print("Erro ao salvar sessao:", e)
            
    def fazer_logout(self):
        self.usuario_id = "1"
        self.usuario_nome = "Operador"
        self.cookies = {}
        api_client.configurar_sessao_com_cookies(self.cookies)
        
        try:
            os.remove(self.arquivo_sessao())
        except:
            pass
            
        self.frame_cards.grid_forget()
        self.btn_logout.grid_forget()
        self.lbl_subtitle.configure(text="Faça login para acessar os módulos.")
        self.lbl_status_login.configure(text="Sessão encerrada.", text_color="gray")
        self.btn_login.configure(state="normal")
        self.frame_login.grid(row=1, column=0, padx=40, pady=20)
        
    def tentar_auto_login(self):
        arquivo = self.arquivo_sessao()
        if os.path.exists(arquivo):
            self.lbl_status_login.configure(text="Restaurando sessão anterior...", text_color="#E2B93B")
            self.btn_login.configure(state="disabled")
            self.update()
            
            try:
                with open(arquivo, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    
                self.usuario_id = dados.get("usuario_id", "1")
                self.usuario_nome = dados.get("usuario_nome", "Operador")
                self.cookies = dados.get("cookies", {})
                api_client.configurar_sessao_com_cookies(self.cookies)
                
                # Teste silencioso para ver se a API não rejeita o cookie
                url_api = self._cfg.get("api_url", "https://useful-gecko-present.ngrok-free.app/api")
                
                def checar_api():
                    try:
                        # Puxa dominios só como teste
                        api_client.carregar_dominios(url_api)
                        self.after(0, self._exibir_modulos)
                    except Exception as e:
                        # Se deu erro, provavelmente o cookie expirou ou a API está offline
                        print("Sessao expirada ou falha ao checar API:", e)
                        self.after(0, self.fazer_logout)
                        
                threading.Thread(target=checar_api, daemon=True).start()
                
            except Exception as e:
                print("Erro ao ler sessao cacheada:", e)
                self.fazer_logout()
                
    def _iniciar_login_web(self):
        self.lbl_status_login.configure(text="Aguardando autenticação na janela...", text_color="#E2B93B")
        self.btn_login.configure(state="disabled")
        self.update()
        
        def iniciar_webview():
            url_api = self._cfg.get("api_url", "https://useful-gecko-present.ngrok-free.app/api")
            url_base = url_api.replace("/api", "")
            url_login = f"{url_base}/login" 
            
            caminho_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_webview.py")
            caminho_python = sys.executable
            
            CREATE_NO_WINDOW = 0x08000000
            proc = subprocess.Popen(
                [caminho_python, caminho_script, url_login],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=CREATE_NO_WINDOW
            )
            
            saida, erro = proc.communicate()
            
            try:
                # O script do webview vai imprimir o JSON com sucesso e cookies
                import re
                # Pega a última linha válida em formato JSON (pois o CEF pode printar lixo)
                match = re.search(r'(\{.*sucesso.*\})', saida)
                if match:
                    dados = json.loads(match.group(1))
                    if dados.get("sucesso"):
                        self.usuario_nome = dados.get("usuario_nome", "Operador")
                        # Vamos usar o nome/email como ID caso o ID numérico não venha na página
                        self.usuario_id = self.usuario_nome 
                        
                        # Injetar os cookies
                        self.cookies = dados.get("cookies", {})
                        api_client.configurar_sessao_com_cookies(self.cookies)
                        
                        self.salvar_sessao()
                        self.after(0, self._exibir_modulos)
                        return
                        
                # Se não achar JSON ou sucesso=False
                self.after(0, lambda: self.btn_login.configure(state="normal"))
                self.after(0, lambda: self.lbl_status_login.configure(text="Login cancelado ou falhou.", text_color="#FF4C4C"))
            except Exception as e:
                import traceback
                erro_detalhado = traceback.format_exc()
                with open("error.log", "w", encoding="utf-8") as f:
                    f.write(f"Erro na captura: {e}\n\nTraceback:\n{erro_detalhado}\n\nSaída Bruta:\n{saida}\n")
                
                print(f"Erro na captura: {e}. Saída: {saida}")
                self.after(0, lambda: self.btn_login.configure(state="normal"))
                self.after(0, lambda: self.lbl_status_login.configure(text=f"Erro: {str(e)[:40]}", text_color="#FF4C4C"))

        threading.Thread(target=iniciar_webview, daemon=True).start()

    def _exibir_modulos(self):
        # Esconde o login
        self.frame_login.grid_forget()
        
        # Altera o subtitulo e mostra os cards
        self.lbl_subtitle.configure(text=f"Bem-vindo(a), {self.usuario_nome}! Selecione o módulo:")
        self.frame_cards.grid(row=1, column=0, padx=40, pady=20)
        
        # Coloca o botão de logout no canto inferior direito
        self.btn_logout.grid(row=2, column=0, sticky="se", padx=30, pady=20)

    # --- Ações dos Módulos ---

    def abrir_triagem(self):
        """Abre o aplicativo painel_triagem.py como um subprocesso e minimiza o HUB."""
        def run_app():
            self.after(0, self.withdraw) # Minimiza o hub
            
            caminho_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painel_triagem.py")
            caminho_python = sys.executable
            
            # Criptografa os cookies em Base64 para passar na linha de comando
            import base64
            import json
            cookies_str = json.dumps(getattr(self, "cookies", {}))
            token = base64.b64encode(cookies_str.encode('utf-8')).decode('utf-8')
            
            # Passa ID, Nome e Token como argumentos obrigatórios
            cmd = [
                caminho_python, caminho_script,
                "--usuario-id", str(self.usuario_id),
                "--usuario-nome", self.usuario_nome,
                "--session-token", token
            ]
            
            subprocess.run(cmd)
            
            # Quando a triagem for fechada, restaura o HUB
            self.after(0, self.deiconify)
            
        threading.Thread(target=run_app, daemon=True).start()

    def abrir_consulta(self):
        """Abre a página web de consulta no navegador."""
        url = "https://useful-gecko-present.ngrok-free.app/estoque"
        try:
            webbrowser.open(url)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erro", f"Não foi possível abrir o navegador: {e}")

    def abrir_banco_dados(self):
        """Abre o navegador padrão no endereço do BD."""
        url = "https://useful-gecko-present.ngrok-free.app/"
        try:
            webbrowser.open(url)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Erro", f"Não foi possível abrir o navegador: {e}")

if __name__ == "__main__":
    app = HubApplication()
    app.mainloop()
