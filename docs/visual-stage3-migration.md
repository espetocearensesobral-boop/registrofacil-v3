# Etapa 3 — Migração visual intermediária

## Escopo executado

A primeira rodada da migração foi aplicada sem alterar a lógica de negócio. O contrato semântico foi adicionado aos seis temas em `color-themes.css`, e `visual-system.css` passou a consumir esses tokens em superfícies, sidebar, botões, formulários, tabelas, modais, alertas, feedback, notificações, atualização do sistema e foco.

A sidebar agora utiliza `--rf-sidebar-surface`, `--rf-sidebar-hover`, `--rf-sidebar-active`, `--rf-sidebar-text` e `--rf-sidebar-active-text`. O corpo, cards, navbar, campos, tabelas e modais utilizam tokens de superfície e borda. Os estados de sucesso, perigo, aviso e informação também foram convertidos para tokens semânticos.

A camada de autenticação recebeu uma compatibilidade semântica compartilhada no final de `palette03-final.css`, permitindo que login, criação de usuário, recuperação e redefinição de senha recebam os tokens do tema selecionado. A migração definitiva dos estilos inline dessas telas permanece como uma tarefa explícita da próxima rodada.

## Validação

| Verificação | Resultado |
|---|---|
| Validador semântico | Aprovado: seis temas e 50 tokens exigidos. |
| Suíte automatizada | 60 testes aprovados. |
| `git diff --check` | Aprovado. |
| Blocos de temas | Seis blocos individuais presentes; há também dois seletores agrupados de aliases. |
| `visual-system.css` | 13 valores hex restantes, concentrados em regras ainda não migradas. |
| `palette03-final.css` | 30 valores hex restantes na camada de compatibilidade. |
| `!important` | 706 ocorrências; o número subiu temporariamente porque a camada final ainda vence estilos inline durante a absorção. |

## Pendências controladas

A rodada não removeu `palette03-final.css`, `theme.css` ou `themes.css`. Também não removeu todos os estilos inline nem os `!important` de compatibilidade. Esses arquivos continuam congelados como camadas legadas para evitar regressões durante a migração. A próxima subetapa deverá eliminar progressivamente os estilos inline de autenticação, navbar e componentes prioritários, permitindo reduzir a especificidade sem perder contraste.

O aumento temporário de `!important` é conhecido e não deve ser interpretado como resultado final. O critério de encerramento da Etapa 3 será uma redução líquida após a retirada dos blocos legados equivalentes e a validação das seis paletas.
