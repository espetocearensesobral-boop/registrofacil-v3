# Validação visual da presença de usuários

A prévia desktop da tela de Cópia de Segurança foi renderizada em 894x768. O botão **Usuários na rede** aparece alinhado no cabeçalho ao lado de **Configurar**. O modal abriu centralizado, com cantos suaves, resumo em três cards (Cadastrados, Online e Offline), lista rolável e ações de atualizar/fechar alinhadas no cabeçalho.

A mensagem `Unexpected token '<'` exibida dentro da prévia é esperada porque a página foi servida como HTML estático em um servidor temporário; a URL `/backup/users-presence` não existe nesse servidor de arquivos e devolve HTML 404 em vez de JSON. Em execução pela aplicação Flask, a URL é gerada para a rota real e o endpoint retorna JSON protegido por sessão administrativa.
## Validação com dados de presença

Com a resposta da API simulada somente na prévia estática, foram exibidos dois cards: um usuário Online com IP `192.168.0.10` e um usuário Offline com IP `192.168.0.21`, além dos contadores 2/1/1. Os nomes e metadados ficaram legíveis, e os estados Online/Offline receberam diferenciação visual.

Um modal global de atualização do sistema apareceu sobre a prévia porque o banco local de desenvolvimento mantinha um estado de atualização independente. Isso não pertence ao modal de presença; a suíte de testes usa banco temporário e confirmou a rota limpa. A validação visual do modal de presença foi feita antes dessa sobreposição e os cards permaneceram corretamente estruturados.
