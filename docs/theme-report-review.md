# Auditoria do relatório cromático das seis paletas

## Síntese

O relatório apresenta boas recomendações de harmonia cromática, mas algumas conclusões de contraste e algumas cores descritas não correspondem aos tokens publicados na release atual. A análise foi feita sobre `static/css/color-themes.css`, que permanece como fonte de verdade dos seis temas.

| Tema | Estado real | Recomendação |
|---|---|---|
| Paleta 01 | Equilibrada; primária sobre fundo = 13,10:1 e texto secundário = 5,10:1 | Manter |
| Paleta 02 | Terracota com contraste de 3,63:1 sobre o fundo; adequada para grandes elementos, não para texto pequeno | Avaliar `#B87A5A` ou usar terracota apenas como fundo/contorno |
| Paleta 03 | Vinho `#7A1F2B` tem 10,20:1 sobre branco; a afirmação de aproximadamente 4:1 está incorreta | Não clarear automaticamente; validar uso em botões e estados |
| Paleta 04 | Sidebar preta tem 21:1 com texto branco; azul ardósia e cinza devem ser avaliados por hierarquia, não por contraste básico | Ajuste visual opcional, sem urgência de acessibilidade |
| Paleta 05 | Sidebar publicada é `#F1F4F3`, texto `#274C5E`, contraste 8,32:1 | A correção proposta para a sidebar já está aplicada |
| Paleta 06 | Tema atual é azul-petróleo com dourado; primária sobre fundo = 9,31:1 | Ajustes de diferenciação podem ser feitos sem substituir a identidade |

## Verificações de contraste

A auditoria computou os pares principais pela fórmula WCAG 2.x. Os resultados relevantes foram: `#7A1F2B` sobre branco = **10,20:1**; `#C1663E` sobre o fundo da Paleta 02 = **3,63:1**; `#7C693C` sobre o fundo da Paleta 06 = **4,73:1**; `#738291` sobre `#2B2B2E` = **3,58:1**; e `#6B665C` sobre o marfim da Paleta 01 = **5,10:1**.

> O contraste deve ser avaliado pelo par real de foreground e background e pelo tamanho/peso do texto. Uma cor pode funcionar como destaque, borda ou superfície sem funcionar como texto pequeno.

A observação do relatório de que o vinho da Paleta 03 teria aproximadamente 4:1 com texto branco não se confirma: o par apresenta 10,20:1. Já a preocupação com a terracota da Paleta 02 é válida para textos pequenos, pois o par medido fica abaixo de 4,5:1.

## Riscos de aplicar todas as sugestões automaticamente

A implementação não possui cinco slots genéricos por tema. Cada cor ocupa papéis semânticos diferentes: primária, hover, ação escura, destaque, fundo, sidebar, texto, bordas e estados de feedback. Portanto, “adicionar uma quinta cor” não pode ser feito sem definir qual token ela substituirá ou qual novo papel semântico receberá.

Além disso, alterar `--color-gold-primary`, `--color-primary` ou `--sidebar` afeta botões, links, badges, estados ativos, modais e páginas públicas. A Paleta 05 já recebeu uma correção específica para evitar branco absoluto na sidebar. A Paleta 01 é o padrão institucional e deve permanecer estável salvo decisão explícita.

## Recomendação

A recomendação segura é executar uma etapa de harmonização controlada, sem alterar imediatamente todos os hexadecimais sugeridos. O primeiro grupo deve tratar apenas tokens com problema objetivo de contraste ou diferenciação: a terracota da Paleta 02 para textos pequenos, a diferenciação dos azuis próximos das Paletas 05 e 06 e a verificação de estados de hover da Paleta 04.

A Paleta 03 não deve ter o vinho clareado com base na justificativa de contraste apresentada, pois a métrica está incorreta. Se houver interesse estético em `#9B2D3C`, isso deve ser tratado como decisão de identidade visual e validado em botões, links, badges, feedback e dark mode.

A proposta “Papel Cartório” pode ser incorporada como uma **variação futura** ou como revisão da Paleta 01, mas não deve ser adicionada como sétimo tema sem revisar o contrato de seis temas, preferências persistidas, validação de tokens e interface de seleção.

## Estado da análise

Nenhuma alteração de cor foi aplicada. A release publicada permanece no commit `4f30b5d`. A auditoria reproduzível está em `docs/theme-report-contrast-audit.txt`; o script usado para os cálculos está em `tools/audit_theme_contrast.py` e deve ser removido ou convertido em ferramenta permanente somente após decisão sobre a próxima etapa.
