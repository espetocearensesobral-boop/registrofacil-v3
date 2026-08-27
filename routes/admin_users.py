# registrofacil/routes/admin_users.py

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
import functools
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import hashlib
import re
import secrets
from datetime import datetime
import sqlite3

from models import (
    executar_query, gravar_log, get_user_by_username,
    get_users_for_admin_list,
    get_sqlite_connection,
    gravar_auditoria_admin, gravar_tentativa_nao_autorizada,
    criar_notificacao_usuario, mascarar_email,
    bump_user_session_epoch
)
from routes.auth import (
    login_status_required, get_client_ip, proteger_input, verificar_csrf_token,
    admin_required, gerar_csrf_token, validate_user_role, ensure_admin_safety
)
from routes.permissoes import permission_required, has_permission
from utils.logger import auth_logger as logger
from utils.notification_contract import success, error, warning

admin_users_bp = Blueprint('admin_users', __name__, url_prefix='/admin')


@admin_users_bp.route('/usuarios', methods=['GET', 'POST'])
@login_status_required
@permission_required('admin_usuarios_visualizar')
def users_list():
    current_user_id = session.get('usuario_id')
    current_user_username = session.get('usuario_username')
    current_user_role = session.get('usuario_role')

    if request.method == 'POST':
        action = request.form.get('action')
        
        if not verificar_csrf_token(request.form.get('csrf_token')):
            flash("Token de segurança inválido. Por favor, recarregue a página e tente novamente.", 'error')
            logger.error(f"Token CSRF inválido em users_list POST. User ID: {current_user_id}, IP: {get_client_ip()}")
            return redirect(url_for('admin_users.users_list'))

        if action == 'inativar_usuario':
            if not has_permission(current_user_id, 'admin_usuarios_ativar'):
                flash('Você não tem permissão para ativar ou inativar usuários.', 'error')
                return redirect(url_for('admin_users.users_list'))

            user_id_to_inactivate = request.form.get('id_usuario', type=int)
            senha_admin_confirmacao = request.form.get('senha_admin', '') 

            try:
                target_user_data = executar_query("SELECT id, usuario, nome, ativo, role FROM usuarios WHERE id = ?", [user_id_to_inactivate], fetch_one=True)

                if not target_user_data:
                    raise ValueError('Usuário não encontrado para inativação.')
                
                if user_id_to_inactivate == current_user_id:
                    raise ValueError('Você não pode inativar seu próprio usuário!')

                ensure_admin_safety(
                    target_user_data,
                    target_role=target_user_data['role'],
                    target_active=False,
                    current_user_id=current_user_id,
                )
                
                if not target_user_data['ativo']:
                    raise ValueError('Usuário já está inativo.')
                
                # ADICIONADO: Validação da senha do usuário logado para confirmar a inativação
                if not senha_admin_confirmacao:
                    raise ValueError('Sua senha de confirmação é obrigatória para realizar esta ação.')
                
                current_user_db_data = get_user_by_username(current_user_username)
                if not current_user_db_data or not check_password_hash(current_user_db_data['senha'], senha_admin_confirmacao):
                    logger.warning(f"Tentativa de inativação falhou: Senha de confirmação incorreta para usuário {current_user_id}.")
                    raise ValueError('Sua senha está incorreta. Inativação não realizada.')


                with get_sqlite_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Reatribuir processos do usuário inativado para o administrador que realizou a ação
                    cursor.execute(
                        "UPDATE processos SET responsavel_id = ? WHERE responsavel_id = ?",
                        (current_user_id, user_id_to_inactivate)
                    )

                    # ADICIONADO: Atualiza session_invalidate_at ao inativar usuário
                    cursor.execute(
                        "UPDATE usuarios SET ativo = 0, deleted_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), session_epoch = COALESCE(session_epoch, 0) + 1, session_invalidate_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime') WHERE id = ?",
                        (user_id_to_inactivate,)
                    )

                flash(f"Usuário '{target_user_data['nome']}' inativado com sucesso! Seus processos foram reatribuídos a você.", 'success')
                gravar_log('Inativou usuário', None, current_user_id, get_client_ip(), f"Usuário {target_user_data['nome']} (ID: {user_id_to_inactivate}) inativado.")

            except ValueError as e:
                flash(f'Erro ao inativar usuário: {e}', 'error')
                logger.error(f"Erro ao inativar usuário (ID: {user_id_to_inactivate}): {e}. User ID: {current_user_id}, IP: {get_client_ip()}")
            except sqlite3.Error as e:
                flash(f'Erro de banco de dados ao inativar usuário: {e}', 'error')
                logger.exception(f"Erro de DB ao inativar usuário (ID: {user_id_to_inactivate}). User ID: {current_user_id}, IP: {get_client_ip()}: {e}")
            except Exception as e:
                flash(f'Erro inesperado ao inativar usuário: {e}', 'error')
                logger.exception(f"Erro inesperado ao inativar usuário (ID: {user_id_to_inactivate}). User ID: {current_user_id}, IP: {get_client_ip()}: {e}")
        
        return redirect(url_for('admin_users.users_list'))


    pagina_atual = request.args.get('pagina', 1, type=int)
    itens_por_pagina = request.args.get('itens_por_pagina', 50, type=int)
    if not (1 <= itens_por_pagina <= 100):
        itens_por_pagina = 50
        flash("Lote de registros inválido; usando o lote padrão de 50.", 'warning')

    filtro_busca = proteger_input(request.args.get('busca'))
    filtro_status = request.args.get('status', 'ativo')
    ordenar = request.args.get('ordenar', 'created_at_desc')

    filters = {
        'status': filtro_status,
        'busca': filtro_busca
    }

    try:
        result = get_users_for_admin_list(filters, pagina_atual, itens_por_pagina, ordenar)
        usuarios = result['users']

        total_usuarios = result['total_records']
        total_paginas = result['total_pages']

        contagem_total_geral = executar_query("SELECT COUNT(*) AS count FROM usuarios", fetch_one=True)['count']
        contagem_ativos = executar_query("SELECT COUNT(*) AS count FROM usuarios WHERE ativo = 1", fetch_one=True)['count']
        contagem_inativos = executar_query("SELECT COUNT(*) AS count FROM usuarios WHERE ativo = 0", fetch_one=True)['count']
        contagem_hoje = executar_query("SELECT COUNT(*) AS count FROM usuarios WHERE strftime('%Y-%m-%d', created_at) = strftime('%Y-%m-%d', 'now', 'localtime')", fetch_one=True)['count']

        has_active_filters = any([
            filtro_status != 'ativo', filtro_busca, ordenar != 'created_at_desc'
        ])

    except Exception as e:
        logger.exception(f"Erro ao carregar lista de usuários: {e}")
        flash(f"Erro ao carregar usuários: {e}", 'danger')
        usuarios = []
        total_usuarios = 0
        total_paginas = 0
        contagem_total_geral = 0
        contagem_ativos = 0
        contagem_inativos = 0
        contagem_hoje = 0
        has_active_filters = False
    
    csrf_token_val = gerar_csrf_token()
    return render_template('admin/usuarios.html',
                           usuarios=usuarios,
                           total_usuarios=total_usuarios,
                           total_paginas=total_paginas,
                           pagina_atual=pagina_atual,
                           itens_por_pagina=itens_por_pagina,
                           filtro_busca=filtro_busca,
                           filtro_status=filtro_status,
                           ordenar=ordenar,
                           contagem_total=contagem_total_geral,
                           contagem_ativos=contagem_ativos,
                           contagem_inativos=contagem_inativos,
                           contagem_hoje=contagem_hoje,
                           has_active_filters=has_active_filters,
                           current_user_id=current_user_id,
                           current_user_role=current_user_role,
                           csrf_token=csrf_token_val)

@admin_users_bp.route('/editar_usuario/<int:user_id>', methods=['GET', 'POST'])
@login_status_required
@permission_required('admin_usuarios_editar')
def edit_user(user_id):
    current_user_id = session.get('usuario_id')
    current_user_username = session.get('usuario_username')
    current_user_role = session.get('usuario_role')

    user_data = None
    try:
        # MODIFICADO: Inclui session_invalidate_at na consulta
        user_data_raw = executar_query(
            "SELECT id, usuario, nome, email, ativo, role, created_at, updated_at, deleted_at, last_login_at, session_invalidate_at FROM usuarios WHERE id = ?",
            [user_id], fetch_one=True
        )
        if not user_data_raw:
            flash('Usuário não encontrado ou já excluído.', 'error')
            logger.warning(f"Usuário não encontrado ou já excluído no DB para ID: {user_id}. Logado: {current_user_id}. IP: {get_client_ip()}")
            if user_id == current_user_id:
                session.clear()
                return redirect(url_for('auth.login'))
            return redirect(url_for('admin_users.users_list'))
        
        user_data = user_data_raw

    except Exception as e:
        logger.exception(f"Erro ao carregar dados do usuário {user_id} para edição: {e}")
        flash('Erro ao carregar dados do usuário. Tente novamente mais tarde.', 'danger')
        return redirect(url_for('admin_users.users_list'))
    
    # Lógica de permissão de acesso à edição no GET - MANTIDA PARA SEGURANÇA
    if current_user_role != 'admin': # Considerar 'suporte' para acesso aqui, se for o caso
        if current_user_id != user_id:
            flash('Acesso negado. Você só pode editar seu próprio perfil.', 'error')
            logger.warning(f"Tentativa de edição não autorizada por role. Logado: {current_user_id} (Role: {current_user_role}) | Alvo: {user_id}. IP: {get_client_ip()}")
            return redirect(url_for('auth.dashboard'))
    
    if request.method == 'POST':
        try:
            # MODIFICADO: Inclui session_invalidate_at na consulta
            user_data_raw = executar_query(
                "SELECT id, usuario, nome, email, ativo, role, created_at, updated_at, deleted_at, last_login_at, session_invalidate_at FROM usuarios WHERE id = ?",
                [user_id], fetch_one=True
            )
            if not user_data_raw:
                flash('Usuário não encontrado para atualização.', 'error')
                return jsonify(success=False, message="Usuário não encontrado para atualização.", type='danger'), 404
            user_data = user_data_raw
        except Exception as e:
            logger.exception(f"Erro ao recarregar dados do usuário {user_id} para validação POST: {e}")
            return jsonify(success=False, message="Erro interno ao recarregar dados do usuário.", type='danger'), 500

        if not verificar_csrf_token(request.form.get('csrf_token')):
            logger.error(f"Token CSRF inválido em edit_user POST. User ID: {current_user_id}, Alvo: {user_id}. IP: {get_client_ip()}")
            return jsonify(success=False, message="Sessão expirada ou token de segurança inválido. Por favor, recarregue a página e tente novamente.", type='danger'), 403
        
        nome = proteger_input(request.form.get('nome'))
        email = proteger_input(request.form.get('email'))
        
        # --- Política de role/status ---
        role_post = proteger_input(request.form.get('role'))

        role = validate_user_role(user_data.get('role', 'user'))
        ativo = user_data.get('ativo', 0)

        # Apenas admin (ou um fluxo granular específico) pode alterar role/status.
        if current_user_role == 'admin':
            role = validate_user_role(role_post or role)
            # A presença da chave 'ativo' significa checkbox marcado.
            ativo = 'ativo' in request.form
        # --- FIM DA POLÍTICA ---

        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')

        try:
            if not nome: raise ValueError('O nome completo é obrigatório.')
            if not email: raise ValueError('O e-mail é obrigatório.')
            if not re.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                raise ValueError('O formato do e-mail é inválido.')
            
            # Checa se o e-mail já está em uso por outro usuário ATIVO (ignora o próprio usuário atual)
            check_email_query = "SELECT id FROM usuarios WHERE email = ? AND id != ? AND ativo = 1 LIMIT 1"
            found_email_user = executar_query(check_email_query, [email, user_id], fetch_one=True)
            if found_email_user:
                raise ValueError(f"O e-mail '{email}' já está em uso por outro usuário ativo.")
            
            if nova_senha:
                if nova_senha != confirmar_senha: raise ValueError('As senhas não coincidem.')
                if len(nova_senha) < 8: raise ValueError('A nova senha deve ter pelo menos 8 caracteres.')

            ensure_admin_safety(user_data, role, bool(ativo), current_user_id=current_user_id)
            security_change = (
                user_data['role'] != role
                or user_data['ativo'] != (1 if ativo else 0)
                or bool(nova_senha)
            )

            with get_sqlite_connection() as conn:
                cursor = conn.cursor()

                sql = "UPDATE usuarios SET nome = ?, email = ?, ativo = ?, role = ?, updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')"
                if security_change:
                    sql += ", session_epoch = COALESCE(session_epoch, 0) + 1, session_invalidate_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')"

                params = [nome, email, (1 if ativo else 0), role]

                if nova_senha:
                    sql += ", senha = ?, must_change_password = 0"
                    params.append(generate_password_hash(nova_senha))

                sql += " WHERE id = ?"
                params.append(user_id) 

                cursor.execute(sql, params)
                rows_affected = cursor.rowcount

                if not rows_affected:
                    raise ValueError("Nenhuma alteração detectada ou usuário não encontrado.")

            gravar_log('Editou usuário', None, current_user_id, get_client_ip(), f"Usuário {user_data['usuario']} (ID: {user_id}) editado. Role: {role}")

            # ADICIONADO: Lógica de logout automático se o usuário se inativar (mantida)
            if user_id == current_user_id and user_data['ativo'] == 1 and ativo == 0:
                session.clear() 
                flash("Sua conta foi inativada. Você foi desconectado(a).", 'success')
                logger.info(f"Usuário (ID: {user_id}) se inativou e foi desconectado.")
                return jsonify(success=True, message="Sua conta foi inativada. Você foi desconectado(a).", redirect=url_for('auth.login')), 200
            
            # ATENÇÃO: Atualiza a sessão para o usuário logado se ele editou o próprio perfil
            if user_id == current_user_id:
                session['usuario_nome'] = nome
                session['usuario_email'] = email
                session['usuario_role'] = role
                session['is_active'] = ativo 
                
                return jsonify({
                    **success('Seu perfil foi atualizado com sucesso!'),
                    'success': True,
                    'redirect': url_for('auth.dashboard'),
                    'user_id': current_user_id,
                    'updated_user_data': {
                        'nome': nome,
                        'email': email,
                        'role': role,
                        'is_active': ativo
                    }
                })

            return jsonify(**success('Usuário atualizado com sucesso!'), redirect=url_for('admin_users.users_list'))

        except ValueError as e:
            logger.warning(f"Erro de validação ao editar usuário (ID: {user_id}): {e}. User ID: {current_user_id}, IP: {get_client_ip()}")
            return jsonify(**warning(str(e)), success=False), 400
        except sqlite3.Error as e:
            logger.exception(f"Erro de banco de dados ao atualizar usuário: {e}", exc_info=True)
            return jsonify(**error('Não foi possível salvar o usuário no banco de dados.'), success=False), 500
        except Exception as e:
            logger.exception(f"Erro inesperado ao atualizar usuário: {e}", exc_info=True)
            return jsonify(**error('Não foi possível concluir a alteração do usuário. Tente novamente.'), success=False), 500
        
    csrf_token_val = gerar_csrf_token()
    return render_template('admin/editar_usuario.html',
                           user_data=user_data,
                           current_user_id=current_user_id,
                           current_user_role=current_user_role,
                           csrf_token=csrf_token_val)




@admin_users_bp.route('/gerenciar/<int:user_id>', methods=['GET', 'POST'])
@login_status_required
@permission_required('admin_usuarios_editar')
def gerenciar_usuario(user_id):
    """
    Interface administrativa para gerenciar usuários.
    Apenas ações administrativas (role, status, reset senha).
    Dados pessoais são protegidos.
    """
    current_user_id = session.get('usuario_id')
    current_user_role = session.get('usuario_role')
    
    # Buscar dados do usuário (com dados minimizados)
    try:
        user_data = executar_query(
            "SELECT id, usuario, nome, email, ativo, role, created_at, last_login_at FROM usuarios WHERE id = ?",
            [user_id],
            fetch_one=True
        )
        
        if not user_data:
            flash('Usuário não encontrado.', 'error')
            return redirect(url_for('admin_users.users_list'))
        
        # Mascarar email
        user_data['email_mascarado'] = mascarar_email(user_data['email'])
        
        # Contar processos vinculados
        processos_count = executar_query(
            "SELECT COUNT(*) as total FROM processos WHERE responsavel_id = ?",
            [user_id],
            fetch_one=True
        )
        user_data['processos_count'] = processos_count['total'] if processos_count else 0
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados do usuário {user_id}: {e}", exc_info=True)
        flash('Erro ao carregar dados do usuário.', 'danger')
        return redirect(url_for('admin_users.users_list'))
    
    if request.method == 'POST':
        if not verificar_csrf_token(request.form.get('csrf_token')):
            return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403
        
        role = proteger_input(request.form.get('role'))
        ativo = 'ativo' in request.form
        senha_admin = request.form.get('senha_admin', '').strip()
        justificativa = request.form.get('justificativa', '').strip()
        
        try:
            role = validate_user_role(role)
            # Validações
            if not senha_admin:
                raise ValueError('Digite sua senha para confirmar as alterações.')
            
            if not justificativa or len(justificativa) < 20:
                raise ValueError('A justificativa deve ter pelo menos 20 caracteres.')
            
            # Verificar senha do admin
            admin_data = get_user_by_username(session.get('usuario_username'))
            if not admin_data or not check_password_hash(admin_data['senha'], senha_admin):
                gravar_tentativa_nao_autorizada(
                    usuario_id=current_user_id,
                    tipo_tentativa='senha_incorreta_gerenciar',
                    ip=get_client_ip(),
                    detalhes=f"Tentativa de gerenciar usuário {user_id} com senha incorreta",
                    alvo_user_id=user_id
                )
                raise ValueError('Senha do administrador incorreta.')
            
            # Detectar mudanças
            mudancas = []
            
            if user_data['role'] != role:
                mudancas.append(('role', user_data['role'], role))
            
            if user_data['ativo'] != (1 if ativo else 0):
                mudancas.append(('ativo', 'Ativo' if user_data['ativo'] else 'Inativo', 'Ativo' if ativo else 'Inativo'))
            
            if not mudancas:
                return jsonify(success=False, message='Nenhuma alteração detectada.', type='warning'), 400

            ensure_admin_safety(
                user_data,
                target_role=role,
                target_active=bool(ativo),
                current_user_id=current_user_id,
            )
            
            # Aplicar mudanças e registrar a auditoria na mesma transação.
            with get_sqlite_connection() as conn:
                cursor = conn.cursor()
                
                sql_updates = []
                if user_data['role'] != role:
                    sql_updates.append("role = ?")
                
                if user_data['ativo'] != (1 if ativo else 0):
                    sql_updates.append("ativo = ?")

                if user_data['role'] != role or user_data['ativo'] != (1 if ativo else 0):
                    sql_updates.append("session_epoch = COALESCE(session_epoch, 0) + 1")
                    sql_updates.append("session_invalidate_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
                
                if sql_updates:
                    params = []
                    if user_data['role'] != role:
                        params.append(role)
                    if user_data['ativo'] != (1 if ativo else 0):
                        params.append(1 if ativo else 0)
                    params.append(user_id)
                    
                    sql = f"UPDATE usuarios SET {', '.join(sql_updates)} WHERE id = ?"
                    cursor.execute(sql, params)

                # Auditoria obrigatória para cada mudança, dentro da mesma transação.
                for campo, valor_ant, valor_novo in mudancas:
                    gravar_auditoria_admin(
                        admin_id=current_user_id,
                        acao=f'alteracao_{campo}',
                        justificativa=justificativa,
                        ip=get_client_ip(),
                        usuario_afetado_id=user_id,
                        campo_alterado=campo,
                        valor_anterior=str(valor_ant),
                        valor_novo=str(valor_novo),
                        user_agent=request.headers.get('User-Agent'),
                        connection=conn,
                    )
            
            # Criar notificação
            if user_data['role'] != role:
                criar_notificacao_usuario(
                    usuario_id=user_id,
                    tipo='role_alterada',
                    titulo='Sua função foi alterada',
                    mensagem=f'Sua função foi alterada de {user_data["role"]} para {role} pelo administrador.'
                )
            
            if user_data['ativo'] and not ativo:
                criar_notificacao_usuario(
                    usuario_id=user_id,
                    tipo='conta_inativada',
                    titulo='Sua conta foi inativada',
                    mensagem='Sua conta foi inativada pelo administrador. Entre em contato para mais informações.'
                )
            
            flash('Alterações salvas com sucesso!', 'success')
            return jsonify(success=True, message='Alterações salvas com sucesso!', redirect=url_for('admin_users.users_list'))
            
        except ValueError as e:
            return jsonify(success=False, message=str(e), type='danger'), 400
        except Exception as e:
            logger.exception(f"Erro ao gerenciar usuário {user_id}: {e}")
            return jsonify(success=False, message='Não foi possível concluir a alteração. Consulte os logs.', type='danger'), 500
    
    csrf_token_val = gerar_csrf_token()
    return render_template('admin/gerenciar_usuario.html',
                         user_data=user_data,
                         current_user_id=current_user_id,
                         current_user_role=current_user_role,
                         csrf_token=csrf_token_val)