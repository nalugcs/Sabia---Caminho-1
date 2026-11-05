# Relatório de QA — Sabiá

**Data:** 2026-11-05 · **Alvo:** `http://127.0.0.1:8000` · **Modo:** local, Playwright +
Chrome headless, viewport 390 × 844.

## Veredito

**Score: 4/5** (local). O fluxo principal passa sem erros; o QA em nuvem não pôde ser
executado porque a conta do Browser Use retornou **402 Payment Required**.

## Escopo testado

1. Consentimento carrega e o TCLE abre.
2. Cadastro com nome, idade, nível, idioma e interesse → dashboard.
3. Código pessoal visível.
4. Lição abre com objetivo, conteúdo, texto de apoio e mensagem inicial.
5. **Prática:** clique em alternativa, correção na hora e explicação.
6. Turno envia, recebe correção/nota e renderiza no chat.
7. Encerrar lição → feedback final com nota.
8. Micro-avaliação salva.
9. Admin: login por senha, painel e exportação CSV.
10. Borda: menor de 18 bloqueado (validação nativa + servidor).

## Resultado

- **16/16 verificações OK.**
- **0 erros de console** e **0 respostas HTTP ≥ 400** no fluxo.
- Export CSV baixa e **não contém nome/sobrenome**.
- A faixa 3D renderiza (WebGL2) sem erro de console e respeita reduced motion.

## Problemas encontrados e corrigidos

| Problema | Correção |
|---|---|
| Os 120 exercícios não apareciam na lição | Seção **Prática** + API `/api/exercicio` + registro em `exerciseattempt` |
| O gabarito era sempre a 1ª opção | Opções embaralhadas por sessão |
| Feedback final mostrava Markdown cru | Markdown + bleach + CSS de leitura |
| `favicon.ico` 404 | Favicon SVG próprio |
| Rótulo `EN` em vez de “Inglês” | Nome vindo do catálogo |
| Idade dependia só do navegador | Teste com `noValidate` confirma o bloqueio no servidor |

## Evidências

- `docs/qa/01-consentimento.png` a `09-menor.png` e `04b-pratica.png`
- `docs/qa/hero-desktop.png` e `hero-mobile.png` (3D)
- `docs/qa/relatorio.json`
- Script reproduzível: `scripts/qa_local.py`

## Não coberto

- QA em navegador de nuvem (bloqueado por cobrança da conta Browser Use).
- Fluxo de questionário após 3 sessões no navegador (coberto por teste de integração).
- LLM real: o QA usou `mock`; a chave OpenAI/Gemini ainda não foi exercitada.
- Carga/concorrência com 100 participantes.
- Leitores de tela e auditoria formal de acessibilidade.

## Por que 4 e não 5

O fluxo local está limpo, mas faltam o teste em nuvem, o LLM real e o questionário
completo no navegador. Assim que esses três forem exercitados, sobe para 5.

## Produção — 2026-11-05

**URL:** <https://sabia-1gv2.onrender.com> · **Plano:** Render free · **Branch:** `Estudos`

**Resultado final: 16/16 PASS** (`docs/qa-prod6/relatorio.json`).

- Health `200`; HTTPS/HSTS/CSP/cookies `Secure`; identidade v0.2 no ar.
- Consentimento, cadastro, dashboard, lição, prática, turno real, feedback, micro,
  admin pelo navegador, export, bloqueio de menor, console e HTTP: todos OK.
- Exports `participantes.csv` e `exercicios.csv` sem nomes/sobrenomes.
- Causa do admin: o `ADMIN_PASSWORD` do Render estava com newline invisível; foi
  recriado digitando e o login passou.
- Banco: ~9 participantes de teste. Antes do piloto, usar um banco novo (Neon) ou
  truncar as tabelas.
- Free: o web service hiberna; primeiro acesso pode levar ~30 s.
