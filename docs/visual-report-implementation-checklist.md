# Checklist de implementação do relatório visual

## Objetivo

Aplicar as correções visuais em etapas verificáveis, preservando os seis temas, o contraste, a responsividade e a suíte automatizada.

## Etapas

| Etapa | Escopo | Critério de aceite |
|---|---|---|
| 1 | Consolidar inventário e localizar hardcodes | Todos os arquivos e seletores-alvo registrados |
| 2 | Bordas, raios e sombras | Raios estruturais usam tokens; sombras possuem níveis xs/sm/md/lg/xl |
| 3 | Cores hardcoded e superfícies | Hovers, upload e superfícies usam tokens semânticos |
| 4 | Estados e hierarquia dos botões | Primário, secundário, terciário, destrutivo, foco, ativo e disabled definidos |
| 5 | Inputs e acessibilidade | Hover, foco, válido, inválido e disabled verificáveis |
| 6 | Microinterações | Fade, skeleton e transições respeitam prefers-reduced-motion |
| 7 | Validação | Seis temas, contraste, JavaScript, testes e diff aprovados |
| 8 | Publicação | Commit, push e árvore limpa em main |

## Checklist detalhado

- [ ] Localizar e substituir raios hardcoded em `processos.css`, `main.css`, templates e estilos locais.
- [ ] Localizar e substituir sombras hardcoded por tokens semânticos.
- [ ] Criar os cinco níveis de sombra: xs, sm, md, lg e xl.
- [ ] Substituir cores hardcoded em hover de filtros, limpeza e upload.
- [ ] Padronizar superfícies de upload e áreas de ação.
- [ ] Completar estados dos botões: normal, hover, active, focus-visible e disabled.
- [ ] Preservar a separação entre ações primárias, secundárias e destrutivas.
- [ ] Revisar focus ring em links, botões, inputs, selects e controles de navegação.
- [ ] Implementar estados visuais `.is-valid` e `.is-invalid` nos campos.
- [ ] Adicionar microinterações discretas com redução de movimento respeitada.
- [ ] Definir skeleton reutilizável sem substituir spinners existentes até validação visual.
- [ ] Atualizar documentação do sistema visual.
- [ ] Validar cada etapa antes de avançar.

## Regra de segurança

Nenhum efeito será aplicado por override indiscriminado quando houver uma classe semântica ou regra local identificável. Cada alteração deverá apontar para um seletor e um arquivo de origem.
