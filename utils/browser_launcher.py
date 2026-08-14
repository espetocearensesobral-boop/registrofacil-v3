# utils/browser_launcher.py
# Abre o Registro Fácil em uma janela de navegador separada,
# sem barra de endereço (modo app), com fullscreen automático.

import sys
import subprocess
import threading
import time
import webbrowser


# Navegadores a tentar, em ordem de preferência, com flags de janela app
_BROWSERS_WINDOWS = [
    # Chrome estável
    [r"C:\Program Files\Google\Chrome\Application\chrome.exe", "{url}"],
    # Chrome (usuário)
    [r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "{url}"],
    # Edge estável
    [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "{url}"],
    [r"C:\Program Files\Microsoft\Edge\Application\msedge.exe", "{url}"],
    # Chromium genérico (via PATH)
    ["chrome",           "{url}"],
    ["msedge",           "{url}"],
    ["chromium",         "{url}"],
    ["chromium-browser", "{url}"],
]

_BROWSERS_LINUX = [
    ["google-chrome",    "{url}"],
    ["chromium-browser", "{url}"],
    ["chromium",         "{url}"],
    ["microsoft-edge",   "{url}"],
]

_BROWSERS_MAC = [
    ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "{url}"],
    ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "{url}"],
    ["open", "-a", "Google Chrome", "{url}"],
]


def _get_candidates(url: str) -> list[list[str]]:
    def fmt(lst):
        return [[arg.replace("{url}", url) for arg in cmd] for cmd in lst]

    if sys.platform == "win32":
        return fmt(_BROWSERS_WINDOWS)
    elif sys.platform == "darwin":
        return fmt(_BROWSERS_MAC)
    else:
        return fmt(_BROWSERS_LINUX)


def _tentar_abrir(url: str) -> bool:
    """Tenta abrir cada candidato. Retorna True se algum abriu."""
    for cmd in _get_candidates(url):
        try:
            # Verifica se o executável existe (para caminhos absolutos)
            exe = cmd[0]
            if exe.startswith(("/", "C:\\", "c:\\")):
                import os
                if not os.path.exists(exe):
                    continue
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )
            return True
        except (FileNotFoundError, OSError, PermissionError):
            continue
    return False


def abrir_navegador(url: str = "http://localhost:5000", delay: float = 1.8):
    """
    Abre o navegador em modo app (sem barra de endereço) e tela cheia.
    Chamado em thread separada para não bloquear o servidor.

    delay: segundos a esperar pelo servidor subir antes de abrir.
    """
    def _run():
        time.sleep(delay)
        opened = _tentar_abrir(url)
        if not opened:
            # Fallback: nova janela no navegador padrão do SO
            webbrowser.open_new(url)

    t = threading.Thread(target=_run, daemon=True, name="browser-launcher")
    t.start()
