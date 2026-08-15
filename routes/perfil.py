# registrofacil/routes/perfil.py

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import re

from models import (
    executar_query, gravar_log, get_user_by_username,
    get_sqlite_connection, gravar_auditoria_admin, 
    gravar_tentativa_nao_autorizada, criar_notificacao_usuario,
    mascarar_email
)
from routes.auth import login_status_required, get_client_ip, proteger_input, verificar_csrf_token, gerar_csrf_token
from utils.logger import logger
from utils.notification_contract import success, error, warning
from config import Config
from utils.file_uploads import get_image_url_for_display, handle_image_upload, remove_image_file, PROFILE_UPLOAD_FOLDER

perfil_bp = Blueprint('perfil', __name__, url_prefix='/perfil')


@perfil_bp.route('/', methods=['GET', 'POST'])
@perfil_bp.route('/<int:user_id>', methods=['GET', 'POST'])
@login_status_required
def index(user_id=None):
    """
    Rota unificada e inteligente para gerenciamento de perfil.
    
    Contextos automáticos:
    - /perfil ou /perfil/{próprio_id} → Auto-edição (qualquer usuário)
    - /perfil/{outro_id} + admin → Gerenciamento admin
    - /perfil/{outro_id} + não admin → Bloqueado
    """
    current_user_id = session.get('usuario_id')
    current_user_username = session.get('usuario_username')
    current_user_role = session.get('usuario_role')
    
    # Determinar ID do usuário alvo
    target_user_id = user_id if user_id else current_user_id
    
    # Determinar contexto
    is_own_profile = (target_user_id == current_user_id)
    is_admin = (current_user_role == 'admin')
    
    # Contexto: próprio perfil (auto-edição)
    if is_own_profile:
        contexto = 'proprio_perfil'
    # Contexto: admin gerenciando outro usuário
    elif is_admin and not is_own_profile:
        contexto = 'gerenciamento_admin'
    # Contexto: usuário comum tentando acessar outro perfil (BLOQUEADO)
    else:
        gravar_tentativa_nao_autorizada(
            usuario_id=current_user_id,
            tipo_tentativa='acesso_perfil_outro_usuario',
            ip=get_client_ip(),
            detalhes=f"Tentativa de acessar perfil do usuário {target_user_id}",
            alvo_user_id=target_user_id,
            user_agent=request.headers.get('User-Agent'),
            bloqueado=True
        )
        flash('Acesso negado. Você só pode visualizar e editar seu próprio perfil.', 'danger')
        logger.warning(f"Tentativa não autorizada: User {current_user_id} tentou acessar perfil do user {target_user_id}")
        return redirect(url_for('perfil.index'))
    
    # Buscar dados do usuário alvo
    try:
        query = """
            SELECT id, usuario, nome, email, ativo, role, foto, created_at, last_login_at
            FROM usuarios 
            WHERE id = ?
        """
        user_data = executar_query(query, [target_user_id], fetch_one=True)
        
        if not user_data:
            flash("Erro: Usuário não encontrado.", 'danger')
            return redirect(url_for('auth.dashboard'))
        
        # Se contexto admin, mascarar email
        if contexto == 'gerenciamento_admin':
            user_data['email_original'] = user_data['email']
            user_data['email_mascarado'] = mascarar_email(user_data['email'])
            
            # Contar processos vinculados
            processos_count = executar_query(
                "SELECT COUNT(*) as total FROM processos WHERE responsavel_id = ?",
                [target_user_id],
                fetch_one=True
            )
            user_data['processos_count'] = processos_count['total'] if processos_count else 0
        
        display_foto_url = get_image_url_for_display(user_data['foto'], user_data['email'], is_company_logo=False)
        
    except Exception as e:
        logger.error(f"Erro ao carregar dados do usuário {target_user_id}: {e}", exc_info=True)
        flash("Erro ao carregar dados do usuário.", 'danger')
        return redirect(url_for('auth.dashboard'))
    
    # ===== PROCESSAMENTO POST =====
    if request.method == 'POST':
        if not verificar_csrf_token(request.form.get('csrf_token')):
            logger.error(f"Token CSRF inválido. User: {current_user_id}, Alvo: {target_user_id}. IP: {get_client_ip()}")
            return jsonify(success=False, message="Sua sessão de segurança expirou. Recarregue a página e tente novamente.", title='Sessão expirada', type='danger'), 403
        
        # ===== CONTEXTO: PRÓPRIO PERFIL (AUTO-EDIÇÃO) =====
        if contexto == 'proprio_perfil':
            nome = proteger_input(request.form.get('nome'))
            email = proteger_input(request.form.get('email'))
            senha_atual = request.form.get('senha_atual')
            nova_senha = request.form.get('nova_senha')
            confirmar_senha = request.form.get('confirmar_senha')
            
            try:
                # Validações
                if not nome: raise ValueError('O nome completo é obrigatório.')
                if not email: raise ValueError('O e-mail é obrigatório.')
                if not re.fullmatch(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                    raise ValueError('O formato do e-mail é inválido.')
                
                # Verificar email duplicado
                check_email = executar_query(
                    "SELECT id FROM usuarios WHERE email = ? AND id != ? AND ativo = 1 LIMIT 1",
                    [email, current_user_id],
                    fetch_one=True
                )
                if check_email:
                    raise ValueError(f"O e-mail '{email}' já está em uso.")
                
                # Validar alteração de senha
                if nova_senha or senha_atual:
                    if not senha_atual:
                        raise ValueError('Para alterar a senha, informe sua senha atual.')
                    
                    user_db_data = get_user_by_username(current_user_username)
                    if not user_db_data or not check_password_hash(user_db_data['senha'], senha_atual):
                        raise ValueError('Senha atual incorreta.')
                    
                    if not nova_senha:
                        raise ValueError('Informe a nova senha.')
                    if nova_senha != confirmar_senha:
                        raise ValueError('As senhas não coincidem.')
                    if len(nova_senha) < 8:
                        raise ValueError('A nova senha deve ter pelo menos 8 caracteres.')
                
                # Processar upload de imagem
                imagem_final = user_data.get('foto')
                
                if 'imagem_perfil' in request.files:
                    uploaded_file = request.files['imagem_perfil']
                    try:
                        new_filename = handle_image_upload(
                            uploaded_file=uploaded_file,
                            current_filename=imagem_final,
                            target_folder=PROFILE_UPLOAD_FOLDER,
                            allowed_extensions=['jpg', 'jpeg', 'png'],
                            max_size_mb=2,
                            prefix=f'usuario_{current_user_id}'
                        )
                        if new_filename:
                            imagem_final = new_filename
                    except ValueError as e:
                        return jsonify(success=False, message=str(e), type='danger', field_error='imagem_perfil'), 400
                
                elif request.form.get('remove_current_image') == '1':
                    if remove_image_file(imagem_final, PROFILE_UPLOAD_FOLDER):
                        imagem_final = None
                
                # Atualizar banco
                with get_sqlite_connection() as conn:
                    cursor = conn.cursor()
                    
                    sql = """
                        UPDATE usuarios 
                        SET nome = ?, email = ?, foto = ?, 
                            updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
                    """
                    params = [nome, email, imagem_final]
                    
                    if nova_senha and senha_atual:
                        sql += ", senha = ?"
                        params.append(generate_password_hash(nova_senha))
                    
                    sql += " WHERE id = ?"
                    params.append(current_user_id)
                    
                    cursor.execute(sql, params)
                
                gravar_log('Editou próprio perfil', None, current_user_id, get_client_ip(), 
                          f"Usuário {user_data['usuario']} editou seu próprio perfil.")
                
                # Atualizar sessão
                session['usuario_nome'] = nome
                session['usuario_email'] = email
                updated_photo_url = get_image_url_for_display(imagem_final, email, is_company_logo=False)
                session['usuario_foto_url'] = updated_photo_url
                
                mensagem = 'Perfil atualizado com sucesso!'
                if nova_senha:
                    mensagem = 'Perfil e senha atualizados com sucesso!'
                    # Limpa flag de troca obrigatória e atualiza o BD
                    session.pop('force_password_change', None)
                    executar_query(
                        "UPDATE usuarios SET must_change_password = 0 WHERE id = ?",
                        [target_user_id]
                    )
                
                return jsonify(
                    success=True,
                    title='Sucesso',
                    type='success',
                    message=mensagem,
                    redirect=url_for('perfil.index'),
                    updated_user_data={
                        'nome': nome,
                        'email': email,
                        'usuario_foto_url': updated_photo_url
                    }
                )
            
            except ValueError as e:
                return jsonify(success=False, message=str(e), title='Verifique os dados', type='warning'), 400
            except Exception as e:
                logger.exception(f"Erro ao atualizar perfil: {e}")
                return jsonify(success=False, message='Não foi possível atualizar o perfil. Tente novamente ou consulte os logs.', title='Erro ao atualizar perfil', type='danger'), 500
        
        # ===== CONTEXTO: GERENCIAMENTO ADMIN =====
        elif contexto == 'gerenciamento_admin':
            role = proteger_input(request.form.get('role'))
            ativo = 'ativo' in request.form
            senha_admin = request.form.get('senha_admin', '').strip()
            justificativa = request.form.get('justificativa', '').strip()
            
            try:
                # Validações
                if not senha_admin:
                    raise ValueError('Digite sua senha para confirmar as alterações.')
                
                if not justificativa or len(justificativa) < 20:
                    raise ValueError('A justificativa deve ter pelo menos 20 caracteres.')
                
                # Verificar senha do admin
                admin_data = get_user_by_username(current_user_username)
                if not admin_data or not check_password_hash(admin_data['senha'], senha_admin):
                    gravar_tentativa_nao_autorizada(
                        usuario_id=current_user_id,
                        tipo_tentativa='senha_incorreta_gerenciar',
                        ip=get_client_ip(),
                        detalhes=f"Senha incorreta ao gerenciar usuário {target_user_id}",
                        alvo_user_id=target_user_id
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
                
                # Aplicar mudanças
                with get_sqlite_connection() as conn:
                    cursor = conn.cursor()
                    
                    sql_updates = []
                    params = []
                    
                    if user_data['role'] != role:
                        sql_updates.append("role = ?")
                        params.append(role)
                    
                    if user_data['ativo'] != (1 if ativo else 0):
                        sql_updates.append("ativo = ?")
                        params.append(1 if ativo else 0)
                        if not ativo:
                            sql_updates.append("session_invalidate_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
                    
                    if sql_updates:
                        params.append(target_user_id)
                        sql = f"UPDATE usuarios SET {', '.join(sql_updates)} WHERE id = ?"
                        cursor.execute(sql, params)
                
                # Gravar auditoria
                for campo, valor_ant, valor_novo in mudancas:
                    gravar_auditoria_admin(
                        admin_id=current_user_id,
                        acao=f'alteracao_{campo}',
                        justificativa=justificativa,
                        ip=get_client_ip(),
                        usuario_afetado_id=target_user_id,
                        campo_alterado=campo,
                        valor_anterior=str(valor_ant),
                        valor_novo=str(valor_novo),
                        user_agent=request.headers.get('User-Agent')
                    )
                
                # Notificações
                if user_data['role'] != role:
                    criar_notificacao_usuario(
                        usuario_id=target_user_id,
                        tipo='role_alterada',
                        titulo='Sua função foi alterada',
                        mensagem=f'Sua função foi alterada de {user_data["role"]} para {role}.'
                    )
                
                if user_data['ativo'] and not ativo:
                    criar_notificacao_usuario(
                        usuario_id=target_user_id,
                        tipo='conta_inativada',
                        titulo='Sua conta foi inativada',
                        mensagem='Sua conta foi inativada pelo administrador.'
                    )
                
                return jsonify(success=True, message='Alterações salvas com sucesso!', redirect=url_for('admin_users.users_list'))
                
            except ValueError as e:
                return jsonify(success=False, message=str(e), type='danger'), 400
            except Exception as e:
                logger.exception(f"Erro ao gerenciar usuário: {e}")
                return jsonify(success=False, message=f'Erro inesperado: {str(e)}', type='danger'), 500
    
    # ===== RENDERIZAR TEMPLATE =====
    csrf_token_val = gerar_csrf_token()
    
    # Template apropriado por contexto
    if contexto == 'proprio_perfil':
        return render_template('perfil.html',
                             user_data=user_data,
                             display_foto_url=display_foto_url,
                             current_user_id=current_user_id,
                             current_user_role=current_user_role,
                             contexto=contexto,
                             csrf_token=csrf_token_val)
    else:  # gerenciamento_admin
        return render_template('admin/perfil_admin.html',
                             user_data=user_data,
                             display_foto_url=display_foto_url,
                             current_user_id=current_user_id,
                             current_user_role=current_user_role,
                             contexto=contexto,
                             csrf_token=csrf_token_val)


@perfil_bp.route('/tema', methods=['GET'])
def obter_tema():
    """API: Retorna o tema atual do usuário."""
    usuario_id = session.get('usuario_id')
    if not usuario_id:
        return jsonify({'erro': 'Não autenticado'}), 401
    
    from models import obter_tema_usuario
    tema = obter_tema_usuario(usuario_id)
    
    return jsonify({'tema_cor': tema})


@perfil_bp.route('/salvar-tema', methods=['POST'])
@login_status_required
def salvar_tema():
    """API para salvar o tema de cor do usuário logado com validação CSRF e auditoria."""
    try:
        # Validação CSRF corporativa para requisições AJAX/JSON
        csrf_token_header = request.headers.get('X-CSRFToken')
        if not verificar_csrf_token(csrf_token_header):
            logger.warning(f"Tentativa de alteração de tema com CSRF inválido. IP: {get_client_ip()}")
            return jsonify({**error('Sua sessão de segurança expirou. Recarregue a página e tente novamente.'), 'success': False}), 403

        data = request.get_json() or {}
        tema = data.get('tema') or data.get('tema_cor')
        
        if not tema:
            return jsonify({**warning('Selecione uma paleta antes de salvar.'), 'success': False}), 400
            
        # Validação de temas permitidos contra injeção de parâmetros
        temas_validos = [
            'grafite-vinho', 'dourado', 'azul-marinho', 'vinho', 'verde-esmeralda',
            'azul-petroleo', 'roxo-real', 'azul-royal', 'verde-oliva',
            'terracota', 'azul-cobalto', 'magenta',             'cinza-grafite',
            'teal', 'indigo', 'ambar', 'verde-floresta', 'azul-aco',
            'coral', 'lavanda', 'preto-classico', 'vermelho-rubi',
            'rosa-antigo', 'laranja-queimado', 'verde-jade',
            'azul-meia-noite', 'violeta-ametista', 'marrom-cafe',
            'cinza-carvao', 'verde-salvia', 'azul-oceano'

        ]
        if tema not in temas_validos:
            return jsonify({**warning('A paleta selecionada não está disponível. Escolha uma das opções exibidas.'), 'success': False}), 400

        usuario_id = session.get('usuario_id')
        if not usuario_id:
            return jsonify({**error('Sua sessão expirou. Entre novamente para salvar a paleta.'), 'success': False}), 401
            
        from models import salvar_tema_usuario
        sucesso = salvar_tema_usuario(usuario_id, tema)
        
        if sucesso is not False:
            session['usuario_tema_cor'] = tema
            session['usuario_tema_explicit'] = True
            
            # Auditoria corporativa formal
            gravar_log(
                acao='Alteração de Tema Visual',
                processo_id=None,
                usuario_id=usuario_id,
                ip=get_client_ip(),
                descricao=f"Usuário alterou o tema visual corporativo para '{tema}'."
            )
            
            return jsonify({**success('Paleta salva com sucesso.'), 'success': True, 'sucesso': True})
        else:
            return jsonify({**error('Não foi possível salvar a paleta no banco de dados.'), 'success': False}), 500
            
    except Exception as e:
        logger.error(f"Erro ao salvar tema do usuário: {e}", exc_info=True)
        return jsonify({**error('Não foi possível salvar a paleta. Consulte os logs para obter detalhes.'), 'success': False}), 500
