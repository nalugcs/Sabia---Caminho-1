# Lições aprendidas — Sabiá / TCC Ana

Registro de erros que já custaram tempo, para não repetirem. **Toda entrada precisa de
uma prevenção verificável** (teste, regra no AGENTS.md, validação automática ou mudança
de processo).

Modelo:

```
## AAAA-MM-DD — título curto
**Onde:** arquivo/rota/ambiente
**Sintoma:** o que se viu
**Causa raiz:** por que aconteceu
**Correção:** o que foi feito
**Prevenção:** teste/regra que impede a repetição
**Status:** resolvido | mitigado | aberto
```

---

## 2026-11-04 — Python do runtime bloqueia extensões nativas

**Onde:** `.venv` criado com o Python do DSH.
**Sintoma:** `ImportError` ao carregar `pydantic_core` ("different Team IDs").
**Causa raiz:** o Python do runtime é assinado com hardened runtime e recusa `.so` de
terceiros com assinatura diferente.
**Correção:** usar Python 3.12 gerenciado pelo `uv` em `.uv-python` e recriar a venv.
**Prevenção:** README e skill `tcc-app` documentam o comando; validar com
`python -c "import pydantic"` antes de instalar dependências.
**Status:** resolvido.

## 2026-11-04 — Datetime sem timezone no SQLModel

**Onde:** `models.py` e rotas de cadastro/encerramento.
**Sintoma:** `ValueError: Datetime values must have timezone information`.
**Causa raiz:** `datetime.utcnow()` gera valor naive; o SQLModel exige aware.
**Correção:** `datetime.now(timezone.utc)` em todos os campos e rotas.
**Prevenção:** teste de cadastro e de encerramento cobre a gravação.
**Status:** resolvido.

## 2026-11-04 — Formulário de teste chegando vazio

**Onde:** `tests/test_flow.py` com `TestClient`.
**Sintoma:** todos os campos vazios e erro "aceite obrigatório".
**Causa raiz:** `data` como lista de tuplas não foi codificado como formulário pelo
httpx; o corpo chegou vazio.
**Correção:** enviar `dict` (com listas para campos múltiplos).
**Prevenção:** o teste de cadastro falha se os campos não chegarem.
**Status:** resolvido.

## 2026-11-04 — Screenshot mobile cortado e esmaecido

**Onde:** captura com Chrome headless.
**Sintoma:** layout cortado à direita e tudo com baixa opacidade.
**Causa raiz:** Chrome headless impõe viewport mínimo de 500 px (não 430) e a captura
aconteceu no meio da animação de entrada.
**Correção:** capturar em 500 px e com `--force-prefers-reduced-motion`.
**Prevenção:** não diagnosticar layout mobile por screenshot de 430 px; usar 500 px,
Playwright ou device emulation de verdade.
**Status:** resolvido.

## 2026-11-04 — Skill de design que era API paga

**Onde:** `design-mobile-apps` (designed-by-ai/skills).
**Sintoma:** a skill exige `SLEEK_API_KEY` e consome créditos do serviço Sleek.
**Causa raiz:** o nome sugere "guia de design", mas é um wrapper de API comercial.
**Correção:** não instalar; usar `frontend-design` + CSS próprio.
**Prevenção:** ler o `SKILL.md` e as dependências antes de instalar qualquer skill.
**Status:** resolvido.

## 2026-11-04 — Busca recursiva dentro da venv

**Onde:** `grep -rn` na raiz do app.
**Sintoma:** comando pendurado por minutos.
**Causa raiz:** a varredura entrou em `.venv`, `.uv-cache` e `.uv-python`.
**Correção:** buscar só em `app/`, `tests/` e `docs/`, ou usar a ferramenta de grep.
**Prevenção:** nunca rodar busca recursiva ampla na raiz; excluir ambientes.
**Status:** resolvido.

## 2026-11-04 — Mudança de schema sem migração

**Onde:** coluna `session_id` em `feedbackresponse`.
**Sintoma:** banco de dev antigo continuou sem a coluna após o código mudar.
**Causa raiz:** `create_all` não altera tabelas existentes.
**Correção:** apagar `data/app.db` no dev e reiniciar.
**Prevenção:** em produção, usar migrações (Alembic) antes do deploy; no dev, documentar
o reset.
**Status:** mitigado (dev); aberto para produção.

## 2026-11-04 — Ordem de perguntas e respostas no chat

**Onde:** notebook original (`historico_aula` global).
**Sintoma:** mensagens fora de ordem e contexto misturado entre usuários.
**Causa raiz:** histórico global e sem separação por sessão/participante.
**Correção:** histórico por sessão no banco, ordenado por id; perfil persiste, conversa
não.
**Prevenção:** testes de turno garantem a ordem (abertura → aluno → assistente).
**Status:** resolvido.

## 2026-11-04 — Feedback final com Markdown cru

**Onde:** `/feedback/{id}` e `feedback.html`.
**Sintoma:** a tela mostrava `## Resumo` e `**negrito**` em vez de títulos e ênfase.
**Causa raiz:** o texto do LLM era Markdown, mas o template renderizava como texto puro.
**Correção:** `markdown` + `bleach` + CSS de leitura; rótulo do idioma vindo do catálogo.
**Prevenção:** teste `test_finish_and_feedback` exige `<h2>Resumo</h2>` e proíbe `##`;
teste de sanitização garante que `<script>` não passa.
**Status:** resolvido.

## 2026-11-04 — QA em nuvem sem créditos

**Onde:** skill `qa` + Browser Use.
**Sintoma:** `start_remote_daemon` retornou HTTP 402 Payment Required.
**Causa raiz:** conta autenticada, mas sem plano/créditos para criar navegador.
**Correção:** QA funcional local com Playwright, documentado como limitação.
**Prevenção:** checar `browser-harness auth status` e billing antes de prometer QA em
nuvem; nunca cair para o Chrome do usuário.
**Status:** mitigado (local); nuvem pendente.

## 2026-11-05 — Senha do admin com quebra de linha no Render

**Onde:** Render, variável `ADMIN_PASSWORD`.
**Sintoma:** a senha do `.env` funcionava local, mas em produção o `/admin` dizia
“Senha incorreta”. Teste via `curl` com o valor + `\n` retornou 303 e os exports 200.
**Causa raiz:** o segredo foi salvo com uma quebra de linha no fim; o input HTML remove
newlines, então o navegador nunca envia o valor exato que o servidor espera.
**Correção:** limpar o campo no Render, digitar/colar só a senha (sem newline), salvar e
reimplantar.
**Prevenção:** validar o login **no navegador**, não só por `curl`; ao cadastrar
segredo, limpar o campo e conferir; manter o teste de login no QA de produção.
**Status:** correção pendente no Render.
