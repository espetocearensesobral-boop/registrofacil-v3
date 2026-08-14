# ============================================================
# EXEMPLOS DE USO DO SISTEMA DE LOGS POR DOMÍNIO
# RegistroFácil — logger_config.py
# ============================================================
#
# Formato de cada entrada:
#   [2024-01-15 14:32:01] [INFO] [auth] [admin / ID: 1] [192.168.1.10] Mensagem
#
# O User_ID e o IP são injetados AUTOMATICAMENTE pelo RequestContextFilter
# a partir do contexto Flask (session e request).
# Para sobrescrever (ex.: fora de request, em jobs do scheduler),
# passe o parâmetro `extra` explicitamente.


# ============================================================
# 1. IMPORTAÇÃO NOS MÓDULOS (routes/auth.py, routes/processos.py, etc.)
# ============================================================

# --- Opção A: Importar os loggers de domínio diretamente (RECOMENDADO) ---
from utils.logger import auth_logger, operacional_logger, sistema_logger, manutencao_logger

# --- Opção B: Manter compatibilidade com código antigo ---
from utils.logger import logger  # grava em logs/operacional/


# ============================================================
# 2. EXEMPLOS EM routes/auth.py
# ============================================================

# 2.1 Login bem-sucedido
auth_logger.info("Login realizado com sucesso.")
# Saída: [2024-01-15 14:32:01] [INFO] [auth] [admin / ID: 1] [192.168.1.10] Login realizado com sucesso.

# 2.2 Falha de login (senha incorreta)
auth_logger.warning(
    f"Tentativa de login falhou para o usuário 'joao': senha incorreta. "
    f"Tentativa 3 de 5."
)

# 2.3 Conta bloqueada
auth_logger.error(
    "Conta bloqueada após 5 tentativas consecutivas de login.",
    extra={'user_id': 'joao / ID: 42', 'ip': '10.0.0.5'}
)

# 2.4 Acesso não autorizado (rota protegida acessada sem permissão)
auth_logger.error(
    "ACESSO NEGADO: usuário sem permissão tentou acessar /admin/usuarios."
)

# 2.5 Logout
auth_logger.info("Sessão encerrada pelo usuário.")

# 2.6 Token de redefinição de senha criado
auth_logger.info(
    "Token de redefinição de senha gerado para o e-mail 'joao@empresa.com'."
)

# 2.7 Evento crítico de segurança (sessão inválida forçada)
auth_logger.critical(
    "Sessão invalidada: token de sessão adulterado detectado.",
    extra={'user_id': 'desconhecido', 'ip': '203.0.113.99'}
)


# ============================================================
# 3. EXEMPLOS EM routes/processos.py
# ============================================================

# 3.1 Cadastro de processo bem-sucedido
operacional_logger.info(
    f"Processo ID 1234 criado com sucesso. Matrícula: 2024-001."
)

# 3.2 Tentativa de edição com dados inválidos
operacional_logger.warning(
    f"Tentativa de edição do Processo ID 1234 rejeitada: "
    f"matrícula '2024-001' já existe em outro processo."
)

# 3.3 Exclusão de processo
operacional_logger.warning(
    "Processo ID 1234 excluído permanentemente."
)

# 3.4 Erro ao salvar processo
operacional_logger.error(
    "Falha ao salvar Processo ID 1234: constraint UNIQUE violada na coluna 'matricula'.",
    exc_info=True  # Inclui o traceback completo
)

# 3.5 Tentativa de exclusão sem permissão
operacional_logger.error(
    "ACESSO NEGADO: usuário sem permissão 'deletar_processo' tentou excluir Processo ID 1234."
)

# 3.6 Edição de Titular vinculado
operacional_logger.info(
    "Titular ID 77 (CPF: ***.***.***-01) atualizado a partir do Processo ID 1234."
)


# ============================================================
# 4. EXEMPLOS EM utils/scheduler.py e models.py (fora de request)
# ============================================================

# Quando executado fora do contexto HTTP (scheduler, init_db, etc.),
# passe sempre o extra para evitar que o filtro tente ler o contexto Flask.

sistema_logger.info(
    "Tabela 'processos' inicializada com sucesso.",
    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
)

sistema_logger.warning(
    "Índice FTS5 'processos_fts' reconstruído com avisos.",
    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
)

sistema_logger.error(
    "Falha ao criar índice de performance na coluna 'data_protocolo'.",
    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'},
    exc_info=True
)


# ============================================================
# 5. EXEMPLOS EM routes/backup.py (domínio manutenção)
# ============================================================

manutencao_logger.info(
    "Backup manual iniciado. Destino: /backups/registrofacil_bkp_20240115_143201.zip",
    extra={'user_id': 'admin / ID: 1', 'ip': '192.168.1.10'}
)

manutencao_logger.info(
    "Backup automático concluído com sucesso. Arquivo: registrofacil_bkp_20240115_030000.zip",
    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
)

manutencao_logger.error(
    "Falha no upload SFTP do backup automático: Connection refused.",
    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'},
    exc_info=True
)

manutencao_logger.warning(
    "Teste de permissão de escrita falhou no diretório /backups/. Verifique as permissões.",
    extra={'user_id': 'SISTEMA', 'ip': '0.0.0.0'}
)


# ============================================================
# 6. CHAMADA MANUAL DA LIMPEZA DE LOGS (90 dias)
# ============================================================
from utils.logger_config import limpar_logs_antigos

# Chamada direta (pode ser usada em testes ou manutenção):
stats = limpar_logs_antigos()
print(f"Limpeza concluída: {stats}")
# Output: Limpeza concluída: {'removidos': 12, 'erros': 0, 'verificados': 47}

# Com retenção personalizada (ex.: 30 dias para debug):
stats = limpar_logs_antigos(retention_days=30)
