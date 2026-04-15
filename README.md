# 💬 MQTT Chat

Веб-чат с регистрацией/авторизацией на основе протокола MQTT.  
Стек: **Go + PostgreSQL + Eclipse Mosquitto + WebSocket**

---

## Требования

- Docker версии 20.10 и выше  
- Docker Compose версии 2.0 и выше  
- Git  

---

## Быстрый старт

### 1. Клонировать репозиторий
```bash
git clone https://github.com/username/mqtt-chat.git
cd mqtt-chat
```

### 2. Создать файл переменных окружения
```bash
cp .env.example .env
```
При необходимости отредактируйте `.env` (по умолчанию всё уже настроено для локального запуска).

### 3. Запустить приложение
```bash
docker-compose up --build
```

### 4. Открыть в браузере
```
http://localhost:8080
```

---

## Структура проекта

```
mqtt-chat/
├── docker-compose.yml
├── .env.example
├── README.md
├── mosquitto/
│   └── mosquitto.conf
├── backend/
│   ├── Dockerfile
│   ├── main.go
│   ├── go.mod
│   └── go.sum
└── frontend/
    ├── index.html      # Страница входа / регистрации
    └── main.html       # Страница чата
```

---

## Архитектура

```
Браузер  ──── WebSocket ────▶  Backend (Go)  ──── MQTT ────▶  Mosquitto
                                    │    ▲
                                    ▼    │
                                PostgreSQL
```

Браузер не подключается к MQTT напрямую. Backend является мостом:
- принимает сообщения от браузера через **WebSocket**
- публикует их в **MQTT топик**
- получает сообщения из MQTT и рассылает всем подключённым клиентам
- сохраняет каждое сообщение в **PostgreSQL**

---

## Переменные окружения

| Переменная    | Описание                  | Значение по умолчанию     |
|---------------|---------------------------|---------------------------|
| `DB_HOST`     | Хост PostgreSQL           | `postgres`                |
| `DB_PORT`     | Порт PostgreSQL           | `5432`                    |
| `DB_USER`     | Пользователь БД           | `user`                    |
| `DB_PASSWORD` | Пароль БД                 | `password`                |
| `DB_NAME`     | Имя базы данных           | `chatdb`                  |
| `MQTT_HOST`   | Хост MQTT брокера         | `mosquitto`               |
| `MQTT_PORT`   | Порт MQTT брокера         | `1883`                    |
| `JWT_SECRET`  | Секретный ключ для JWT    | `change_me_in_production` |
| `APP_PORT`    | Порт приложения           | `8080`                    |

---

## API

| Метод | Эндпоинт                    | Описание                  | Авторизация |
|-------|-----------------------------|---------------------------|-------------|
| POST  | `/api/register`             | Регистрация пользователя  | Нет         |
| POST  | `/api/login`                | Вход, возвращает JWT      | Нет         |
| GET   | `/api/messages?topic=...`   | История сообщений         | JWT         |
| GET   | `/ws?topic=...&token=...`   | WebSocket соединение      | JWT         |

---

## Остановка

```bash
docker-compose down
```

Полная очистка включая данные БД:
```bash
docker-compose down -v
```

---

## Частые проблемы

**Приложение не запускается — порт занят**
```bash
# Изменить порт в .env:
APP_PORT=8081
```

**Ошибка подключения к базе данных**  
База данных может не успеть запуститься. Подождать 10–15 секунд и перезапустить:
```bash
docker-compose restart app
```

**Mosquitto не принимает подключения**  
Убедиться, что файл `mosquitto/mosquitto.conf` существует и содержит:
```
listener 1883
allow_anonymous true
```

---
