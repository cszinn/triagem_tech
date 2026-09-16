"""
ui/componentes.py — Widgets reutilizáveis para o painel de triagem.
Garante visual moderno e permite digitação livre em todos os campos.
"""

import tkinter as tk
import unicodedata
import difflib
import customtkinter as ctk

# Define uma fonte moderna e maior por padrão
FONTE_LABEL = ("Segoe UI", 14, "bold")
FONTE_ENTRY = ("Segoe UI", 14)


# =============================================================================
#  1. ReadOnlyField — Campo de leitura com estilo verde (dados USB)
# =============================================================================
class ReadOnlyField(ctk.CTkFrame):
    """Campo com label + entry somente-leitura (texto verde)."""

    def __init__(self, master, label_text, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(self, text=label_text, font=ctk.CTkFont(*FONTE_LABEL))
        self._label.pack(anchor="w", pady=(0, 2))

        self._entry = ctk.CTkEntry(
            self, state="disabled",
            text_color="#00FF00", height=35,
            font=ctk.CTkFont(*FONTE_ENTRY, weight="bold")
        )
        self._entry.pack(fill="x")

    def get(self) -> str:
        return self._entry.get()

    def set(self, valor: str, modo_manual=False):
        self._entry.configure(state="normal")
        self._entry.delete(0, 'end')
        if valor is not None:
            self._entry.insert(0, str(valor))
            
        if not modo_manual:
            self._entry.configure(state="disabled", text_color="#00FF00")
        else:
            self._entry.configure(text_color="#FFFFFF")

    def set_editavel(self, editavel: bool):
        if editavel:
            self._entry.configure(state="normal", text_color="#FFFFFF")
        else:
            self._entry.configure(state="disabled", text_color="#00FF00")

    def bind_entry(self, sequence, func):
        self._entry.bind(sequence, func)

    def focus(self):
        self._entry.focus_set()

    def select_all(self):
        self._entry.select_range(0, 'end')


# =============================================================================
#  2. LabeledEntry — Campo de entrada livre com label
# =============================================================================
class LabeledEntry(ctk.CTkFrame):
    """Campo editável simples com label acima."""

    def __init__(self, master, label_text, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(self, text=label_text, font=ctk.CTkFont(*FONTE_LABEL))
        self._label.pack(anchor="w", pady=(0, 2))

        self._entry = ctk.CTkEntry(self, height=35, font=ctk.CTkFont(*FONTE_ENTRY))
        self._entry.pack(fill="x")

    def get(self) -> str:
        return self._entry.get()

    def set(self, valor: str):
        self._entry.delete(0, 'end')
        if valor is not None:
            self._entry.insert(0, str(valor))

    def clear(self):
        self._entry.delete(0, 'end')

    def bind_entry(self, sequence, func):
        self._entry.bind(sequence, func)

    def focus(self):
        self._entry.focus_set()


# =============================================================================
#  3. AutocompleteEntry — Campo com busca fuzzy e entrada TOTALMENTE livre
# =============================================================================
class AutocompleteEntry(ctk.CTkFrame):
    """
    Label + CTkEntry com popup Toplevel de sugestões filtradas.
    PERMITE digitação livre sem interrupção (o usuário pode digitar algo que não está na lista).
    """

    def __init__(self, master, label_text, values=None, command=None, estilo_hw=False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(self, text=label_text, font=ctk.CTkFont(*FONTE_LABEL))
        self._label.pack(anchor="w", pady=(0, 2))

        self._estilo_hw = estilo_hw
        self._entry = ctk.CTkEntry(
            self, height=35, font=ctk.CTkFont(*FONTE_ENTRY, weight="bold")
        )
        
        if estilo_hw:
            self._entry.configure(state="disabled", text_color="#00FF00")
            
        self._entry.pack(fill="x")

        self._values = values or []
        self._command = command
        self._popup_clicando = False
        self._last_notified_value = ""

        # Criar popup Toplevel
        self._popup = tk.Toplevel(self)
        self._popup.withdraw()
        self._popup.overrideredirect(True)
        self._popup.wm_attributes('-topmost', True)

        frame = tk.Frame(self._popup, bg='#2F80ED', relief='flat', bd=2) # Cor mais premium na borda
        frame.pack(fill='both', expand=True)

        scrollbar = tk.Scrollbar(frame, bg='#333333', troughcolor='#1E1E1E',
                                  relief='flat', width=10)
        scrollbar.pack(side='right', fill='y')

        self._listbox = tk.Listbox(
            frame,
            yscrollcommand=scrollbar.set,
            bg='#1E1E1E', fg='#E0E0E0',
            selectbackground='#2F80ED', selectforeground='#FFFFFF',
            relief='flat', borderwidth=0, highlightthickness=0,
            font=('Segoe UI', 12), activestyle='none', cursor='hand2',
        )
        self._listbox.pack(side='left', fill='both', expand=True, padx=2, pady=2)
        scrollbar.config(command=self._listbox.yview)

        # Bindings do entry
        self._entry.bind('<KeyRelease>', self._on_keyrelease, add='+')
        self._entry.bind('<Button-1>', self._on_click_entry, add='+')
        self._entry.bind('<FocusOut>', self._on_focusout, add='+')

        # Bindings da listbox
        self._listbox.bind('<ButtonPress-1>', lambda e: setattr(self, '_popup_clicando', True))
        self._listbox.bind('<ButtonRelease-1>', self._selecionar)
        self._listbox.bind('<FocusOut>', lambda e: self.after(100, self._fechar_popup))

    def _notificar(self, valor: str):
        """Dispara o comando (callback) apenas se o valor mudou desde a última vez."""
        if self._command and valor != self._last_notified_value:
            self._last_notified_value = valor
            self._command(valor)

    def _filtrar(self, termo: str) -> list:
        termo_norm = unicodedata.normalize('NFKD', termo).encode('ASCII', 'ignore').decode('utf-8').lower()
        if not termo_norm or termo in ["Carregando...", "Selecione..."]:
            return self._values

        filtrados = []
        for valor in self._values:
            valor_str = str(valor)
            valor_norm = unicodedata.normalize('NFKD', valor_str).encode('ASCII', 'ignore').decode('utf-8').lower()
            if termo_norm in valor_norm:
                filtrados.append(valor_str)
            else:
                for palavra in valor_norm.split():
                    if difflib.SequenceMatcher(None, termo_norm, palavra).ratio() > 0.7:
                        filtrados.append(valor_str)
                        break
        return filtrados

    def _mostrar_popup(self, valores):
        if not valores:
            self._fechar_popup()
            return

        self._listbox.delete(0, 'end')
        for v in valores:
            self._listbox.insert('end', '  ' + str(v))

        self.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height()
        w = self._entry.winfo_width()
        h = min(len(valores), 6) * 26 + 4

        self._popup.geometry(f"{w}x{h}+{x}+{y}")
        self._popup.deiconify()
        self._popup.lift()
        self._entry.focus_set()

    def _fechar_popup(self):
        try:
            self._popup.withdraw()
        except Exception:
            pass

    def _selecionar(self, event=None):
        """Disparado ao clicar na lista."""
        sel = self._listbox.curselection()
        if sel:
            valor = self._listbox.get(sel[0]).strip()
            # Restaurar estado original de edição temporariamente
            estado_anterior = self._entry.cget("state")
            self._entry.configure(state="normal")
            self._entry.delete(0, 'end')
            self._entry.insert(0, valor)
            self._entry.configure(state=estado_anterior)
            
            self._fechar_popup()
            self._entry.focus_set()
            
            if valor:
                self._notificar(valor)
        self._popup_clicando = False

    def _on_keyrelease(self, event):
        if self._entry.cget("state") == "disabled":
            return
            
        if event.keysym == 'Escape':
            self._fechar_popup()
            return
        if event.keysym == 'Return':
            # Enter fecha a lista e dispara o comando com o texto que o usuário digitou livremente
            valor = self._entry.get().strip()
            self._fechar_popup()
            if valor:
                self._notificar(valor)
            return
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Tab'):
            return

        resultado = self._filtrar(self._entry.get())
        self._mostrar_popup(resultado)

    def _on_click_entry(self, event):
        if self._entry.cget("state") == "disabled":
            return
        resultado = self._filtrar(self._entry.get())
        self._mostrar_popup(resultado if resultado else self._values)

    def _on_focusout(self, event):
        # Fecha o popup e notifica se houve alteração manual
        def _verificar():
            if not self._popup_clicando:
                self._fechar_popup()
                valor = self._entry.get().strip()
                if valor:
                    self._notificar(valor)
        self.after(150, _verificar)

    # --- API pública ---
    def get(self) -> str:
        return self._entry.get().strip()

    def set(self, valor: str, modo_manual=False):
        self._entry.configure(state="normal")
        self._entry.delete(0, 'end')
        if valor is not None:
            self._entry.insert(0, str(valor))
            
        if self._estilo_hw:
            if not modo_manual:
                self._entry.configure(state="disabled", text_color="#00FF00")
            else:
                self._entry.configure(state="normal", text_color="#FFFFFF")

    def set_values(self, values: list):
        self._values = values

    def set_editavel(self, editavel: bool):
        if self._estilo_hw:
            if editavel:
                self._entry.configure(state="normal", text_color="#FFFFFF")
            else:
                self._entry.configure(state="disabled", text_color="#00FF00")

    def bind_entry(self, sequence, func):
        self._entry.bind(sequence, func)

    def focus(self):
        self._entry.focus_set()
