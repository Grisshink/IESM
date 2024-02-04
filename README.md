# IESM - Invisible Encrypted Scratch Messenger

Система, использующая облачные переменные скретча для передачи сообщений друг другу.

## Сборка

Чтобы собрать приложение, достаточно запустить эти команды:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
pyinstaller --name IESM main.py
```

Выходной исполняемый файл будет лежать в папке `dist/IESM/`

## Использование

При запуске приложения появится окно со входом. Для входа нужны эти значения:

- Имя пользователя и пароль от скретч аккаунта (нужен для соединения с облачными переменными)
- ID Проекта, к которому нужно подключиться
- Имя комнаты (Можно оставить пустым)
- Кодировка сообщений (Влияет на макс лимит символов в одном сообщении, но также может ограничить набор допустимых символов в сообщении. По умолчанию стоит кодировка `iso8859_5`, что даёт наилучшую работу системы)

После входа система определяет доступные облачные переменные (На высоконагруженных проектах это происходит почти моментально), если такие не найдутся, то можно их добавить вручную через меню *"Соединение"*.
