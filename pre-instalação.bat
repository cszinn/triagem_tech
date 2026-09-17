@echo off
echo =======================================================
echo     Instalador Automatico - Sistema de Triagem
echo =======================================================
echo.

echo [1/4] Instalando Python 3.14 via Winget...
winget install --id Python.Python.3.14 --silent --accept-package-agreements --accept-source-agreements

echo.
echo [2/4] Instalando Apple Devices (Drivers iOS)...
winget install --id 9NP83LWLPZ9K --exact --accept-package-agreements --accept-source-agreements

echo.
echo [3/4] Configurando o PATH do Windows...
setx PATH "%PATH%;%~dp0platform-tools" /M

echo.
echo [4/4] Instalando dependencias do Python...
timeout /t 5 /nobreak > NUL

:: Tenta instalar usando o Launcher nativo do Python (que ja deve estar no PATH)
py -m pip install --upgrade pip
py -m pip install -r "%~dp0requirements.txt"

if %errorlevel% neq 0 (
    echo.
    echo [AVISO IMPORTANTE]
    echo Falha ao instalar modulos. O Windows ainda nao reconheceu o Python instalado.
    echo Por favor, FECHE esta janela e EXECUTE ESTE ARQUIVO NOVAMENTE para concluir!
    echo.
)

echo.
echo =======================================================
echo   Instalacao concluida com sucesso!
echo   Por favor, REINICIE O COMPUTADOR para aplicar o PATH.
echo =======================================================
pause