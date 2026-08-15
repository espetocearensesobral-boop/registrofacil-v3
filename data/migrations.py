"""Migrações de dados versionadas do banco SQLite."""

from config import Config
from utils.logger import logger
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
