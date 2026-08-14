# registrofacil/routes/configuracoes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
import os
import secrets
from datetime import datetime

from routes.auth import login_status_required, admin_required, verificar_csrf_token, get_client_ip, gerar_csrf_token
from routes.permissoes import permission_required
from models import (
    get_email_config, save_email_config, send_email,
    get_backup_config, save_backup_config,
    gravar_log, obter_status_processo_config, obter_tipos_servico,
    update_status_processo, update_tipo_servico,
    add_status_processo, add_tipo_servico,
    toggle_status_processo, toggle_tipo_servico
)
from config import Config
from utils.logger import logger
from utils.scheduler import configure_and_start_scheduler

configuracoes_bp = Blueprint('configuracoes', __name__, url_prefix='/configuracoes')

def proteger_input(texto):
    if texto is None:
        return ""
    return str(texto).strip()

@configuracoes_bp.route('/', methods=['GET', 'POST'])
@configuracoes_bp.route('/salvar', methods=['GET', 'POST'])
@login_status_required
@permission_required('config_geral')
def index():
    usuario_id = session.get('usuario_id')
    usuario_role = session.get('usuario_role')
    active_tab = request.args.get('tab', 'status')

    if request.method == 'POST':
        # Verifica se é uma requisição AJAX (para e-mail)
        is_ajax = (request.headers.get('X-Requested-With') == 'XMLHttpRequest') or \
                 (request.form.get('test_email') == '1') or \
                 (request.form.get('action') == 'update_email_config')

        if not verificar_csrf_token(request.form.get('csrf_token')):
            msg = "Token de segurança inválido. Por favor, tente novamente."
            if is_ajax:
                return jsonify({'success': False, 'message': msg})
            flash(msg, 'danger')
            return redirect(url_for('configuracoes.index', tab=active_tab))

        action = request.form.get('action')
        
        try:
            if action == 'update_db_settings':
                active_tab = 'db'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                # Simulação de teste de conexão para a aba de banco de dados
                from models import test_db_connection
                if test_db_connection():
                    flash("Conexão com o banco de dados está funcional!", 'success')
                else:
                    flash("Erro ao conectar com o banco de dados.", 'danger')
            
            elif action == 'optimize_db':
                active_tab = 'db'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                # Otimizar banco de dados usando VACUUM
                from models import optimize_database
                try:
                    if optimize_database():
                        flash("Banco de dados otimizado com sucesso! O arquivo foi desfragmentado e reorganizado.", 'success')
                        gravar_log("Otimizou banco de dados", None, usuario_id, get_client_ip(), "Banco de dados otimizado (VACUUM)", contexto="Comando VACUUM executado pelo administrador")
                    else:
                        flash("Erro ao otimizar o banco de dados. Verifique os logs.", 'danger')
                except Exception as e:
                    logger.error(f"Erro ao otimizar banco de dados: {e}")
                    flash(f"Erro ao otimizar banco de dados: {str(e)}", 'danger')

            elif action == 'update_email_config':
                active_tab = 'email'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                # Mapeamento de campos para coincidir com o template
                smtp_host = proteger_input(request.form.get('mail_server'))
                smtp_port_raw = request.form.get('mail_port')
                smtp_port = int(smtp_port_raw) if smtp_port_raw and smtp_port_raw.isdigit() else 587
                smtp_username = proteger_input(request.form.get('mail_username'))
                smtp_password = request.form.get('mail_password')
                sender_email = proteger_input(request.form.get('mail_default_sender'))
                sender_name = "Registro Fácil"
                
                use_tls = 1 if request.form.get('mail_use_tls') == '1' else 0
                use_ssl = 1 if request.form.get('mail_use_ssl') == '1' else 0
                smtp_encryption = 'tls' if use_tls else ('ssl' if use_ssl else 'none')
                
                ativo = 1 if request.form.get('ativo') in ['1', 'on'] else 0
                config_id_raw = request.form.get('id')
                config_id = int(config_id_raw) if config_id_raw and config_id_raw.isdigit() else None

                if not all([smtp_host, smtp_username, sender_email]):
                    raise ValueError("Todos os campos obrigatórios de e-mail devem ser preenchidos.")
                
                # Validar formato de e-mail
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, sender_email):
                    raise ValueError("O e-mail do remetente não é válido.")

                email_data = {
                    'id': config_id,
                    'smtp_host': smtp_host,
                    'smtp_port': smtp_port,
                    'smtp_encryption': smtp_encryption,
                    'smtp_username': smtp_username,
                    'smtp_password': smtp_password,
                    'sender_email': sender_email,
                    'sender_name': sender_name,
                    'ativo': ativo
                }

                # Se for apenas teste
                if request.form.get('test_email') == '1':
                    success, message = send_email(
                        to_address=sender_email,
                        subject="Teste de Configuração - Registro Fácil",
                        body="Se você recebeu este e-mail, sua configuração SMTP está funcionando corretamente.",
                        sender_name=sender_name,
                        sender_email=sender_email,
                        app_instance=current_app._get_current_object()
                    )
                    return jsonify({'success': success, 'message': message})

                # Se não houver ID, é uma nova configuração
                is_new = config_id is None or config_id <= 0
                if save_email_config(email_data, is_new_config=is_new):
                    gravar_log("Configurações de e-mail atualizadas", None, usuario_id, get_client_ip(),
                        f"Servidor SMTP: {smtp_host} | Remetente: {sender_email}",
                        contexto=f"Host: {smtp_host}\nPorta: {smtp_port}\nE-mail: {sender_email}\nCriptografia: {smtp_encryption}\nAtivo: {'Sim' if ativo else 'Não'}")
                    return jsonify({'success': True, 'message': "Configurações de e-mail salvas com sucesso!"})
                else:
                    raise ValueError("Falha ao salvar as configurações de e-mail no banco de dados.")
            
            elif action == 'update_backup_settings':
                active_tab = 'backup'
                if usuario_role != 'admin':
                    raise ValueError("Acesso restrito a administradores.")
                
                local_path = proteger_input(request.form.get('local_path'))
                uploads_path = None  # Caminho de anexos é gerenciado pelo Config, não pelo formulário
                auto_backup_enabled = 1 if request.form.get('auto_backup_enabled') in ['on', '1', 'true', True] else 0
                backup_frequency = proteger_input(request.form.get('backup_frequency'))
                backup_time = proteger_input(request.form.get('backup_time'))
                backup_days = request.form.getlist('backup_days[]')
                backup_day_of_month_raw = request.form.get('backup_day_of_month')
                backup_day_of_month = int(backup_day_of_month_raw) if backup_day_of_month_raw and backup_day_of_month_raw.isdigit() else 1

                if not local_path:
                    raise ValueError("O caminho local para o backup é obrigatório.")
                
                try:
                    os.makedirs(local_path, exist_ok=True)
                    test_file = os.path.join(local_path, f".test_{secrets.token_hex(4)}")
                    with open(test_file, 'w') as f: f.write("test")
                    os.remove(test_file)
                except Exception as e:
                    raise ValueError(f"Erro de permissão no caminho de backup: {e}")

                backup_config_data = {
                    'id': int(request.form.get('id')) if request.form.get('id') else None,
                    'local_path': local_path,
                    'uploads_path': uploads_path,
                    'auto_backup_enabled': auto_backup_enabled,
                    'backup_frequency': backup_frequency,
                    'backup_time': backup_time,
                    'backup_days': backup_days,
                    'backup_day_of_month': backup_day_of_month,
                    'cloud_provider': 'none'
                }

                if save_backup_config(backup_config_data):
                    try:
                        configure_and_start_scheduler(current_app.app_context)
                        flash("Configurações de backup atualizadas com sucesso!", 'success')
                    except Exception as e:
                        logger.error(f"Erro ao reconfigurar scheduler: {e}")
                        flash("Configurações salvas, mas houve um erro no agendador.", 'warning')
                    gravar_log("Configurações de backup atualizadas", None, usuario_id, get_client_ip(),
                    f"Tipo: {backup_frequency} | Auto: {'Ativado' if auto_backup_enabled else 'Desativado'} | Hora: {backup_time}",
                    contexto=f"Frequência: {backup_frequency}\nAuto-backup: {'Ativado' if auto_backup_enabled else 'Desativado'}\nHorário: {backup_time}\nCaminho: {local_path}")

            elif action == 'add_status':
                active_tab = 'status'
                nome = proteger_input(request.form.get('nome'))
                hex_color = proteger_input(request.form.get('hex_color'))
                if not nome or not hex_color:
                    raise ValueError("Nome e cor são obrigatórios.")
                add_status_processo(nome, hex_color)
                flash(f"Status '{nome}' adicionado com sucesso!", 'success')
                gravar_log("Status adicionado", None, usuario_id, get_client_ip(),
                f"Status '{nome}' criado com cor {hex_color}",
                contexto=f"Nome: {nome}\nCor: {hex_color}")

            elif action == 'edit_status':
                active_tab = 'status'
                status_id = int(request.form.get('id')) if request.form.get('id') else None
                nome = proteger_input(request.form.get('nome'))
                hex_color = proteger_input(request.form.get('hex_color'))
                ativo = 1 if request.form.get('ativo') == '1' else 0
                update_status_processo(status_id, nome, hex_color, ativo)
                flash(f"Status '{nome}' atualizado!", 'success')
                gravar_log("Status editado", None, usuario_id, get_client_ip(),
                f"Status ID {status_id}: {nome}",
                contexto=f"ID: {status_id} | Nome: {nome}")

            elif action == 'toggle_status':
                active_tab = 'status'
                status_id = int(request.form.get('id')) if request.form.get('id') else None
                toggle_status_processo(status_id)
                flash("Status alterado!", 'success')

            elif action == 'add_service':
                active_tab = 'services'
                nome = proteger_input(request.form.get('nome'))
                descricao = proteger_input(request.form.get('descricao'))
                prazo_raw = request.form.get('prazo_padrao')
                prazo = int(prazo_raw) if prazo_raw and prazo_raw.isdigit() else 0
                add_tipo_servico(nome, descricao, prazo)
                flash(f"Serviço '{nome}' adicionado!", 'success')
                gravar_log("Tipo de serviço adicionado", None, usuario_id, get_client_ip(),
                f"Serviço '{nome}' adicionado",
                contexto=f"Nome: {nome}\nPrazo padrão: {prazo} dias")

            elif action == 'edit_service':
                active_tab = 'services'
                service_id = int(request.form.get('id')) if request.form.get('id') else None
                nome = proteger_input(request.form.get('nome'))
                descricao = proteger_input(request.form.get('descricao'))
                prazo_raw = request.form.get('prazo_padrao')
                prazo = int(prazo_raw) if prazo_raw and prazo_raw.isdigit() else 0
                ativo = 1 if request.form.get('ativo') == '1' else 0
                update_tipo_servico(service_id, nome, descricao, ativo, prazo)
                flash(f"Serviço '{nome}' atualizado!", 'success')
                gravar_log("Tipo de serviço editado", None, usuario_id, get_client_ip(),
                f"Serviço ID {service_id}: {nome}",
                contexto=f"ID: {service_id} | Nome: {nome}")

            elif action == 'toggle_service':
                active_tab = 'services'
                service_id = int(request.form.get('id')) if request.form.get('id') else None
                toggle_tipo_servico(service_id)
                flash("Tipo de serviço alterado!", 'success')

        except ValueError as e:
            logger.warning(f"Erro de validação nas configurações: {e}")
            if is_ajax:
                return jsonify({'success': False, 'message': str(e)})
            flash(f"Erro: {str(e)}", 'danger')
        except Exception as e:
            logger.exception(f"Erro ao processar configurações: {e}")
            if is_ajax:
                return jsonify({'success': False, 'message': f"Erro inesperado: {str(e)}"})
            flash(f"Erro inesperado: {str(e)}", 'danger')

        return redirect(url_for('configuracoes.index', tab=active_tab))

    # GET request
    try:
        email_config = get_email_config()
        backup_config = get_backup_config()
        tipos_processo = obter_tipos_servico()
        status_processo = obter_status_processo_config()
        
        if email_config:
            email_config['mail_server'] = email_config.get('smtp_host', '')
            email_config['mail_port'] = email_config.get('smtp_port', 587)
            email_config['mail_username'] = email_config.get('smtp_username', '')
            email_config['mail_password'] = email_config.get('smtp_password', '')
            email_config['mail_default_sender'] = email_config.get('sender_email', '')
            email_config['mail_use_tls'] = (email_config.get('smtp_encryption') == 'tls')
            email_config['mail_use_ssl'] = (email_config.get('smtp_encryption') == 'ssl')

        db_config = {
            'path_completo': Config.DATABASE_PATH
        }
        
        # Carrega dados da empresa para aba Estabelecimento
        from models import get_empresa_info
        from utils.file_uploads import get_image_url_for_display
        empresa_data = get_empresa_info() or {}
        display_logo_url = get_image_url_for_display(empresa_data.get('logo'), is_company_logo=True)

        from utils.helpers import get_contrast_color
        csrf_token_val = gerar_csrf_token()

        return render_template('configuracoes.html',
                               email_config=email_config,
                               backup_config=backup_config,
                               tipos_processo=tipos_processo,
                               status_list=status_processo,
                               db_config=db_config,
                               active_tab=active_tab,
                               DEFAULT_BACKUP_PATH=Config.DEFAULT_BACKUP_PATH,
                               UPLOAD_PROCESSOS_DIR=Config.UPLOAD_PROCESSOS_DIR,
                               csrf_token=csrf_token_val,
                               get_contrast_color=get_contrast_color,
                               empresa=empresa_data,
                               display_logo_url=display_logo_url)
    except Exception as e:
        logger.exception(f"Erro ao carregar página de configurações: {e}")
        flash(f"Erro ao carregar configurações: {str(e)}", 'danger')
        return redirect(url_for('auth.dashboard'))
