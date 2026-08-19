@echo off
setlocal EnableExtensions

:: ============================================================================
:: Registro Fácil — Build Windows
:: Compila o servidor central em modo onedir usando um ambiente de build isolado.
:: Requer Windows 10/11 e Python 3.11 ou 3.12.
::
:: Execução normal: abre uma janela persistente, mostra o log e aguarda uma tecla.
:: Execução CI: defina CI=true para executar diretamente, sem pausa interativa.
:: ============================================================================

if /i "%CI%"=="true" goto build_main

set "RF_BUILD_LOG=%TEMP%\RegistroFacil_BUILD.log"
echo Registro Facil - diagnostico do build > "%RF_BUILD_LOG%"
echo Iniciando em %DATE% %TIME% >> "%RF_BUILD_LOG%"
echo Diretorio: %~dp0 >> "%RF_BUILD_LOG%"
echo.
echo Registro Facil - build iniciado em %DATE% %TIME%
echo O progresso sera exibido nesta janela.
echo Log de inicio: %RF_BUILD_LOG%
echo.
call :build_main
set "RF_BUILD_EXIT=%ERRORLEVEL%"
echo Build finalizado com codigo %RF_BUILD_EXIT% em %DATE% %TIME%>> "%RF_BUILD_LOG%"

echo.
echo O build terminou com codigo %RF_BUILD_EXIT%.
echo O resumo do diagnostico foi salvo em:
echo %RF_BUILD_LOG%
echo.
type "%RF_BUILD_LOG%"
echo.
pause
exit /b %RF_BUILD_EXIT%

:build_main
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

if exist "%VENV_DIR%\Scripts\python.exe" goto check_existing_venv
goto discover_python

:check_existing_venv
"%VENV_DIR%\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)" >nul 2>&1
if errorlevel 1 goto recreate_venv
goto venv_ready

:recreate_venv
echo [INFO] Ambiente virtual existente nao usa Python 3.11/3.12; recriando.
rmdir /s /q "%VENV_DIR%" >nul 2>&1
if exist "%VENV_DIR%" (
    echo [ERRO] Nao foi possivel remover o ambiente virtual antigo: %VENV_DIR%
    exit /b 1
)

goto discover_python

:discover_python
:: 1) Python Launcher: prioriza 3.12 e aceita 3.11 como fallback.
where py >nul 2>&1
if errorlevel 1 goto probe_path_python312
py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto try_py311
set "PY_EXE=py"
set "PY_ARGS=-3.12"
goto create_venv

:try_py311
py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto probe_path_python312
set "PY_EXE=py"
set "PY_ARGS=-3.11"
goto create_venv

:: 2) Interpretadores expostos diretamente no PATH.
:probe_path_python312
where python3.12 >nul 2>&1
if errorlevel 1 goto probe_path_python311
python3.12 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto probe_path_python311
set "PY_EXE=python3.12"
set "PY_ARGS="
goto create_venv

:probe_path_python311
where python3.11 >nul 2>&1
if errorlevel 1 goto probe_path_python3
python3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto probe_path_python3
set "PY_EXE=python3.11"
set "PY_ARGS="
goto create_venv

:probe_path_python3
where python3 >nul 2>&1
if errorlevel 1 goto probe_path_python
python3 -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)" >nul 2>&1
if errorlevel 1 goto probe_path_python
set "PY_EXE=python3"
set "PY_ARGS="
goto create_venv

:probe_path_python
where python >nul 2>&1
if errorlevel 1 goto probe_standard_python312
python -c "import sys; raise SystemExit(0 if sys.version_info[:2] in ((3, 11), (3, 12)) else 1)" >nul 2>&1
if errorlevel 1 goto probe_standard_python312
set "PY_EXE=python"
set "PY_ARGS="
goto create_venv

:: 3) Instalacoes comuns do Python.org fora do PATH.
:probe_standard_python312
if not exist "%LocalAppData%\Programs\Python\Python312\python.exe" goto probe_standard_python311
"%LocalAppData%\Programs\Python\Python312\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto probe_standard_python311
set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
set "PY_ARGS="
goto create_venv

:probe_standard_python311
if not exist "%LocalAppData%\Programs\Python\Python311\python.exe" goto probe_programfiles_python312
"%LocalAppData%\Programs\Python\Python311\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto probe_programfiles_python312
set "PY_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
set "PY_ARGS="
goto create_venv

:probe_programfiles_python312
if not exist "%ProgramFiles%\Python312\python.exe" goto probe_programfiles_python311
"%ProgramFiles%\Python312\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto probe_programfiles_python311
set "PY_EXE=%ProgramFiles%\Python312\python.exe"
set "PY_ARGS="
goto create_venv

:probe_programfiles_python311
if not exist "%ProgramFiles%\Python311\python.exe" goto probe_programfiles_x86_python312
"%ProgramFiles%\Python311\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto probe_programfiles_x86_python312
set "PY_EXE=%ProgramFiles%\Python311\python.exe"
set "PY_ARGS="
goto create_venv

:probe_programfiles_x86_python312
if not exist "%ProgramFiles(x86)%\Python312\python.exe" goto probe_programfiles_x86_python311
"%ProgramFiles(x86)%\Python312\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto probe_programfiles_x86_python311
set "PY_EXE=%ProgramFiles(x86)%\Python312\python.exe"
set "PY_ARGS="
goto create_venv

:probe_programfiles_x86_python311
if not exist "%ProgramFiles(x86)%\Python311\python.exe" goto python_not_found
"%ProgramFiles(x86)%\Python311\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if errorlevel 1 goto python_not_found
set "PY_EXE=%ProgramFiles(x86)%\Python311\python.exe"
set "PY_ARGS="
goto create_venv

:python_not_found
echo [ERRO] Python 3.11 ou 3.12 nao encontrado.
echo        O script tentou py -3.12, py -3.11, PATH e instalacoes padrao.
echo        Verifique com "py -0p" ou instale Python 3.12 x64.
exit /b 1

:create_venv
echo [INFO] Interpretador selecionado: %PY_EXE% %PY_ARGS%
echo [1/7] Criando ambiente virtual de build...
"%PY_EXE%" %PY_ARGS% -m venv "%VENV_DIR%"
if errorlevel 1 goto fail

goto venv_ready

:venv_ready
set "BUILD_PY=%CD%\%VENV_DIR%\Scripts\python.exe"
if not exist "%BUILD_PY%" goto fail
set "PIP_CACHE_DIR=%TEMP%\RegistroFacil-pip-cache"
if not exist "%PIP_CACHE_DIR%" mkdir "%PIP_CACHE_DIR%" >nul 2>&1

for /f "tokens=3 delims=' " %%v in ('findstr /C:"VERSION =" config.py') do set "APP_VERSION=%%v"
if not defined APP_VERSION goto fail

for /f "delims=" %%a in ('"%BUILD_PY%" -c "import platform; print(platform.machine())"') do set "SYS_ARCH=%%a"

echo.
echo ==========================================================
echo  Registro Facil v%APP_VERSION% - Build do servidor central
echo ==========================================================
echo  Arquitetura: %SYS_ARCH%
echo.

echo [2/7] Instalando dependencias fixadas...
"%BUILD_PY%" -m pip install --disable-pip-version-check --no-cache-dir --upgrade pip
if errorlevel 1 goto fail
"%BUILD_PY%" -m pip install --disable-pip-version-check --no-cache-dir -r requirements.txt -r requirements-build.txt
if errorlevel 1 goto fail

"%BUILD_PY%" -c "import flask, waitress, weasyprint, magic, openpyxl, paramiko, cryptography; print('Dependencias runtime verificadas')"
if errorlevel 1 goto fail

for /f "delims=" %%v in ('"%BUILD_PY%" -m PyInstaller --version') do set "PI_VERSION=%%v"
echo  PyInstaller: %PI_VERSION%

echo [3/7] Limpando artefatos anteriores...
if exist "%DIST_DIR%\%APP_NAME%" rmdir /s /q "%DIST_DIR%\%APP_NAME%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"
if not exist "%ICON_PATH%" goto fail

echo [4/7] Validando arquivos de interface...
if not exist "templates" goto missing_templates
if not exist "static" goto missing_static
if not exist "routes" goto missing_routes
if not exist "data" goto missing_data
if not exist "utils" goto missing_utils

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
if errorlevel 1 goto fail

echo [6/7] Verificando executavel e metadados...
if not exist "%OUT_DIR%\%APP_NAME%.exe" goto fail
"%BUILD_PY%" -c "from pathlib import Path; p=Path(r'%OUT_DIR%'); required=['RegistroFacil.exe','_internal']; missing=[x for x in required if not (p/x).exists()]; raise SystemExit('Arquivos ausentes: '+str(missing)) if missing else None"
if errorlevel 1 goto fail
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
exit /b 0

:missing_templates
echo [ERRO] Pasta templates nao encontrada.
goto fail

:missing_static
echo [ERRO] Pasta static nao encontrada.
goto fail

:missing_routes
echo [ERRO] Pasta routes nao encontrada.
goto fail

:missing_data
echo [ERRO] Pasta data nao encontrada.
goto fail

:missing_utils
echo [ERRO] Pasta utils nao encontrada.
goto fail

:fail
echo.
echo [ERRO] Build interrompido. Nenhum instalador deve ser gerado.
exit /b 1
