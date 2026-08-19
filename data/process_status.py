"""Serviços de configuração de status dos processos."""

from data.database import executar_query
from utils.logger import operacional_logger as logger

def add_status_processo(nome, hex_color):
    validar_nome_unico_db('status_processo', 'nome', nome)
    return executar_query(
        "INSERT INTO status_processo (nome, hex_color, ativo) VALUES (?, ?, ?)",
        [nome, hex_color, 1]
    )

def update_status_processo(status_id, nome, hex_color, ativo):
    current_status = executar_query("SELECT nome, ativo FROM status_processo WHERE id = ?", [status_id], fetch_one=True)
    if not current_status:
        raise ValueError("Status não encontrado para edição.")

    validar_nome_unico_db('status_processo', 'nome', nome, status_id)
        
    return executar_query(
        "UPDATE status_processo SET nome = ?, hex_color = ?, ativo = ? WHERE id = ?",
        [nome, hex_color, 1 if ativo else 0, status_id]
    )

def toggle_status_processo(status_id):
    current_status = executar_query("SELECT nome, ativo FROM status_processo WHERE id = ?", [status_id], fetch_one=True)
    if not current_status:
        raise ValueError("Status não encontrado.")
    
    novo_status = not current_status['ativo']
    
    if current_status['ativo'] == 1 and not novo_status:
        count_in_use = executar_query("SELECT COUNT(*) FROM processos WHERE status_id = ?", [status_id], fetch_one=True)['COUNT(*)']
        if count_in_use > 0:
            raise ValueError(f"Não foi possível desativar o status '{current_status['nome']}' porque ele está sendo utilizado por {count_in_use} processo(s).")

    return executar_query(
        "UPDATE status_processo SET ativo = ? WHERE id = ?",
        [1 if novo_status else 0, status_id]
    )

