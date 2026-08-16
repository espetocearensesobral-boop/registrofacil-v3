# Onda de harmonização cromática

## Escopo

A primeira alteração foi aplicada somente à Paleta 02, mantendo o contrato de seis temas, a preferência persistida do usuário e o dark mode. As Paletas 05 e 06 foram auditadas e não receberam substituições porque seus tokens reais já possuem hierarquia suficiente entre primária, hover e sidebar.

| Token | Antes | Depois | Justificativa |
|---|---|---|---|
| Paleta 02 `--color-gold-primary` | `#C1663E` | `#A85C3A` | Terracota menos saturada e mais adequada para UI densa. |
| Paleta 02 `--color-gold-dark` | `#9C4322` | `#7F4029` | Hover mais profundo, mantendo a leitura do texto branco. |

## Contraste

O contraste de texto branco sobre o acento da Paleta 02 passou de **4,01:1** para **4,93:1**. A mudança supera o limiar AA usual para texto normal e preserva o papel do acento em botões, badges e destaques.

A auditoria também confirmou que o vinho `#7A1F2B` da Paleta 03 apresenta 10,20:1 sobre branco, portanto não foi clareado. A sidebar da Paleta 05 continua com `#F1F4F3` e texto `#274C5E`, e a Paleta 06 continua com primária e hover visualmente diferenciados.

## Validação

A validação semântica confirmou 6 temas e 50 tokens obrigatórios. A suíte terminou com 60 testes passando. Os módulos JavaScript de tema e acessibilidade passaram na checagem sintática, e `git diff --check` não encontrou problemas.

## Estado

A alteração está apenas na árvore local e ainda não foi commitada, publicada ou mesclada. Os relatórios de contraste reproduzível estão em `docs/theme-wave-final-contrast.txt` e `docs/theme-wave-palette02-validation.txt`. O script de auditoria está em `tools/audit_theme_contrast.py`.
