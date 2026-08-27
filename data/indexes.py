"""Índices de performance do banco de dados."""

from utils.logger import sistema_logger as logger

def criar_indices_performance(cursor):
    """Cria índices otimizados para melhorar performance das queries."""
    try:
        indices = [
            # Processos
            "CREATE INDEX IF NOT EXISTS idx_processos_status ON processos(status_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_tipo ON processos(tipo_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_responsavel ON processos(responsavel_id)",
            "CREATE INDEX IF NOT EXISTS idx_processos_created_at ON processos(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_processos_data_entrada ON processos(data_entrada DESC)",
            "CREATE INDEX IF NOT EXISTS idx_processos_numero ON processos(numero_processo)",
            "CREATE INDEX IF NOT EXISTS idx_processos_matricula ON processos(matricula)",
            "CREATE INDEX IF NOT EXISTS idx_processos_prazo ON processos(prazo_final, data_conclusao)",

            # Anexos
            "CREATE INDEX IF NOT EXISTS idx_anexos_processo_id ON anexos_processos(processo_id)",

            # Histórico (coluna correta: timestamp_alteracao)
            "CREATE INDEX IF NOT EXISTS idx_historico_processo ON historico_processos(processo_id, timestamp_alteracao DESC)",
            "CREATE INDEX IF NOT EXISTS idx_historico_usuario ON historico_processos(usuario_id, timestamp_alteracao DESC)",

            # Titulares (removido índice cpf_cnpj pois a coluna não existe na tabela)
            "CREATE INDEX IF NOT EXISTS idx_titulares_nome ON titulares(nome)",

            # Usuários
            "CREATE INDEX IF NOT EXISTS idx_usuarios_email ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usuarios_ativos ON usuarios(ativo)",

            # Logs
            "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs(usuario_id, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_acao ON logs(acao, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_logs_event_id ON logs(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_logs_domain_type ON logs(domain, event_type, timestamp DESC)",

            # Login attempts
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip, tempo DESC)",
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_identity ON login_attempts(identidade_hash, tempo DESC)",
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_event_id ON login_attempts(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_request_id ON login_attempts(request_id)",

            # Notificações
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON notificacoes(usuario_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_lida ON notificacoes(usuario_id, lida)",

            # Permissões (v3.3.5)
            "CREATE INDEX IF NOT EXISTS idx_permissoes_usuario ON permissoes_usuarios(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_permissoes_modulo ON permissoes_usuarios(modulo_id)",
            "CREATE INDEX IF NOT EXISTS idx_permissoes_usuario_modulo ON permissoes_usuarios(usuario_id, modulo_id)",

            # Módulos Sistema (v3.3.5)
            "CREATE INDEX IF NOT EXISTS idx_modulos_categoria ON modulos_sistema(categoria, ordem)",
            "CREATE INDEX IF NOT EXISTS idx_modulos_ativo ON modulos_sistema(ativo)",

            # Perfis de Permissão
            "CREATE INDEX IF NOT EXISTS idx_perfis_permissao_nome ON perfis_permissao(nome)",
            "CREATE INDEX IF NOT EXISTS idx_perfis_modulos_perfil ON perfis_permissao_modulos(perfil_id)",
            "CREATE INDEX IF NOT EXISTS idx_usuario_perfil_usuario ON usuario_perfil(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_usuario_perfil_perfil ON usuario_perfil(perfil_id)",

            # Auditoria e Segurança (v3.16.5)
            "CREATE INDEX IF NOT EXISTS idx_auditoria_admin_id ON auditoria_admin(admin_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auditoria_usuario_afetado ON auditoria_admin(usuario_afetado_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auditoria_acao ON auditoria_admin(acao, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_auditoria_event_id ON auditoria_admin(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_tentativas_usuario ON tentativas_acesso_nao_autorizado(usuario_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tentativas_ip ON tentativas_acesso_nao_autorizado(ip, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tentativas_event_id ON tentativas_acesso_nao_autorizado(event_id)",
            "CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario_lida ON notificacoes_usuario(usuario_id, lida)",
        ]

        for index_sql in indices:
            try:
                cursor.execute(index_sql)
            except Exception as e:
                logger.warning(f"Índice já existe ou erro ao criar: {e}")

        logger.info("Índices de performance criados/verificados com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao criar índices: {e}", exc_info=True)
