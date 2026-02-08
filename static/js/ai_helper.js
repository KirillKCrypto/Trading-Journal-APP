document.addEventListener("DOMContentLoaded", () => {
  const chatContainer = document.getElementById("chat-container");
  const form = document.getElementById("ai-form");
  const textarea = document.getElementById("user_text");
  const loading = document.getElementById("loading-indicator");
  const submitBtn = document.getElementById("submit-btn");

  let loadingInterval;

  // Функция добавления сообщения в чат
  function addMessage(role, content, isHTML = false) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `chat-message ${role}`;

    const avatar = role === "user" ? "Вы" : "AI";
    const messageContent = isHTML ? content : content.replace(/\n/g, "<br>");

    messageDiv.innerHTML = `
      <div class="chat-avatar">${avatar}</div>
      <div class="chat-bubble">${messageContent}</div>
    `;

    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    saveChatHistory();
  }

  // Сохранение истории чата
  function saveChatHistory() {
    const messages = Array.from(chatContainer.querySelectorAll(".chat-message")).map(msg => ({
      role: msg.classList.contains("user") ? "user" : "assistant",
      content: msg.querySelector(".chat-bubble").innerHTML
    }));
    localStorage.setItem("chatHistory", JSON.stringify(messages));
  }

  // Загрузка истории чата
  function loadChatHistory() {
    try {
      const history = JSON.parse(localStorage.getItem("chatHistory") || "[]");
      history.forEach(({ role, content }) => addMessage(role, content, true));
    } catch (e) {
      console.warn("Ошибка загрузки истории чата:", e);
      localStorage.removeItem("chatHistory");
    }
  }

  // Управление индикатором загрузки
  function showLoading() {
    loading.style.display = "block";
    submitBtn.disabled = true;
    let dotCount = 0;

    loadingInterval = setInterval(() => {
      dotCount = (dotCount + 1) % 4;
      loading.querySelector("#dots").textContent = ".".repeat(dotCount);
    }, 500);
  }

  function hideLoading() {
    loading.style.display = "none";
    submitBtn.disabled = false;
    clearInterval(loadingInterval);
  }

  // Обработка отправки формы
  async function handleFormSubmit(e) {
    e.preventDefault();
    const text = textarea.value.trim();
    if (!text) return;

    addMessage("user", text);
    textarea.value = "";
    showLoading();

    try {
      const response = await fetch("/ai/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({ text })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      addMessage("assistant", data.response, true);

    } catch (error) {
      console.error("Chat error:", error);
      addMessage("assistant",
        `<div class="error-message">
          <strong>Ошибка:</strong> ${error.message || "Неизвестная ошибка"}
         </div>`,
        true
      );
    } finally {
      hideLoading();
    }
  }

  // Очистка истории чата (опционально)
  function clearChatHistory() {
    if (confirm("Очистить всю историю чата?")) {
      chatContainer.innerHTML = "";
      localStorage.removeItem("chatHistory");
    }
  }

  // Инициализация
  function init() {
    loadChatHistory();
    form.addEventListener("submit", handleFormSubmit);

    // Автофокус на текстовом поле
    textarea.focus();

    // Обработка клавиши Enter (без Shift)
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event("submit"));
      }
    });
  }

  init();
});