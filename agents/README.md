# Agentes de revisão — Sabiá

Estes são os agentes **do projeto** (diferentes dos 3 subagentes efêmeros que geraram as
lições e do app em si, que não usa agentes em runtime). Eles servem para revisar as 60
lições atuais e qualquer conteúdo novo.

## Elenco

| Agente | Papel | Quando usar |
|---|---|---|
| `orchestrator` | Divide o lote, chama revisores, consolida | sempre |
| `technical-writer` | Clareza, consistência, PT-BR, formato | toda revisão |
| `pedagogical-reviewer` | Progressão, CEFR, carga cognitiva, exercícios | toda revisão |
| `language-specialist-en/es/fr` | Naturalidade e correção no idioma | por idioma |
| `source-checker` | Aponta afirmações que exigem fonte confiável | quando houver explicação gramatical |
| `assessment-reviewer` | Gabaritos, ambiguidade, opções | antes de publicar |

## Contrato de saída

Cada revisor devolve JSON:

```json
{
  "language": "Inglês",
  "issues": [
    {
      "lesson": 3,
      "field": "phrases|content|exercises|objective",
      "severity": "alta|media|baixa",
      "problem": "o que está errado",
      "fix": "correção sugerida",
      "source": "referência, se aplicável"
    }
  ],
  "summary": "2 a 5 frases",
  "human_review": "o que exige especialista humano"
}
```

O schema formal está em [`review-schema.json`](review-schema.json).

## Como rodar

**Agora (dentro do DSH):** os revisores foram executados como subagentes em paralelo,
um por idioma + um pedagógico. O resultado consolidado está em
`docs/revisao-licoes.md` e `.json`.

**Depois (com chave Gemini):**

```bash
cd tcc-ana/app
LLM_PROVIDER=openai LLM_API_KEY=... .venv/bin/python ../scripts/review_lessons.py
```

O script lê `agents/*.md`, envia cada idioma ao revisor especialista, consolida e grava
`docs/revisao-licoes.md`/`.json`.

## Regras

- Revisor de LLM é **triagem**, não substitui professor humano. O campo
  `human_review` existe para isso.
- Não inventar fontes. Se não tiver certeza, pedir verificação em Cambridge/RAE/
  Académie/Larousse.
- Nada é aplicado automaticamente: correções passam por revisão humana antes de entrar
  no JSON do app.
- Toda correção aplicada vira entrada em `docs/licoes-aprendidas.md` se tiver causado
  retrabalho.

## Rodada 1 — resultado (2026-11-05)

- 4 revisores, 64 achados brutos.
- 25 correções aplicadas em EN/ES/FR (gabaritos não únicos, regras falsas, traduções,
  elisão, textos de apoio).
- 3 correções de app: exercícios exibidos, opções embaralhadas, respostas gravadas.
- Relatório consolidado: `docs/revisao-licoes.md`; dados: `docs/revisao-licoes.json`.
- Pendente: revisão humana (professor nativo + CEFR) e calibragem da progressão 11–20.

## OpenAI

O `review_lessons.py` usa a interface OpenAI-compatible. Com a OpenAI disponível:

```bash
LLM_PROVIDER=openai \
LLM_BASE_URL=https://api.openai.com/v1 \
LLM_API_KEY=... \
LLM_MODEL=<modelo> \
.venv/bin/python ../scripts/review_lessons.py
```
