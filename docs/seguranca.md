# Segurança e postura defensiva — Sabiá

Documento vivo. Toda mudança de superfície (rota, formulário, integração) deve atualizar
esta página e os testes correspondentes.

## 1. Ativos

| Ativo | Sensibilidade |
|---|---|
| Nome, sobrenome, idade, nível, interesses | dados pessoais (LGPD) |
| Turnos, notas, erros, feedback | dados de pesquisa |
| Código do participante | credencial de acesso (sem senha) |
| `APP_SECRET`, `ADMIN_PASSWORD`, `LLM_API_KEY` | segredos |
| Disponibilidade do app durante a coleta | crítica para o TCC |

## 2. Atores e superfícies

- **Visitante** — TCLE, cadastro, entrada por código.
- **Participante** — dashboard, lições, questionário.
- **Pesquisadora (admin)** — painel e exportações.
- **Provedor de LLM** — recebe o texto do turno (não recebe nome/idade).
- **Atacante externo** — formulários, APIs JSON, enumeração de código, admin.

## 3. Ameaças e controles

| Ameaça | Vetor | Controle implementado |
|---|---|---|
| Enumeração de códigos | `/entrar` | código de 6 caracteres (32^6 ≈ 1 bilhão), rate limit 8/min por IP, evento `auth_failed` |
| Força bruta no admin | `/admin/entrar` | rate limit 6/min, comparação em tempo constante, cookie de 8 h |
| CSRF | formulários e APIs | token double-submit (cookie + campo/header), `SameSite=Lax`, header `X-CSRF-Token` nas chamadas JS |
| XSS | conteúdo do LLM e campos | autoescape do Jinja, renderização via `textContent`, CSP restritiva |
| Injeção de prompt | mensagem do aluno | instruções delimitadas no system prompt, saída em JSON validado, modelo não executa ferramentas |
| SQL injection | filtros e cadastro | SQLModel/SQLAlchemy com parâmetros |
| Vazamento em exportação | CSV do admin | exige login, usa apenas `code` (sem nome/sobrenome) |
| Sequestro de sessão | cookie `pid` | assinado, `HttpOnly`, `SameSite=Lax`, `Secure` em produção |
| DoS simples | endpoints caros | rate limit por IP em turno, encerramento, micro e cadastro |
| Exposição de segredos | repositório/logs | tudo por ambiente, `.env` no `.gitignore`, nenhuma chave logada |
| Clickjacking | iframe | `X-Frame-Options: DENY` + `frame-ancestors 'none'` |

### Cabeçalhos enviados

`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
`Referrer-Policy: no-referrer`, `Permissions-Policy`, `Cross-Origin-Opener-Policy` e,
com HTTPS, `Strict-Transport-Security`.

### Cookies

- `pid` (participante): assinado, `HttpOnly`, `SameSite=Lax`, 180 dias, `Secure` quando
  `APP_COOKIE_SECURE=1`.
- `admin`: assinado, `HttpOnly`, `SameSite=Strict`, 8 horas.
- `csrf`: token aleatório de 32 bytes, `HttpOnly`, 6 horas.

## 4. LGPD

- Consentimento versionado (`tcle_version`) e registrado com data.
- Minimização: só o necessário para a pesquisa.
- Exportações pseudonimizadas (código, não nome).
- **Pendente:** rotina de exclusão a pedido e política de retenção formal.
- Dados de pesquisa não devem ser usados para outras finalidades.

## 5. Riscos residuais (conhecidos)

- Admin usa fator único (senha); recomendável 2FA ou VPN em produção.
- Sem WAF/CDN; rate limit é em memória (uma instância).
- Injeção de prompt não é 100% eliminável; o modelo só produz texto, não executa ações.
- Sem backup automatizado ainda.
- SQLite não escala para muitas escritas concorrentes; Postgres antes do piloto grande.
- Dependências ainda não passaram por `pip-audit`/SCA no CI.

## 6. Resposta a incidente

1. Conter: desativar admin (remover `ADMIN_PASSWORD`), trocar `APP_SECRET` (invalida
   sessões) e rotacionar `LLM_API_KEY`.
2. Avaliar: exportar `eventos` e `turnos` para identificar escopo.
3. Corrigir e testar: adicionar caso em `tests/` e entrada em `docs/licoes-aprendidas.md`.
4. Comunicar: orientador e, se houver dado pessoal exposto, participantes afetados.
5. Registrar: data, causa raiz, prevenção.

## 7. Checklist antes do deploy

- [ ] `APP_SECRET` aleatório com 32+ caracteres.
- [ ] `ADMIN_PASSWORD` forte e fora do código.
- [ ] `APP_COOKIE_SECURE=1` e HTTPS.
- [ ] `RATE_LIMIT_ENABLED=1`.
- [ ] Postgres com backup diário.
- [ ] Migrações (Alembic) antes de subir schema.
- [ ] `pip-audit` sem vulnerabilidades críticas.
- [ ] Testar CSRF, headers e exportação em produção.
