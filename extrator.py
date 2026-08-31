import subprocess
import time

def checar_dispositivo():
    # Verifica os dispositivos conectados via ADB
    resultado = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    linhas = resultado.stdout.strip().split('\n')
    
    if len(linhas) > 1:
        # Pega o status do primeiro aparelho da lista
        status_aparelho = linhas[1]
        
        if "unauthorized" in status_aparelho:
            print("\n[Aviso] Celular conectado, mas precisa de autorização. Olhe a tela do celular e confirme a Depuração USB.")
            time.sleep(3)
            return None
            
        dispositivo = status_aparelho.split('\t')[0]
        if dispositivo and dispositivo != "offline":
            return dispositivo
            
    return None

def extrair_dados():
    print("\n[+] Extraindo dados da placa-mãe...")
    
    # Comandos para puxar as propriedades do sistema
    marca = subprocess.getoutput('adb shell getprop ro.product.brand').strip().capitalize()
    modelo = subprocess.getoutput('adb shell getprop ro.product.model').strip()
    serie = subprocess.getoutput('adb shell getprop ro.serialno').strip()
    
    print("\n--- Dados Coletados ---")
    print(f"Marca: {marca}")
    print(f"Modelo: {modelo}")
    print(f"S/N: {serie}")
    print("-----------------------\n")

def iniciar_triagem():
    print("Sistema de Triagem Iniciado.")
    print("Aguardando celular na porta USB...")
    
    while True:
        disp = checar_dispositivo()
        if disp:
            print(f"\nCelular detectado (ID: {disp})")
            extrair_dados()
            
            print("Pode desconectar o aparelho. Aguardando o próximo...")
            # Pausa para dar tempo de tirar o cabo
            time.sleep(10) 
        time.sleep(2)

if __name__ == "__main__":
    iniciar_triagem()