document.addEventListener('DOMContentLoaded', function () {
  // Проверяем, есть ли список задач на странице
  const taskList = document.getElementById('task-list');
  if (!taskList) return;

  // === ВОССТАНОВЛЕНИЕ ПОРЯДКА (только для активных задач) ===
  function restoreOrder() {
    // Проверяем, находимся ли мы на странице активных задач
    const isActiveTasksPage = window.location.pathname === '/tasks' ||
                             window.location.pathname.includes('task_list');

    if (!isActiveTasksPage) return;

    const savedOrder = JSON.parse(localStorage.getItem('taskOrder')) || [];
    if (!savedOrder.length) return;

    const items = Array.from(taskList.children);
    const itemsMap = new Map();
    items.forEach(item => itemsMap.set(item.dataset.id, item));

    // Фильтруем сохраненный порядок, оставляя только существующие задачи
    const validOrder = savedOrder.filter(id => itemsMap.has(id));

    // Находим новые задачи (которых нет в сохраненном порядке)
    const existingIds = new Set(validOrder);
    const newItems = items.filter(item => !existingIds.has(item.dataset.id));

    // Очищаем список
    taskList.innerHTML = '';

    // Сначала добавляем задачи в сохраненном порядке
    validOrder.forEach(id => {
      if (itemsMap.has(id)) {
        taskList.appendChild(itemsMap.get(id));
      }
    });

    // Затем добавляем новые задачи в конец
    newItems.forEach(item => {
      taskList.appendChild(item);
    });

    // Обновляем localStorage, убирая удаленные задачи
    const currentOrder = Array.from(taskList.children).map(li => li.dataset.id);
    localStorage.setItem('taskOrder', JSON.stringify(currentOrder));
  }

  restoreOrder();

  // === DRAG & DROP ПОРЯДОК (только для активных задач) ===
  const reorderUrl = taskList.dataset.reorderUrl;
  const isActiveTasksPage = window.location.pathname === '/tasks' ||
                           window.location.pathname.includes('task_list');

  if (isActiveTasksPage && typeof Sortable !== 'undefined') {
    Sortable.create(taskList, {
      animation: 300,
      ghostClass: 'sortable-ghost',
      chosenClass: 'sortable-chosen',
      dragClass: 'sortable-drag',
      placeholderClass: 'sortable-placeholder',
      easing: 'cubic-bezier(0.25, 0.8, 0.25, 1)',
      forceFallback: true,
      fallbackClass: 'sortable-fallback',
      onStart: () => document.body.style.cursor = 'grabbing',
      onEnd: function () {
        document.body.style.cursor = '';
        const order = Array.from(taskList.children).map(li => li.dataset.id);
        localStorage.setItem('taskOrder', JSON.stringify(order));

        if (reorderUrl) {
          fetch(reorderUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order })
          }).catch(err => console.warn('reorder fetch failed', err));
        }
      }
    });
  }

  // Остальной код остается без изменений...
  // === ОТКРЫТИЕ МОДАЛКИ ЗАДАЧИ ===
  if (typeof bootstrap !== 'undefined' && document.getElementById('taskModal')) {
    document.querySelectorAll('.task-item').forEach(item => {
      item.addEventListener('click', function (event) {
        // Проверяем, не кликнули ли по кнопке или форме
        if (event.target.tagName === 'BUTTON' ||
            event.target.closest('form') ||
            event.target.closest('button')) {
          return;
        }

        const modalEl = document.getElementById('taskModal');
        if (!modalEl) return;

        const modal = new bootstrap.Modal(modalEl);
        document.getElementById('modalTitle').textContent = this.dataset.title || '';
        document.getElementById('modalDescription').textContent = this.dataset.description || '(нет описания)';
        document.getElementById('modalPriority').textContent = this.dataset.priority || '(не указано)';
        document.getElementById('modalCompleted').textContent = this.dataset.completed || '(не указано)';
        document.getElementById('modalCreated').textContent = this.dataset.created || '';
        modal.show();
      });
    });
  }

  // === УДАЛЕНИЕ С ПОДТВЕРЖДЕНИЕМ ===
  let deleteFormToSubmit = null;
  const deleteModal = document.getElementById('deleteConfirmModal');
  const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');

  if (deleteModal && confirmDeleteBtn) {
    document.querySelectorAll('form.delete-form').forEach(form => {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        deleteFormToSubmit = this;
        const bootstrapModal = new bootstrap.Modal(deleteModal);
        bootstrapModal.show();
      });
    });

    confirmDeleteBtn.addEventListener('click', () => {
      if (deleteFormToSubmit) {
        const bootstrapModal = bootstrap.Modal.getInstance(deleteModal);
        bootstrapModal.hide();
        deleteFormToSubmit.submit();
      }
    });
  }
});