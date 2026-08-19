@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: ============================================================================
:: Registro Fácil — Build Windows
:: Compila o servidor central em modo onedir usando um ambiente de build isolado.
:: Requer Windows 10/11 x64 ou x86 e Python 3.11 instalado.
:: ============================================================================

cd /d "%~dp0"
set "APP_NAME=RegistroFacil"
set "MAIN_SCRIPT=app.py"
set "ICON_PATH=static\img\certificate.ico"
set "DIST_DIR=dist"
set "BUILD_DIR=build_temp"
set "VENV_DIR=.venv-build"
set "OUT_DIR=%DIST_DIR%\%APP_NAME%"
set "PY_EXE="
set "PY_ARGS="

if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 goto :venv_ready
    echo [INFO] Ambiente virtual existente nao usa Python 3.11; recriando.
    rmdir /s /q "%VENV_DIR%"
)

:: 1) Python Launcher: funciona mesmo quando python.exe nao esta no PATH.
where py >nul 2>&1
if not errorlevel 1 (
    py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_EXE=py"
        set "PY_ARGS=-3.11"
        goto :python_ready
    )
)

:: 2) Interpretadores expostos diretamente no PATH.
for %%C in (python3.11 python3 python) do (
    where %%C >nul 2>&1
    if not errorlevel 1 (
        %%C -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
        if not errorlevel 1 (
            set "PY_EXE=%%C"
            set "PY_ARGS="
            goto :python_ready
        )
    )
)

:: 3) Instalacoes comuns do Python.org fora do PATH.
for %%P in ("%LocalAppData%\Programs\Python\Python311\python.exe" "%ProgramFiles%\Python311\python.exe" "%ProgramFiles(x86)%\Python311\python.exe") do (
    if exist "%%~P" (
        "%%~P" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
        if not errorlevel 1 (
            set "PY_EXE=%%~P"
            set "PY_ARGS="
            goto :python_ready
        )
    )
)

:python_ready
if not defined PY_EXE (
    echo [ERRO] Python 3.11 nao encontrado.
    echo        O script tentou o Launcher ^(py -3.11^), PATH e instalacoes padrao.
    echo        Verifique com "py -0p" ou instale Python 3.11 x64.
    pause
    exit /b 1
)

echo [INFO] Interpretador selecionado: %PY_EXE% %PY_ARGS%
echo [1/7] Criando ambiente virtual de build...
"%PY_EXE%" %PY_ARGS% -m venv "%VENV_DIR%"
if errorlevel 1 (
    echo [ERRO] Falha ao criar o ambiente virtual.
    pause
    exit /b 1
)

:venv_ready
set "BUILD_PY=%VENV_DIR%\Scripts\python.exe"
if not exist "%BUILD_PY%" (
    echo [ERRO] Python do ambiente de build nao encontrado em %BUILD_PY%.
    pause
    exit /b 1
)

for /f "tokens=3 delims=' " %%v in ('findstr /C:"VERSION =" config.py') do set "APP_VERSION=%%v"
if not defined APP_VERSION (
    echo [ERRO] Nao foi possivel obter Config.VERSION.
    pause
    exit /b 1
)

for /f "usebackq delims=" %%a in (`"%BUILD_PY%" -c "import platform; print(platform.machine())"`) do set "SYS_ARCH=%%a"

echo.
echo ==========================================================
echo  Registro Facil v%APP_VERSION% - Build do servidor central
echo ==========================================================
echo  Arquitetura: %SYS_ARCH%
echo.

echo [2/7] Instalando dependencias fixadas...
"%BUILD_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%BUILD_PY%" -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto :fail

"%BUILD_PY%" -c "import flask, waitress, weasyprint, magic, openpyxl, paramiko, cryptography; print('Dependencias runtime verificadas')"
if errorlevel 1 (
    echo [ERRO] Dependencia runtime ausente ou sem suporte nativo.
    echo        PDF exige WeasyPrint e suas bibliotecas nativas.
    goto :fail
)

for /f "usebackq delims=" %%v in (`"%BUILD_PY%" -m PyInstaller --version`) do set "PI_VERSION=%%v"
echo  PyInstaller: %PI_VERSION%

echo [3/7] Limpando artefatos anteriores...
if exist "%DIST_DIR%\%APP_NAME%" rmdir /s /q "%DIST_DIR%\%APP_NAME%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"

if not exist "%ICON_PATH%" (
    echo [ERRO] Icone nao encontrado: %ICON_PATH%
    goto :fail
)

echo [4/7] Validando arquivos de interface...
if not exist "templates" goto :missing_templates
if not exist "static" goto :missing_static
if not exist "routes" goto :missing_routes
if not exist "data" goto :missing_data
if not exist "utils" goto :missing_utils

echo [5/7] Compilando executavel onedir...
"%BUILD_PY%" -m PyInstaller ^
    --name "%APP_NAME%" ^
    --onedir ^
    --windowed ^
    --icon="%ICON_PATH%" ^
    --distpath="%DIST_DIR%" ^
    --workpath="%BUILD_DIR%" ^
    --specpath="." ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import "flask" ^
    --hidden-import "jinja2" ^
    --hidden-import "waitress" ^
    --hidden-import "bcrypt" ^
    --hidden-import "cryptography" ^
    --hidden-import "cryptography.fernet" ^
    --hidden-import "apscheduler" ^
    --hidden-import "openpyxl" ^
    --hidden-import "paramiko" ^
    --hidden-import "nacl" ^
    --hidden-import "email_validator" ^
    --hidden-import "flask_mail" ^
    --hidden-import "magic" ^
    --collect-submodules "data" ^
    --collect-submodules "routes" ^
    --collect-submodules "utils" ^
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
if errorlevel 1 goto :fail

echo [6/7] Verificando executavel e metadados...
if not exist "%OUT_DIR%\%APP_NAME%.exe" (
    echo [ERRO] Executavel nao encontrado em %OUT_DIR%.
    goto :fail
)
"%BUILD_PY%" -c "from pathlib import Path; p=Path(r'%OUT_DIR%'); required=['RegistroFacil.exe','_internal']; missing=[x for x in required if not (p/x).exists()]; raise SystemExit('Arquivos ausentes: '+str(missing)) if missing else None"
if errorlevel 1 goto :fail
(
    echo RegistroFacil v%APP_VERSION%
    echo Compilado em: %DATE% %TIME%
    echo Arquitetura: %SYS_ARCH%
    echo PyInstaller: %PI_VERSION%
) > "%OUT_DIR%\versao.txt"

for /f "tokens=3" %%s in ('dir /s "%OUT_DIR%" ^| find "File(s)"') do set "DIR_SIZE=%%s"
echo [7/7] Build concluido.
echo.
echo Executavel: %OUT_DIR%\%APP_NAME%.exe
echo Versao:     %APP_VERSION%
echo Tamanho:    %DIR_SIZE%
echo.
echo Para gerar o instalador, compile INSTALADOR_RegistroFacil.iss com:
echo ISCC.exe /DMyAppVersion=%APP_VERSION% INSTALADOR_RegistroFacil.iss
if /i not "%CI%"=="true" explorer "%OUT_DIR%"
pause
exit /b 0

:missing_templates
 echo [ERRO] Pasta templates nao encontrada.
 goto :fail
:missing_static
 echo [ERRO] Pasta static nao encontrada.
 goto :fail
:missing_routes
 echo [ERRO] Pasta routes nao encontrada.
 goto :fail
:missing_data
 echo [ERRO] Pasta data nao encontrada.
 goto :fail
:missing_utils
 echo [ERRO] Pasta utils nao encontrada.
 goto :fail
:fail
echo.
echo [ERRO] Build interrompido. Nenhum instalador deve ser gerado.
pause
exit /b 1
