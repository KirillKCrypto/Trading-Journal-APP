document.addEventListener("DOMContentLoaded", () => {
  console.log("AI Helper JS loaded");

  // Элементы для управления ключом API
  const apiKeySection = document.getElementById("api-key-section");
  const chatSection = document.getElementById("chat-section");
  const saveKeyBtn = document.getElementById("save-key-btn");
  const apiKeyInput = document.getElementById("api-key-input");
  const keyStatus = document.getElementById("key-status");

  // Элементы чата
  const chatContainer = document.getElementById("chat-container");
  const form = document.getElementById("ai-form");
  const textarea = document.getElementById("user_text");
  const loading = document.getElementById("loading-indicator");
  const submitBtn = document.getElementById("submit-btn");

  let loadingInterval;

  // Функция добавления сообщения в чат (ВЫНЕСЕНО ВВЕРХ!)
  function addMessage(role, content, isHTML = false) {
    if (!chatContainer) return;

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

  // Функция для показа статуса ключа
  function showKeyStatus(text, type) {
    if (!keyStatus) return;

    keyStatus.textContent = text;
    keyStatus.style.display = 'block';
    keyStatus.style.color = type === 'success' ? 'green' : 'red';
    keyStatus.style.padding = '10px';
    keyStatus.style.borderRadius = '5px';
    keyStatus.style.marginTop = '10px';
    keyStatus.style.backgroundColor = type === 'success' ? '#e8f5e9' : '#ffebee';

    setTimeout(() => {
      keyStatus.style.display = 'none';
    }, 3000);
  }

  // Сохранение истории чата
  function saveChatHistory() {
    if (!chatContainer) return;

    const messages = Array.from(chatContainer.querySelectorAll(".chat-message")).map(msg => ({
      role: msg.classList.contains("user") ? "user" : "assistant",
      content: msg.querySelector(".chat-bubble").innerHTML
    }));
    localStorage.setItem("chatHistory", JSON.stringify(messages));
  }

  // Загрузка истории чата
  function loadChatHistory() {
    if (!chatContainer) return;

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
    if (!loading || !submitBtn) return;

    loading.style.display = "block";
    submitBtn.disabled = true;
    let dotCount = 0;

    loadingInterval = setInterval(() => {
      dotCount = (dotCount + 1) % 4;
      const dotsEl = loading.querySelector("#dots");
      if (dotsEl) {
        dotsEl.textContent = ".".repeat(dotCount);
      }
    }, 500);
  }

  function hideLoading() {
    if (!loading || !submitBtn) return;

    loading.style.display = "none";
    submitBtn.disabled = false;
    if (loadingInterval) {
      clearInterval(loadingInterval);
    }
  }

  // 1. Проверяем, есть ли сохраненный API ключ
  const savedKey = localStorage.getItem('openrouter_key');
  console.log("Saved key exists:", !!savedKey);

  if (savedKey) {
    // Ключ есть - показываем чат, скрываем форму
    if (apiKeySection) {
      apiKeySection.classList.add('hidden');
      console.log("API key section hidden");
    }
    if (chatSection) {
      chatSection.classList.remove('hidden');
      console.log("Chat section shown");
    }

    // Инициализируем чат
    initChat();
  } else {
    // Ключа нет - показываем форму, скрываем чат
    if (apiKeySection) {
      apiKeySection.classList.remove('hidden');
      console.log("API key section shown");
    }
    if (chatSection) {
      chatSection.classList.add('hidden');
      console.log("Chat section hidden");
    }
  }

  // 2. Обработчик сохранения ключа
  if (saveKeyBtn) {
    saveKeyBtn.addEventListener('click', function() {
      console.log("Save key button clicked");
      const key = apiKeyInput.value.trim();

      if (!key) {
        showKeyStatus('Введите ключ', 'error');
        return;
      }

      // Сохраняем в localStorage
      localStorage.setItem('openrouter_key', key);
      console.log("Key saved to localStorage");

      // Показываем сообщение об успехе
      showKeyStatus('✅ Ключ сохранен!', 'success');

      // Скрываем форму и показываем чат через секунду
      setTimeout(() => {
        if (apiKeySection) {
          apiKeySection.classList.add('hidden');
          console.log("API key section hidden");
        }
        if (chatSection) {
          chatSection.classList.remove('hidden');
          console.log("Chat section shown");
        }

        // Инициализируем чат
        initChat();

        // Добавляем приветственное сообщение
        addMessage('assistant', 'API ключ сохранен. Чем могу помочь?', true);
      }, 1000);
    });
  }

  // 3. Функция инициализации чата
  function initChat() {
    console.log("Initializing chat...");

    // Проверяем, что элементы чата существуют
    if (!chatContainer || !form || !textarea) {
      console.error("Не найдены элементы чата");
      return;
    }

    // Загружаем историю чата
    loadChatHistory();

    // Добавляем обработчик формы
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

    console.log("Chat initialized successfully");
  }

  // Обработка отправки формы
  async function handleFormSubmit(e) {
    e.preventDefault();

    if (!textarea) return;

    const text = textarea.value.trim();
    if (!text) return;

    // 1. Получаем ключ из localStorage
    const apiKey = localStorage.getItem('openrouter_key');
    console.log("API Key from localStorage:", apiKey ? "found" : "NOT FOUND");

    if (!apiKey) {
      addMessage("assistant",
        `<div class="error-message">
          <strong>Ошибка:</strong> API ключ не найден. Пожалуйста, введите ключ снова.
         </div>`,
        true
      );

      // Показываем форму для ключа
      if (apiKeySection) apiKeySection.classList.remove('hidden');
      if (chatSection) chatSection.classList.add('hidden');
      return;
    }

    addMessage("user", text);
    textarea.value = "";
    showLoading();

    try {
      // 2. Отправляем ключ вместе с запросом
      const response = await fetch("/ai/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest"
        },
        body: JSON.stringify({
          text: text,
          api_key: apiKey  // ⬅️ Ключ передается здесь
        })
      });

      console.log("Response status:", response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Response data:", data);

      if (data.error) {
        throw new Error(data.error);
      }

      addMessage("assistant", data.response, true);

    } catch (error) {
      console.error("Chat error:", error);

      let errorMessage = error.message || "Неизвестная ошибка";

      // Если ошибка связана с API ключом
      if (errorMessage.includes('401') || errorMessage.includes('ключ') ||
          errorMessage.includes('API') || errorMessage.includes('auth')) {
        // Удаляем неверный ключ
        localStorage.removeItem('openrouter_key');
        errorMessage = "Неверный API ключ. Пожалуйста, введите ключ снова.";

        // Показываем форму для ключа
        setTimeout(() => {
          if (apiKeySection) apiKeySection.classList.remove('hidden');
          if (chatSection) chatSection.classList.add('hidden');
        }, 2000);
      }

      addMessage("assistant",
        `<div class="error-message">
          <strong>Ошибка:</strong> ${errorMessage}
         </div>`,
        true
      );
    } finally {
      hideLoading();
    }
  }

  // Очистка истории чата
  function clearChatHistory() {
    if (!chatContainer) return;

    if (confirm("Очистить всю историю чата?")) {
      chatContainer.innerHTML = "";
      localStorage.removeItem("chatHistory");
    }
  }

  // Дополнительно: кнопка очистки ключа (опционально)
  function addClearKeyButton() {
    const clearBtn = document.createElement('button');
    clearBtn.textContent = '🗑️ Очистить ключ';
    clearBtn.style.cssText = `
      margin-top: 10px;
      padding: 5px 10px;
      background: #ff6b6b;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 0.9em;
    `;

    clearBtn.addEventListener('click', function() {
      if (confirm("Удалить сохраненный API ключ?")) {
        localStorage.removeItem('openrouter_key');
        localStorage.removeItem('chatHistory');

        // Показываем форму для ключа
        if (apiKeySection) apiKeySection.classList.remove('hidden');
        if (chatSection) chatSection.classList.add('hidden');

        // Очищаем чат
        if (chatContainer) chatContainer.innerHTML = "";

        // Очищаем поле ввода
        if (apiKeyInput) apiKeyInput.value = "";

        showKeyStatus('✅ Ключ удален', 'success');
      }
    });

    // Добавляем кнопку в форму API ключа
    if (apiKeySection) {
      apiKeySection.appendChild(clearBtn);
    }
  }

  // Добавляем кнопку очистки
  addClearKeyButton();
});

