#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verificar_duplicatas_telefone.py

Script de diagnóstico para o RegistroFácil.

Objetivo: verificar se os dados atuais do banco já respeitam a regra de
negócio implementada em models.py::validar_telefone_unico(), ANTES de
qualquer decisão sobre adicionar constraints no banco.

IMPORTANTE — leia antes de agir:
A regra atual NÃO é "telefone único no sistema". É:
  - Um mesmo titular PODE reusar o mesmo telefone em vários processos
    (isso é o caso normal de uso).
  - O que é proibido é o MESMO telefone estar vinculado a DOIS TITULARES
    DIFERENTES (na tabela `titulares` ou em `processos.apresentante_telefone`
    associado a um `titular` diferente).

Por isso, uma constraint SQL `UNIQUE(telefone)` simples NÃO é compatível com
essa regra — ela quebraria o uso normal (rejeitaria o 2º processo de um
cliente que já usou aquele telefone antes). Este script existe para
confirmar isso com dados reais e mostrar o estado atual da integridade,
independentemente de qual solução for adotada no futuro (aplicação vs banco).

Uso:
    python verificar_duplicatas_telefone.py [caminho_para_o_banco.db]

Se nenhum caminho for informado, tenta usar o caminho padrão do Config
(funciona se rodado a partir da raiz do projeto, em modo .py de desenvolvimento).
"""

import sys
import os
import sqlite3


def obter_caminho_banco():
    if len(sys.argv) > 1:
        return sys.argv[1]
    try:
        from config import Config
        return Config.DATABASE_PATH
    except Exception:
        caminho_padrao = os.path.join(os.getcwd(), 'registrofacil.db')
        print(f"[Aviso] Não foi possível importar Config. Tentando caminho padrão: {caminho_padrao}")
        return caminho_padrao


def linha_separadora(titulo=""):
    print("\n" + "=" * 78)
    if titulo:
        print(titulo)
        print("=" * 78)


def main():
    db_path = obter_caminho_banco()

    if not os.path.exists(db_path):
        print(f"[ERRO] Banco de dados não encontrado em: {db_path}")
        print("Informe o caminho correto: python verificar_duplicatas_telefone.py \"C:\\ProgramData\\RegistroFacil\\registrofacil.db\"")
        sys.exit(1)

    print(f"Analisando banco de dados: {db_path}\n")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # -------------------------------------------------------------------
    # 1) Telefones em `titulares` compartilhados por titulares diferentes
    #    (violação real da regra atual, se existir)
    # -------------------------------------------------------------------
    linha_separadora("1) TABELA 'titulares': telefones repetidos entre titulares DIFERENTES")
    cur.execute("""
        SELECT telefone, COUNT(*) as qtd, GROUP_CONCAT(nome, ' | ') as titulares
        FROM titulares
        WHERE telefone IS NOT NULL AND TRIM(telefone) != ''
        GROUP BY telefone
        HAVING COUNT(*) > 1
        ORDER BY qtd DESC
    """)
    titulares_duplicados = cur.fetchall()

    if not titulares_duplicados:
        print("Nenhum telefone duplicado entre titulares diferentes. ✅")
    else:
        print(f"Encontrados {len(titulares_duplicados)} telefone(s) usados por mais de um titular:\n")
        for row in titulares_duplicados:
            print(f"  Telefone '{row['telefone']}' -> {row['qtd']} titulares: {row['titulares']}")

    # -------------------------------------------------------------------
    # 2) Telefones em `processos.apresentante_telefone` vinculados a
    #    titulares diferentes (mesma verificação que validar_telefone_unico
    #    faz na tabela processos)
    # -------------------------------------------------------------------
    linha_separadora("2) TABELA 'processos': apresentante_telefone repetido entre titulares DIFERENTES")
    cur.execute("""
        SELECT apresentante_telefone,
               COUNT(DISTINCT titular) as qtd_titulares_distintos,
               GROUP_CONCAT(DISTINCT titular) as titulares,
               COUNT(*) as qtd_processos
        FROM processos
        WHERE apresentante_telefone IS NOT NULL AND TRIM(apresentante_telefone) != ''
        GROUP BY apresentante_telefone
        HAVING COUNT(DISTINCT titular) > 1
        ORDER BY qtd_titulares_distintos DESC
    """)
    processos_duplicados = cur.fetchall()

    if not processos_duplicados:
        print("Nenhum apresentante_telefone compartilhado entre titulares diferentes. ✅")
    else:
        print(f"Encontrados {len(processos_duplicados)} telefone(s) usados em processos de titulares diferentes:\n")
        for row in processos_duplicados:
            print(
                f"  Telefone '{row['apresentante_telefone']}' -> "
                f"{row['qtd_titulares_distintos']} titulares distintos "
                f"({row['qtd_processos']} processos): {row['titulares']}"
            )

    # -------------------------------------------------------------------
    # 3) Informativo: quantos processos reusam legitimamente o telefone
    #    do MESMO titular (isso é esperado e NÃO é problema)
    # -------------------------------------------------------------------
    linha_separadora("3) Informativo: reuso legítimo do mesmo telefone pelo MESMO titular")
    cur.execute("""
        SELECT titular, apresentante_telefone, COUNT(*) as qtd_processos
        FROM processos
        WHERE apresentante_telefone IS NOT NULL AND TRIM(apresentante_telefone) != ''
        GROUP BY titular, apresentante_telefone
        HAVING COUNT(*) > 1
        ORDER BY qtd_processos DESC
        LIMIT 10
    """)
    reuso_legitimo = cur.fetchall()
    if not reuso_legitimo:
        print("Nenhum titular reusou o mesmo telefone em múltiplos processos ainda.")
    else:
        print(f"Exemplos de reuso legítimo (top 10) — isto é ESPERADO e seria quebrado por um UNIQUE simples:\n")
        for row in reuso_legitimo:
            print(f"  Titular '{row['titular']}' usou '{row['apresentante_telefone']}' em {row['qtd_processos']} processos")

    # -------------------------------------------------------------------
    # Veredito final
    # -------------------------------------------------------------------
    linha_separadora("VEREDITO")
    total_violacoes = len(titulares_duplicados) + len(processos_duplicados)

    if total_violacoes == 0:
        print("Os dados atuais RESPEITAM a regra de negócio implementada no código")
        print("(nenhum telefone está vinculado a titulares diferentes hoje).")
    else:
        print(f"⚠️  Há {total_violacoes} caso(s) que já violam a regra atual do código.")
        print("Isso sugere que a validação foi contornada em algum momento (edição direta")
        print("no banco, importação de dados antiga, ou bug já corrigido). Vale investigar")
        print("esses casos manualmente antes de qualquer mudança de schema.")

    print()
    print("Independentemente do resultado acima: uma constraint SQL `UNIQUE(telefone)`")
    print("simples NÃO é recomendada, pois a regra de negócio é condicional (único por")
    print("titular, não global) — ver seção 3. Se quiser reduzir a janela de race condition")
    print("da validação atual, a alternativa correta é envolver a checagem + o INSERT/UPDATE")
    print("na MESMA transação com um lock (ex.: BEGIN IMMEDIATE no SQLite), não uma constraint.")

    conn.close()


if __name__ == '__main__':
    main()
