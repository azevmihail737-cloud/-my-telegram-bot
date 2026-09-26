DIGITAL SHOP BOT — Bothost

1. Загрузите bot.py и requirements.txt на Bothost.
2. Тип проекта: Python.
3. Токен НЕ вставляйте в bot.py.
   Bothost передаёт токен в переменную BOT_TOKEN автоматически.
4. Главный файл: bot.py
5. ADMIN_ID уже указан в начале bot.py.
6. После деплоя перезапустите бота.
7. В логе должно появиться:
   Bot started: @имя_бота

После этого отправьте боту /start.

Если бот уже запускался через webhook, bot.py автоматически удалит webhook перед polling.
