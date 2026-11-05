# Revisão das 60 lições — rodada 1

**Data:** 2026-11-05 · **Escopo:** 3 idiomas × 20 lições · **Agentes:** especialista EN,
especialista ES, especialista FR, coordenação pedagógica/editorial (4 revisores em
paralelo). Total bruto: **64 achados**.

> Triagem feita por LLM com papéis definidos. **Não substitui professor nativo nem
> avaliador CEFR.** O que depende de julgamento humano está marcado no fim.

## O que estava crítico (e foi corrigido)

| Problema | Impacto | Correção |
|---|---|---|
| Os 120 exercícios não apareciam na lição | O banco não era aplicado; a avaliação ficava só no chat | Seção **Prática** na lição, com correção e explicação; respostas gravadas em `exerciseattempt` e exportadas em `exercicios.csv` |
| O gabarito era sempre a 1ª opção | Dava para acertar 100% sem ler | Opções embaralhadas por sessão (`build_exercise_view`), com teste de variação |
| A lição 12 não tinha texto, só rótulos | Objetivo de interpretação não podia ser praticado | Texto de apoio em EN/ES/FR (90–120 palavras), exibido na lição e enviado ao prompt |
| Gabaritos não únicos (EN 20, ES 15, ES 14, ES 5, ES 6) | Medida inválida | Contexto/sujeito explícito e alternativas que não completam a frase |
| Regras falsas (ES 13 ser/estar; ES 16 “bastante”) | Ensinava errado | Explicações corrigidas |
| “Je aime” (FR 4) | Item agramatical | Enunciado mudou para `J'___` e a elisão foi explicada |
| Traduções artificiais (EN 8/9/17, ES 5, FR 4/19) | Perda de sentido | Traduções ajustadas |
| Explicação imprecisa (EN 1) | “he/she/it” no lugar do sujeito | Explicação reescrita |

## O que permanece aberto

### Alto

- **Progressão nominal:** Avançado (11–15) e Fluente (16–20) ainda usam estruturas
  A2–B1; faltam produção, inferência e registro formal.
- **Syllabus diferente por idioma:** os 20 temas coincidem, mas objetivos e conteúdos
  não são equivalentes (EN 9 é aeroporto; ES/FR é trem/hotel; EN 15 revisa tempos;
  ES/FR argumenta).
- **Lição 12:** o texto entrou, mas os exercícios ainda cobram vocabulário, não ideia
  principal/inferência.
- **FR 5:** conteúdo do Básico é metalinguagem francesa (“les verbes être et avoir”),
  sem exemplos traduzidos.
- **“Jogo”:** o tipo existe, mas a mecânica é múltipla escolha comum.
- **Distratores:** ainda há opções implausíveis e explicações que só repetem a tradução.

### Médio

- ES 11/17 e EN 11/16: nível declarado acima do que as tarefas pedem.
- EN 10/20 e FR 13/17: exercícios não cobrem tudo o que o objetivo promete.
- ES 18: promete ritmo/entonação, mas o app é textual.
- FR 1 e 5: mistura `tu`/`vous` sem critério explícito.
- Repertório estreito (família nuclear, viagens, restaurante); faltam variantes de
  gênero e contextos de trabalho/estudo.

## Por idioma (destaques)

### Inglês (15 achados)
- Alta: L20 com duas respostas; L13 penalizava “if I was”; L12 sem texto.
- Média: L10/L20 não cobrem o objetivo; L11/L16 acima do nível; L8/L17 traduções.
- Corrigido: 10 itens, incluindo os três de alta.

### Espanhol (18 achados)
- Alta: L15, L14, L5 e L6 com gabarito não único; L13 e L16 com regra falsa.
- Média: L12 sem texto; L11/L17 acima do nível.
- Corrigido: 7 itens; leitura adicionada.

### Francês (15 achados)
- Alta: L4 `Je aime`; L12 sem texto.
- Média: L5 metalinguagem; L6 nomenclatura; L13/L17 exercícios desalinhados.
- Corrigido: 5 itens + leitura.

### Pedagógico/editorial (16 achados)
- Alta: exercícios invisíveis; gabarito sempre na 1ª posição; L12 sem texto;
  progressão nominal.
- Média: objetivos pouco observáveis; distratores fracos; repertório estreito.

## O que um humano precisa validar

1. Correção e naturalidade nas três línguas, por professores nativos.
2. Calibragem CEFR dos 20 objetivos e dos 120 itens.
3. Se os exercícios devem valer nota/feedback no TCC e como registrar isso.
4. Validade das notas do LLM (concordância entre avaliadores, piloto).
5. Adequação cultural, de gênero e acessibilidade.
6. Como o app textual lida com pronúncia/entonação — hoje não lida.

## Arquivos e reprodutibilidade

- Correções: `scripts/fix_lessons_review1.py` (idempotente).
- Relatório consolidado das lições: `docs/licoes-60.xlsx` (abas Lições, Frases,
  Exercícios, Leituras).
- Agentes e contrato: `agents/`.
- Revisão automatizada futura: `scripts/review_lessons.py` com `LLM_PROVIDER=openai`.
