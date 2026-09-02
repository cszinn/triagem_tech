import sys
import os
import subprocess
import threading
import webbrowser
import customtkinter as ctk

# Configuração visual base
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class HubApplication(ctk.CTk):
    def __init__(self):
        super().__init__()

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
        
        self.lbl_title.pack(pady=(10, 0))
        
        self.lbl_subtitle = ctk.CTkLabel(self.frame_top, text="Selecione o módulo que deseja acessar", text_color="gray", font=ctk.CTkFont(size=16))
        self.lbl_subtitle.pack(pady=(5, 10))

        # Container dos Cards
        self.frame_cards = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_cards.grid(row=1, column=0, padx=40, pady=20)
        
        # Grid 2x2 para os cards
        self.frame_cards.grid_columnconfigure(0, weight=1)
        self.frame_cards.grid_columnconfigure(1, weight=1)

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
        self.lbl_rodape = ctk.CTkLabel(self, text="Instituto ITI - Versão 1.0", text_color="gray", font=ctk.CTkFont(size=12))
        self.lbl_rodape.grid(row=2, column=0, sticky="s", pady=20)

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

    # --- Ações dos Módulos ---

    def abrir_triagem(self):
        """Abre o aplicativo painel_triagem.py como um subprocesso e minimiza o HUB."""
        def run_app():
            self.after(0, self.withdraw) # Minimiza o hub
            
            caminho_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "painel_triagem.py")
            caminho_python = sys.executable
            
            # Executa o script bloqueando a thread (por isso usamos threading.Thread)
            subprocess.run([caminho_python, caminho_script])
            
            # Quando a triagem for fechada, restaura o HUB
            self.after(0, self.deiconify)
            
        threading.Thread(target=run_app, daemon=True).start()

    def abrir_consulta(self):
        """Abre a página web de consulta no navegador."""
        url = "https://useful-gecko-present.ngrok-free.app/consulta" # Placeholder link
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
