# RegistroFácil 3.28.58

## Resumo

A versão 3.28.58 promove o redesign completo da interface do RegistroFácil para todas as superfícies HTML do projeto, mantendo rotas, permissões, formulários, integrações JavaScript e o sistema de temas existentes.

## Destaques

A interface autenticada recebeu uma camada visual transversal para shell, navegação, cards, tabelas, filtros, formulários, KPIs, modais, estados vazios, detalhes e responsividade. As telas de backup, métricas, perfil, atividades, auditoria, titulares e apresentantes também receberam refatorações específicas de markup e acessibilidade.

As tabs de métricas e configurações agora expõem estados e relações com atributos ARIA. As listas de titulares e apresentantes usam links reais para ordenação, captions acessíveis e ações nomeadas. As tabelas administrativas e de cadastros se adaptam a cartões legíveis em telas menores. A documentação standalone também foi alinhada à identidade visual e passou a exibir a versão atual.

## Compatibilidade e validação

Nenhum endpoint ou contrato de formulário foi alterado. A versão foi sincronizada em `config.py`, no script do instalador Windows, nos testes de atualização e na documentação standalone. A validação final compilou 49 templates Jinja sem erros e executou 129 testes automatizados com sucesso.

## Referências

[1]: https://github.com/espetocearensesobral-boop/registrofacil-v3 "Repositório RegistroFácil v3"
