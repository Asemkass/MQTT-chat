// Функция переключения между формами
function toggleForms() {
    const loginForm = document.getElementById('login-form');
    const regForm = document.getElementById('register-form');
    
    if (loginForm.style.display === 'none') {
        loginForm.style.display = 'block';
        regForm.style.display = 'none';
    } else {
        loginForm.style.display = 'none';
        regForm.style.display = 'block';
    }
    
    // Очищаем ошибки при переключении
    document.getElementById('login-error').innerText = '';
    document.getElementById('reg-error').innerText = '';
    document.getElementById('reg-success').innerText = '';
}

// Базовый URL нашего будущего бэкенда
const API_URL = '/api';
// Функция входа
async function login() {
    const usernameInput = document.getElementById('login-username').value;
    const passwordInput = document.getElementById('login-password').value;
    const errorDiv = document.getElementById('login-error');
    errorDiv.innerText = '';

    if (!usernameInput || !passwordInput) {
        errorDiv.innerText = 'Заполните все поля';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameInput, password: passwordInput })
        });

        if (response.ok) {
            const data = await response.json();
            // Сохраняем токен и логин
            localStorage.setItem('token', data.token);
            localStorage.setItem('username', usernameInput);
            // Переходим в чат
            window.location.href = 'main.html';
        } else if (response.status === 401) {
            errorDiv.innerText = 'Неверный логин или пароль';
        } else {
            errorDiv.innerText = 'Ошибка сервера';
        }
    } catch (error) {
        console.error('Ошибка:', error);
        errorDiv.innerText = 'Не удалось подключиться к серверу';
    }
}

// Функция регистрации
async function register() {
    const usernameInput = document.getElementById('reg-username').value;
    const passwordInput = document.getElementById('reg-password').value;
    const errorDiv = document.getElementById('reg-error');
    const successDiv = document.getElementById('reg-success');
    errorDiv.innerText = '';
    successDiv.innerText = '';

    if (!usernameInput || !passwordInput) {
        errorDiv.innerText = 'Заполните все поля';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameInput, password: passwordInput })
        });

        if (response.status === 201) {
            successDiv.innerText = 'Регистрация успешна! Теперь вы можете войти.';
            document.getElementById('reg-username').value = '';
            document.getElementById('reg-password').value = '';
        } else if (response.status === 409) {
            errorDiv.innerText = 'Такой логин уже занят';
        } else {
            errorDiv.innerText = 'Ошибка при регистрации';
        }
    } catch (error) {
        console.error('Ошибка:', error);
        errorDiv.innerText = 'Не удалось подключиться к серверу';
    }
}