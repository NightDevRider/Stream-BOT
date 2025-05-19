import disnake
from disnake.ext import commands, tasks
import aiohttp
import json
import os
import random

class TwitchNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("config/twitch.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.token = None
        self.headers = None
        self.message = None
        self.state_file = "stream_state.json"
        self.check_stream.start()

    def load_state(self):
        if os.path.exists(self.state_file):
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"stream_live": False, "notified_discord": False, "notified_telegram": False}

    def save_state(self, state):
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f)

    async def get_oauth_token(self):
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.config["client_id"],
            "client_secret": self.config["client_secret"],
            "grant_type": "client_credentials"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                self.token = data["access_token"]
                self.headers = {
                    "Client-ID": self.config["client_id"],
                    "Authorization": f"Bearer {self.token}"
                }

    async def check_stream_status(self):
        url = f"https://api.twitch.tv/helix/streams?user_login={self.config['broadcaster_login']}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                data = await resp.json()
                return data["data"][0] if data["data"] else None

    @tasks.loop(minutes=5)
    async def check_stream(self):
        if not self.headers:
            await self.get_oauth_token()

        state = self.load_state()
        stream_info = await self.check_stream_status()
        channel = self.bot.get_channel(self.config["discord_channel_id"])
        if not channel:
            print("❌ Discord-канал не найден.")
            return

        twitch_url = f"https://twitch.tv/{self.config['broadcaster_login']}"

        if stream_info:
            if not state["notified_discord"]:
                title = stream_info["title"]
                game = stream_info["game_name"]
                viewers = stream_info["viewer_count"]
                thumbnail = stream_info["thumbnail_url"].replace("{width}", "1280").replace("{height}", "720")
                random_message = random.choice([  # List of random messages
                    "Заходи, будет весело и жарко! 🔥",
                    "Срочно на стрим! Это будет легендарно! 🚀",
                    "Давно ждали? Мы уже стартовали! 🎮",
                    "Твой вечер станет лучше с этим стримом! 😎",
                    "Не пропусти этот стрим! Будет жарко 🔥",
                    "Хватай вкусняшки и присоединяйся к стриму! 🍿",
                    "Ждём тебя на стриме! Врывайся в чат! 💬",
                    "Настроение — смотреть крутой стрим! 🎬",
                    "Прямо сейчас происходит что-то эпичное! 🤩",
                    "Мы уже здесь, а где же ты? Подключайся! 👾"
                ])

                embed = disnake.Embed(
                    title=title,
                    description=f"Игра: {game}\nЗрители: {viewers}",
                    url=twitch_url,
                    color=0x9146FF
                )
                embed.set_image(url=thumbnail)
                embed.set_author(
                    name=self.config['broadcaster_login'],
                    icon_url=f"https://static-cdn.jtvnw.net/jtv_user_pictures/{self.config['broadcaster_login']}-profile_image.png"
                )
                embed.set_footer(text="Twitch • Стартуем 🎮")

                message_text = (
                    f"@everyone 🔴 Стрим начался!\n\n"
                    f"**{self.config['broadcaster_login']}** уже в эфире 👉 {twitch_url}\n\n"
                    f"{random_message}"
                )

                self.message = await channel.send(content=message_text, embed=embed)
                print("✅ Уведомление о стриме отправлено в Discord.")
                state["notified_discord"] = True
                state["stream_live"] = True
                self.save_state(state)

        elif not stream_info and state["stream_live"]:
            await channel.send("⚫️ Стрим завершён.")
            print("⚪ Стрим завершён. Уведомление отправлено.")
            state["stream_live"] = False
            state["notified_discord"] = False
            self.save_state(state)

    @check_stream.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(TwitchNotifier(bot))
