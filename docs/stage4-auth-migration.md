# Etapa 4 — Autenticação e hardcodes prioritários

## Correções aplicadas

As telas públicas passaram a receber uma camada semântica compartilhada no final de `palette03-final.css`. Login, criação de usuário, recuperação de senha e redefinição agora utilizam o tema ativo para superfícies, textos, campos, foco, botões, alertas, links, logos e indicadores de versão.

A tipografia do layout autenticado foi alinhada ao contrato institucional, substituindo o import isolado de Inter por Source Sans 3, IBM Plex Mono e Fraunces. O `base.html` também deixou de importar Segoe UI e passou a usar o conjunto institucional.

A navbar teve seus estados primário, secundário, perigo e edição migrados para tokens semânticos. Foram removidos valores fixos de preto, cinza, vermelho e sombras de hover do bloco inline. O aviso de novos usuários, que possuía cores inline amarelas, foi transformado em `auth-notice auth-notice-warning`.

Os efeitos conflitantes de deslocamento, sombra e transformação permanecem desativados nos estados migrados. O foco utiliza o anel semântico e os estados públicos preservam contraste entre texto e superfície.

## Validação

| Verificação | Resultado |
|---|---|
| Compilação Python | Aprovada. |
| Validador semântico | Aprovado: seis temas e 50 tokens. |
| Suíte automatizada | 60 testes aprovados. |
| `git diff --check` | Aprovado. |
| Blocos de estilo inline nas quatro telas públicas | 1 ocorrência funcional restante, correspondente ao bloco estrutural compartilhado em uma tela. |
| Cores hex no `base.html` | 2 ocorrências residuais, fora das ações principais migradas. |
| Componente semântico de aviso | Aplicado ao cadastro de usuário. |

## Pendências controladas

Os blocos de estilo inline estruturais das telas públicas ainda serão extraídos para uma folha `auth.css` em uma rodada específica, pois possuem diferenças de layout entre login, cadastro, recuperação e redefinição. A camada semântica já garante o comportamento visual correto enquanto essa extração não ocorre.

A próxima etapa deve concentrar-se em responsividade, incluindo sidebar, hamburger único, breakpoints, tabelas, KPIs e validação nas cinco larguras definidas no plano.
