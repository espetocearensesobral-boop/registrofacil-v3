# Auditoria e Limpeza da Interface — 21 de agosto de 2026

## Escopo

Foi realizada uma revisão estática da camada de apresentação do Registro Fácil, abrangendo templates Jinja2, folhas CSS carregadas pelo `base.html`, scripts JavaScript, referências entre rotas e templates, links que abrem novas abas, handlers inline, classes legadas e contratos automatizados de regressão. A análise foi restrita a mudanças seguras: nenhuma regra de negócio, permissão, proteção CSRF, sessão, auditoria, API de notificações ou catálogo de temas foi removida.

| Superfície | Antes | Depois | Observação |
|---|---:|---:|---|
| Templates HTML | 54 | 48 | Seis duplicatas raiz sem referência ativa foram removidas. |
| Folhas CSS | 12 | 12 | Mantidas; somente blocos comprovadamente órfãos foram limpos. |
| Scripts JavaScript | 10 | 9 | `notifications.js` não era carregado nem referenciado pela interface atual. |
| Temas institucionais | 30 | 30 | Catálogo preservado integralmente. |
| Módulos importados no smoke test | — | 35 | Todos importados com sucesso. |

## Falhas corrigidas

### Links de relatório sem destino funcional

Os cinco modais de relatório das telas **Todos os Processos**, **Processos do Dia**, **Pendentes**, **Em Andamento** e **Meus Processos** continham links `href="#"`. Não havia JavaScript ativo atribuindo uma URL a esses links. O usuário podia abrir o modal, mas os comandos de PDF e impressão não executavam a operação correta.

Os links agora apontam diretamente para `processos.gerar_pdf_lista` e `processos.imprimir_lista`, preservando os parâmetros de pesquisa e enviando explicitamente o `view_mode` de cada tela. Foi criado um contrato de regressão para impedir o retorno de links vazios nesses cinco templates.

### Isolamento de novas abas

Foram corrigidos os links de PDF, WhatsApp, consulta de processo e impressão que abriam novas abas sem isolamento explícito. Os elementos agora usam `rel="noopener noreferrer"`; as chamadas `window.open` passaram a usar as opções `noopener,noreferrer`. Essa correção foi aplicada aos fluxos ativos de processos, titulares, apresentantes e atividades.

### Acessibilidade dos modais

Os botões de fechamento que ainda utilizavam `aria-label="Close"` foram padronizados para `aria-label="Fechar"`, mantendo o idioma da interface e melhorando a compreensão por leitores de tela.

### Resíduos de interface removidos

Foram eliminados os seletores CSS legados de Representantes, que não possuem mais telas ou componentes correspondentes. Também foi removido o bloco de estilos da antiga tela de dados da organização, substituída pela configuração integrada, além do seletor `rf-heading-icon`, que não aparece nos templates atuais.

Seis templates raiz duplicados foram removidos após confirmação de que as rotas renderizam somente os equivalentes atuais dentro de `templates/processos/` e de que a tela de estabelecimento foi incorporada a `configuracoes.html`:

```text
templates/todos.html
templates/visualizar.html
templates/em_andamento.html
templates/hoje.html
templates/pendentes.html
templates/empresa.html
```

O arquivo `static/js/notifications.js` também foi removido porque não era carregado por nenhum template nem referenciado por código ativo. As rotas backend de notificações foram preservadas, assim como o motor global de toasts usado pela aplicação.

## Decisões de preservação

Durante a auditoria, o bloco de filtros com classes `process-filter-*` foi identificado como ativo no include `templates/processos/_filter_toolbar.html`. Ele não foi removido, apesar de inicialmente parecer legado, porque é utilizado diretamente pelas cinco telas de processos. Essa verificação evitou uma limpeza destrutiva.

O link `btn-consultar-processo` do Histórico de Atividades também foi preservado. Embora comece com `href="#"` e fique oculto, o script inline atribui dinamicamente a URL de visualização quando o registro possui `processo_id`. Ele recebeu isolamento de nova aba e permaneceu coberto por contrato de teste.

## Validação realizada

| Verificação | Resultado |
|---|---|
| Validador de release Windows | Aprovado em `3.28.47`. |
| Lint visual | Aprovado. |
| Sincronização dos temas | Aprovada; 30 temas. |
| Tokens semânticos | Aprovados; 59 tokens obrigatórios. |
| Smoke test de importação | Aprovado; 35 módulos. |
| Suíte completa | Aprovada sem falhas; 121 testes coletados. |
| Contratos HTML/CSS/JS de limpeza | Aprovados. |
| `git diff --check` | Aprovado. |

## Resultado

A limpeza removeu duplicações comprovadamente órfãs, corrigiu operações de relatório que estavam sem destino, fortaleceu a abertura de novas abas, padronizou a acessibilidade dos modais e preservou os componentes ativos que poderiam ser confundidos com resíduos. O conjunto está pronto para commit e publicação após a última revisão do diff.
