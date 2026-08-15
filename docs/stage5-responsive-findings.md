# Etapa 5 — Achados de validação responsiva

A tela pública de login foi validada no servidor atualizado da versão 3.19.0. O DOM recebeu `data-cor="paleta-01"`, a versão exibida foi `v3.19.0` e os estilos computados confirmaram Source Sans 3, fundo `#F5F2EA`, texto primário `#1D1B18`, botão primário `#0F2A43` e label secundário `#6B665C`.

A revisão corrigiu o contraste que inicialmente deixava o título e os textos da autenticação claros demais sobre a superfície clara. A correção utilizou tokens semânticos e seletores públicos com especificidade controlada, sem recuperar cores fixas da Paleta 03.

Na responsividade, a sidebar mobile passou a usar `--rf-sidebar-width` em vez de 230px fixos. O drawer permanece com um único fluxo de abertura pelo `#mobile-menu-btn`; o hamburger legado interno da sidebar fica oculto no breakpoint mobile. O botão mobile foi ampliado para 44px, e tabelas passaram a manter área de rolagem horizontal e altura de toque adequada.

KPIs, cards, filtros e grids receberam `min-width: 0`, espaçamento responsivo e empilhamento em telas estreitas. A fonte mínima de badges e tabelas foi elevada para o contrato semântico, evitando os 11–11,5px identificados no baseline.
