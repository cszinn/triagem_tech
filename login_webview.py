import sys
import webview
import json
import time

def on_loaded(window):
    # Pega a URL atual
    current_url = window.get_current_url()
    
    # Se a URL não contiver 'login', assumimos que o usuário logou e foi para o dashboard
    if "login" not in current_url.lower():
        try:
            # Pega todos os cookies
            cookies = window.get_cookies()
            cookies_dict = {}
            for c in cookies:
                # pywebview retorna objetos ou dicts dependendo do backend. 
                # Vamos tentar formatar para dict simples
                if hasattr(c, 'name') and hasattr(c, 'value'):
                    cookies_dict[c.name] = c.value
                elif isinstance(c, dict):
                    cookies_dict[c.get('name', '')] = c.get('value', '')
            
            # Tenta pegar algum texto que pareça um email na tela (ex: cs.off@outlook.com)
            # Um script basico pra achar texto com @ 
            js_script = r"""
            (function() {
                var bodyText = document.body.innerText;
                var emailRegex = /([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]+)/;
                var match = bodyText.match(emailRegex);
                return match ? match[1] : 'Operador';
            })();
            """
            nome = window.evaluate_js(js_script)
            if not nome:
                nome = "Operador"
                
            resultado = {
                "sucesso": True,
                "usuario_nome": nome,
                "cookies": cookies_dict
            }
            
            print(json.dumps(resultado))
            sys.stdout.flush()
            
            # Fecha a janela logo após extrair
            time.sleep(1)
            window.destroy()
        except Exception as e:
            # Silencia erros e continua
            pass

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"sucesso": False, "erro": "URL nao fornecida"}))
        sys.exit(1)
        
    url = sys.argv[1]
    
    # Cria a janela
    window = webview.create_window("Login - Triagem Tech", url, width=600, height=700)
    window.events.loaded += on_loaded
    
    # private_mode=True cria um perfil em-memória (previne o erro 0x800700AA de pasta travada)
    webview.start(private_mode=True) 

if __name__ == '__main__':
    main()
