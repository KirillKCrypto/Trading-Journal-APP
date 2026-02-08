// Массив для хранения выбранных сделок
let selectedTrades = [];

// Используем переменные из window.flaskData или значения по умолчанию
const currentDate = window.flaskData?.currentDate || new Date().toISOString().split('T')[0];
const dateFromFilter = window.flaskData?.dateFrom || '';
const dateToFilter = window.flaskData?.dateTo || '';
const DELETE_MULTIPLE_URL = window.flaskData?.deleteMultipleUrl || '/trades/delete_multiple';

function submitForm() {
    const form = document.getElementById('filter-form');
    if (form) form.submit();
}

// Инициализация flatpickr с правильными значениями
const dateFromPicker = flatpickr("#date_from", {
    dateFormat: "Y-m-d",
    maxDate: dateToFilter || currentDate,
    defaultDate: dateFromFilter || null,
    allowInput: true,
    disableMobile: true,
    onChange: function(selectedDates, dateStr) {
        if (selectedDates.length > 0) {
            dateToPicker.set('minDate', dateStr);
            if (dateToPicker.input.value && dateToPicker.input.value < dateStr) {
                dateToPicker.clear();
            }
        } else {
            dateToPicker.set('minDate', null);
        }
        submitForm();
    }
});

const dateToPicker = flatpickr("#date_to", {
    dateFormat: "Y-m-d",
    minDate: dateFromFilter || null,
    maxDate: currentDate,
    defaultDate: dateToFilter || null,
    allowInput: true,
    disableMobile: true,
    onChange: function(selectedDates, dateStr) {
        if (selectedDates.length > 0) {
            dateFromPicker.set('maxDate', dateStr);
            if (dateFromPicker.input.value && dateFromPicker.input.value > dateStr) {
                dateFromPicker.clear();
            }
        } else {
            dateFromPicker.set('maxDate', currentDate);
        }
        submitForm();
    }
});

// Автоотправка формы при изменении любого select
document.querySelectorAll('#filter-form select').forEach(el => {
    el.addEventListener('change', submitForm);
});

// Функции для массового удаления
document.addEventListener('DOMContentLoaded', function() {
    // Обработчик для "Выбрать все"
    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.addEventListener('change', function() {
            const checkboxes = document.querySelectorAll('.trade-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateSelectedTrades();
        });
    }

    // Обработчики для чекбоксов сделок
    document.querySelectorAll('.trade-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedTrades);
    });

    // Обработчик для кнопки удаления
    const deleteBtn = document.getElementById('deleteSelected');
    if (deleteBtn) {
        deleteBtn.addEventListener('click', showDeleteConfirmation);
    }

    // Обработчик для подтверждения удаления
    const confirmDeleteBtn = document.getElementById('confirmDelete');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', deleteSelectedTrades);
    }

    // Инициализация состояния кнопки удаления
    updateSelectedTrades();
});

function updateSelectedTrades() {
    selectedTrades = [];
    const checkboxes = document.querySelectorAll('.trade-checkbox:checked');

    checkboxes.forEach(checkbox => {
        selectedTrades.push(parseInt(checkbox.value)); // Преобразуем в число
    });

    const deleteBtn = document.getElementById('deleteSelected');
    const selectAll = document.getElementById('selectAll');

    if (deleteBtn) {
        if (selectedTrades.length > 0) {
            deleteBtn.style.display = 'block';
            deleteBtn.textContent = `🗑️ Удалить выбранные (${selectedTrades.length})`;
        } else {
            deleteBtn.style.display = 'none';
        }
    }

    if (selectAll) {
        const totalCheckboxes = document.querySelectorAll('.trade-checkbox').length;
        selectAll.checked = selectedTrades.length === totalCheckboxes && totalCheckboxes > 0;
        selectAll.indeterminate = selectedTrades.length > 0 && selectedTrades.length < totalCheckboxes;
    }
}

function showDeleteConfirmation() {
    if (selectedTrades.length === 0) return;

    const selectedCount = document.getElementById('selectedCount');
    if (selectedCount) {
        selectedCount.textContent = selectedTrades.length;
    }

    const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    modal.show();
}

async function deleteSelectedTrades() {
    if (selectedTrades.length === 0) return;

    try {
        const response = await fetch(DELETE_MULTIPLE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ trade_ids: selectedTrades })
        });

        if (response.ok) {
            const result = await response.json();

            // Закрываем модальное окно
            const modalEl = document.getElementById('deleteConfirmModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();

            // Показываем сообщение об успехе
            showMessage(`Успешно удалено ${result.deleted_count || selectedTrades.length} сделок`, 'success');

            // Перезагружаем страницу через секунду
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error('Ошибка при удалении');
        }
    } catch (error) {
        console.error('Error:', error);
        showMessage('Ошибка при удалении сделок', 'error');
    }
}

function getCSRFToken() {
    // Если используете CSRF защиту, добавьте получение токена
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

function showMessage(message, type) {
    // Создаем временное сообщение
    const messageEl = document.createElement('div');
    messageEl.textContent = message;
    messageEl.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#28a745' : '#dc3545'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 10000;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;

    document.body.appendChild(messageEl);

    setTimeout(() => {
        if (messageEl.parentNode) {
            document.body.removeChild(messageEl);
        }
    }, 3000);
}