# Registro Fácil 3.27.0

**Data da release:** 17 de agosto de 2026  
**Branch:** `main`

## Resumo

A versão 3.27.0 consolida a evolução da experiência de consulta e relatórios do Registro Fácil. O foco desta release foi reduzir duplicidade, melhorar a legibilidade documental, centralizar ações de processo e padronizar as saídas de Titulares, Apresentantes e Processos.

## Principais alterações

### Busca Inteligente

A Busca Inteligente passou a aceitar uma consulta unificada por nome, telefone, matrícula, ID e outros dados. A consulta é executada somente após o usuário informar um termo. Os resultados oferecem as ações Visualizar, Imprimir e Baixar PDF, sem exibir identificadores internos desnecessários.

### Relatórios

A Central Geral de Relatórios foi removida, incluindo os módulos de contatos, serviços e tipos e os cards de acesso associados. O Relatório de processos foi preservado.

Os relatórios cadastrais de Titulares e Apresentantes passaram a oferecer impressão, Excel e PDF com filtros consistentes. Os documentos receberam cabeçalho institucional, resumo da consulta, estado vazio padronizado, rodapé, paginação e melhor contraste.

O Relatório de processos passou a registrar no documento o contexto da consulta, a ordenação aplicada e a situação de prazo, incluindo processos vencidos, em dia e sem prazo definido.

### Interface e navegação

A sidebar recebeu organização por categorias, tipografia legível, animação de abertura e fechamento e consolidação da entidade Apresentantes. Também foram corrigidos estados visuais persistentes de botões e aplicada uma camada final de padronização de layout.

## Validação

A release foi validada com:

| Verificação | Resultado |
|---|---|
| Compilação Python | Aprovada |
| `git diff --check` | Aprovado |
| Testes automatizados | 59 aprovados |
| Relatório de processos | Preservado e validado |
| Busca Inteligente | Preservada e validada |
| Working tree | Limpa e sincronizada com `origin/main` |

## Commits principais

| Commit | Escopo |
|---|---|
| `bc489db` | Padronização de contexto e estados vazios dos relatórios |
| `a9c1d97` | PDFs padronizados para Titulares e Apresentantes |
| `2fd478c` | Padronização dos documentos de impressão cadastrais |
| `474a7c6` | Contexto, filtros e situação de prazo no Relatório de processos |

## Compatibilidade

A versão mantém Flask, Jinja2, Bootstrap 5, SQLite, WeasyPrint e a estrutura atual de migrações. Não foram introduzidas alterações de schema nesta atualização.

## Identificação

A versão central do aplicativo é definida em `config.py` como `3.27.0`. O compilador Windows, a documentação pública, o changelog e os parâmetros de cache dos assets foram atualizados para acompanhar essa versão.
