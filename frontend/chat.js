const API_URL = '/api';
const WS_URL = `ws://${window.location.host}/ws`;

let currentTopic = '';
let socket = null;
let username = '';

// 1. Проверка авторизации при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    username = localStorage.getItem('username');

    if (!token || !username) {
        // Если токена нет, отправляем обратно на страницу входа
        window.location.href = 'index.html';
        return;
    }

    // Отображаем имя пользователя в шапке
    document.querySelector('#user-info span').innerText = username;
});

// Выход из аккаунта
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    if (socket) socket.close();
    window.location.href = 'index.html';
}

// 2. Подключение к топику
async function connectToTopic() {
    const topicInput = document.getElementById('topic-input').value.trim();
    if (!topicInput) return;

    currentTopic = topicInput;
    const token = localStorage.getItem('token');
    const chatWindow = document.getElementById('chat-window');

    // Очищаем окно чата
    chatWindow.innerHTML = '';

    try {
        // Загружаем историю (последние 50 сообщений)
        const response = await fetch(`${API_URL}/messages?topic=${encodeURIComponent(currentTopic)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const messages = await response.json();
            // По ТЗ история должна быть в правильном порядке.
            // Если бэкенд отдаст новые сверху, тут мы можем сделать messages.reverse()
            if (messages && messages.length > 0) {
                // Разворачиваем массив, чтобы старые были сверху, а новые снизу
                messages.reverse().forEach(msg => appendMessage(msg));
            } else {
                chatWindow.innerHTML = '<div class="system-message">История пуста. Напишите первое сообщение!</div>';
            }
        } else if (response.status === 401) {
            logout(); // Токен протух
            return;
        }
    } catch (error) {
        console.error('Ошибка загрузки истории:', error);
    }

    // Закрываем старое соединение, если было
    if (socket) {
        socket.close();
    }

    // Открываем новое WebSocket соединение
    // Передаем токен через параметр, так как JS WebSockets не поддерживают заголовки
    socket = new WebSocket(`${WS_URL}?topic=${encodeURIComponent(currentTopic)}&token=${token}`);

    socket.onopen = () => {
        console.log(`Подключено к топику: ${currentTopic}`);
        // Включаем поля ввода
        document.getElementById('message-input').disabled = false;
        document.getElementById('send-btn').disabled = false;
        
        // Убираем системное сообщение, если история была пуста
        const sysMsg = chatWindow.querySelector('.system-message');
        if (sysMsg) sysMsg.remove();
    };

    socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        appendMessage(msg);
    };

    socket.onclose = () => {
        console.log('Соединение закрыто');
        document.getElementById('message-input').disabled = true;
        document.getElementById('send-btn').disabled = true;
    };
}

// 3. Отправка сообщения
function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();

    if (!text || !socket || socket.readyState !== WebSocket.OPEN) return;

    // По ТЗ клиент отправляет только текст
    const payload = { text: text };
    socket.send(JSON.stringify(payload));
    
    input.value = '';
    input.focus();
}

// Отправка по нажатию Enter
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// 4. Отрисовка сообщения в UI
function appendMessage(msg) {
    const chatWindow = document.getElementById('chat-window');
    const isMe = msg.username === username;

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isMe ? 'me' : 'other'}`;

    // Форматируем время (если пришло с бэкенда)
    let timeStr = '';
    if (msg.sent_at) {
        const date = new Date(msg.sent_at);
        timeStr = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
    }

    messageDiv.innerHTML = `
        <div class="bubble">
            <div class="msg-header">
                <span class="msg-author">${isMe ? 'Вы' : msg.username}</span>
                <span class="msg-time">${timeStr}</span>
            </div>
            <div class="msg-text">${escapeHTML(msg.text)}</div>
        </div>
    `;

    chatWindow.appendChild(messageDiv);
    
    // Автопрокрутка вниз
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Защита от XSS (чтобы не вставляли HTML-теги в сообщения)
function escapeHTML(str) {
    const div = document.createElement('div');
    div.innerText = str;
    return div.innerHTML;
}