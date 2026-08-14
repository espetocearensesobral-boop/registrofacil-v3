"""Templates de processos e auxiliares de apresentação."""

import secrets
import string

from data.database import executar_query

def criar_template(nome, descricao, tipo_id, status_id, prazo_dias, 
                   observacoes_padrao, usuario_id, publico=0):
    """Cria um novo template de processo."""
    query = """
        INSERT INTO templates_processos 
        (nome, descricao, tipo_id, status_id, prazo_dias, observacoes_padrao, usuario_criador, publico)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    return executar_query(query, [nome, descricao, tipo_id, status_id, 
                                  prazo_dias, observacoes_padrao, usuario_id, publico])

def listar_templates(usuario_id=None):
    """Lista templates disponíveis para o usuário."""
    if usuario_id:
        query = """
            SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome, s.hex_color as status_cor
            FROM templates_processos t
            LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
            LEFT JOIN status_processo s ON t.status_id = s.id
            WHERE t.publico = 1 OR t.usuario_criador = ?
            ORDER BY t.nome
        """
        return executar_query(query, [usuario_id], fetch_all=True) or []
    else:
        query = """
            SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome, s.hex_color as status_cor
            FROM templates_processos t
            LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
            LEFT JOIN status_processo s ON t.status_id = s.id
            WHERE t.publico = 1
            ORDER BY t.nome
        """
        return executar_query(query, fetch_all=True) or []

def obter_template(template_id):
    """Obtém um template específico."""
    query = """
        SELECT t.*, ts.nome as tipo_nome, s.nome as status_nome
        FROM templates_processos t
        LEFT JOIN tipos_servico ts ON t.tipo_id = ts.id
        LEFT JOIN status_processo s ON t.status_id = s.id
        WHERE t.id = ?
    """
    return executar_query(query, [template_id], fetch_one=True)

def atualizar_template(template_id, dados):
    """Atualiza um template existente."""
    campos = []
    valores = []
    
    campos_permitidos = ['nome', 'descricao', 'tipo_id', 'status_id', 
                        'prazo_dias', 'observacoes_padrao', 'publico']
    
    for campo in campos_permitidos:
        if campo in dados:
            campos.append(f"{campo} = ?")
            valores.append(dados[campo])
    
    if not campos:
        return False
    
    campos.append("updated_at = strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')")
    valores.append(template_id)
    
    query = f"UPDATE templates_processos SET {', '.join(campos)} WHERE id = ?"
    return executar_query(query, valores)

def excluir_template(template_id, usuario_id):
    """Exclui um template (apenas o criador pode excluir)."""
    query = "DELETE FROM templates_processos WHERE id = ? AND usuario_criador = ?"
    return executar_query(query, [template_id, usuario_id])

def gerar_senha_temporaria(tamanho=12):
    """
    Gera uma senha temporária forte.
    
    Args:
        tamanho: Tamanho da senha (padrão 12)
    
    Returns:
        Senha temporária gerada
    """
    import string
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(tamanho))

def mascarar_email(email):
    """
    Mascara um email para exibição segura.
    
    Args:
        email: Email a ser mascarado
    
    Returns:
        Email mascarado (exemplo: m***@email.com)
    """
    if not email or '@' not in email:
        return email
    
    partes = email.split('@')
    usuario = partes[0]
    dominio = partes[1]
    
    if len(usuario) <= 2:
        usuario_mascarado = usuario[0] + '*'
    else:
        usuario_mascarado = usuario[0] + '***'
    
    return f"{usuario_mascarado}@{dominio}"

