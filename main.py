import disnake
import os
import sys
from disnake.ext import commands
from dotenv import load_dotenv

# Устанавливаем кодировку UTF-8 для консоли
sys.stdout.reconfigure(encoding='utf-8')

# Загружаем переменные окружения из .env файла
load_dotenv()

# Создаём объект активности
activity = disnake.Activity(
    type=disnake.ActivityType.watching,
    name="Twitch!",
    url="https://twitch.tv/pika_dev"
)

# Инициализация бота
bot = commands.Bot(
    command_prefix="$",  # Префикс для команд
    intents=disnake.Intents.all(),
    activity=activity,
    reload=True,
    help_command=None
)

# Загружаем cogs (расширения)
def load_cogs(path):
    for file in os.listdir(path):
        cog_path = os.path.join(path, file)
        # Рекурсивно загружаем файлы
        if os.path.isdir(cog_path):
            load_cogs(cog_path)
        elif file.endswith(".py"):
            try:
                cog_name = os.path.splitext(file)[0]
                cog_extension = f"cogs.{cog_name}"
                bot.load_extension(cog_extension)
                print(f"[Extension]> {cog_extension} loaded")
            except Exception as e:
                print(f"Error while loading cog > {cog_extension}: {type(e).__name__} - {e}")

# Загрузка всех cogs из папки 'cogs'
load_cogs("cogs")

# Событие on_ready, когда бот успешно подключился
@bot.event
async def on_ready():
    await bot.change_presence(status=disnake.Status.dnd, activity=activity)
    print(f"{bot.user.name} was successfully launched")
    print(f"Extensions loaded: {len(bot.cogs)}")

# Запуск бота с токеном из .env
bot.run(os.getenv("TOKEN"))
