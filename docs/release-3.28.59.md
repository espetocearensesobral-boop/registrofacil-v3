# RegistroFácil 3.28.59

## Correções de segurança e integridade

Esta versão remove documentos de processos do estado versionado, impede novos uploads de runtime no Git, restringe as permissões dos segredos persistentes, exige configuração de produção explícita e adiciona headers HTTP de hardening. Também aplica autorização granular ao dashboard, às APIs analíticas e à busca AJAX de apresentantes.

A validação de backups agora compara tamanho e SHA-256 de cada entrada declarada, rejeita arquivos não declarados no manifesto e mantém os logs no ciclo de promoção e rollback quando o diretório é fornecido. O limite de tentativas de login passou a considerar IP e identidade com hash, sem armazenar o nome de usuário em claro na tabela de tentativas.

## Correções funcionais e frontend

O cadastro de apresentantes deixou de usar `executar_query` como context manager. Os listeners JavaScript duplicados e inválidos dos formulários de processo foram removidos, os templates passaram a construir autocomplete e prévia de arquivos com `textContent`, e os KPIs foram alinhados aos seletores CSS ativos.

O contrato de ordem e capitalização do dashboard foi atualizado para refletir a interface vigente, eliminando a falha do pipeline. Mensagens de exceção internas também deixaram de ser devolvidas diretamente nas principais rotas administrativas.

## Dependências

As dependências de runtime foram atualizadas para releases sem vulnerabilidades conhecidas segundo a auditoria executada em 25 de agosto de 2026. A instalação foi validada em ambiente virtual limpo com `pip check` sem conflitos.

## Validação

A suíte completa de testes passou no ambiente virtual com dependências finais. Também passaram a compilação Python, o lint de interface, a verificação de temas, o contrato de release Windows, os smoke tests de importação e os testes direcionados de autorização, backup, headers, login e dashboard.

> A limpeza do histórico Git dos documentos que já foram publicados em commits anteriores requer um procedimento separado e deliberadamente não destrutivo. Esta versão remove os arquivos do estado atual e impede reincidência; a reescrita do histórico não foi executada automaticamente.
