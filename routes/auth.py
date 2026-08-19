# registrofacil/routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import re
import secrets
from datetime import datetime, timedelta
import functools
import sqlite3
import random
import pytz

from models import (
    executar_query, gravar_log, verificar_tentativas_login,
    registrar_tentativa_login,     get_user_by_username, get_user_by_id, create_user,
    set_config,
    get_today_processes_count,
    get_prenotados_processes_count,
    get_em_andamento_processes_count,
    get_in_progress_processes_count,
    get_user_linked_processes_count,
    get_recent_processes, get_critical_deadline_processes, 
    release_all_locks, send_email,
    obter_status_processo_config,
    get_status_id_by_name,
    get_concluidos_processes_count,
    update_user_last_login,
    touch_user_presence,
    clear_user_presence,
    get_empresa_info, 
    create_password_reset_token, 
    get_password_reset_token, 
    mark_password_reset_token_as_used, 
    get_sqlite_connection # Necessário para a transação atômica
)
from utils.logger import auth_logger as logger
from config import Config
from utils.helpers import get_contrast_color, formatar_data
from utils.file_uploads import get_image_url_for_display
from utils.messages import GREETING_PHRASES


auth_bp = Blueprint('auth', __name__, url_prefix='/')

def gerar_csrf_token():
    """Retorna o token da sessão, criando-o apenas quando necessário.

    A função é segura para ser chamada durante a renderização de qualquer
    view: abrir outra tela não invalida formulários que o usuário já abriu.
    A rotação após autenticação continua explícita no fluxo de login.
    """
    if not session.get('csrf_token'):
        session['csrf_token'] = secrets.token_hex(32)
    return session['csrf_token']

def verificar_csrf_token(token):
    if 'csrf_token' not in session or not token:
        return False
    return secrets.compare_digest(session.get('csrf_token', ''), token)

def is_logged_in_status():
    return session.get('logado', False)


def _invalidate_current_session(reason=None):
    if reason:
        logger.warning(reason)
    session.clear()


def _validate_active_session():
    """Valida a conta e a versão de sessão diretamente no banco."""
    if not is_logged_in_status():
        return False

    user_id = session.get('usuario_id')
    user_data = get_user_by_id(user_id) if user_id else None
    if not user_data:
        _invalidate_current_session(f"Sessão sem usuário válido. User ID: {user_id}")
        return False

    if user_data.get('ativo') == 0:
        _invalidate_current_session(f"Sessão invalidada para usuário {user_id}: conta inativa no DB.")
        return False

    session_epoch = session.get('session_epoch')
    db_epoch = user_data.get('session_epoch')
    if session_epoch is not None and db_epoch is not None:
        try:
            if int(session_epoch) != int(db_epoch):
                _invalidate_current_session(
                    f"Sessão invalidada para usuário {user_id}: epoch de sessão desatualizado."
                )
                return False
        except (TypeError, ValueError):
            _invalidate_current_session(f"Sessão inválida para usuário {user_id}: epoch malformado.")
            return False
    else:
        # Sessões antigas não carregam epoch. Se o banco já foi incrementado,
        # elas devem ser revogadas, pois não é possível provar sua validade.
        if session_epoch is None and db_epoch is not None:
            try:
                if int(db_epoch) > 0:
                    _invalidate_current_session(
                        f"Sessão legada invalidada para usuário {user_id}: epoch ausente."
                    )
                    return False
            except (TypeError, ValueError):
                _invalidate_current_session(f"Sessão inválida para usuário {user_id}: epoch malformado.")
                return False

        # Compatibilidade com sessões criadas antes da migração para session_epoch.
        session_start_time_str = session.get('session_start_time')
        invalidate_at = user_data.get('session_invalidate_at')
        if session_start_time_str and invalidate_at:
            try:
                session_invalidate_dt = datetime.strptime(invalidate_at, '%Y-%m-%d %H:%M:%S')
                session_start_dt = datetime.strptime(session_start_time_str, '%Y-%m-%d %H:%M:%S')
                if session_start_dt < session_invalidate_dt:
                    _invalidate_current_session(
                        f"Sessão legada invalidada para usuário {user_id}: timestamp mais recente."
                    )
                    return False
            except (ValueError, TypeError):
                logger.warning(
                    f"Erro ao parsear data da sessão legada para o usuário {user_id}."
                )

    return True


def _touch_authenticated_presence():
    """Atualiza a presença no máximo uma vez a cada 30 segundos por sessão."""
    user_id = session.get('usuario_id')
    if not user_id:
        return
    now = datetime.now()
    previous = session.get('presence_touch_at')
    if previous:
        try:
            previous_dt = datetime.strptime(previous, '%Y-%m-%d %H:%M:%S')
            if (now - previous_dt).total_seconds() < 30:
                return
        except (TypeError, ValueError):
            pass
    try:
        if touch_user_presence(user_id, get_client_ip()):
            session['presence_touch_at'] = now.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as exc:
        logger.warning(f'Não foi possível atualizar a presença do usuário {user_id}: {exc}')


def login_status_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not _validate_active_session():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message="Sessão expirada. Por favor, faça login novamente.", redirect=url_for('auth.login'), type='danger'), 401
            flash("Você precisa estar logado para acessar esta página.", 'error')
            logger.warning(f"Acesso não autorizado. IP: {get_client_ip()}")
            return redirect(url_for('auth.login'))

        # Força troca de senha se sinalizado - redireciona para perfil exceto se já estiver lá

        _touch_authenticated_presence()

        if session.get('force_password_change'):
            from flask import request as _req
            # Permite acesso ao perfil e ao logout; bloqueia todo o resto
            allowed = ('perfil.', 'auth.logout')
            endpoint = _req.endpoint or ''
            if not any(endpoint.startswith(p) for p in allowed):
                flash("Você precisa alterar sua senha antes de continuar.", 'warning')
                return redirect(url_for('perfil.index'))

        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not _validate_active_session():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message="Sessão expirada. Por favor, faça login novamente.", redirect=url_for('auth.login'), type='danger'), 401
            flash("Você precisa estar logado para acessar esta página.", 'error')
            logger.warning(f"Tentativa de acesso administrativo sem sessão válida. IP: {get_client_ip()}")
            return redirect(url_for('auth.login'))

        user = get_user_by_id(session.get('usuario_id'))
        session_role = session.get('usuario_role')
        if (
            not user
            or user.get('role') not in ['admin', 'suporte']
            or session_role != user.get('role')
        ):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(success=False, message="Acesso restrito a administradores.", type='danger'), 403
            flash("Acesso restrito a administradores.", 'error')
            logger.warning(
                f"Acesso de administrador negado para Usuário ID: {session.get('usuario_id')}, "
                f"Role no DB: {user.get('role') if user else None}, IP: {get_client_ip()}"
            )
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def proteger_input(text):
    """
    Sanitiza texto para armazenamento seguro no banco de dados.
    
    IMPORTANTE: NÃO faz HTML-escape aqui. O escape para exibição em HTML
    é responsabilidade do template (Jinja2 auto-escape). Fazer escape aqui
    causaria duplo-escape a cada edição (& → &amp; → &amp;amp; → ...).
    
    Remove apenas tags HTML para prevenir XSS caso o valor seja exibido
    sem escape em algum contexto, mantendo o texto plano original.
    """
    if not text:
        return ""
    import re
    text = str(text).strip()
    # Remove tags HTML (XSS prevention), mantém o texto plano
    text = re.sub(r'<[^>]+>', '', text)
    return text


def get_client_ip():
    if Config.TRUST_PROXY_HEADERS and request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr


def validate_user_role(role):
    """Aceita somente roles reconhecidas pelo modelo de autorização."""
    valid_roles = {'admin', 'suporte', 'user'}
    if role not in valid_roles:
        raise ValueError('A função informada é inválida.')
    return role


def ensure_admin_safety(user_data, target_role, target_active, current_user_id=None):
    """Impede auto-bloqueio e remoção do último administrador ativo."""
    if user_data['id'] == current_user_id and (
        target_role != user_data['role'] or not target_active
    ):
        raise ValueError('Você não pode remover ou reduzir os próprios privilégios nesta tela.')

    if user_data['role'] == 'admin' and (target_role != 'admin' or not target_active):
        active_admins = executar_query(
            "SELECT COUNT(*) AS total FROM usuarios WHERE role = 'admin' AND ativo = 1",
            fetch_one=True
        )
        if (active_admins or {}).get('total', 0) <= 1:
            raise ValueError('O sistema precisa manter pelo menos um administrador ativo.')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in_status():
        return redirect(url_for('auth.dashboard'))

    usuario_input = ''
    ip = get_client_ip()

    current_logo_filename = None
    try:
        empresa_info = get_empresa_info() 
        if empresa_info:
            current_logo_filename = empresa_info.get('logo') 
    except Exception as e:
        logger.warning(f"Não foi possível obter a logo da empresa para a tela de login: {e}")
    
    logo_url_for_template = get_image_url_for_display(current_logo_filename, is_company_logo=True)


    if request.method == 'POST':
        if request.form.get('honeypot', '') != '':
            flash("Acesso não autorizado.", 'error')
            logger.warning(f"Honeypot acionado para IP: {ip}")
            gravar_log("Falha de login: Honeypot acionado", None, None, ip)
            registrar_tentativa_login(ip, False)
            session.pop('csrf_token', None)
            return render_template('login.html', csrf_token=gerar_csrf_token(),
                                   usuario=usuario_input, logo_url=logo_url_for_template)

        pode_tentar, erro_tentativas = verificar_tentativas_login(ip) 
        if not pode_tentar:
            flash(erro_tentativas, 'error')
            logger.warning(f"Login bloqueado para IP '{ip}' devido a excesso de tentativas.")
            gravar_log("Tentativa de login bloqueada por excesso de tentativas", None, None, ip) 
            registrar_tentativa_login(ip, False) 
            session.pop('csrf_token', None)
            return render_template('login.html', csrf_token=gerar_csrf_token(),
                                   usuario=usuario_input, logo_url=logo_url_for_template)

        if not verificar_csrf_token(request.form.get('csrf_token')):
            flash("Token de segurança inválido ou expirado. Por favor, recarregue a página e tente novamente.", 'error')
            logger.error(f"Falha de login: Token CSRF inválido para IP: {ip}")
            gravar_log("Falha de login: Token CSRF inválido", None, None, ip) 
            registrar_tentativa_login(ip, False) 
            session.pop('csrf_token', None)
            return render_template('login.html', csrf_token=gerar_csrf_token(),
                                   usuario=usuario_input, logo_url=logo_url_for_template)

        usuario_input = proteger_input(request.form.get('usuario', ''))
        senha_input = request.form.get('senha', '')

        if not usuario_input or not senha_input:
            flash("Preencha todos os campos.", 'error')
            logger.warning(f"Tentativa de login com campos vazios. IP: {ip}")
            gravar_log("Falha de login: Campos vazios", None, None, ip) 
            registrar_tentativa_login(ip, False) 
            return render_template('login.html', csrf_token=gerar_csrf_token(),
                                   usuario=usuario_input, logo_url=logo_url_for_template)

        try:
            user = get_user_by_username(usuario_input) 

            if not user:
                flash("Usuário ou senha inválidos. Verifique suas credenciais.", 'error')
                action_log = f"Falha de login: Usuário não encontrado ({usuario_input})"
                logger.warning(action_log)
                gravar_log(action_log, None, None, ip) 
                registrar_tentativa_login(ip, False) 
                return render_template('login.html', csrf_token=gerar_csrf_token(),
                                       usuario=usuario_input, logo_url=logo_url_for_template)

            if user['ativo'] == 0:
                flash("Usuário ou senha inválidos. Verifique suas credenciais.", 'error')
                action_log = f"Falha de login: Conta inativa para usuário '{usuario_input}'"
                logger.warning(action_log)
                gravar_log(action_log, None, user['id'], ip) 
                registrar_tentativa_login(ip, False) 
                return render_template('login.html', csrf_token=gerar_csrf_token(),
                                       usuario=usuario_input, logo_url=logo_url_for_template)

            if not check_password_hash(user['senha'], senha_input):
                flash("Usuário ou senha inválidos. Verifique suas credenciais.", 'error')
                action_log = f"Falha de login: Senha incorreta para usuário '{usuario_input}'"
                logger.warning(action_log)
                gravar_log(action_log, None, user['id'], ip) 
                registrar_tentativa_login(ip, False) 
                return render_template('login.html', csrf_token=gerar_csrf_token(),
                                       usuario=usuario_input, logo_url=logo_url_for_template)

            # Define o timestamp atual para invalidar sessões antigas e marcar o início desta.
            agora_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            executar_query(
                "UPDATE usuarios SET session_epoch = COALESCE(session_epoch, 0) + 1, "
                "session_invalidate_at = ?, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?",
                [agora_str, user['id']]
            )
            novo_session_epoch = int(user.get('session_epoch') or 0) + 1
            # --- FIM DA ATUALIZAÇÃO ---

            # Rotaciona o conteúdo da sessão após autenticação para evitar session fixation.
            session.clear()
            session.permanent = True
            session['logado'] = True
            session['usuario_id'] = user['id']
            session['usuario_nome'] = user['nome']
            session['usuario_email'] = user['email']
            session['usuario_username'] = user['usuario']
            session['usuario_role'] = user['role']
            session['session_epoch'] = novo_session_epoch
            session['session_start_time'] = agora_str # Compatibilidade e diagnóstico
            
            # Set empresa logo in session so sidebar and all pages use it
            try:
                _emp = get_empresa_info()
                session['empresa_logo_url'] = get_image_url_for_display(_emp.get('logo') if _emp else None, is_company_logo=True)
            except Exception:
                session['empresa_logo_url'] = url_for('static', filename='img/registrofacil.png')
            
            update_user_last_login(user['id'])
            touch_user_presence(user['id'], ip)

            custom_greeting = ""
            user_name = user['nome']
            first_name = user_name.split(' ')[0]

            sobral_timezone = pytz.timezone('America/Fortaleza')
            current_time_sobral = datetime.now(sobral_timezone)
            
            last_login_dt_aware = None
            if user['last_login_at']:
                try:
                    last_login_dt_naive = datetime.strptime(user['last_login_at'], '%Y-%m-%d %H:%M:%S')
                    last_login_dt_aware = sobral_timezone.localize(last_login_dt_naive)
                except ValueError:
                    logger.warning(f"Formato inválido para last_login_at de usuário {user['id']}: {user['last_login_at']}. Ignorando para lógica de saudação.")
            
            if last_login_dt_aware:
                time_since_last_login = (current_time_sobral - last_login_dt_aware).total_seconds()
                
                is_same_day = (last_login_dt_aware.date() == current_time_sobral.date())
                is_yesterday = (last_login_dt_aware.date() == (current_time_sobral - timedelta(days=1)).date())
                
                if is_same_day and time_since_last_login > (5 * 60):
                    custom_greeting = random.choice(GREETING_PHRASES['welcome_back']).format(nome=first_name)
                elif is_yesterday and current_time_sobral.hour < 10 and random.random() < 0.5:
                    custom_greeting = random.choice(GREETING_PHRASES['welcome_back']).format(nome=first_name)
            
            if not custom_greeting:
                day_of_week = current_time_sobral.strftime('%A').lower()
                
                if day_of_week in GREETING_PHRASES['weekdays']:
                    custom_greeting = random.choice(GREETING_PHRASES['weekdays'][day_of_week]).format(nome=first_name)
                else:
                    hour = current_time_sobral.hour
                    if 5 <= hour < 12:
                        custom_greeting = random.choice(GREETING_PHRASES['morning']).format(nome=first_name)
                    elif 12 <= hour < 18:
                        custom_greeting = random.choice(GREETING_PHRASES['afternoon']).format(nome=first_name)
                    else:
                        custom_greeting = random.choice(GREETING_PHRASES['evening']).format(nome=first_name)
                    
            if random.random() < 0.7:
                custom_greeting = custom_greeting.strip()
                if custom_greeting.endswith(('.', '!', '?')):
                    custom_greeting = custom_greeting[:-1] 
                
                custom_greeting += f". {random.choice(GREETING_PHRASES['motivational'])}"
            
            session['custom_greeting'] = custom_greeting

            session['csrf_token'] = secrets.token_hex(32) 

            flash("Login realizado com sucesso!", 'success')
            logger.info(f"Login bem-sucedido para usuário: '{usuario_input}' (ID: {user['id']})")
            gravar_log(f"Login bem-sucedido: {usuario_input}", None, user['id'], ip) 
            registrar_tentativa_login(ip, True)

            # Força troca de senha se sinalizado (ex: primeiro acesso com senha padrão)
            if user.get('must_change_password') == 1:
                session['force_password_change'] = True
                flash("Por segurança, você precisa alterar sua senha antes de continuar.", 'warning')
                return redirect(url_for('perfil.index'))

            return redirect(url_for('auth.dashboard'))

        except Exception as e:
            flash("Ocorreu um erro inesperado ao tentar fazer login. Por favor, tente novamente mais tarde.", 'error')
            logger.exception(f"Erro inesperado durante login para '{usuario_input}': {e}")
            gravar_log(f"Erro durante login: {str(e)}", None, None, ip) 
            registrar_tentativa_login(ip, False) 

    csrf_token_val = gerar_csrf_token()
    return render_template('login.html', csrf_token=csrf_token_val,
                           usuario=usuario_input, logo_url=logo_url_for_template)

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_status_required
def logout():
    if not is_logged_in_status(): 
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        if not verificar_csrf_token(request.form.get('csrf_token')):
            flash("Token de segurança inválido. Por favor, recarregue a página e tente novamente.", 'error')
            logger.error(f"Falha de logout: Token CSRF inválido para Usuário ID: {session.get('usuario_id')}, IP: {get_client_ip()}")
            return redirect(url_for('auth.dashboard'))
        
        try:
            usuario_id = session.get('usuario_id')
            if usuario_id:
                clear_user_presence(usuario_id)
                gravar_log("Logout do sistema", None, usuario_id, get_client_ip()) 
                logger.info(f"Usuário {session.get('usuario_nome')} (ID: {usuario_id}) realizou logout.")
                
                release_all_locks(usuario_id) 
            
        except Exception as e:
            logger.error(f"Erro ao gravar log ou liberar locks durante o logout: {e}", exc_info=True)
            
        session.clear()
        flash("Logout realizado com sucesso!", 'success')
        return redirect(url_for('auth.login'))
    else:
        csrf_token_val = gerar_csrf_token()
        return render_template('logout.html', csrf_token=csrf_token_val)

@auth_bp.route('/dashboard')
@login_status_required
def dashboard():
    user_id = session.get('usuario_id')
    
    custom_greeting = session.get('custom_greeting', 'Olá, usuário!')

    all_status = obter_status_processo_config() 
    
    pending_status_options = []
    all_pending_status_ids = []
    for status_item in all_status:
        if "Pendente" in status_item['nome']: 
            pending_status_options.append(status_item)
            all_pending_status_ids.append(str(status_item['id']))
            
    finalizado_status_id = get_status_id_by_name('Finalizado') 
    prenotado_status_id = get_status_id_by_name('Prenotado')

    dashboard_info = {
        'processos_concluidos': get_concluidos_processes_count(), 
        'processos_hoje': get_today_processes_count(), 
        'processos_prenotados': get_prenotados_processes_count(),
        'processos_em_andamento': get_em_andamento_processes_count(),
        'processos_pendentes': get_in_progress_processes_count(), 
        'processos_vinculados_a_mim': get_user_linked_processes_count(user_id), 
        'processos_recentes': get_recent_processes(limit=5), 
        'processos_com_prazo_critico': get_critical_deadline_processes(limit=5), 
        'pending_status_options': pending_status_options,
        'all_pending_status_ids_str': ','.join(all_pending_status_ids),
        'finalizado_status_id': finalizado_status_id,
        'prenotado_status_id': prenotado_status_id
    }

    return render_template('dashboard.html', 
                           dashboard_info=dashboard_info,
                           get_contrast_color=get_contrast_color,
                           formatar_data=formatar_data,
                           now=datetime.now(),
                           custom_greeting=custom_greeting
                          )

@auth_bp.route('/recuperar_senha', methods=['GET', 'POST'])
def recuperar_senha():
    logger.info(f"Acessando página de recuperação de senha. IP: {get_client_ip()}")
    
    email_input = ''

    current_logo_filename = None
    try:
        empresa_info = get_empresa_info() 
        if empresa_info:
            current_logo_filename = empresa_info.get('logo') 
    except Exception as e:
        logger.warning(f"Não foi possível obter a logo da empresa para a tela de recuperação de senha: {e}")
    
    logo_url_for_template = get_image_url_for_display(current_logo_filename, is_company_logo=True)


    if request.method == 'POST':
        if not verificar_csrf_token(request.form.get('csrf_token')):
            flash("Token de segurança inválido. Por favor, recarregue a página e tente novamente.", 'error')
            logger.error(f"Token CSRF inválido em recuperar_senha POST. IP: {get_client_ip()}")
            return render_template('recuperar_senha.html', logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())

        email_input = proteger_input(request.form.get('email'))

        if not email_input:
            flash("Por favor, informe seu e-mail de cadastro.", 'error')
            return render_template('recuperar_senha.html', logo_url=logo_url_for_template, email=email_input, csrf_token=gerar_csrf_token())

        try:
            user = executar_query("SELECT id, email, nome, usuario FROM usuarios WHERE email = ? AND ativo = 1", [email_input], fetch_one=True) 
            
            if not user:
                flash("Se o e-mail estiver cadastrado, um link de recuperação será enviado para sua caixa de entrada.", 'info')
                logger.info(f"Tentativa de recuperação de senha para e-mail não existente/inativo: {email_input}. IP: {get_client_ip()}")
                return render_template('recuperar_senha.html', logo_url=logo_url_for_template, email=email_input, csrf_token=gerar_csrf_token())

            reset_token = create_password_reset_token(user['id'])

            # O endpoint agora existe e o link será gerado corretamente
            recover_link = url_for('auth.reset_password', short_id=reset_token, _external=True)
            email_body = f"""
                Olá {user['nome']},

                Recebemos uma solicitação para redefinir a sua senha no sistema Registro Fácil.
                Para redefinir sua senha, clique no link abaixo:

                {recover_link}

                Se você não solicitou esta redefinição de senha, por favor, ignore este e-mail.
                O link é válido por um tempo limitado.

                Atenciosamente,
                Equipe Registro Fácil
            """
            
            email_sent, email_msg = send_email(user['email'], "Registro Fácil - Recuperação de Senha", email_body, sender_name=None, sender_email=None, app_instance=current_app) 

            if email_sent:
                flash("Se o e-mail estiver cadastrado, um link de recuperação será enviado para sua caixa de entrada.", 'success')
                gravar_log(f"Link de recuperação de senha enviado para {user['email']}", None, user['id'], get_client_ip()) 
                logger.info(f"Link de recuperação de senha enviado para {user['email']}. IP: {get_client_ip()}")
            else:
                flash("Não foi possível enviar o e-mail de recuperação no momento. Tente novamente mais tarde.", 'error')
                logger.error(f"Falha ao enviar e-mail de recuperação para {user['email']}: {email_msg}. IP: {get_client_ip()}")

        except Exception as e:
            flash("Ocorreu um erro inesperado ao processar sua solicitação de recuperação de senha. Por favor, tente novamente mais tarde.", 'error')
            logger.exception(f"Erro inesperado em recuperar_senha para e-mail '{email_input}': {e}")
            return render_template('recuperar_senha.html', logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())

    csrf_token_val = gerar_csrf_token()
    return render_template('recuperar_senha.html', logo_url=logo_url_for_template, csrf_token=csrf_token_val, email=email_input)

# =========================================================================================
# ROTA DE RESETAR SENHA (ADICIONADA PARA RESOLVER O BuildError e CORRIGIDA A VALIDAÇÃO DE DATA)
# =========================================================================================
@auth_bp.route('/reset_password/<short_id>', methods=['GET', 'POST'])
def reset_password(short_id):
    # Obtém a URL da logo da empresa para o template
    current_logo_filename = None
    try:
        empresa_info = get_empresa_info() 
        if empresa_info:
            current_logo_filename = empresa_info.get('logo') 
    except Exception as e:
        logger.warning(f"Não foi possível obter a logo da empresa para a tela de redefinição de senha: {e}")
    
    logo_url_for_template = get_image_url_for_display(current_logo_filename, is_company_logo=True)
    
    # 1. Validar e obter dados do token
    token_data = get_password_reset_token(short_id)
    
    # Validação CRÍTICA do token - Se não existe, é inválido.
    if not token_data:
        flash("Link de recuperação de senha inválido ou expirado.", 'error')
        logger.warning(f"Tentativa de acesso a reset_password com short_id inexistente: {short_id[:6]}... IP: {get_client_ip()}")
        return redirect(url_for('auth.recuperar_senha'))
        
    try:
        # --- CORREÇÃO DE TIMEZONE ---
        # 1. Converte a data de expiração (que é hora local ingênua)
        expires_at_dt_naive = datetime.strptime(token_data['expires_at'], '%Y-%m-%d %H:%M:%S')
        # 2. Obtém a hora atual ingênua (local do servidor)
        now_naive = datetime.now()
        # --- FIM DA CORREÇÃO DE TIMEZONE ---
    except ValueError:
        flash("Erro interno: formato de data de expiração inválido.", 'error')
        logger.error(f"Token '{short_id}' com data de expiração inválida: {token_data['expires_at']}. IP: {get_client_ip()}")
        return redirect(url_for('auth.recuperar_senha'))
        
    # Validação 2: Já foi usado?
    if token_data['is_used'] == 1:
        flash("Este link de recuperação de senha já foi utilizado.", 'error')
        logger.warning(f"Tentativa de acesso a reset_password com short_id já utilizado: {short_id[:6]}... IP: {get_client_ip()}")
        return redirect(url_for('auth.login'))
    
    # Validação 3: Está expirado? (Usando a comparação ingênua corrigida)
    if now_naive > expires_at_dt_naive:
        flash("O link de recuperação de senha expirou.", 'error')
        logger.warning(f"Tentativa de acesso a reset_password com short_id expirado: {short_id[:6]}... IP: {get_client_ip()}")
        return redirect(url_for('auth.recuperar_senha'))

    # Se o token for válido, pega o ID e dados do usuário
    user_id = token_data['user_id']
    # A consulta aqui é para garantir que o usuário ainda existe e está ativo.
    user_data = executar_query("SELECT id, nome, senha FROM usuarios WHERE id = ? AND ativo = 1", [user_id], fetch_one=True)
    
    if not user_data:
        flash("Erro: Usuário associado ao link não encontrado ou inativo.", 'error')
        logger.error(f"Usuário ID {user_id} não encontrado/inativo para o token {short_id}. IP: {get_client_ip()}")
        return redirect(url_for('auth.login'))


    if request.method == 'POST':
        if not verificar_csrf_token(request.form.get('csrf_token')):
            flash("Erro de segurança (CSRF). Por favor, tente novamente.", 'error')
            return render_template('reset_password.html', token=short_id, logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())

        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        # Validação de senha no servidor
        if not nova_senha or not confirmar_senha:
            flash("Ambos os campos de senha são obrigatórios.", 'warning')
            return render_template('reset_password.html', token=short_id, logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())
            
        if nova_senha != confirmar_senha:
            flash("As senhas digitadas não coincidem.", 'warning')
            return render_template('reset_password.html', token=short_id, logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())

        if len(nova_senha) < 8:
            flash("A senha deve ter pelo menos 8 caracteres.", 'warning')
            return render_template('reset_password.html', token=short_id, logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())

        try:
            # Hash da nova senha
            new_password_hash = generate_password_hash(nova_senha)
            
            # Atualizar senha e marcar token como usado em uma transação atômica
            with get_sqlite_connection() as conn:
                # 1. Atualizar senha (usa 'senha' como o nome da coluna no DB)
                conn.execute("UPDATE usuarios SET senha = ?, must_change_password = 0, session_epoch = COALESCE(session_epoch, 0) + 1, session_invalidate_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?", (new_password_hash, user_id))
                
                # 2. Marcar token como usado
                mark_password_reset_token_as_used(token_data['token_id'], connection=conn)
                
            # CORREÇÃO CRÍTICA DE SEGURANÇA: Limpar sessão atual do usuário, se logado
            if session.get('usuario_id') == user_id:
                session.clear() # Força o novo login com a nova senha

            # Log e Redirecionamento de Sucesso
            gravar_log('Redefinição de Senha', None, user_id, get_client_ip(), "Senha redefinida com sucesso via token.")
            flash("Sua senha foi redefinida com sucesso. Por favor, faça login.", 'success')
            return redirect(url_for('auth.login'))

        except sqlite3.Error as e:
            # Erro de banco de dados
            flash(f"Erro de banco de dados ao redefinir a senha. Por favor, tente novamente.", 'error')
            logger.exception(f"Erro de DB ao redefinir senha (short_id: {short_id[:6]}..., User ID: {user_id}): {e}. IP: {get_client_ip()}")
            return render_template('reset_password.html', token=short_id, logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())

        except Exception as e:
            # Erro genérico
            flash("Ocorreu um erro inesperado ao redefinir a senha. Tente novamente mais tarde.", 'error')
            logger.exception(f"Erro inesperado ao redefinir senha (short_id: {short_id[:6]}..., User ID: {user_id}): {e}. IP: {get_client_ip()}")
            return render_template('reset_password.html', token=short_id, logo_url=logo_url_for_template, csrf_token=gerar_csrf_token())

    # GET Request (exibe o formulário de redefinição)
    csrf_token_val = gerar_csrf_token()
    return render_template('reset_password.html', 
                           token=short_id, 
                           logo_url=logo_url_for_template, 
                           user_name=user_data['nome'], 
                           csrf_token=csrf_token_val)

@auth_bp.route('/novo_usuario', methods=['GET', 'POST'])
def novo_usuario():
    
    logo_url_for_template = None # Inicializa para evitar NameError

    current_logo_filename = None
    try:
        empresa_info = get_empresa_info() 
        if empresa_info:
            current_logo_filename = empresa_info.get('logo') 
    except Exception as e:
        logger.warning(f"Não foi possível obter a logo da empresa para a tela de cadastro público: {e}")
    
    # ATUALIZAÇÃO: Calcula a URL da logo após o bloco try/except
    logo_url_for_template = get_image_url_for_display(current_logo_filename, is_company_logo=True)

    if request.method == 'POST':
        if request.form.get('honeypot', '') != '':
            flash("Acesso não autorizado.", 'error')
            logger.warning(f"Honeypot acionado em cadastro público para IP: {get_client_ip()}")
            gravar_log("Falha de cadastro: Honeypot acionado", None, None, get_client_ip()) 
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=request.form.get('nome', ''), email=request.form.get('email', ''),
                                   usuario=request.form.get('usuario', ''), csrf_token=gerar_csrf_token())

        if not verificar_csrf_token(request.form.get('csrf_token')):
            flash("Token de segurança inválido. Por favor, recarregue a página e tente novamente.", 'error')
            logger.error(f"Falha de cadastro: Token CSRF inválido para IP: {get_client_ip()}")
            gravar_log("Falha de cadastro: Token CSRF inválido", None, None, get_client_ip()) 
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=request.form.get('nome', ''), email=request.form.get('email', ''),
                                   usuario=request.form.get('usuario', ''), csrf_token=gerar_csrf_token())

        nome = proteger_input(request.form.get('nome', ''))
        email = proteger_input(request.form.get('email', ''))
        usuario = proteger_input(request.form.get('usuario', ''))
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        ip = get_client_ip()

        if not nome or not email or not usuario or not senha or not confirmar_senha:
            flash("Todos os campos são obrigatórios.", 'error')
            logger.warning(f"Tentativa de cadastro com campos vazios. IP: {ip}")
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=nome, email=email, usuario=usuario, csrf_token=gerar_csrf_token())

        import re as _re_email
        if not _re_email.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            flash("Por favor, insira um endereço de e-mail válido.", 'error')
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=nome, email=email, usuario=usuario, csrf_token=gerar_csrf_token())

        if senha != confirmar_senha:
            flash("As senhas não coincidem. Por favor, digite senhas iguais.", 'error')
            logger.warning(f"Tentativa de cadastro: senhas não coincidem para usuário '{usuario}'. IP: {ip}")
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=nome, email=email, usuario=usuario, csrf_token=gerar_csrf_token())

        if len(senha) < 8:
            flash("A senha deve ter no mínimo 8 caracteres para sua segurança.", 'error')
            logger.warning(f"Tentativa de cadastro: senha muito curta para usuário '{usuario}'. IP: {ip}")
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=nome, email=email, usuario=usuario, csrf_token=gerar_csrf_token())

        try:
            rows_affected = create_user(nome, email, usuario, generate_password_hash(senha), role='user') 

            if rows_affected:
                flash("Sua conta foi criada com sucesso! Por favor, faça login.", 'success')
                logger.info(f"Novo usuário '{usuario}' registrado com sucesso. IP: {ip}")
                gravar_log(f"Novo usuário registrado: {usuario}", None, None, ip) 
                return redirect(url_for('auth.login'))
            else:
                flash("Erro ao criar conta. O nome de usuário ou e-mail já está em uso.", 'error')
                logger.warning(f"Falha ao registrar usuário '{usuario}'. Provavelmente duplicidade de usuário/email. IP: {get_client_ip()}")
                return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                       nome=nome, email=email, usuario=usuario, csrf_token=gerar_csrf_token())
        except sqlite3.IntegrityError as e:
            flash("Erro ao criar conta: o nome de usuário ou e-mail já está em uso.", 'error')
            logger.warning(f"Falha ao registrar usuário '{usuario}'. Duplicidade de usuário/email. Erro: {e}. IP: {get_client_ip()}")
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=nome, email=email, usuario=usuario, csrf_token=gerar_csrf_token())
        except Exception as e:
            flash("Ocorreu um erro inesperado ao criar sua conta. Por favor, tente novamente mais tarde.", 'error')
            logger.exception(f"Erro inesperado durante registro para '{usuario}': {e}")
            return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                                   nome=nome, email=email, usuario=usuario, csrf_token=gerar_csrf_token())

    csrf_token_val = gerar_csrf_token()
    return render_template('novo_usuario.html', logo_url=logo_url_for_template,
                           nome=request.form.get('nome', ''),
                           email=request.form.get('email', ''),
                           usuario=request.form.get('usuario', ''),
                           csrf_token=csrf_token_val)