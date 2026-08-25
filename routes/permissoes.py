# registrofacil/routes/permissoes.py

from flask import Blueprint, request, jsonify, session, render_template, flash, redirect, url_for
from models import executar_query, gravar_log
from routes.auth import login_status_required, admin_required, verificar_csrf_token, get_client_ip, gerar_csrf_token
from utils.logger import auth_logger as logger
import functools

permissoes_bp = Blueprint('permissoes', __name__, url_prefix='/permissoes')


def get_user_permissions(user_id):
    """Obtém todas as permissões de um usuário"""
    query = """
        SELECT m.nome, m.descricao, m.categoria, p.concedido
        FROM modulos_sistema m
        LEFT JOIN permissoes_usuarios p ON m.id = p.modulo_id AND p.usuario_id = ?
        WHERE m.ativo = 1
        ORDER BY m.categoria, m.ordem
    """
    return executar_query(query, [user_id])


def has_permission(user_id, permission_name):
    """Verifica se um usuário tem uma permissão específica"""
    # Admins sempre têm todas as permissões
    user_query = "SELECT role FROM usuarios WHERE id = ?"
    user = executar_query(user_query, [user_id], fetch_one=True)
    
    if user and user['role'] in ['admin', 'suporte']:
        return True
    
    # Verifica permissão específica
    query = """
        SELECT p.concedido
        FROM permissoes_usuarios p
        JOIN modulos_sistema m ON p.modulo_id = m.id
        WHERE p.usuario_id = ? AND m.nome = ? AND p.concedido = 1
    """
    result = executar_query(query, [user_id, permission_name], fetch_one=True)
    return result is not None


def permission_required(permission_name):
    """Decorator para verificar se o usuário tem permissão para acessar uma rota"""
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('usuario_id')
            session_role = session.get('usuario_role')
            persisted_user = executar_query(
                "SELECT role, ativo FROM usuarios WHERE id = ?",
                [user_id],
                fetch_one=True
            ) if user_id else None

            # A role persistida e a role da sessão precisam coincidir. Isso
            # bloqueia sessões obsoletas mesmo quando a epoch ainda não foi
            # carregada por uma instalação legada.
            role_consistente = (
                persisted_user
                and persisted_user.get('ativo') == 1
                and persisted_user.get('role') == session_role
            )
            if not role_consistente or not has_permission(user_id, permission_name):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify(
                        success=False, 
                        message="Você não tem permissão para realizar esta ação.", 
                        type='danger'
                    ), 403
                else:
                    flash("Você não tem permissão para acessar esta página.", 'error')
                    logger.warning(
                        f"Acesso negado para Usuário ID: {user_id}, "
                        f"Permissão: {permission_name}, IP: {get_client_ip()}"
                    )
                    return redirect(url_for('auth.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@permissoes_bp.route('/usuario/<int:usuario_id>', methods=['GET'])
@login_status_required
@admin_required
def visualizar_permissoes(usuario_id):
    """Visualiza as permissões de um usuário específico"""
    try:
        # Buscar informações do usuário
        user_query = "SELECT id, usuario, nome, email, role FROM usuarios WHERE id = ?"
        usuario = executar_query(user_query, [usuario_id], fetch_one=True)
        
        if not usuario:
            flash("Usuário não encontrado.", 'error')
            return redirect(url_for('admin_users.users_list'))
        
        # Buscar permissões do usuário
        permissoes = get_user_permissions(usuario_id)
        
        # Organizar permissões por categoria
        permissoes_por_categoria = {}
        for perm in permissoes:
            categoria = perm['categoria']
            if categoria not in permissoes_por_categoria:
                permissoes_por_categoria[categoria] = []
            permissoes_por_categoria[categoria].append(perm)
        
        csrf_token = gerar_csrf_token()
        
        return render_template(
            'permissoes_usuario.html',
            usuario=usuario,
            permissoes_por_categoria=permissoes_por_categoria,
            csrf_token=csrf_token
        )
        
    except Exception as e:
        logger.error(f"Erro ao visualizar permissões do usuário {usuario_id}: {e}", exc_info=True)
        flash("Erro ao carregar permissões do usuário.", 'error')
        return redirect(url_for('admin_users.users_list'))


@permissoes_bp.route('/atualizar/<int:usuario_id>', methods=['POST'])
@login_status_required
@admin_required
def atualizar_permissoes(usuario_id):
    """Atualiza as permissões de um usuário"""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        return jsonify(
            success=False,
            message="Token de segurança inválido.",
            type='danger'
        ), 403
    
    try:
        # Verificar se o usuário existe
        user_query = "SELECT id, usuario, nome, role FROM usuarios WHERE id = ?"
        usuario = executar_query(user_query, [usuario_id], fetch_one=True)
        
        if not usuario:
            return jsonify(
                success=False,
                message="Usuário não encontrado.",
                type='error'
            ), 404
        
        # Não permitir alterar permissões de admin
        if usuario['role'] in ['admin', 'suporte']:
            return jsonify(
                success=False,
                message="Não é possível alterar permissões de administradores.",
                type='warning'
            ), 400
        
        # Obter permissões selecionadas
        permissoes_selecionadas = request.form.getlist('permissoes[]')
        
        # Buscar todos os módulos
        modulos_query = "SELECT id, nome FROM modulos_sistema WHERE ativo = 1"
        modulos = executar_query(modulos_query)
        
        admin_id = session.get('usuario_id')
        alteracoes = 0
        
        # Atualizar permissões
        for modulo in modulos:
            modulo_id = modulo['id']
            modulo_nome = modulo['nome']
            tem_permissao = modulo_nome in permissoes_selecionadas
            
            # Verificar se já existe registro
            check_query = """
                SELECT id FROM permissoes_usuarios 
                WHERE usuario_id = ? AND modulo_id = ?
            """
            existe = executar_query(check_query, [usuario_id, modulo_id], fetch_one=True)
            
            if existe:
                # Atualizar registro existente
                update_query = """
                    UPDATE permissoes_usuarios 
                    SET concedido = ?, concedido_por = ?, 
                        concedido_em = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')
                    WHERE usuario_id = ? AND modulo_id = ?
                """
                executar_query(update_query, [1 if tem_permissao else 0, admin_id, usuario_id, modulo_id])
                alteracoes += 1
            elif tem_permissao:
                # Inserir novo registro apenas se a permissão foi concedida
                insert_query = """
                    INSERT INTO permissoes_usuarios (usuario_id, modulo_id, concedido, concedido_por)
                    VALUES (?, ?, 1, ?)
                """
                executar_query(insert_query, [usuario_id, modulo_id, admin_id])
                alteracoes += 1
        
        # Gravar log
        gravar_log(
            "Atualização de Permissões",
            None,
            admin_id,
            get_client_ip(),
            f"Permissões atualizadas para usuário {usuario['nome']} (ID: {usuario_id}). "
            f"{len(permissoes_selecionadas)} permissões concedidas."
        )
        
        return jsonify(
            success=True,
            message=f"Permissões atualizadas com sucesso! {len(permissoes_selecionadas)} permissões concedidas.",
            type='success'
        ), 200
        
    except Exception as e:
        logger.error(f"Erro ao atualizar permissões do usuário {usuario_id}: {e}", exc_info=True)
        return jsonify(
            success=False,
            message="Não foi possível atualizar as permissões. Consulte os logs.",
            type='error'
        ), 500


@permissoes_bp.route('/listar_modulos', methods=['GET'])
@login_status_required
@admin_required
def listar_modulos():
    """Lista todos os módulos do sistema"""
    try:
        query = """
            SELECT id, nome, descricao, categoria, ativo, ordem
            FROM modulos_sistema
            WHERE ativo = 1
            ORDER BY categoria, ordem
        """
        modulos = executar_query(query)
        
        # Organizar por categoria
        modulos_por_categoria = {}
        for modulo in modulos:
            categoria = modulo['categoria']
            if categoria not in modulos_por_categoria:
                modulos_por_categoria[categoria] = []
            modulos_por_categoria[categoria].append(modulo)
        
        return jsonify(
            success=True,
            modulos=modulos_por_categoria
        ), 200
        
    except Exception as e:
        logger.error(f"Erro ao listar módulos: {e}", exc_info=True)
        return jsonify(
            success=False,
            message="Erro ao listar módulos do sistema.",
            type='error'
        ), 500


# ─────────────────────────────────────────────────────────────────────────────
# GESTÃO DE PERFIS DE PERMISSÃO
# ─────────────────────────────────────────────────────────────────────────────

@permissoes_bp.route('/perfis', methods=['GET'])
@login_status_required
@permission_required('admin_perfis')
def listar_perfis():
    """Lista todos os perfis de permissão"""
    try:
        perfis = executar_query("""
            SELECT p.id, p.nome, p.descricao, p.created_at,
                   u.nome AS criado_por_nome,
                   COUNT(DISTINCT pm.modulo_id) AS total_permissoes,
                   COUNT(DISTINCT up.usuario_id) AS total_usuarios
            FROM perfis_permissao p
            LEFT JOIN usuarios u ON p.criado_por = u.id
            LEFT JOIN perfis_permissao_modulos pm ON p.id = pm.perfil_id
            LEFT JOIN usuario_perfil up ON p.id = up.perfil_id
            GROUP BY p.id
            ORDER BY p.nome
        """)
        csrf_token = gerar_csrf_token()
        return render_template('perfis_permissao.html', perfis=perfis, csrf_token=csrf_token)
    except Exception as e:
        logger.error(f"Erro ao listar perfis: {e}", exc_info=True)
        flash("Erro ao carregar perfis.", 'error')
        return redirect(url_for('admin_users.users_list'))


@permissoes_bp.route('/perfis/criar', methods=['POST'])
@login_status_required
@permission_required('admin_perfis')
def criar_perfil():
    """Cria um novo perfil de permissão"""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403
    try:
        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        if not nome:
            return jsonify(success=False, message="Nome do perfil é obrigatório.", type='warning'), 400

        admin_id = session.get('usuario_id')
        executar_query(
            "INSERT INTO perfis_permissao (nome, descricao, criado_por) VALUES (?, ?, ?)",
            [nome, descricao, admin_id]
        )
        perfil = executar_query("SELECT id FROM perfis_permissao WHERE nome = ?", [nome], fetch_one=True)
        gravar_log("Criou Perfil de Permissão", None, admin_id, get_client_ip(), f"Perfil: {nome}")
        return jsonify(success=True, message=f"Perfil '{nome}' criado com sucesso.", type='success',
                       perfil_id=perfil['id'] if perfil else None), 201
    except Exception as e:
        logger.error(f"Erro ao criar perfil: {e}", exc_info=True)
        return jsonify(success=False, message="Erro ao criar perfil. Nome já pode existir.", type='error'), 500


@permissoes_bp.route('/perfis/<int:perfil_id>', methods=['GET'])
@login_status_required
@permission_required('admin_perfis')
def visualizar_perfil(perfil_id):
    """Visualiza um perfil e suas permissões"""
    try:
        perfil = executar_query("SELECT * FROM perfis_permissao WHERE id = ?", [perfil_id], fetch_one=True)
        if not perfil:
            flash("Perfil não encontrado.", 'error')
            return redirect(url_for('permissoes.listar_perfis'))

        modulos = executar_query("""
            SELECT m.id, m.nome, m.descricao, m.categoria, m.ordem,
                   CASE WHEN pm.perfil_id IS NOT NULL THEN 1 ELSE 0 END AS concedido
            FROM modulos_sistema m
            LEFT JOIN perfis_permissao_modulos pm ON m.id = pm.modulo_id AND pm.perfil_id = ?
            WHERE m.ativo = 1
            ORDER BY m.categoria, m.ordem
        """, [perfil_id])

        modulos_por_categoria = {}
        for m in modulos:
            cat = m['categoria']
            if cat not in modulos_por_categoria:
                modulos_por_categoria[cat] = []
            modulos_por_categoria[cat].append(m)

        usuarios_vinculados = executar_query("""
            SELECT u.id, u.nome, u.email, u.usuario, up.atribuido_em
            FROM usuario_perfil up
            JOIN usuarios u ON up.usuario_id = u.id
            WHERE up.perfil_id = ?
            ORDER BY u.nome
        """, [perfil_id])

        csrf_token = gerar_csrf_token()
        return render_template('perfil_permissao_detalhe.html',
                               perfil=perfil,
                               modulos_por_categoria=modulos_por_categoria,
                               usuarios_vinculados=usuarios_vinculados,
                               csrf_token=csrf_token)
    except Exception as e:
        logger.error(f"Erro ao visualizar perfil {perfil_id}: {e}", exc_info=True)
        flash("Erro ao carregar perfil.", 'error')
        return redirect(url_for('permissoes.listar_perfis'))


@permissoes_bp.route('/perfis/<int:perfil_id>/atualizar', methods=['POST'])
@login_status_required
@permission_required('admin_perfis')
def atualizar_perfil(perfil_id):
    """Atualiza permissões de um perfil"""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403
    try:
        perfil = executar_query("SELECT id, nome FROM perfis_permissao WHERE id = ?", [perfil_id], fetch_one=True)
        if not perfil:
            return jsonify(success=False, message="Perfil não encontrado.", type='error'), 404

        nome = request.form.get('nome', '').strip()
        descricao = request.form.get('descricao', '').strip()
        permissoes_selecionadas = request.form.getlist('permissoes[]')

        if nome:
            executar_query(
                "UPDATE perfis_permissao SET nome=?, descricao=?, updated_at=strftime('%Y-%m-%d %H:%M:%S','now','localtime') WHERE id=?",
                [nome, descricao, perfil_id]
            )

        # Reconstruir permissões do perfil
        executar_query("DELETE FROM perfis_permissao_modulos WHERE perfil_id = ?", [perfil_id])
        for modulo_nome in permissoes_selecionadas:
            executar_query("""
                INSERT OR IGNORE INTO perfis_permissao_modulos (perfil_id, modulo_id)
                SELECT ?, id FROM modulos_sistema WHERE nome = ? AND ativo = 1
            """, [perfil_id, modulo_nome])

        # Propagar permissões a todos os usuários vinculados a este perfil
        usuarios_vinculados = executar_query(
            "SELECT usuario_id FROM usuario_perfil WHERE perfil_id = ?", [perfil_id]
        )
        admin_id = session.get('usuario_id')
        for uv in usuarios_vinculados:
            _aplicar_permissoes_perfil(uv['usuario_id'], perfil_id, admin_id)

        gravar_log("Atualizou Perfil de Permissão", None, admin_id, get_client_ip(),
                   f"Perfil ID {perfil_id}: {len(permissoes_selecionadas)} permissões")
        return jsonify(success=True, message="Perfil atualizado com sucesso!", type='success'), 200
    except Exception as e:
        logger.error(f"Erro ao atualizar perfil {perfil_id}: {e}", exc_info=True)
        return jsonify(success=False, message="Não foi possível atualizar o perfil de permissão. Consulte os logs.", type='error'), 500


@permissoes_bp.route('/perfis/<int:perfil_id>/excluir', methods=['POST'])
@login_status_required
@permission_required('admin_perfis')
def excluir_perfil(perfil_id):
    """Exclui um perfil de permissão"""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403
    try:
        perfil = executar_query("SELECT id, nome FROM perfis_permissao WHERE id = ?", [perfil_id], fetch_one=True)
        if not perfil:
            return jsonify(success=False, message="Perfil não encontrado.", type='error'), 404

        usuarios_count = executar_query(
            "SELECT COUNT(*) AS c FROM usuario_perfil WHERE perfil_id = ?", [perfil_id], fetch_one=True
        )
        if usuarios_count and usuarios_count['c'] > 0:
            return jsonify(success=False,
                           message=f"Não é possível excluir: {usuarios_count['c']} usuário(s) estão vinculados a este perfil.",
                           type='warning'), 400

        executar_query("DELETE FROM perfis_permissao WHERE id = ?", [perfil_id])
        admin_id = session.get('usuario_id')
        gravar_log("Excluiu Perfil de Permissão", None, admin_id, get_client_ip(), f"Perfil: {perfil['nome']}")
        return jsonify(success=True, message=f"Perfil '{perfil['nome']}' excluído.", type='success'), 200
    except Exception as e:
        logger.error(f"Erro ao excluir perfil {perfil_id}: {e}", exc_info=True)
        return jsonify(success=False, message="Erro ao excluir perfil.", type='error'), 500


@permissoes_bp.route('/usuario/<int:usuario_id>/aplicar_perfil', methods=['POST'])
@login_status_required
@permission_required('admin_permissoes')
def aplicar_perfil_usuario(usuario_id):
    """Vincula um perfil a um usuário e aplica suas permissões"""
    if not verificar_csrf_token(request.form.get('csrf_token')):
        return jsonify(success=False, message="Token de segurança inválido.", type='danger'), 403
    try:
        usuario = executar_query("SELECT id, nome, role FROM usuarios WHERE id = ?", [usuario_id], fetch_one=True)
        if not usuario:
            return jsonify(success=False, message="Usuário não encontrado.", type='error'), 404
        if usuario['role'] in ['admin', 'suporte']:
            return jsonify(success=False, message="Não é possível vincular perfis a administradores.", type='warning'), 400

        perfil_id = request.form.get('perfil_id', type=int)
        admin_id = session.get('usuario_id')

        if perfil_id:
            perfil = executar_query("SELECT id, nome FROM perfis_permissao WHERE id = ?", [perfil_id], fetch_one=True)
            if not perfil:
                return jsonify(success=False, message="Perfil não encontrado.", type='error'), 404

            # Vincular usuário ao perfil
            executar_query("""
                INSERT INTO usuario_perfil (usuario_id, perfil_id, atribuido_por)
                VALUES (?, ?, ?)
                ON CONFLICT(usuario_id) DO UPDATE SET
                    perfil_id = excluded.perfil_id,
                    atribuido_por = excluded.atribuido_por,
                    atribuido_em = strftime('%Y-%m-%d %H:%M:%S','now','localtime')
            """, [usuario_id, perfil_id, admin_id])

            # Aplicar permissões do perfil
            _aplicar_permissoes_perfil(usuario_id, perfil_id, admin_id)

            gravar_log("Aplicou Perfil a Usuário", None, admin_id, get_client_ip(),
                       f"Usuário {usuario['nome']} → Perfil {perfil['nome']}")
            return jsonify(success=True, message=f"Perfil '{perfil['nome']}' aplicado ao usuário.", type='success'), 200
        else:
            # Remover vínculo de perfil e limpar permissões derivadas do perfil
            executar_query("DELETE FROM usuario_perfil WHERE usuario_id = ?", [usuario_id])
            executar_query("DELETE FROM permissoes_usuarios WHERE usuario_id = ?", [usuario_id])
            gravar_log("Removeu Perfil de Usuário", None, admin_id, get_client_ip(),
                       f"Usuário {usuario['nome']} desvinculado — permissões limpas",
                       contexto=f"Perfil e todas as permissões do usuário '{usuario['nome']}' foram removidos.")
            return jsonify(success=True, message="Perfil removido. Permissões do usuário foram limpas.", type="info"), 200
    except Exception as e:
        logger.error(f"Erro ao aplicar perfil ao usuário {usuario_id}: {e}", exc_info=True)
        return jsonify(success=False, message="Não foi possível aplicar o perfil de permissão. Consulte os logs.", type='error'), 500


def _aplicar_permissoes_perfil(usuario_id, perfil_id, admin_id):
    """
    Aplica as permissões de um perfil a um usuário.
    Remove todas as permissões anteriores e aplica apenas as do perfil.
    """
    # Limpar permissões atuais
    executar_query("DELETE FROM permissoes_usuarios WHERE usuario_id = ?", [usuario_id])

    # Buscar módulos do perfil
    modulos_perfil = executar_query("""
        SELECT m.id
        FROM perfis_permissao_modulos pm
        JOIN modulos_sistema m ON pm.modulo_id = m.id
        WHERE pm.perfil_id = ? AND m.ativo = 1
    """, [perfil_id])

    for m in modulos_perfil:
        executar_query("""
            INSERT OR IGNORE INTO permissoes_usuarios (usuario_id, modulo_id, concedido, concedido_por)
            VALUES (?, ?, 1, ?)
        """, [usuario_id, m['id'], admin_id])


@permissoes_bp.route('/usuario/<int:usuario_id>/perfil_atual', methods=['GET'])
@login_status_required
@permission_required('admin_permissoes')
def perfil_atual_usuario(usuario_id):
    """Retorna o perfil atual de um usuário"""
    try:
        perfil = executar_query("""
            SELECT p.id, p.nome, p.descricao, up.atribuido_em
            FROM usuario_perfil up
            JOIN perfis_permissao p ON up.perfil_id = p.id
            WHERE up.usuario_id = ?
        """, [usuario_id], fetch_one=True)

        todos_perfis = executar_query("SELECT id, nome, descricao FROM perfis_permissao ORDER BY nome")

        return jsonify(
            success=True,
            perfil_atual=dict(perfil) if perfil else None,
            todos_perfis=[dict(p) for p in todos_perfis]
        ), 200
    except Exception as e:
        logger.error(f"Erro ao buscar perfil do usuário {usuario_id}: {e}", exc_info=True)
        return jsonify(success=False, message="Erro ao buscar perfil.", type='error'), 500
