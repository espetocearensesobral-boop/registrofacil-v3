# Auditoria visual final — Registro Fácil 3.24.8

## Escopo

A revisão cobriu o catálogo de 20 temas, tokens semânticos, superfícies, tipografia, formulários, botões, estados de foco/hover/active/disabled, feedbacks, telas de autenticação e resíduos de configuração do antigo modo escuro.

## Achados e correções

| Área | Achado | Correção |
|---|---|---|
| Catálogo de temas | O cabeçalho de `color-themes.css` ainda descrevia 15 temas e dark mode. | Atualizado para 20 temas e experiência clara de alto contraste. |
| Tipografia | `compact.css`, `main.css` e `processos.css` usavam aliases `--font-*` sem declaração consolidada. | Criados aliases compatíveis vinculados à escala `--rf-font-*`. |
| Cores estruturais | Tokens antigos `--color-gray-light`, `--color-gray-medium` e `--sidebar-header-height` eram consumidos sem contrato central. | Criados aliases semânticos compatíveis, preservando as folhas existentes. |
| Variáveis autorreferentes | O bloco final de `visual-system.css` redefinia tokens para si próprios, como `--color-error: var(--color-error)`, podendo invalidar valores computados. | Removidas as autorreferências; mantido somente `--color-black-premium` como alias seguro para a cor primária. |
| Modo escuro | Restavam seletores explícitos em logout e permissões. | Removidos, mantendo exclusivamente a experiência clara. |
| Permissões | A tela usava verde, amarelo e vermelho fixos fora do sistema de temas. | Substituídos por tokens semânticos de sucesso, aviso e erro. |
| Documentação interna | Havia referências a versões 3.18/3.4, seis temas e Paleta 03. | Comentários atualizados para a arquitetura vigente. |
| Cache | Os estilos estavam identificados como 3.24.7 antes da auditoria. | Cache-busting atualizado para 3.24.8 em `base.html` e `login.html`. |

## Resultado

A auditoria não encontrou resíduos ativos de `dark-mode`, `theme-toggle`, `data-bs-theme="dark"` ou `prefers-color-scheme: dark`. As referências históricas a quinze temas permanecem apenas na migração 011, onde são necessárias para documentar e atualizar bancos antigos; elas não representam opções ativas do catálogo.

A suíte de validação semântica confirmou **20 temas** e **50 tokens obrigatórios**. A compilação Python e os **60 testes automatizados** foram aprovados, sem alterações no contrato funcional do sistema.

## Release

A revisão foi versionada como **3.24.8**. O próximo passo é publicar o commit na branch `main` após a conferência do diff.
