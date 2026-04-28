# Используем официальный легкий образ Python
FROM python:3.12-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями и устанавливаем их
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Копируем весь код бэкенда и фронтенда
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Переходим в папку бэкенда для запуска
WORKDIR /app/backend

# Команда запуска сервера
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]