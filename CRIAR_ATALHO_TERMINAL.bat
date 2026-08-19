@echo off
setlocal EnableExtensions

:: Cria um atalho .url no Desktop do terminal para o Registro Fácil central.
:: Uso: CRIAR_ATALHO_TERMINAL.bat http://192.168.0.10:5000

set "SERVER_URL=%~1"
if not defined SERVER_URL set /p "SERVER_URL=Digite a URL do servidor central (ex.: http://192.168.0.10:5000): "
if not defined SERVER_URL (
    echo [ERRO] URL nao informada.
    pause
    exit /b 1
)

if /i not "%SERVER_URL:~0,7%"=="http://" if /i not "%SERVER_URL:~0,8%"=="https://" (
    echo [ERRO] A URL deve iniciar com http:// ou https://.
    pause
    exit /b 1
)

set "SHORTCUT=%USERPROFILE%\Desktop\Registro Facil - Servidor.url"
>"%SHORTCUT%" echo [InternetShortcut]
>>"%SHORTCUT%" echo URL=%SERVER_URL%
>>"%SHORTCUT%" echo IconIndex=0

echo Atalho criado em:
echo %SHORTCUT%
echo Destino: %SERVER_URL%
pause
exit /b 0
