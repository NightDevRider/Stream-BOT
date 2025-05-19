import disnake
from disnake.ext import commands, tasks
import aiohttp
import json
import socket
import os
from aiohttp import ClientConnectorError

class TwitchToTelegram(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Загрузка конфигурации
        with open("config/twitch.json", "r", encoding="utf-8") as f:
            twitch_cfg = json.load(f)
            self.client_id = twitch_cfg["client_id"]
            self.client_secret = twitch_cfg["client_secret"]
            self.twitch_login = twitch_cfg["broadcaster_login"]

        with open("config/telegram.json", "r", encoding="utf-8") as f:
            tg_cfg = json.load(f)
            self.telegram_token = tg_cfg["token"]
            self.telegram_chat_id = tg_cfg["chat_id"]

        self.token = None
        self.user_id = None
        self.state_file = "stream_state.json"

        self.check_stream.start()

    def cog_unload(self):
        self.check_stream.cancel()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"stream_live": False, "notified_discord": False, "notified_telegram": False}

    def save_state(self, state):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f)

    async def get_app_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, params=params) as resp:
                    data = await resp.json()
                    self.token = data.get("access_token")
                    if self.token:
                        print("✅ Успешно получен Twitch токен.")
                    else:
                        print(f"❌ Ошибка получения токена: {data}")
        except ClientConnectorError as e:
            print(f"❌ [DNS/Connection Error] Не удалось подключиться к Twitch: {e}")
        except Exception as e:
            print(f"❌ Ошибка при получении токена: {e}")

    async def get_user_id(self):
        url = f"https://api.twitch.tv/helix/users?login={self.twitch_login}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Client-ID": self.client_id
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    if "data" in data and data["data"]:
                        self.user_id = data["data"][0]["id"]
                        print(f"✅ Найден Twitch user_id: {self.user_id}")
                    else:
                        print(f"❌ Не удалось получить user_id: {data}")
        except Exception as e:
            print(f"❌ Ошибка при получении user_id: {e}")

    @tasks.loop(seconds=60)
    async def check_stream(self):
        try:
            # Проверка DNS-доступности Twitch
            try:
                socket.gethostbyname("id.twitch.tv")
            except socket.gaierror:
                print("❌ DNS не может разрешить адрес id.twitch.tv — проверь подключение.")
                return

            if not self.token:
                await self.get_app_token()
            if not self.user_id:
                await self.get_user_id()

            headers = {
                "Authorization": f"Bearer {self.token}",
                "Client-ID": self.client_id
            }

            url = f"https://api.twitch.tv/helix/streams?user_id={self.user_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()

            state = self.load_state()

            if data["data"]:
                if not state["notified_telegram"]:
                    print("🔴 Стрим начался! Отправляем в Telegram...")
                    await self.send_telegram_message(data["data"][0])
                    state["stream_live"] = True
                    state["notified_telegram"] = True
                    self.save_state(state)
            else:
                if state["stream_live"]:
                    print("⚪ Стрим завершён.")
                    state["stream_live"] = False
                    state["notified_discord"] = False
                    state["notified_telegram"] = False
                    self.save_state(state)

        except Exception as e:
            print(f"[Twitch->Telegram Error]: {e}")

    async def send_telegram_message(self, stream):
        title = stream.get("title", "Без названия")
        game = stream.get("game_name", "Игра не указана")
        preview = stream["thumbnail_url"].replace("{width}", "1280").replace("{height}", "720")
        url = f"https://twitch.tv/{self.twitch_login}"

        text = (
            f"🔴 <b>Стрим начался!</b>\n\n"
            f"<b>{title}</b>\n"
            f"🕹 <i>{game}</i>\n\n"
            f"<a href='{preview}'>🖼 Превью</a>\n"
            f"📺 <a href='{url}'>Смотреть на Twitch</a>"
        )

        tg_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(tg_url, data=payload) as resp:
                if resp.status == 200:
                    print("✅ Уведомление отправлено в Telegram")
                else:
                    print(f"❌ Ошибка Telegram: {resp.status}")
                    print(await resp.text())

    @check_stream.before_loop
    async def before_check_stream(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(TwitchToTelegram(bot))
