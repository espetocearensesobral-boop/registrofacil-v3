# registrofacil/routes/empresa.py

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
import functools
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import hashlib
import re
import secrets
import sqlite3

from models import (
    executar_query, gravar_log, get_user_by_username,
    get_empresa_info, save_empresa_info,
    get_sqlite_connection,
)
from routes.auth import login_status_required, get_client_ip, proteger_input, verificar_csrf_token, admin_required, gerar_csrf_token
from routes.permissoes import permission_required
from utils.logger import operacional_logger as logger
from config import Config
from utils.file_uploads import get_image_url_for_display, handle_image_upload, remove_image_file, EMPRESA_UPLOAD_FOLDER
from utils.helpers import validar_telefone, validar_email

empresa_bp = Blueprint('empresa', __name__, url_prefix='/empresa')

@empresa_bp.route('/', methods=['GET', 'POST'])
@login_status_required
# REMOVIDO: @admin_required
@permission_required('empresa_visualizar')
def index():
    empresa_data = {}
    try:
        empresa_data_raw = get_empresa_info()
        if empresa_data_raw:
            empresa_data = empresa_data_raw

    except Exception as e:
        logger.exception(f"Erro ao carregar dados da empresa: {e}")
        flash("Não foi possível carregar os dados da empresa. Consulte os logs.", 'danger')
        empresa_data = {}

    display_logo_url = get_image_url_for_display(empresa_data.get('logo'), is_company_logo=True)

    if request.method == 'POST':
        # ADICIONADO: Verificação de role para o método POST
        if session.get('usuario_role') != 'admin':
            logger.warning(f"Tentativa de edição de informações da empresa por usuário não-admin. Usuário ID: {session.get('usuario_id')}, IP: {get_client_ip()}")
            flash("Acesso restrito a administradores para editar as informações da empresa.", 'error')
            return redirect(url_for('empresa.index'))

        if not verificar_csrf_token(request.form.get('csrf_token')):
            flash("Token de segurança inválido. Por favor, recarregue a página e tente novamente.", 'error')
            logger.error(f"Token CSRF inválido na rota da empresa POST. User ID: {session.get('usuario_id')}, IP: {get_client_ip()}")
            return redirect(url_for('empresa.index'))

        usuario_id = session.get('usuario_id')
        current_user_username = session.get('usuario_username')
        
        try:
            # REMOVIDO: Lógica de verificação de senha atual
            # A validação de senha foi removida conforme sua solicitação.
            # Agora, a alteração dos dados da empresa não exige a senha do usuário logado.

            dados_form = {
                'id': empresa_data.get('id'),
                'cartorio': proteger_input(request.form.get('cartorio')),
                'oficial': proteger_input(request.form.get('oficial')),
                'substituta': proteger_input(request.form.get('substituta')),
                'endereco': proteger_input(request.form.get('endereco')),
                'telefone': proteger_input(request.form.get('telefone')),
                'email': proteger_input(request.form.get('email')),
                'logo': empresa_data.get('logo')
            }

            # Validações de campos obrigatórios
            if not dados_form['cartorio']: raise ValueError('O campo Nome da Organização é obrigatório.')
            if not dados_form['oficial']: raise ValueError('O campo Oficial Responsável é obrigatório.')
            if not dados_form['endereco']: raise ValueError('O Endereço Completo é obrigatório.')
            if not dados_form['telefone']: raise ValueError('O Telefone é obrigatório.')
            if not dados_form['email']: raise ValueError('O E-mail é obrigatório.')
            
            # Validação de formato de e-mail e telefone usando utils.helpers
            validar_telefone(dados_form['telefone']) 
            validar_email(dados_form['email'])       

            is_new_record = not bool(empresa_data.get('id'))
            
            # Lógica para upload/remoção da imagem da logo do cartório
            # SVG removido: por ser XML, pode conter <script>/on* e habilitar XSS
            # armazenado se o arquivo for aberto/renderizado inline no navegador.
            ALLOWED_LOGO_EXTENSIONS = ['jpg', 'jpeg', 'png']
            MAX_LOGO_SIZE_MB = 2

            if 'logo' in request.files:
                uploaded_file = request.files['logo']
                try:
                    new_filename = handle_image_upload(
                        uploaded_file=uploaded_file,
                        current_filename=dados_form['logo'],
                        target_folder=EMPRESA_UPLOAD_FOLDER,
                        allowed_extensions=ALLOWED_LOGO_EXTENSIONS,
                        max_size_mb=MAX_LOGO_SIZE_MB,
                        prefix='logo_cartorio'
                    )
                    if new_filename:
                        dados_form['logo'] = new_filename
                except ValueError as e:
                    flash(f"Erro no upload da logo: {e}", 'warning')
                    logger.warning(f"Erro de validação no upload da logo da empresa: {e}. User ID: {usuario_id}")
                except Exception as e:
                    flash("Não foi possível processar a logo. Consulte os logs.", 'warning')
                    logger.error(f"Erro inesperado no upload da logo da empresa: {e}. User ID: {usuario_id}", exc_info=True)

            elif request.form.get('remover_logo') == '1':
                if remove_image_file(dados_form['logo'], EMPRESA_UPLOAD_FOLDER):
                    dados_form['logo'] = None
                else:
                    dados_form['logo'] = None
                    logger.warning(f"Falha ao remover arquivo físico da logo da empresa, mas o DB será atualizado para nulo. User ID: {usuario_id}")

            with get_sqlite_connection() as conn:
                rows_affected = save_empresa_info(dados_form, is_new_record, connection=conn)
                
                if rows_affected:
                    flash('Dados da empresa atualizados com sucesso!', 'success')
                    # ALTERADO: Passando a conexão para gravar_log para evitar 'database is locked'
                    gravar_log('Atualizou informações da empresa', None, usuario_id, get_client_ip(), f"Organização: {dados_form['cartorio']}", connection=conn)

                    session['empresa_logo_url'] = get_image_url_for_display(dados_form.get('logo'), is_company_logo=True)
                else:
                    flash('Nenhuma alteração detectada ou erro ao salvar.', 'info')

        except ValueError as e:
            flash(f"Erro de validação: {e}", 'error')
            logger.warning(f"Erro de validação ao salvar info da empresa: {e}. User ID: {usuario_id}, IP: {get_client_ip()}")
        except sqlite3.Error as e:
            flash("Não foi possível salvar os dados da empresa. Consulte os logs.", 'danger')
            logger.exception(f"Erro de DB ao salvar info da empresa. User ID: {usuario_id}, IP: {get_client_ip()}: {e}")
        except Exception as e:
            flash("Não foi possível salvar os dados da empresa. Consulte os logs.", 'danger')
            logger.exception(f"Erro inesperado ao salvar info da empresa. User ID: {usuario_id}, IP: {get_client_ip()}: {e}")
        
        return redirect(url_for('configuracoes.index', tab='estabelecimento'))

    csrf_token_val = gerar_csrf_token()
    # Se chamado diretamente (URL /empresa/), redireciona para configuracoes/estabelecimento
    return redirect(url_for('configuracoes.index', tab='estabelecimento'))