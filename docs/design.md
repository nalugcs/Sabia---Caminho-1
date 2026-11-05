# Identidade visual e UX — Sabiá

Baseada no pacote **Identidade v0.2 — direção Bico**, aplicado ao app sem trocar a
peça 3D.

## Conceito

“O sabiá não nasce cantando. Aprende ouvindo.” O app é a conversa que ensina, não um
curso. A identidade é tropical-editorial: fauna brasileira sem clichê de pássaro
desenhado.

## Símbolo: Bico

Duas massas e um rasgo: um círculo e um bico. Funciona a 16 px, vira ícone de app e não
depende de silhueta de bicho.

- **Header:** Bico em tinta, wordmark `sabiá` em Instrument Serif.
- **Favicon/ícone:** fundo noite `#13211c` + Bico areia `#efe6d6` (nunca inverte).
- **3D:** o campo de ondas foi mantido; só mudou de paleta para folha, areia e canto.

## Tokens

| Token | Valor | Uso |
|---|---|---|
| `--paper` | `#f2f4ee` | fundo |
| `--surface` | `#fbfcf8` | cartões |
| `--ink` | `#13211c` | texto |
| `--muted` | `#5c6a62` | texto secundário |
| `--line` | `#dadfd4` | hairlines |
| `--accent` / `--canto` | `#b4502a` | ação e acento quente |
| `--accent-text` | `#8f3d1f` | links e texto de acento |
| `--leaf` / `--folha` | `#2f5d4a` | apoio, progresso, acerto |
| `--sand` / `--areia` | `#efe6d6` | seleção e superfícies quentes |

## Tipografia

- **Instrument Serif** — display, títulos, wordmark; tracking −0.02 a −0.038em.
- **Instrument Sans** — corpo e interface (400–700).
- **IBM Plex Mono** — metadados, labels em caixa alta com tracking 0.09em.
- Fontes locais em `static/fonts/` (woff2, subsets latin/latin-ext), sem CDN.

## Movimento

- Entrada da página e escalonamento do consentimento.
- Mensagens do chat com fade/translate curto; indicador de digitação; selo de nota.
- Bico em hover muda para o acento; sem loop decorativo.
- `prefers-reduced-motion`: desliga tudo e mantém um quadro estático da onda.

## Peça 3D

Campo de ondas em pontos (Three.js local), 82 × 40 pontos no desktop e 52 × 26 no
mobile, cores interpoladas entre folha, areia e canto. Câmera em perspectiva, paralaxe
suave, pausa fora da viewport e fallback estático. Fica em faixa própria abaixo do
consentimento, sem competir com a leitura.

## Telas

- **Consentimento:** duas colunas + faixa 3D com legenda “O canto que ensina”.
- **Cadastro:** formulário de duas colunas, chips de idioma/interesse.
- **Dashboard:** código pessoal, progresso de 3 sessões, recomendação explicada,
  ponto de atenção e CTA laranja.
- **Lição:** conversa primeiro no mobile; trilho com objetivo, texto de apoio, prática
  com 2 exercícios corrigidos na hora.
- **Feedback:** Markdown seguro, Likert.
- **Questionário:** 35 Likert, NPS e abertas.
- **Admin:** contagens, exportações e erros.

## Por que não React/Vite

Não é um problema; é custo. O app é formulários + chat e o 3D/motion coube em Three.js
puro + CSS/WAAPI. React/Vite passa a valer se entrarmos em bibliotecas de componentes
(21st.dev, Magic UI, ReactBits) ou cenas complexas com React Three Fiber. O backend
continua o mesmo.

## Créditos

Instrument Serif / Instrument Sans / IBM Plex Mono (SIL OFL) · Three.js (MIT) ·
pacote de identidade v0.2 da Ana.
