import disnake
import aiohttp
import json
import os
from disnake.ext import commands, tasks

DB_PATH = "data/video_db_clips.json"
CONFIG_PATH = "config/twitch_clips.json"

class TwitchClipsNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.video_db_clips = self.load_db()
        self.token = None
        self.headers = None
        self.check_new_clips.start()

    def load_config(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_db(self):
        if not os.path.exists(DB_PATH):
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump({"clips": [], "messages": []}, f, indent=2)

        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "clips" not in data:
            data["clips"] = []
        if "messages" not in data:
            data["messages"] = []

        return data

    def save_db(self):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(self.video_db_clips, f, indent=2)

    async def get_oauth_token(self):
        print("🔑 Получение OAuth токена...")
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "grant_type": "client_credentials"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                print("📦 Ответ Twitch OAuth:", data)
                self.token = data["access_token"]
                self.headers = {
                    "Client-ID": self.config["client_id"],
                    "Authorization": f"Bearer {self.token}"
                }

    async def fetch_broadcaster_id(self):
        login = self.config["broadcaster_login"]
        url = f"https://api.twitch.tv/helix/users?login={login}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                data = await resp.json()
                return data["data"][0]["id"] if data["data"] else None

    @tasks.loop(minutes=1)
    async def check_new_clips(self):
        print("🔁 check_new_clips: запуск проверки...")
        if not self.headers:
            await self.get_oauth_token()

        broadcaster_id = await self.fetch_broadcaster_id()
        if not broadcaster_id:
            print("❌ Ошибка: не удалось получить broadcaster_id.")
            return

        url = f"https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}&first=5"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                data = await resp.json()

        if "data" not in data:
            print("❌ Нет поля 'data' в ответе Twitch API")
            return

        new_clips = []
        for clip in data["data"]:
            clip_id = clip["id"]
            if clip_id not in self.video_db_clips["clips"]:
                print(f"🆕 Найден новый клип: {clip['title']}")
                self.video_db_clips["clips"].append(clip_id)
                new_clips.append({
                    "id": clip_id,
                    "title": clip["title"],
                    "url": clip["url"],
                    "thumbnail_url": clip["thumbnail_url"]
                })

        channel = self.bot.get_channel(self.config["discord_channel_id"])
        if not channel:
            print("❌ Канал Discord не найден!")
            return

        if not new_clips:
            print("📭 Новых клипов нет.")
            return

        for clip in reversed(new_clips):
            embed = disnake.Embed(
                title="🎬 Новый клип на Twitch!",
                description=f"**{clip['title']}**\n[➡️ Смотреть]({clip['url']})",
                color=disnake.Color.purple()
            )
            embed.set_image(url=clip["thumbnail_url"])

            msg = await channel.send(content="@everyone", embed=embed)
            self.video_db_clips["messages"].append({
                "clip_id": clip["id"],
                "message_id": msg.id
            })
            print(f"✅ Клип отправлен: {clip['title']}")

        self.save_db()

    @check_new_clips.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(TwitchClipsNotifier(bot))
