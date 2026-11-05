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

  initLesson();
  initPractice();
  initMicro();
})();
