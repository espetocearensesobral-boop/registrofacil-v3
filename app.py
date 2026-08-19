# registrofacil/app.py

import os
import socket
import sys  # <<< ADIÇÃO 1: Importa o módulo 'sys'
from flask import Flask, redirect, url_for, request, session
from jinja2 import Environment
from config import Config
from models import init_db, executar_query, set_config, get_config, get_user_by_username
from utils.logger import sistema_logger, setup_all_loggers, manutencao_logger
from utils.logger_config import limpar_logs_antigos, limpar_logs_persistidos
from datetime import datetime
from utils.helpers import formatar_data

# Importar a blueprint de backup
from routes.backup import backup_bp

# Importar a função de configuração do scheduler
from utils.scheduler import configure_and_start_scheduler

# ADICIONE ESTA LINHA: Importar o servidor Waitress
from waitress import serve

# --- INÍCIO DA CORREÇÃO PARA O .EXE ---
# ADIÇÃO 2: Lógica para resolver os caminhos quando executado como .exe
if getattr(sys, 'frozen', False):
    # Rodando como .exe (congelado)
    # Templates/static vêm do bundle temporário do PyInstaller (_MEIPASS)
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')

    # Redireciona erros de inicialização para log em ProgramData, pois
    # o modo --windowed suprime o console e erros ficam invisíveis
    import tempfile
    _log_dir = os.path.join(
        os.environ.get('PROGRAMDATA', 'C:\\ProgramData'),
        'RegistroFacil', 'logs'
    )
    os.makedirs(_log_dir, exist_ok=True)
    _startup_log = os.path.join(_log_dir, 'startup_errors.log')
    try:
        sys.stderr = open(_startup_log, 'a', encoding='utf-8')
        sys.stdout = open(_startup_log, 'a', encoding='utf-8')
    except Exception:
        pass
else:
    # Rodando como script .py normal
    template_folder = 'templates'
    static_folder = 'static'
# --- FIM DA CORREÇÃO PARA O .EXE ---


def combine_filter(dict1, dict2):
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        raise TypeError("Filter 'combine' expects two dictionaries.")
    combined = dict1.copy()
    combined.update(dict2)
    return combined

def format_datetime_full_filter(value):
    return formatar_data(value)

def nl2br_filter(value):
    if value is None:
        return ""
    return value.replace('\n', '<br>')


def create_app():
    # ALTERAÇÃO 3: Passa os caminhos corretos para a instância do Flask
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config.from_object(Config)
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
    app.jinja_env.filters['combine'] = combine_filter
    app.jinja_env.filters['format_datetime_full'] = format_datetime_full_filter
    app.jinja_env.filters['nl2br'] = nl2br_filter

    app.jinja_env.globals.update(now=lambda: datetime.now())

    @app.before_request
    def ensure_csrf_token():
        """
        Garante que a sessão tenha um csrf_token antes da view ser executada.
        Context processors devem apenas injetar variáveis nos templates, não
        mutar estado (sessão); por isso essa geração fica aqui, e não em
        inject_global_vars.
        """
        if 'csrf_token' not in session:
            from routes.auth import gerar_csrf_token
            gerar_csrf_token()

    @app.before_request
    def block_mutations_during_update():
        """Impede alterações enquanto o sistema está em atualização."""
        if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return None
        endpoint = request.endpoint or ''
        if endpoint.startswith('system_updates.') or endpoint in {'auth.login', 'auth.logout'}:
            return None
        try:
            from data.system_updates import get_update_state, is_maintenance_active
            if is_maintenance_active(get_update_state()):
                message = 'O sistema está em atualização. Aguarde a conclusão para continuar.'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                    from flask import jsonify
                    return jsonify(success=False, message=message, type='maintenance'), 423
                return message, 423
        except Exception:
            # Falha na leitura do estado não deve derrubar a aplicação.
            # O endpoint de atualização registrará a falha caso necessário.
            return None
        return None

    @app.context_processor
    def inject_global_vars():
        # Apenas injeta o valor já garantido pelo before_request acima.
        # Views que precisam rotacionar o token explicitamente (ex.: login)
        # continuam podendo chamar gerar_csrf_token() e passar csrf_token
        # diretamente para render_template, que tem precedência sobre isto.
        return dict(request=request, csrf_token=session.get('csrf_token', ''))

    @app.context_processor
    def inject_app_version():
        """Injeta a versão do aplicativo em todos os templates para evitar strings hardcoded."""
        return dict(app_version=Config.VERSION)

    @app.context_processor
    def inject_permissions():
        """Adiciona função de verificação de permissões aos templates"""
        from utils.permissions_helper import has_permission
        
        def check_permission(permission_name):
            user_id = session.get('usuario_id')
            # O helper consulta a role persistida; não confia em role armazenada
            # na sessão, que pode ter ficado obsoleta após uma alteração admin.
            return has_permission(user_id, permission_name) if user_id else False
        
        return dict(has_permission=check_permission)
    @app.context_processor
    def inject_tema_cor():
        from data.themes import APPEARANCE_DEFAULT, tema_institucional_valido

        usuario_id = session.get("usuario_id")
        tema_cor = APPEARANCE_DEFAULT
        if usuario_id:
            from models import obter_preferencia_visual_usuario
            preferencias = obter_preferencia_visual_usuario(usuario_id)
            tema_cor = preferencias.get('tema_cor') or APPEARANCE_DEFAULT
        if not tema_institucional_valido(tema_cor):
            tema_cor = APPEARANCE_DEFAULT
        return dict(tema_cor_usuario=tema_cor, tema_padrao_usuario=tema_cor)

    # -----------------------------------------------------------------------
    # Inicialização do sistema de logs por domínio
    # -----------------------------------------------------------------------
    setup_all_loggers(console=True)
    sistema_logger.info(
        f"RegistroFácil v{Config.VERSION} iniciando — sistema de logs por domínio ativo.",
        extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
    )

    # Limpeza de logs antigos (> 90 dias) na inicialização
    try:
        limpar_logs_antigos()
    except Exception as _log_clean_err:
        sistema_logger.warning(
            f"Falha na limpeza inicial de logs: {_log_clean_err}",
            extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
        )

    init_db()
    try:
        limpar_logs_persistidos()
    except Exception as _persisted_log_clean_err:
        sistema_logger.warning(
            f"Falha na retenção persistente inicial de logs: {_persisted_log_clean_err}",
            extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0', 'domain': 'sistema', 'event_type': 'logs.retention_failed'}
        )

    # Importação e registro das Blueprints.
    from routes.auth import auth_bp
    from routes.processos import processos_bp
    from routes.search import search_bp
    from routes.atividades import atividades_bp
    from routes.configuracoes import configuracoes_bp
    from routes.admin_users import admin_users_bp
    from routes.empresa import empresa_bp
    from routes.backup import backup_bp
    from routes.utils_routes import utils_bp
    from routes.titulares import titulares_bp
    from routes.apresentantes import apresentantes_bp
    from routes.dashboard import dashboard_bp
    from routes.notificacoes import notificacoes_bp
    from routes.perfil import perfil_bp  # NOVA ROTA
    from routes.permissoes import permissoes_bp  # SISTEMA DE PERMISSÕES
    from routes.system_updates import system_updates_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(titulares_bp)
    app.register_blueprint(apresentantes_bp)
    app.register_blueprint(processos_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(atividades_bp)
    app.register_blueprint(configuracoes_bp)
    app.register_blueprint(admin_users_bp)
    app.register_blueprint(empresa_bp)
    app.register_blueprint(backup_bp)
    app.register_blueprint(utils_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(notificacoes_bp)
    app.register_blueprint(perfil_bp)  # REGISTRAR NOVA ROTA
    app.register_blueprint(permissoes_bp)  # REGISTRAR SISTEMA DE PERMISSÕES
    app.register_blueprint(system_updates_bp)


    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # -----------------------------------------------------------------------
    # Rota para servir arquivos de upload (empresa e processos)
    # Funciona tanto em modo .py (static/uploads/) quanto .exe (ProgramData/uploads/)
    # -----------------------------------------------------------------------
    @app.route('/uploads/<path:filepath>')
    def serve_upload(filepath):
        """Serve arquivos de upload a partir de Config.UPLOAD_ROOT_DIR.

        Subpasta pública (sem autenticação): empresa/
          -> Logo da empresa é exibida nas telas de login, recuperar_senha e reset_password.
        Subpasta privada (exige sessão): processos/
        """
        from flask import abort, send_from_directory

        # Segurança: normaliza e impede path traversal antes de qualquer verificação
        safe = os.path.normpath(filepath).replace('\\', '/')
        if '..' in safe or os.path.isabs(safe):
            abort(403)

        abs_root = os.path.abspath(Config.UPLOAD_ROOT_DIR)
        abs_file = os.path.abspath(os.path.join(Config.UPLOAD_ROOT_DIR, safe))

        if not abs_file.startswith(abs_root + os.sep):
            abort(403)

        # empresa/ é pública: logo exibida nas páginas sem autenticação (login, recuperar_senha...)
        is_public = safe.startswith('empresa/') or safe.startswith('empresa' + os.sep)

        # Anexos de processos exigem sessão autenticada.
        if not is_public and not session.get('usuario_id'):
            abort(401)

        if not os.path.isfile(abs_file):
            abort(404)

        return send_from_directory(os.path.dirname(abs_file), os.path.basename(abs_file))

    with app.app_context():
        from models import send_email
        # Criação do usuário admin padrão é gerenciada pelo init_db() em models.py
        # para evitar duplicação. O init_db() já cria o admin com must_change_password=1.

        try:
            logo_url = get_config('empresa_logo_url')
            if not logo_url:
                set_config('empresa_logo_url', Config.DEFAULT_LOGO_URL)
                sistema_logger.info(f"Configuração de logo padrão definida como: {Config.DEFAULT_LOGO_URL}")
            else:
                sistema_logger.info(f"Configuração de logo existente: {logo_url}")
        except Exception as e:
            sistema_logger.error(f"Erro ao configurar logo padrão: {e}", exc_info=True)
            
        # Configura e inicia o scheduler com o contexto do aplicativo
        configure_and_start_scheduler(app.app_context)

        # Agendamento da limpeza automática de logs (diária, às 03:00)
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from utils.scheduler import scheduler as _scheduler
            if _scheduler.running:
                _scheduler.add_job(
                    limpar_logs_antigos,
                    trigger='cron',
                    hour=3,
                    minute=0,
                    id='job_limpeza_logs_90dias',
                    replace_existing=True,
                    name='Limpeza automática de arquivos de log (90 dias)'
                )
                _scheduler.add_job(
                    limpar_logs_persistidos,
                    trigger='cron',
                    hour=3,
                    minute=10,
                    id='job_retencao_logs_sqlite',
                    replace_existing=True,
                    name='Retenção de logs persistidos'
                )
                sistema_logger.info(
                    "Jobs de retenção de logs agendados para 03:00 e 03:10 (diário).",
                    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0', 'domain': 'sistema', 'event_type': 'logs.retention_scheduled'}
                )
        except Exception as _sched_err:
            sistema_logger.warning(
                f"Não foi possível agendar limpeza automática de logs: {_sched_err}",
                extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
            )

    return app


def _cli_option(name: str, default: str | None = None) -> str | None:
    """Lê uma opção simples do executável sem introduzir dependência de argparse."""
    arguments = sys.argv[1:]
    for index, argument in enumerate(arguments):
        if argument == name and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(name + '='):
            return argument.split('=', 1)[1]
    return default


def _server_port_available(host: str, port: int) -> bool:
    """Evita inicializar uma segunda aplicação central na mesma porta."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        probe.close()


if __name__ == '__main__':
    cli_args = set(sys.argv[1:])

    # O mesmo executável pode atuar como servidor, worker de atualização ou
    # executor de backup sem depender de uma instalação Python no servidor.
    if '--update-worker' in cli_args:
        from data.update_worker import main as update_worker_main
        raise SystemExit(update_worker_main())
    if '--backup-runner' in cli_args:
        from utils.backup_runner import main as backup_runner_main
        raise SystemExit(backup_runner_main(['--source', 'scheduled']))

    host = _cli_option('--host', os.environ.get('REGISTROFACIL_HOST', '0.0.0.0')) or '0.0.0.0'
    port_raw = _cli_option('--port', os.environ.get('REGISTROFACIL_PORT', '5000')) or '5000'
    try:
        port = int(port_raw)
    except (TypeError, ValueError):
        port = 5000
    if not _server_port_available(host, port):
        print(f'ERRO: a porta {port} já está em uso. O servidor central já pode estar em execução.')
        raise SystemExit(1)

    app = create_app()

    # ── 1. Lock do arquivo de banco de dados ─────────────────────────────────
    try:
        from config import Config as _Cfg
        from utils.db_lock import adquirir_lock_db
        _db_locked = adquirir_lock_db(_Cfg.DATABASE_PATH)
        if _db_locked:
            sistema_logger.info("Lock do banco de dados adquirido — arquivo protegido.")
        else:
            sistema_logger.warning("Não foi possível adquirir lock no arquivo DB.")
    except Exception as _lock_err:
        sistema_logger.error(f"Erro ao adquirir lock do banco: {_lock_err}", exc_info=True)

    # ── 2. Abrir navegador somente no modo interativo ─────────────────────────
    open_browser = '--no-browser' not in cli_args
    if os.environ.get('REGISTROFACIL_OPEN_BROWSER', 'true').strip().lower() in {'0', 'false', 'no'}:
        open_browser = False
    if open_browser:
        try:
            from utils.browser_launcher import abrir_navegador
            browser_host = '127.0.0.1' if host in {'0.0.0.0', '::'} else host
            abrir_navegador(url=f"http://{browser_host}:{port}", delay=1.8)
        except Exception as _browser_err:
            sistema_logger.warning(f"Não foi possível abrir navegador automaticamente: {_browser_err}")

    sistema_logger.info("Iniciando aplicação Flask 'Registro Fácil' com Waitress...")
    serve(app, host=host, port=port, threads=8)
