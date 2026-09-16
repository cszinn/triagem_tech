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
python -m pip install --upgrade pip
python -m pip install -r "%~dp0requirements.txt"

echo.
echo =======================================================
echo   Instalacao concluida com sucesso!
echo   Por favor, REINICIE O COMPUTADOR para aplicar o PATH.
echo =======================================================
pause