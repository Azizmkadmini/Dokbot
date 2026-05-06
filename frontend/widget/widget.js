(function () {
  "use strict";

  const DEFAULT_CONFIG = {
    apiUrl: "http://localhost:8000",
    tenantId: "demo",
    primaryColor: "#6366f1",
    title: "Support Assistant",
    placeholder: "Ask a question...",
    welcomeMessage: "Hi! How can I help you today?",
    position: "bottom-right",
  };

  function init(userConfig = {}) {
    const cfg = { ...DEFAULT_CONFIG, ...userConfig };

    injectStyles(cfg);
    const { button, panel, messagesEl, input, sendBtn } = buildDOM(cfg);

    let history = [];
    let isOpen = false;

    button.addEventListener("click", () => {
      isOpen = !isOpen;
      panel.style.display = isOpen ? "flex" : "none";
      button.innerHTML = isOpen ? closeSVG() : chatSVG();
      if (isOpen && messagesEl.children.length === 0) {
        appendMessage(messagesEl, "assistant", cfg.welcomeMessage);
      }
    });

    async function send() {
      const question = input.value.trim();
      if (!question) return;

      input.value = "";
      sendBtn.disabled = true;
      appendMessage(messagesEl, "user", question);
      const typingEl = appendTyping(messagesEl);

      try {
        const res = await fetch(`${cfg.apiUrl}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tenant_id: cfg.tenantId, question, history }),
        });

        typingEl.remove();

        if (!res.ok) {
          const err = await res.json();
          appendMessage(messagesEl, "assistant", err.detail || "Something went wrong.", true);
          return;
        }

        const data = await res.json();
        appendMessage(messagesEl, "assistant", data.answer);
        history.push({ role: "user", content: question });
        history.push({ role: "assistant", content: data.answer });
        if (history.length > 12) history = history.slice(-12);
      } catch (e) {
        typingEl.remove();
        appendMessage(messagesEl, "assistant", "Network error. Please try again.", true);
      } finally {
        sendBtn.disabled = false;
        input.focus();
      }
    }

    sendBtn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
    });
  }

  function appendMessage(container, role, text, isError = false) {
    const wrap = document.createElement("div");
    wrap.className = `rag-msg rag-msg--${role}`;
    if (isError) wrap.classList.add("rag-msg--error");

    const bubble = document.createElement("div");
    bubble.className = "rag-bubble";
    bubble.textContent = text;
    wrap.appendChild(bubble);
    container.appendChild(wrap);
    container.scrollTop = container.scrollHeight;
    return wrap;
  }

  function appendTyping(container) {
    const wrap = document.createElement("div");
    wrap.className = "rag-msg rag-msg--assistant";
    wrap.innerHTML = '<div class="rag-bubble rag-typing"><span></span><span></span><span></span></div>';
    container.appendChild(wrap);
    container.scrollTop = container.scrollHeight;
    return wrap;
  }

  function buildDOM(cfg) {
    const isRight = cfg.position === "bottom-right";

    const button = document.createElement("button");
    button.className = "rag-trigger";
    button.style.cssText = `${isRight ? "right:24px" : "left:24px"};background:${cfg.primaryColor}`;
    button.innerHTML = chatSVG();
    button.setAttribute("aria-label", "Open support chat");

    const panel = document.createElement("div");
    panel.className = "rag-panel";
    panel.style.cssText = `${isRight ? "right:24px" : "left:24px"};display:none`;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", cfg.title);

    panel.innerHTML = `
      <div class="rag-header" style="background:${cfg.primaryColor}">
        <span>${cfg.title}</span>
        <button class="rag-close" aria-label="Close">${closeSVG()}</button>
      </div>
      <div class="rag-messages" id="rag-messages"></div>
      <div class="rag-footer">
        <textarea class="rag-input" rows="1" placeholder="${cfg.placeholder}"></textarea>
        <button class="rag-send" style="background:${cfg.primaryColor}" aria-label="Send">${sendSVG()}</button>
      </div>
    `;

    panel.querySelector(".rag-close").addEventListener("click", () => {
      panel.style.display = "none";
      button.innerHTML = chatSVG();
    });

    document.body.appendChild(button);
    document.body.appendChild(panel);

    return {
      button,
      panel,
      messagesEl: panel.querySelector(".rag-messages"),
      input: panel.querySelector(".rag-input"),
      sendBtn: panel.querySelector(".rag-send"),
    };
  }

  function injectStyles(cfg) {
    if (document.getElementById("rag-widget-styles")) return;
    const style = document.createElement("style");
    style.id = "rag-widget-styles";
    style.textContent = `
      .rag-trigger {
        position: fixed; bottom: 24px; width: 56px; height: 56px; border-radius: 50%;
        border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 20px rgba(0,0,0,.25); z-index: 9999; transition: transform .2s;
      }
      .rag-trigger:hover { transform: scale(1.08); }
      .rag-panel {
        position: fixed; bottom: 92px; width: 360px; height: 520px;
        background: #fff; border-radius: 16px; box-shadow: 0 8px 40px rgba(0,0,0,.18);
        z-index: 9998; flex-direction: column; overflow: hidden; font-family: system-ui, sans-serif;
      }
      .rag-header {
        padding: 16px 20px; display: flex; align-items: center; justify-content: space-between;
        color: #fff; font-weight: 600; font-size: 15px;
      }
      .rag-close { background: none; border: none; color: #fff; cursor: pointer; padding: 4px; }
      .rag-messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; }
      .rag-msg { display: flex; }
      .rag-msg--user { justify-content: flex-end; }
      .rag-bubble {
        max-width: 80%; padding: 10px 14px; border-radius: 14px; font-size: 14px;
        line-height: 1.5; white-space: pre-wrap; word-break: break-word;
      }
      .rag-msg--user .rag-bubble { background: #6366f1; color: #fff; border-bottom-right-radius: 4px; }
      .rag-msg--assistant .rag-bubble { background: #f3f4f6; color: #111; border-bottom-left-radius: 4px; }
      .rag-msg--error .rag-bubble { background: #fee2e2; color: #b91c1c; }
      .rag-typing { display: flex; gap: 4px; align-items: center; padding: 14px 16px; }
      .rag-typing span {
        width: 7px; height: 7px; background: #9ca3af; border-radius: 50%;
        animation: rag-bounce .9s infinite;
      }
      .rag-typing span:nth-child(2) { animation-delay: .2s; }
      .rag-typing span:nth-child(3) { animation-delay: .4s; }
      @keyframes rag-bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-6px)} }
      .rag-footer { padding: 12px 16px; border-top: 1px solid #e5e7eb; display: flex; gap: 8px; align-items: flex-end; }
      .rag-input {
        flex: 1; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 12px;
        font-size: 14px; resize: none; outline: none; font-family: inherit;
      }
      .rag-input:focus { border-color: #6366f1; }
      .rag-send {
        width: 38px; height: 38px; border-radius: 10px; border: none; cursor: pointer;
        display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      }
      .rag-send:disabled { opacity: .5; cursor: not-allowed; }
      @media (max-width: 420px) { .rag-panel { width: calc(100vw - 32px); right: 16px !important; left: 16px !important; } }
    `;
    document.head.appendChild(style);
  }

  function chatSVG() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`;
  }
  function closeSVG() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
  }
  function sendSVG() {
    return `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`;
  }

  window.RAGSupport = { init };
})();
