from __future__ import annotations

"""Itens do questionário final (versão 1.0 do instrumento)."""

FINAL_BLOCKS = [
    {
        "id": "utilidade",
        "title": "Utilidade percebida",
        "items": [
            ("u1", "As aulas me ajudaram a praticar o idioma de forma útil."),
            ("u2", "O conteúdo pareceu relevante para situações reais."),
            ("u3", "Eu usaria este app novamente."),
            ("u4", "Eu recomendaria este app a alguém aprendendo idiomas."),
        ],
    },
    {
        "id": "personalizacao",
        "title": "Personalização percebida",
        "items": [
            ("p1", "As aulas pareceram ajustadas ao meu nível."),
            ("p2", "Os temas tiveram a ver com meus interesses."),
            ("p3", "O app levou em conta meus erros anteriores."),
            ("p4", "Senti que o app foi se adaptando a mim ao longo das aulas."),
        ],
    },
    {
        "id": "feedback",
        "title": "Clareza do feedback",
        "items": [
            ("f1", "As correções foram fáceis de entender."),
            ("f2", "O feedback explicou o erro de forma clara."),
            ("f3", "As sugestões de melhoria foram úteis."),
            ("f4", "O feedback foi específico, não genérico."),
        ],
    },
    {
        "id": "dificuldade",
        "title": "Adequação da dificuldade",
        "items": [
            ("d1", "O nível de dificuldade foi adequado para mim."),
            ("d2", "As aulas foram desafiadoras na medida certa."),
            ("d3", "As aulas foram fáceis demais para mim."),
        ],
    },
    {
        "id": "realismo",
        "title": "Realismo das conversas",
        "items": [
            ("r1", "As conversas pareceram situações reais."),
            ("r2", "As respostas da IA soaram naturais."),
            ("r3", "Consegui imaginar usando o que pratiquei em contexto real."),
        ],
    },
    {
        "id": "engajamento",
        "title": "Engajamento e confiança",
        "items": [
            ("g1", "Fiquei motivado(a) a continuar."),
            ("g2", "Me senti mais confiante para falar ou escrever no idioma."),
            ("g3", "As aulas prenderam minha atenção."),
            ("g4", "Percebi progresso ao longo das sessões."),
        ],
    },
    {
        "id": "aprendizagem",
        "title": "Contribuição para a aprendizagem",
        "items": [
            ("c1", "Aprendi vocabulário novo."),
            ("c2", "Entendi melhor meus erros recorrentes."),
            ("c3", "Sinto que melhorei no idioma."),
        ],
    },
    {
        "id": "usabilidade",
        "title": "Usabilidade (SUS)",
        "items": [
            ("s1", "Eu acho que gostaria de usar este app com frequência."),
            ("s2", "Achei o app desnecessariamente complexo."),
            ("s3", "Achei o app fácil de usar."),
            ("s4", "Acho que precisaria de apoio técnico para conseguir usar o app."),
            ("s5", "Achei que as funções do app estavam bem integradas."),
            ("s6", "Achei que havia muita inconsistência no app."),
            ("s7", "Imagino que a maioria das pessoas aprenderia a usar o app rapidamente."),
            ("s8", "Achei o app muito complicado de usar."),
            ("s9", "Me senti confiante ao usar o app."),
            ("s10", "Precisei aprender muitas coisas antes de conseguir usar o app."),
        ],
    },
]

OPEN_QUESTIONS = [
    ("o1", "O que mais ajudou no seu aprendizado?"),
    ("o2", "O que mais atrapalhou?"),
    ("o3", "O que você mudaria no app?"),
]

LIKERT_KEYS = [key for block in FINAL_BLOCKS for key, _ in block["items"]]
