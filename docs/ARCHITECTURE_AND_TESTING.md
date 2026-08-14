# Arquitetura e testes do RegistroFácil

## Visão geral

A camada de dados foi dividida no pacote `data/`, mantendo `models.py` como uma fachada de compatibilidade. As rotas existentes continuam importando símbolos legados sem conhecer a organização interna dos módulos.

| Componente | Responsabilidade |
| --- | --- |
| `models.py` | Reexporta funções e símbolos públicos para preservar imports existentes. |
| `data/schema.py` | Cria e verifica tabelas, índices, dados iniciais e campos de segurança. |
| `data/migrations.py` | Executa migrações versionadas do SQLite. |
| `data/database.py` | Centraliza conexões e execução de consultas. |
| `data/users.py` | Usuários, login, sessões, tokens e auditoria relacionada. |
| `data/processes.py` | Operações de processos e vínculos de domínio. |
| `data/representatives.py` | CRUD de representantes e associações com processos. |
| `routes/` | Camada HTTP, autenticação, autorização e renderização. |
| `tests/` | Testes de domínio e testes HTTP com banco temporário. |

## Compatibilidade

Novos módulos devem ser importados diretamente dentro da camada de dados. Código de rota ou integração externa que ainda usa `models.py` pode continuar usando a fachada, evitando uma migração simultânea e reduzindo o risco de regressão.

A consulta de autenticação retorna `must_change_password` junto com os dados do usuário. Assim, o login consegue marcar `force_password_change` na sessão quando a conta inicial ou uma conta recém-resetada exige alteração de senha.

## Segurança operacional

Em produção, defina `REGISTROFACIL_ENV=production`, `INITIAL_ADMIN_PASSWORD` durante a primeira inicialização e uma `SECRET_KEY` persistente gerenciada pelo ambiente. Os cookies de sessão usam `HttpOnly`, `SameSite=Lax` e `Secure` por padrão em produção. `TRUST_PROXY_HEADERS` só deve ser habilitado quando a aplicação estiver atrás de um proxy reverso confiável que realmente remova ou reescreva os cabeçalhos encaminhados.

A aplicação não deve ser exposta diretamente à Internet sem TLS no proxy reverso. O proxy deve terminar HTTPS, encaminhar somente os cabeçalhos necessários e restringir o acesso ao servidor Flask. A flag `SESSION_COOKIE_SECURE` exige que o navegador receba a aplicação por HTTPS.

## Instalação e testes

Crie um ambiente virtual, instale as dependências do projeto e execute a suíte a partir da raiz:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

Os testes HTTP usam um banco SQLite temporário e desabilitam o scheduler real. A cobertura inclui redirecionamento de usuários anônimos, validação CSRF, login, troca obrigatória de senha, invalidação de sessão após novo login e bloqueio de usuários comuns em rotas administrativas.

Para executar apenas os testes HTTP:

```bash
python -m pytest tests/test_http_auth.py tests/test_http_authorization.py -q
```
