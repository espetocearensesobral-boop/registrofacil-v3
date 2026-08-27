"""Migrações de dados versionadas do banco SQLite."""

from config import Config
from utils.logger import sistema_logger as logger
from data.database import get_sqlite_connection

DATABASE_PATH = Config.DATABASE_PATH


def executar_migracoes_dados(connection=None):
    """Aplica migrações de dados pendentes de forma transacional."""
    with get_sqlite_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA user_version")
        versao_atual = cursor.fetchone()[0]
        logger.info(f"Versão atual do banco (user_version): {versao_atual}")

        migracoes = []

        def migracao_001(cursor):
            cursor.execute("""
                UPDATE processos
                SET possui_matricula = 1
                WHERE matricula IS NOT NULL
                  AND matricula != ''
                  AND (possui_matricula IS NULL OR possui_matricula = 0)
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 001] {n} processo(s) tiveram possui_matricula corrigido para 1.")

        migracoes.append(migracao_001)

        def migracao_002(cursor):
            cursor.execute("""
                UPDATE titulares
                SET ultimo_registro_id = (
                    SELECT p.id FROM processos p
                    WHERE p.titular = titulares.nome
                    ORDER BY p.data_entrada DESC, p.id DESC
                    LIMIT 1
                )
                WHERE (
                    ultimo_registro_id IS NULL
                    OR NOT EXISTS (
                        SELECT 1 FROM processos WHERE id = titulares.ultimo_registro_id
                    )
                )
                AND EXISTS (
                    SELECT 1 FROM processos WHERE titular = titulares.nome
                )
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 002] {n} titular(es) tiveram ultimo_registro_id sincronizado.")

        migracoes.append(migracao_002)

        def migracao_003(cursor):
            cursor.execute("""
                UPDATE processos
                SET numero_processo = 'PROC-' || CAST(id AS TEXT)
                WHERE numero_processo IS NULL OR numero_processo = ''
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 003] {n} processo(s) receberam numero_processo padrão.")

        migracoes.append(migracao_003)

        def migracao_004(cursor):
            cursor.execute("""
                UPDATE processos SET envolvido_notas = 0
                WHERE envolvido_notas IS NULL
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 004] {n} processo(s) tiveram envolvido_notas normalizado.")

        migracoes.append(migracao_004)

        def migracao_005(cursor):
            cursor.execute("""
                UPDATE usuarios SET must_change_password = 0
                WHERE must_change_password IS NULL
            """)
            n = cursor.rowcount
            if n > 0:
                logger.info(f"[Migração 005] {n} usuário(s) tiveram must_change_password normalizado.")

        migracoes.append(migracao_005)

        def migracao_006(cursor):
            cursor.execute("UPDATE tipos_servico SET ativo = 1 WHERE ativo IS NULL")
            n1 = cursor.rowcount
            cursor.execute("UPDATE status_processo SET ativo = 1 WHERE ativo IS NULL")
            n2 = cursor.rowcount
            if n1 + n2 > 0:
                logger.info(f"[Migração 006] {n1} tipo(s) e {n2} status normalizados (ativo = 1).")

        migracoes.append(migracao_006)

        def migracao_007(cursor):
            """Atualiza avaliações opcionais sem usar sintaxe PostgreSQL no SQLite."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'reviews'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 007] Tabela 'reviews' ausente; recurso opcional não instalado.")
                return

            colunas = {
                row[1] for row in cursor.execute("PRAGMA table_info(reviews)").fetchall()
            }
            definicoes = {
                "service_id": "TEXT",
                "service_title": "TEXT",
                "service_experience": "TEXT",
            }
            adicionadas = 0
            for nome, tipo in definicoes.items():
                if nome not in colunas:
                    cursor.execute(f"ALTER TABLE reviews ADD COLUMN {nome} {tipo}")
                    adicionadas += 1

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS reviews_service_id_idx "
                "ON reviews(service_id)"
            )
            logger.info("[Migração 007] %s coluna(s) de avaliação adicionada(s).", adicionadas)

        migracoes.append(migracao_007)

        def migracao_008(cursor):
            """Migra preferências visuais antigas para o modelo institucional."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user_preferences'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 008] user_preferences ausente; nada a migrar.")
                return
            colunas = {
                row[1] for row in cursor.execute("PRAGMA table_info(user_preferences)").fetchall()
            }
            if "sidebar_selection_color" not in colunas:
                cursor.execute(
                    "ALTER TABLE user_preferences ADD COLUMN sidebar_selection_color TEXT DEFAULT '#1B4368'"
                )
            cursor.execute(
                "UPDATE user_preferences SET tema_cor = 'paleta-01' "
                "WHERE tema_cor IS NULL OR tema_cor = 'grafite-vinho' "
                "OR tema_cor NOT IN ('paleta-01', 'paleta-02', 'paleta-03')"
            )
            cursor.execute(
                "UPDATE user_preferences SET sidebar_selection_color = '#1B4368' "
                "WHERE sidebar_selection_color IS NULL OR sidebar_selection_color = ''"
            )
            logger.info("[Migração 008] Preferências visuais convertidas para Paletas 01–03.")

        migracoes.append(migracao_008)

        def migracao_009(cursor):
            """Normaliza preferências existentes para os dez temas institucionais."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user_preferences'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 009] user_preferences ausente; nada a migrar.")
                return
            validos = "('paleta-01', 'paleta-02', 'paleta-03', 'paleta-04', 'paleta-05', 'paleta-06', 'paleta-07', 'paleta-08', 'paleta-09', 'paleta-10')"
            cursor.execute(
                f"UPDATE user_preferences SET tema_cor = 'paleta-01' "
                f"WHERE tema_cor IS NULL OR tema_cor NOT IN {validos}"
            )
            logger.info("[Migração 009] Preferências visuais normalizadas para dez temas.")

        migracoes.append(migracao_009)

        def migracao_010(cursor):
            """Garante que o catálogo atual de dez temas seja aceito no banco."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user_preferences'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 010] user_preferences ausente; nada a migrar.")
                return
            validos = "('paleta-01', 'paleta-02', 'paleta-03', 'paleta-04', 'paleta-05', 'paleta-06', 'paleta-07', 'paleta-08', 'paleta-09', 'paleta-10')"
            cursor.execute(
                f"UPDATE user_preferences SET tema_cor = 'paleta-01' "
                f"WHERE tema_cor IS NULL OR tema_cor NOT IN {validos}"
            )
            logger.info("[Migração 010] Preferências visuais normalizadas para dez temas.")

        migracoes.append(migracao_010)

        def migracao_011(cursor):
            """Migração histórica que expandiu o catálogo visual persistido para quinze temas."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user_preferences'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 011] user_preferences ausente; nada a migrar.")
                return
            validos = "('paleta-01', 'paleta-02', 'paleta-03', 'paleta-04', 'paleta-05', 'paleta-06', 'paleta-07', 'paleta-08', 'paleta-09', 'paleta-10', 'paleta-11', 'paleta-12', 'paleta-13', 'paleta-14', 'paleta-15')"
            cursor.execute(
                f"UPDATE user_preferences SET tema_cor = 'paleta-01' "
                f"WHERE tema_cor IS NULL OR tema_cor NOT IN {validos}"
            )
            logger.info("[Migração 011] Preferências visuais históricas normalizadas para quinze temas.")

        migracoes.append(migracao_011)

        def migracao_012(cursor):
            """Expande o catálogo visual persistido para trinta temas."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user_preferences'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 012] user_preferences ausente; nada a migrar.")
                return
            validos = "('paleta-01', 'paleta-02', 'paleta-03', 'paleta-04', 'paleta-05', 'paleta-06', 'paleta-07', 'paleta-08', 'paleta-09', 'paleta-10', 'paleta-11', 'paleta-12', 'paleta-13', 'paleta-14', 'paleta-15', 'paleta-16', 'paleta-17', 'paleta-18', 'paleta-19', 'paleta-20', 'paleta-21', 'paleta-22', 'paleta-23', 'paleta-24', 'paleta-25', 'paleta-26', 'paleta-27', 'paleta-28', 'paleta-29', 'paleta-30')"
            cursor.execute(
                f"UPDATE user_preferences SET tema_cor = 'paleta-01' "
                f"WHERE tema_cor IS NULL OR tema_cor NOT IN {validos}"
            )
            logger.info("[Migração 012] Preferências visuais normalizadas para trinta temas.")

        migracoes.append(migracao_012)

        def migracao_013(cursor):
            """Consolida o catálogo visual de trinta temas em bancos já existentes."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user_preferences'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 013] user_preferences ausente; nada a migrar.")
                return
            validos = "('paleta-01', 'paleta-02', 'paleta-03', 'paleta-04', 'paleta-05', 'paleta-06', 'paleta-07', 'paleta-08', 'paleta-09', 'paleta-10', 'paleta-11', 'paleta-12', 'paleta-13', 'paleta-14', 'paleta-15', 'paleta-16', 'paleta-17', 'paleta-18', 'paleta-19', 'paleta-20', 'paleta-21', 'paleta-22', 'paleta-23', 'paleta-24', 'paleta-25', 'paleta-26', 'paleta-27', 'paleta-28', 'paleta-29', 'paleta-30')"
            cursor.execute(
                f"UPDATE user_preferences SET tema_cor = 'paleta-01' "
                f"WHERE tema_cor IS NULL OR tema_cor NOT IN {validos}"
            )
            logger.info("[Migração 013] Preferências visuais consolidadas para trinta temas.")

        migracoes.append(migracao_013)

        def migracao_014(cursor):
            """Remove Representantes e consolida eventuais dados legados em Apresentantes."""
            tabela_representantes = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'representantes'"
            ).fetchone()
            if tabela_representantes:
                registros = cursor.execute(
                    "SELECT nome, telefone, email FROM representantes ORDER BY id"
                ).fetchall()
                for registro in registros:
                    nome, telefone, email = registro
                    if not nome:
                        continue
                    existente = cursor.execute(
                        "SELECT id FROM apresentantes WHERE nome = ?",
                        (nome,),
                    ).fetchone()
                    if existente:
                        cursor.execute(
                            """UPDATE apresentantes
                               SET telefone = COALESCE(NULLIF(telefone, ''), ?),
                                   email = COALESCE(NULLIF(email, ''), ?)
                             WHERE id = ?""",
                            (telefone, email, existente[0]),
                        )
                    else:
                        cursor.execute(
                            """INSERT INTO apresentantes (nome, telefone, email)
                               VALUES (?, ?, ?)""",
                            (nome, telefone, email),
                        )
                cursor.execute("DROP TABLE representantes")
                logger.info("[Migração 014] Dados legados de representantes consolidados em apresentantes e tabela removida.")

            tabela_processos = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'processos'"
            ).fetchone()
            if not tabela_processos:
                return

            colunas = {
                row[1] for row in cursor.execute("PRAGMA table_info(processos)").fetchall()
            }
            colunas_legadas = {'representante', 'representante_telefone', 'representante_email'} & colunas
            if not colunas_legadas:
                return

            if 'representante' in colunas and 'apresentante' in colunas:
                cursor.execute(
                    """UPDATE processos
                          SET apresentante = representante
                        WHERE (apresentante IS NULL OR TRIM(apresentante) = '')
                          AND representante IS NOT NULL
                          AND TRIM(representante) <> ''"""
                )
            if 'representante_telefone' in colunas and 'apresentante_telefone' in colunas:
                cursor.execute(
                    """UPDATE processos
                          SET apresentante_telefone = representante_telefone
                        WHERE (apresentante_telefone IS NULL OR TRIM(apresentante_telefone) = '')
                          AND representante_telefone IS NOT NULL
                          AND TRIM(representante_telefone) <> ''"""
                )
            if 'representante_email' in colunas and 'apresentante_email' in colunas:
                cursor.execute(
                    """UPDATE processos
                          SET apresentante_email = representante_email
                        WHERE (apresentante_email IS NULL OR TRIM(apresentante_email) = '')
                          AND representante_email IS NOT NULL
                          AND TRIM(representante_email) <> ''"""
                )

            for coluna in ('representante', 'representante_telefone', 'representante_email'):
                if coluna in colunas:
                    cursor.execute(f"ALTER TABLE processos DROP COLUMN {coluna}")
            logger.info("[Migração 014] Colunas legadas de representante removidas de processos.")

        migracoes.append(migracao_014)

        def migracao_015(cursor):
            """Preserva logs de processos removidos trocando CASCADE por SET NULL."""
            tabela = cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'logs'"
            ).fetchone()
            if not tabela:
                logger.info("[Migração 015] Tabela 'logs' ausente; nada a migrar.")
                return

            foreign_keys = cursor.execute("PRAGMA foreign_key_list(logs)").fetchall()
            processo_fk = next((row for row in foreign_keys if row[3] == 'processo_id'), None)
            if not processo_fk or str(processo_fk[6]).upper() != 'CASCADE':
                logger.info("[Migração 015] Relação de processo da tabela 'logs' já preserva exclusões.")
                return

            existing_indexes = cursor.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'index' AND tbl_name = 'logs' AND sql IS NOT NULL"
            ).fetchall()
            for row in existing_indexes:
                cursor.execute(f'DROP INDEX IF EXISTS "{row[0].replace(chr(34), chr(34) * 2)}"')

            cursor.execute("PRAGMA foreign_keys = OFF")
            cursor.execute("ALTER TABLE logs RENAME TO logs_legacy_015")
            cursor.execute("""
                CREATE TABLE logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acao TEXT NOT NULL,
                    contexto TEXT,
                    processo_id INTEGER,
                    usuario_id INTEGER,
                    ip TEXT,
                    event_id TEXT,
                    request_id TEXT,
                    domain TEXT DEFAULT 'operacional',
                    event_type TEXT DEFAULT 'legacy',
                    entity_id TEXT,
                    severity TEXT DEFAULT 'INFO',
                    timestamp TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
                    FOREIGN KEY (processo_id) REFERENCES processos(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("""
                INSERT INTO logs (
                    id, acao, contexto, processo_id, usuario_id, ip,
                    event_id, request_id, domain, event_type, entity_id,
                    severity, timestamp
                )
                SELECT
                    old.id, old.acao, old.contexto,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM processos p WHERE p.id = old.processo_id
                    ) THEN old.processo_id ELSE NULL END,
                    old.usuario_id, old.ip, old.event_id, old.request_id,
                    old.domain, old.event_type,
                    CASE
                        WHEN old.entity_id IS NOT NULL THEN old.entity_id
                        WHEN old.processo_id IS NOT NULL AND NOT EXISTS (
                            SELECT 1 FROM processos p WHERE p.id = old.processo_id
                        ) THEN CAST(old.processo_id AS TEXT)
                        ELSE NULL
                    END,
                    old.severity, old.timestamp
                FROM logs_legacy_015 old
            """)
            cursor.execute("DROP TABLE logs_legacy_015")
            cursor.execute("PRAGMA foreign_keys = ON")

            for index_sql in (
                "CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_logs_usuario ON logs(usuario_id, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_logs_acao ON logs(acao, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_logs_event_id ON logs(event_id)",
                "CREATE INDEX IF NOT EXISTS idx_logs_domain_type ON logs(domain, event_type, timestamp DESC)",
            ):
                cursor.execute(index_sql)
            logger.info("[Migração 015] Tabela 'logs' reconstruída com ON DELETE SET NULL; registros preservados.")

        migracoes.append(migracao_015)

        total = len(migracoes)
        pendentes = migracoes[versao_atual:]

        if not pendentes:
            logger.info("Banco de dados já está na versão mais recente. Nenhuma migração necessária.")
            return

        logger.info(f"Aplicando {len(pendentes)} migração(ões) (v{versao_atual} → v{total})...")

        try:
            for i, migracao in enumerate(pendentes, start=versao_atual + 1):
                logger.info(f"Executando migração {i:03d}...")
                migracao(cursor)

            cursor.execute(f"PRAGMA user_version = {total}")
            conn.commit()
            logger.info(f"Migrações concluídas. Banco atualizado para versão {total}.")

        except Exception as e:
            conn.rollback()
            logger.error(
                f"Erro durante migrações de dados. Rollback efetuado. Erro: {e}",
                exc_info=True,
            )
            raise
