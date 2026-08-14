#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Migração: Sistema de Segurança Avançado
Data: 2025-02-16
Descrição: Adiciona permissões granulares e auditoria completa
"""

import sqlite3
import sys
import os

# Caminho do banco de dados
DB_PATH = '/home/claude/registrofacil.db'

def executar_migracao():
    """Executa a migração do banco de dados"""
    
    print("=" * 60)
    print("MIGRAÇÃO: Sistema de Segurança Avançado")
    print("=" * 60)
    print()
    
    if not os.path.exists(DB_PATH):
        print(f"❌ ERRO: Banco de dados não encontrado em {DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("✓ Conexão com banco de dados estabelecida")
        print()
        
        # ============================================================
        # 1. ADICIONAR NOVOS CAMPOS NA TABELA USUARIOS
        # ============================================================
        print("📝 Fase 1: Adicionando novos campos na tabela usuarios...")
        
        novos_campos = [
            ("senha_temporaria", "INTEGER DEFAULT 0"),
            ("forcar_alteracao_senha", "INTEGER DEFAULT 0"),
            ("ultimo_reset_senha", "DATETIME"),
            ("ultimo_reset_por", "INTEGER")
        ]
        
        # Verificar quais campos já existem
        cursor.execute("PRAGMA table_info(usuarios)")
        campos_existentes = [row[1] for row in cursor.fetchall()]
        
        campos_adicionados = 0
        for campo, tipo in novos_campos:
            if campo not in campos_existentes:
                try:
                    cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {campo} {tipo}")
                    print(f"  ✓ Campo '{campo}' adicionado")
                    campos_adicionados += 1
                except sqlite3.Error as e:
                    print(f"  ⚠️ Erro ao adicionar campo '{campo}': {e}")
            else:
                print(f"  ℹ️ Campo '{campo}' já existe (pulando)")
        
        print(f"  → {campos_adicionados} novos campos adicionados")
        print()
        
        # ============================================================
        # 2. CRIAR TABELA DE AUDITORIA ADMINISTRATIVA
        # ============================================================
        print("📝 Fase 2: Criando tabela de auditoria administrativa...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auditoria_admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                admin_nome TEXT NOT NULL,
                admin_email TEXT,
                acao TEXT NOT NULL,
                usuario_afetado_id INTEGER,
                usuario_afetado_nome TEXT,
                usuario_afetado_email TEXT,
                campo_alterado TEXT,
                valor_anterior TEXT,
                valor_novo TEXT,
                justificativa TEXT NOT NULL,
                ip TEXT NOT NULL,
                user_agent TEXT,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                FOREIGN KEY (admin_id) REFERENCES usuarios(id),
                FOREIGN KEY (usuario_afetado_id) REFERENCES usuarios(id)
            )
        """)
        print("  ✓ Tabela 'auditoria_admin' criada/verificada")
        
        # Criar índices
        indices_auditoria = [
            ("idx_auditoria_admin_admin_id", "auditoria_admin(admin_id)"),
            ("idx_auditoria_admin_usuario_afetado_id", "auditoria_admin(usuario_afetado_id)"),
            ("idx_auditoria_admin_acao", "auditoria_admin(acao)"),
            ("idx_auditoria_admin_created_at", "auditoria_admin(created_at)")
        ]
        
        for nome_idx, campos_idx in indices_auditoria:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {nome_idx} ON {campos_idx}")
                print(f"  ✓ Índice '{nome_idx}' criado")
            except sqlite3.Error as e:
                print(f"  ⚠️ Erro ao criar índice '{nome_idx}': {e}")
        
        print()
        
        # ============================================================
        # 3. CRIAR TABELA DE TENTATIVAS NÃO AUTORIZADAS
        # ============================================================
        print("📝 Fase 3: Criando tabela de tentativas não autorizadas...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tentativas_acesso_nao_autorizado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                usuario_nome TEXT,
                tipo_tentativa TEXT NOT NULL,
                detalhes TEXT,
                alvo_user_id INTEGER,
                alvo_user_nome TEXT,
                ip TEXT NOT NULL,
                user_agent TEXT,
                bloqueado INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (alvo_user_id) REFERENCES usuarios(id)
            )
        """)
        print("  ✓ Tabela 'tentativas_acesso_nao_autorizado' criada/verificada")
        
        # Criar índices
        indices_tentativas = [
            ("idx_tentativas_usuario_id", "tentativas_acesso_nao_autorizado(usuario_id)"),
            ("idx_tentativas_tipo", "tentativas_acesso_nao_autorizado(tipo_tentativa)"),
            ("idx_tentativas_created_at", "tentativas_acesso_nao_autorizado(created_at)")
        ]
        
        for nome_idx, campos_idx in indices_tentativas:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {nome_idx} ON {campos_idx}")
                print(f"  ✓ Índice '{nome_idx}' criado")
            except sqlite3.Error as e:
                print(f"  ⚠️ Erro ao criar índice '{nome_idx}': {e}")
        
        print()
        
        # ============================================================
        # 4. CRIAR TABELA DE NOTIFICAÇÕES
        # ============================================================
        print("📝 Fase 4: Criando tabela de notificações...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notificacoes_usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                lida INTEGER DEFAULT 0,
                acao_url TEXT,
                created_at DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                lida_em DATETIME,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        print("  ✓ Tabela 'notificacoes_usuario' criada/verificada")
        
        # Criar índices
        indices_notificacoes = [
            ("idx_notificacoes_usuario_id", "notificacoes_usuario(usuario_id)"),
            ("idx_notificacoes_lida", "notificacoes_usuario(lida)"),
            ("idx_notificacoes_created_at", "notificacoes_usuario(created_at)")
        ]
        
        for nome_idx, campos_idx in indices_notificacoes:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {nome_idx} ON {campos_idx}")
                print(f"  ✓ Índice '{nome_idx}' criado")
            except sqlite3.Error as e:
                print(f"  ⚠️ Erro ao criar índice '{nome_idx}': {e}")
        
        print()
        
        # ============================================================
        # 5. COMMIT DAS ALTERAÇÕES
        # ============================================================
        conn.commit()
        print("✓ Todas as alterações foram salvas no banco de dados")
        print()
        
        # ============================================================
        # 6. VERIFICAÇÕES PÓS-MIGRAÇÃO
        # ============================================================
        print("📊 Verificações pós-migração:")
        print()
        
        # Verificar tabelas criadas
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name IN ('auditoria_admin', 'tentativas_acesso_nao_autorizado', 'notificacoes_usuario')
            ORDER BY name
        """)
        tabelas = cursor.fetchall()
        print(f"  ✓ {len(tabelas)} novas tabelas criadas:")
        for tabela in tabelas:
            print(f"    - {tabela[0]}")
        print()
        
        # Verificar campos adicionados
        cursor.execute("PRAGMA table_info(usuarios)")
        campos = cursor.fetchall()
        novos_campos_list = [campo[0] for campo, _ in novos_campos]
        campos_encontrados = [c[1] for c in campos if c[1] in novos_campos_list]
        print(f"  ✓ {len(campos_encontrados)} novos campos em 'usuarios':")
        for campo in campos_encontrados:
            print(f"    - {campo}")
        print()
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM auditoria_admin")
        count_audit = cursor.fetchone()[0]
        print(f"  ℹ️ Registros em auditoria_admin: {count_audit}")
        
        cursor.execute("SELECT COUNT(*) FROM tentativas_acesso_nao_autorizado")
        count_tent = cursor.fetchone()[0]
        print(f"  ℹ️ Registros em tentativas_acesso_nao_autorizado: {count_tent}")
        
        cursor.execute("SELECT COUNT(*) FROM notificacoes_usuario")
        count_notif = cursor.fetchone()[0]
        print(f"  ℹ️ Registros em notificacoes_usuario: {count_notif}")
        
        print()
        print("=" * 60)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        
        cursor.close()
        conn.close()
        
        return True
        
    except sqlite3.Error as e:
        print(f"\n❌ ERRO durante a migração: {e}")
        print("\nRevertendo alterações...")
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"\n❌ ERRO INESPERADO: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    sucesso = executar_migracao()
    sys.exit(0 if sucesso else 1)
