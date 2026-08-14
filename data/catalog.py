"""Catálogo e administração de tipos de serviço."""

from data.database import executar_query

def validar_tipo_servico(tipo_id):
    if not isinstance(tipo_id, int) or tipo_id <= 0:
        raise ValueError("ID de tipo de serviço inválido.")
    result = executar_query("SELECT id FROM tipos_servico WHERE id = ? AND ativo = 1", [tipo_id], fetch_one=True)
    if not result:
        raise ValueError(f"Tipo de serviço com ID {tipo_id} inválido, não encontrado ou inativo.")
    return True

def validar_nome_unico_db(tabela, coluna, nome, id_excluir=None):
    query = f"SELECT COUNT(*) FROM {tabela} WHERE {coluna} = ?"
    params = [nome]
    if id_excluir:
        query += " AND id != ?"
        params.append(id_excluir)
    
    result = executar_query(query, params, fetch_one=True)
    if result['COUNT(*)'] > 0:
        raise ValueError(f"O nome '{nome}' já está em uso.")
    return True

def obter_tipos_servico():
    return executar_query("SELECT id, nome, descricao, ativo, prazo_padrao FROM tipos_servico ORDER BY nome ASC")

def add_tipo_servico(nome, descricao, prazo_padrao):
    if prazo_padrao is None or prazo_padrao < 0:
        prazo_padrao = 30
    validar_nome_unico_db('tipos_servico', 'nome', nome)
    return executar_query(
        "INSERT INTO tipos_servico (nome, descricao, ativo, prazo_padrao) VALUES (?, ?, ?, ?)",
        [nome, descricao, 1, prazo_padrao]
    )

def update_tipo_servico(service_id, nome, descricao, ativo, prazo_padrao):
    current_service = executar_query("SELECT nome, ativo FROM tipos_servico WHERE id = ?", [service_id], fetch_one=True)
    if not current_service:
        raise ValueError("Tipo de serviço não encontrado para edição.")

    if prazo_padrao is None or prazo_padrao < 0:
        prazo_padrao = 30
    validar_nome_unico_db('tipos_servico', 'nome', nome, service_id)

    return executar_query(
        "UPDATE tipos_servico SET nome = ?, descricao = ?, ativo = ?, prazo_padrao = ? WHERE id = ?",
        [nome, descricao, 1 if ativo else 0, prazo_padrao, service_id]
    )

def toggle_tipo_servico(service_id):
    current_service = executar_query("SELECT nome, ativo FROM tipos_servico WHERE id = ?", [service_id], fetch_one=True)
    if not current_service:
        raise ValueError("Tipo de serviço não encontrado.")

    novo_status = not current_service['ativo']

    if current_service['ativo'] == 1 and not novo_status:
        count_in_use = executar_query("SELECT COUNT(*) FROM processos WHERE tipo_id = ?", [service_id], fetch_one=True)['COUNT(*)']
        if count_in_use > 0:
            raise ValueError(f"Não foi possível desativar o serviço '{current_service['nome']}' porque ele está sendo utilizado por {count_in_use} processo(s).")
            
    return executar_query(
        "UPDATE tipos_servico SET ativo = ? WHERE id = ?",
        [1 if novo_status else 0, service_id]
    )

