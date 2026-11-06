(() => {
  "use strict";

  const lessonRoot = document.querySelector("[data-session]");
  const chat = document.querySelector("[data-chat]");
  const composer = document.querySelector("[data-composer]");
  const csrfToken =
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

  function jsonHeaders() {
    return {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    };
  }

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function scrollToEnd() {
    if (chat) chat.lastElementChild?.scrollIntoView({ block: "end", behavior: "smooth" });
  }

  function addMessage(role, text) {
    const article = el("article", `msg msg-${role}`);
    article.appendChild(el("p", "", text));
    chat.appendChild(article);
    scrollToEnd();
    return article;
  }

  function addError(text) {
    const article = el("article", "msg msg-error");
    article.appendChild(el("p", "", text));
    chat.appendChild(article);
    scrollToEnd();
  }

  function addTurn(data) {
    const article = el("article", "msg msg-assistant");
    const paragraph = el("p", "", data.resposta || "");
    if (typeof data.score === "number") {
      paragraph.appendChild(el("span", "score", `${data.score}/10`));
    }
    article.appendChild(paragraph);

    const rows = [
      ["Correção", data.correcao],
      ["Explicação", data.explicacao],
      ["Exemplo", data.exemplo],
      ["Próximo passo", data.proximo_passo],
    ].filter(([, value]) => value);

    if (rows.length) {
      const details = el("details", "correction");
      details.appendChild(el("summary", "", "Correção e nota"));
      const dl = el("dl");
      for (const [label, value] of rows) {
        dl.appendChild(el("dt", "", label));
        dl.appendChild(el("dd", "", value));
      }
      details.appendChild(dl);
      article.appendChild(details);
    }

    chat.appendChild(article);
    scrollToEnd();
  }

  async function sendTurn(event) {
    event.preventDefault();
    const textarea = composer.querySelector("textarea");
    const message = textarea.value.trim();
    if (!message || composer.dataset.busy === "1") return;

    composer.dataset.busy = "1";
    const button = composer.querySelector("button");
    button.disabled = true;
    addMessage("user", message);
    textarea.value = "";

    const typing = el("div", "typing");
    typing.append(el("span"), el("span"), el("span"));
    chat.appendChild(typing);
    scrollToEnd();

    try {
      const response = await fetch("/api/turno", {
        method: "POST",
        headers: jsonHeaders(),
        body: JSON.stringify({
          session_id: Number(lessonRoot.dataset.session),
          message,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Não foi possível enviar agora.");
      }
      addTurn(await response.json());
    } catch (error) {
      addError(error.message || "Falha de conexão. Tente de novo.");
    } finally {
      typing.remove();
      composer.dataset.busy = "0";
      button.disabled = false;
      textarea.focus();
    }
  }

  function initLesson() {
    if (!chat || !composer || !lessonRoot) return;
    composer.addEventListener("submit", sendTurn);
    const textarea = composer.querySelector("textarea");
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        composer.requestSubmit();
      }
    });

    const finish = document.getElementById("finish-lesson");
    finish?.addEventListener("click", async () => {
      if (!window.confirm("Encerrar a lição e ver o feedback?")) return;
      finish.disabled = true;
      try {
        const response = await fetch("/api/encerrar", {
          method: "POST",
          headers: jsonHeaders(),
          body: JSON.stringify({ session_id: Number(lessonRoot.dataset.session) }),
        });
        if (!response.ok) throw new Error("Não foi possível encerrar agora.");
        window.location.href = `/feedback/${lessonRoot.dataset.session}`;
      } catch (error) {
        finish.disabled = false;
        addError(error.message);
      }
    });
  }

  function initMicro() {
    const form = document.querySelector("[data-micro]");
    if (!form) return;
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const answers = {};
      for (const [key, value] of new FormData(form).entries()) {
        answers[key] = Number(value);
      }
      const status = form.querySelector("[data-micro-status]");
      const button = form.querySelector("button");
      button.disabled = true;
      try {
        const response = await fetch("/api/micro", {
          method: "POST",
          headers: jsonHeaders(),
          body: JSON.stringify({
            session_id: Number(form.dataset.session),
            answers,
          }),
        });
        if (!response.ok) throw new Error("Não foi possível salvar.");
        if (status) status.textContent = "Respostas salvas. Obrigado!";
        setTimeout(() => { window.location.href = "/app"; }, 900);
      } catch (error) {
        if (status) status.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
  }

  function initPractice() {
    const practice = document.querySelector("[data-practice]");
    if (!practice || !lessonRoot) return;

    practice.querySelectorAll(".exercise").forEach((exercise) => {
      const index = Number(exercise.dataset.index);
      const feedback = exercise.querySelector(".exercise-feedback");
      const buttons = Array.from(exercise.querySelectorAll(".option"));

      buttons.forEach((button) => {
        button.addEventListener("click", async () => {
          if (exercise.dataset.busy === "1") return;
          exercise.dataset.busy = "1";
          buttons.forEach((item) => {
            item.disabled = true;
          });

          try {
            const response = await fetch("/api/exercicio", {
              method: "POST",
              headers: jsonHeaders(),
              body: JSON.stringify({
                session_id: Number(lessonRoot.dataset.session),
                exercise_index: index,
                choice: button.dataset.choice,
              }),
            });
            if (!response.ok) {
              const body = await response.json().catch(() => ({}));
              throw new Error(body.detail || "Não foi possível corrigir agora.");
            }
            const data = await response.json();
            button.classList.add(data.correct ? "is-correct" : "is-wrong");
            if (!data.correct) {
              const right = buttons.find((item) => item.dataset.choice === data.answer);
              if (right) right.classList.add("is-correct");
            }
            feedback.hidden = false;
            feedback.classList.add(data.correct ? "is-correct" : "is-wrong");
            feedback.textContent = data.correct
              ? `Correto. ${data.explanation}`
              : `Ainda não. Resposta: ${data.answer}. ${data.explanation}`;
          } catch (error) {
            buttons.forEach((item) => {
              item.disabled = false;
            });
            exercise.dataset.busy = "0";
            feedback.hidden = false;
            feedback.textContent = error.message;
          }
        });
      });
    });
  }


  function initPracticeRun() {
    const root = document.querySelector("[data-practice-run]");
    if (!root) return;

    const cards = Array.from(root.querySelectorAll("[data-practice-card]"));
    const progress = root.querySelector("[data-practice-progress]");
    const scoreLabel = root.querySelector("[data-practice-score]");
    const result = root.querySelector("[data-practice-result]");
    const total = cards.length;
    const storageKey = `sabia-practice-${root.dataset.session}`;
    let saved = null;
    try { saved = JSON.parse(sessionStorage.getItem(storageKey) || "null"); } catch (error) { saved = null; }
    let current = saved && Number.isInteger(saved.index) && saved.index < total ? saved.index : 0;
    let score = saved && Number.isInteger(saved.score) ? saved.score : 0;

    function persist() {
      try { sessionStorage.setItem(storageKey, JSON.stringify({ index: current, score })); } catch (error) { /* modo privado */ }
    }

    function showCard(index) {
      current = index;
      cards.forEach((card, position) => {
        card.hidden = position !== index;
        card.dataset.busy = "0";
      });
      if (progress) progress.textContent = `${index + 1} de ${total}`;
      if (scoreLabel) scoreLabel.textContent = `${score} acerto${score === 1 ? "" : "s"}`;
      persist();
    }

    if (!total) {
      if (result) result.hidden = false;
      return;
    }

    cards.forEach((card) => {
      const index = Number(card.dataset.index);
      const buttons = Array.from(card.querySelectorAll(".option"));
      const feedback = card.querySelector("[data-feedback]");
      const next = card.querySelector("[data-next]");

      buttons.forEach((button) => {
        button.addEventListener("click", async () => {
          if (card.dataset.busy === "1") return;
          card.dataset.busy = "1";
          buttons.forEach((item) => { item.disabled = true; });

          try {
            const response = await fetch("/api/pratica", {
              method: "POST",
              headers: jsonHeaders(),
              body: JSON.stringify({
                session_id: Number(root.dataset.session),
                index,
                choice: button.dataset.choice,
              }),
            });
            if (!response.ok) {
              const body = await response.json().catch(() => ({}));
              throw new Error(body.detail || "Não foi possível corrigir agora.");
            }
            const data = await response.json();
            button.classList.add(data.correct ? "is-correct" : "is-wrong");
            if (!data.correct) {
              const right = buttons.find((item) => item.dataset.choice === data.answer);
              if (right) right.classList.add("is-correct");
            } else {
              score += 1;
            }
            if (scoreLabel) scoreLabel.textContent = `${score} acerto${score === 1 ? "" : "s"}`;
            persist();
            if (feedback) {
              feedback.hidden = false;
              feedback.classList.add(data.correct ? "is-correct" : "is-wrong");
              feedback.textContent = data.correct
                ? `Correto. ${data.explanation}`
                : `Ainda não. Resposta: ${data.answer}. ${data.explanation}`;
            }
            if (next) {
              next.hidden = false;
              next.textContent = index + 1 >= total ? "Ver resultado" : "Próximo";
            }
          } catch (error) {
            buttons.forEach((item) => { item.disabled = false; });
            card.dataset.busy = "0";
            if (feedback) {
              feedback.hidden = false;
              feedback.textContent = error.message;
            }
          }
        });
      });

      if (next) {
        next.addEventListener("click", () => {
          if (index + 1 >= total) {
            cards.forEach((item) => { item.hidden = true; });
            try { sessionStorage.removeItem(storageKey); } catch (error) { /* modo privado */ }
            if (result) {
              result.hidden = false;
              const title = result.querySelector("[data-result-title]");
              const copy = result.querySelector("[data-result-copy]");
              if (title) {
                title.textContent = score === total ? "Rodada perfeita." :
                  score >= Math.ceil(total * 0.6) ? "Bom trabalho." : "Vale revisar.";
              }
              if (copy) {
                copy.textContent = `Você acertou ${score} de ${total}. ` +
                  "Você pode repetir com outra ordem ou levar isso para a conversa.";
              }
            }
            return;
          }
          current = index + 1;
          showCard(current);
        });
      }
    });

    showCard(current);
  }


  function initCodeModal() {
    const dialog = document.querySelector("[data-code-modal]");
    if (!dialog) return;
    const code = (document.querySelector("[data-code-value]")?.textContent || "").trim();
    const modalCode = dialog.querySelector("[data-code-modal-value]");
    const status = dialog.querySelector("[data-code-status]");
    const openButton = document.querySelector("[data-code-open]");
    const key = "sabia-code-ack";

    function setStatus(text) {
      if (status) status.textContent = text;
    }

    function remember() {
      try { localStorage.setItem(key, code); } catch (error) { /* modo privado */ }
    }

    function show() {
      if (typeof dialog.showModal !== "function") return;
      if (!dialog.open) dialog.showModal();
    }

    async function copy() {
      try {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(code);
        } else {
          const area = document.createElement("textarea");
          area.value = code;
          area.setAttribute("readonly", "");
          area.style.position = "fixed";
          area.style.opacity = "0";
          document.body.appendChild(area);
          area.select();
          document.execCommand("copy");
          area.remove();
        }
        setStatus("Código copiado.");
      } catch (error) {
        setStatus("Não foi possível copiar. Selecione o código acima.");
      }
    }

    if (modalCode) modalCode.textContent = code;
    try {
      if (localStorage.getItem(key) !== code) show();
    } catch (error) { show(); }

    if (openButton) openButton.addEventListener("click", show);
    dialog.querySelector("[data-code-copy]")?.addEventListener("click", copy);
    dialog.querySelector("[data-code-share]")?.addEventListener("click", async () => {
      if (navigator.share) {
        try {
          await navigator.share({
            title: "Sabiá — meu código",
            text: `Meu código no Sabiá é ${code}. Guarde para voltar de qualquer aparelho.`,
          });
          setStatus("Compartilhado.");
          return;
        } catch (error) {
          if (error.name === "AbortError") return;
        }
      }
      await copy();
    });
    dialog.querySelector("[data-code-close]")?.addEventListener("click", () => {
      remember();
      dialog.close();
    });
    dialog.addEventListener("close", remember);
  }

  initLesson();
  initPractice();
  initPracticeRun();
  initMicro();
  initCodeModal();
})();
