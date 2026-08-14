# registrofacil/utils/permissions_helper.py
"""
Funções auxiliares para o sistema de permissões
"""

from models import executar_query
from flask import session


def has_permission(user_id, permission_name):
    """
    Verifica se um usuário tem uma permissão específica
    
    Args:
        user_id: ID do usuário
        permission_name: Nome da permissão (ex: 'processos_editar')
    
    Returns:
        bool: True se tem permissão, False caso contrário
    """
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


def has_any_permission(user_id, permission_names):
    """
    Verifica se um usuário tem pelo menos uma das permissões especificadas
    
    Args:
        user_id: ID do usuário
        permission_names: Lista de nomes de permissões
    
    Returns:
        bool: True se tem pelo menos uma permissão, False caso contrário
    """
    for permission_name in permission_names:
        if has_permission(user_id, permission_name):
            return True
    return False


def has_all_permissions(user_id, permission_names):
    """
    Verifica se um usuário tem todas as permissões especificadas
    
    Args:
        user_id: ID do usuário
        permission_names: Lista de nomes de permissões
    
    Returns:
        bool: True se tem todas as permissões, False caso contrário
    """
    for permission_name in permission_names:
        if not has_permission(user_id, permission_name):
            return False
    return True


def get_user_permissions_list(user_id):
    """
    Obtém lista de todas as permissões de um usuário
    
    Args:
        user_id: ID do usuário
    
    Returns:
        list: Lista de nomes de permissões que o usuário possui
    """
    # Admins têm todas as permissões
    user_query = "SELECT role FROM usuarios WHERE id = ?"
    user = executar_query(user_query, [user_id], fetch_one=True)
    
    if user and user['role'] in ['admin', 'suporte']:
        # Retorna todas as permissões do sistema
        query = "SELECT nome FROM modulos_sistema WHERE ativo = 1"
        modulos = executar_query(query)
        return [m['nome'] for m in modulos]
    
    # Busca permissões específicas do usuário
    query = """
        SELECT m.nome
        FROM permissoes_usuarios p
        JOIN modulos_sistema m ON p.modulo_id = m.id
        WHERE p.usuario_id = ? AND p.concedido = 1 AND m.ativo = 1
    """
    permissoes = executar_query(query, [user_id])
    return [p['nome'] for p in permissoes]


def can_access_module(user_id, module_name):
    """
    Verifica se o usuário pode acessar um módulo específico
    Alias para has_permission para manter compatibilidade
    """
    return has_permission(user_id, module_name)


def get_current_user_permissions():
    """
    Obtém as permissões do usuário atual da sessão
    
    Returns:
        list: Lista de nomes de permissões do usuário atual
    """
    user_id = session.get('usuario_id')
    if not user_id:
        return []
    
    return get_user_permissions_list(user_id)


def check_permission_or_admin(user_id, permission_name):
    """
    Verifica se o usuário é admin OU tem a permissão específica
    Útil para casos onde admins sempre podem fazer algo
    
    Args:
        user_id: ID do usuário
        permission_name: Nome da permissão
    
    Returns:
        bool: True se é admin ou tem a permissão
    """
    return has_permission(user_id, permission_name)


# Mapeamento de rotas para permissões
# Use este mapeamento para verificar permissões em templates
ROUTE_PERMISSIONS = {
    # Processos
    'processos.todos': 'processos_visualizar',
    'processos.hoje': 'processos_visualizar',
    'processos.pendentes': 'processos_visualizar',
    'processos.vinculados': 'processos_visualizar',
    'processos.visualizar': 'processos_visualizar',
    'processos.novo': 'processos_criar',
    'processos.editar': 'processos_editar',
    'processos.excluir': 'processos_excluir',
    'processos.download_anexo': 'processos_anexos',
    'processos.exportar_excel': 'processos_exportar',
    'processos.imprimir_lista': 'processos_imprimir',
    'processos.gerar_pdf': 'processos_pdf',
    'processos.gerar_relatorio_customizado': 'processos_relatorio',

    # Titulares
    'titulares.index': 'titulares_visualizar',
    'titulares.visualizar': 'titulares_visualizar',
    'titulares.api_buscar': 'titulares_visualizar',
    'titulares.api_verificar_duplicidade': 'titulares_visualizar',
    'titulares.novo': 'titulares_criar',
    'titulares.editar': 'titulares_editar',
    'titulares.excluir': 'titulares_excluir',
    'titulares.exportar_excel': 'titulares_exportar',
    'titulares.imprimir': 'titulares_imprimir',

    # Atividades
    'atividades.historico': 'atividades_visualizar',

    # Métricas
    'dashboard.metricas': 'metricas_visualizar',
    'dashboard.api_metricas_usuario': 'metricas_visualizar',

    # Configurações
    'configuracoes.index': 'config_geral',

    # Backup
    'backup.index': 'backup_visualizar',
    'backup.manual_backup': 'backup_criar',
    'backup.download_backup': 'backup_download',
    'backup.delete_backup': 'backup_excluir',

    # Empresa
    'empresa.index': 'empresa_visualizar',

    # Administração de Usuários
    'admin_users.users_list': 'admin_usuarios_visualizar',
    'admin_users.edit_user': 'admin_usuarios_editar',
    'admin_users.gerenciar_usuario': 'admin_usuarios_editar',

    # Permissões e Perfis
    'permissoes.visualizar_permissoes': 'admin_permissoes',
    'permissoes.atualizar_permissoes': 'admin_permissoes',
    'permissoes.aplicar_perfil_usuario': 'admin_permissoes',
    'permissoes.listar_perfis': 'admin_perfis',
    'permissoes.criar_perfil': 'admin_perfis',
    'permissoes.visualizar_perfil': 'admin_perfis',
    'permissoes.atualizar_perfil': 'admin_perfis',
    'permissoes.excluir_perfil': 'admin_perfis',
}


def get_permission_for_route(route_name):
    """
    Obtém o nome da permissão necessária para acessar uma rota
    
    Args:
        route_name: Nome da rota (ex: 'processos.index')
    
    Returns:
        str: Nome da permissão ou None se não houver mapeamento
    """
    return ROUTE_PERMISSIONS.get(route_name)
