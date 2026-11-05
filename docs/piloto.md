# Piloto — 3 a 5 pessoas

Objetivo: descobrir fricção de onboarding, clareza do feedback, uso da prática e
estabilidade **antes** de abrir para ~100 participantes.

## Fase 0 — testar o LLM real (antes do piloto)

1. Pegue a chave do provedor (OpenAI ou Gemini).
2. Rode o teste de fumaça:

```bash
cd tcc-ana/app
LLM_PROVIDER=openai \
LLM_BASE_URL=https://api.openai.com/v1 \
LLM_API_KEY="sua-chave" \
LLM_MODEL="seu-modelo" \
.venv/bin/python scripts/check_llm.py
```

3. O script precisa dizer **JSON válido**, com latência e os campos `resposta`,
   `correcao`, `explicacao`, `nota`, `proximo_passo`, `erros`.
4. Suba o app com o provedor real:

```bash
LLM_PROVIDER=openai LLM_API_KEY=... LLM_MODEL=... \
  .venv/bin/python -m uvicorn app.main:app --port 8000
```

5. Faça uma lição inteira (3 turnos + 1 exercício) e 10 turnos variados. Anote latência
   e qualidade em `docs/piloto-observacoes.md`.

Critério: p95 ≤ 8 s por turno; feedback compreensível; sem resposta vazia.

## Fase 1 — sessão com 3 a 5 pessoas

**Duração:** 30–40 min por pessoa · **Formato:** presencial ou videochamada com
compartilhamento de tela · **Participantes:** maiores de 18, com TCLE.

### Roteiro

1. **Boas-vindas (2 min).** Explique que não é prova, que pode falar em voz alta o que
   está pensando e que pode parar.
2. **Consentimento (2 min).** Leia o TCLE, registre o aceite. Peça autorização separada
   se for gravar áudio/tela.
3. **Cadastro (5 min).** Peça para se cadastrar sem ajuda. Observe onde trava: idade,
   nível, escolha de idioma, código pessoal.
4. **Primeira lição (10 min).** Faça 3 turnos de conversa e **um exercício da seção
   Prática**. Observe se entende a correção e o botão “Encerrar lição”.
5. **Feedback (3 min).** Encerre, leia o feedback e responda a micro-avaliação.
6. **Debrief (10 min).** Perguntas:
   - O que foi mais fácil e mais confuso no começo?
   - A correção te ajudou a entender o erro? Por quê?
   - O nível da lição pareceu adequado?
   - Você usaria isso de novo? O que faria você desistir?
   - A conversa pareceu real?
   - Algo quebrou, demorou ou pareceu estranho no celular?
7. **Admin (2 min).** Exporte `participantes.csv`, `turnos.csv` e `exercicios.csv`;
   confira se não há nome/sobrenome.

### O que observar

| Dimensão | Sinais |
|---|---|
| Onboarding | dúvidas no TCLE, idade, nível, idioma, código |
| Compreensão | lê a instrução? entende onde escrever? acha a prática? |
| Feedback | entende o erro e o próximo passo? |
| Nível | acha fácil/difícil demais? |
| Conversa | respostas parecem naturais? latência incomoda? |
| Dispositivo | teclado cobre o campo? botão fora da tela? |
| Erros | 4xx/5xx, console, resposta vazia, travamento |

### Registro de bug

```
Data:
Participante (código):
Passo:
Esperado:
Ocorrido:
Severidade: bloqueia / atrapalha / cosmético
Evidência: print ou vídeo
```

### Critérios de sucesso do piloto

- 5/5 concluem cadastro sem ajuda.
- 4/5 concluem uma lição + um exercício + feedback.
- Nenhum erro bloqueante.
- Feedback final compreendido por pelo menos 4/5.
- Se aplicar SUS: ≥ 70 (com 3–5 pessoas é indicativo, não estatística).

### Dados e ética

- Use os códigos, não os nomes, nos registros.
- Guarde os consentimentos à parte; apague os dados do piloto depois da análise, se
  combinado no TCLE.
- Não grave tela/áudio sem autorização explícita.

## Depois do piloto

1. Triagem dos bugs por severidade.
2. Corrigir bloqueantes e repetir com 2 pessoas.
3. Ajustar prompts/feedback se a compreensão falhar.
4. Só então abrir para os ~100.

## Publicar temporariamente para o piloto remoto

Se o deploy ainda não estiver no ar, exponha o servidor local só durante a sessão:

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Envie o link `https://...trycloudflare.com` para o participante. Encerre o túnel ao
terminar. Isso serve para 3–5 pessoas; para ~100, use Render/Neon.
