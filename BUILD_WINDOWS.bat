@echo off
:: ============================================================================
::  RegistroFacil v3.27.0 - Script de Compilacao para Windows
::  Gera um executavel standalone (.exe) via PyInstaller
::  Compativel com: Windows 10/11, x64 e x86
:: ============================================================================
setlocal EnableDelayedExpansion

:: ── Configuraçoes do projeto ─────────────────────────────────────────────────
set "APP_NAME=RegistroFacil"
set "APP_VERSION=3.27.0"
set "MAIN_SCRIPT=app.py"
set "ICON_PATH=static\img\certificate.ico"
set "DIST_DIR=dist"
set "BUILD_DIR=build_temp"
set "SPEC_DIR=."

:: ── Pasta de trabalho = pasta do script ──────────────────────────────────────
:: CORRIGIDO: o .bat já está dentro da pasta do projeto, não usar subpasta
cd /d "%~dp0"

:: ── Banner ───────────────────────────────────────────────────────────────────
echo.
echo  ==========================================================
echo   RegistroFacil v%APP_VERSION% - Compilador de Executavel
echo  ==========================================================
echo.

:: ── 1. Verificar Python ──────────────────────────────────────────────────────
echo [1/7] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado no PATH.
    echo         Instale Python 3.10+ e adicione ao PATH do sistema.
    echo         Download: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo  Python !PY_VER! encontrado.

:: ── 2. Verificar/Instalar pip ────────────────────────────────────────────────
echo.
echo [2/7] Verificando pip e dependencias...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] pip nao encontrado. Reinstale Python com pip incluido.
    pause
    exit /b 1
)

:: Atualizar pip silenciosamente
python -m pip install --upgrade pip --quiet

:: Instalar dependencias do projeto
echo  Instalando dependencias do requirements.txt...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [AVISO] Alguns pacotes podem nao ter instalado corretamente.
    echo          Verifique o requirements.txt manualmente se houver erros.
)

:: Instalar PyInstaller
echo  Instalando/atualizando PyInstaller...
python -m pip install pyinstaller --upgrade --quiet
if errorlevel 1 (
    echo  [ERRO] Falha ao instalar PyInstaller.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python -m PyInstaller --version 2^>^&1') do set PI_VER=%%v
echo  PyInstaller !PI_VER! pronto.

:: ── 3. Limpar compilacoes anteriores ─────────────────────────────────────────
echo.
echo [3/7] Limpando compilacoes anteriores...
if exist "%DIST_DIR%\%APP_NAME%" (
    rmdir /s /q "%DIST_DIR%\%APP_NAME%"
    echo  Pasta dist anterior removida.
)
if exist "%BUILD_DIR%" (
    rmdir /s /q "%BUILD_DIR%"
    echo  Pasta build anterior removida.
)
if exist "%APP_NAME%.spec" (
    del /q "%APP_NAME%.spec"
    echo  Arquivo .spec anterior removido.
)
echo  Limpeza concluida.

:: ── 4. Verificar ativo WeasyPrint (dependencias nativas) ─────────────────────
echo.
echo [4/7] Verificando dependencias nativas (WeasyPrint/GTK)...
python -c "import weasyprint; print('  WeasyPrint OK')" 2>nul
if errorlevel 1 (
    echo  [AVISO] WeasyPrint nao encontrado ou sem GTK instalado.
    echo         A geracao de PDF pode nao funcionar no executavel.
    echo         Para suporte a PDF, instale GTK3 Runtime:
    echo         https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
    echo.
    echo  Continuando compilacao sem WeasyPrint nativo...
    set "WEASYPRINT_EXCLUDE=--exclude-module weasyprint --exclude-module cairocffi --exclude-module cairosvg --exclude-module tinycss2 --exclude-module cssselect2"
) else (
    set "WEASYPRINT_EXCLUDE="
)

:: ── 5. Detectar arquitetura e configurar ─────────────────────────────────────
echo.
echo [5/7] Detectando arquitetura do sistema...
python -c "import platform; print(platform.machine())" > %TEMP%\arch.tmp 2>nul
set /p SYS_ARCH=<%TEMP%\arch.tmp
del %TEMP%\arch.tmp
echo  Arquitetura detectada: !SYS_ARCH!

:: ── 6. Compilar com PyInstaller ──────────────────────────────────────────────
echo.
echo [6/7] Compilando executavel (pode demorar alguns minutos)...
echo.

python -m PyInstaller ^
    --name "%APP_NAME%" ^
    --onedir ^
    --windowed ^
    --icon="%ICON_PATH%" ^
    --distpath="%DIST_DIR%" ^
    --workpath="%BUILD_DIR%" ^
    --specpath="%SPEC_DIR%" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "config.py;." ^
    --add-data "models.py;." ^
    --add-data "routes;routes" ^
    --add-data "utils;utils" ^
    --hidden-import "flask" ^
    --hidden-import "flask.templating" ^
    --hidden-import "flask.json" ^
    --hidden-import "jinja2" ^
    --hidden-import "jinja2.ext" ^
    --hidden-import "jinja2.loaders" ^
    --hidden-import "jinja2.environment" ^
    --hidden-import "waitress" ^
    --hidden-import "waitress.server" ^
    --hidden-import "waitress.task" ^
    --hidden-import "waitress.channel" ^
    --hidden-import "bcrypt" ^
    --hidden-import "cryptography" ^
    --hidden-import "cryptography.fernet" ^
    --hidden-import "cryptography.hazmat.primitives" ^
    --hidden-import "cryptography.hazmat.backends" ^
    --hidden-import "cryptography.hazmat.backends.openssl" ^
    --hidden-import "cryptography.hazmat.primitives.kdf.pbkdf2" ^
    --hidden-import "apscheduler" ^
    --hidden-import "apscheduler.schedulers.background" ^
    --hidden-import "apscheduler.triggers.interval" ^
    --hidden-import "apscheduler.triggers.cron" ^
    --hidden-import "apscheduler.executors.pool" ^
    --hidden-import "openpyxl" ^
    --hidden-import "openpyxl.styles" ^
    --hidden-import "openpyxl.utils" ^
    --hidden-import "openpyxl.writer.excel" ^
    --hidden-import "openpyxl.reader.excel" ^
    --hidden-import "paramiko" ^
    --hidden-import "paramiko.transport" ^
    --hidden-import "paramiko.auth_handler" ^
    --hidden-import "pytz" ^
    --hidden-import "pytz.tzinfo" ^
    --hidden-import "nacl" ^
    --hidden-import "nacl.secret" ^
    --hidden-import "nacl.utils" ^
    --hidden-import "sqlite3" ^
    --hidden-import "email_validator" ^
    --hidden-import "flask_mail" ^
    --hidden-import "werkzeug" ^
    --hidden-import "werkzeug.security" ^
    --hidden-import "werkzeug.serving" ^
    --hidden-import "pkg_resources" ^
    --hidden-import "pkg_resources.py2_warn" ^
    --hidden-import "routes.auth" ^
    --hidden-import "routes.processos" ^
    --hidden-import "routes.titulares" ^
    --hidden-import "routes.atividades" ^
    --hidden-import "routes.search" ^
    --hidden-import "routes.admin_users" ^
    --hidden-import "routes.configuracoes" ^
    --hidden-import "routes.dashboard" ^
    --hidden-import "routes.backup" ^
    --hidden-import "routes.empresa" ^
    --hidden-import "routes.notificacoes" ^
    --hidden-import "routes.permissoes" ^
    --hidden-import "routes.perfil" ^
    --hidden-import "utils.logger" ^
    --hidden-import "utils.logger_config" ^
    --hidden-import "utils.helpers" ^
    --hidden-import "utils.browser_launcher" ^
    --hidden-import "utils.db_lock" ^
    --hidden-import "utils.db_crypto" ^
    --hidden-import "utils.file_uploads" ^
    --hidden-import "utils.messages" ^
    --hidden-import "utils.scheduler" ^
    --hidden-import "utils.permissions_helper" ^
    --hidden-import "utils.startup_auth" ^
    --collect-submodules "flask" ^
    --collect-submodules "jinja2" ^
    --collect-submodules "waitress" ^
    --collect-submodules "cryptography" ^
    --collect-submodules "apscheduler" ^
    --collect-data "flask" ^
    --collect-data "jinja2" ^
    --noconfirm ^
    --clean ^
    "%MAIN_SCRIPT%"

if errorlevel 1 (
    echo.
    echo  [ERRO] A compilacao falhou. Verifique as mensagens acima.
    echo         Dicas comuns de solucao:
    echo         - Execute como Administrador
    echo         - Desative o Antivirus temporariamente
    echo         - Verifique se todas as dependencias estao instaladas
    pause
    exit /b 1
)

:: ── 7. Pos-compilacao: ajustes e verificacao ──────────────────────────────────
echo.
echo [7/7] Finalizando e verificando saida...

set "OUT_DIR=%DIST_DIR%\%APP_NAME%"

:: Verificar se o exe foi gerado
if not exist "%OUT_DIR%\%APP_NAME%.exe" (
    echo  [ERRO] Executavel nao encontrado em %OUT_DIR%\
    pause
    exit /b 1
)

:: Criar arquivo de versao
echo RegistroFacil v%APP_VERSION% > "%OUT_DIR%\versao.txt"
echo Compilado em: %DATE% %TIME% >> "%OUT_DIR%\versao.txt"
echo Arquitetura: !SYS_ARCH! >> "%OUT_DIR%\versao.txt"

:: Tamanho da pasta de saida
for /f "tokens=3" %%s in ('dir /s "%OUT_DIR%" ^| find "File(s)"') do set DIR_SIZE=%%s
echo.
echo  ==========================================================
echo   COMPILACAO CONCLUIDA COM SUCESSO!
echo  ==========================================================
echo.
echo   Executavel: %OUT_DIR%\%APP_NAME%.exe
echo   Versao:     %APP_VERSION%
echo   Sistema:    !SYS_ARCH!
echo.
echo   PROXIMOS PASSOS:
echo   1. Teste o executavel em %OUT_DIR%\
echo   2. Execute o Inno Setup com INSTALADOR_RegistroFacil.iss
echo      para gerar o instalador profissional.
echo.
echo  ==========================================================
echo.

:: Abrir pasta de saida no Explorer
explorer "%OUT_DIR%"

pause
exit /b 0
