import disnake
import os
import json
import random
from disnake.ext import commands, tasks
import aiohttp

DB_PATH = "data/video_db_tiktok.json"
CONFIG_PATH = "config/tiktok.json"

class TikTokNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.video_db_tiktok = self.load_db()
        self.check_new_videos.start()

    def load_config(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_db(self):
        if not os.path.exists(DB_PATH):
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump({"tiktok": [], "messages": []}, f, indent=1)
        with open(DB_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "tiktok" not in data:
            data["tiktok"] = []
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        return data

    def save_db(self):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(self.video_db_tiktok, f, indent=2)

    @tasks.loop(minutes=60)
    async def check_new_videos(self):
        username = self.config["username"]
        channel_id = self.config["discord_channel_id"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://www.tikwm.com/api/user/posts?unique_id={username}") as resp:
                    data = await resp.json()

            if data["code"] != 0:
                print(f"❌ Ошибка от API TikWM: {data['msg']}")
                return

            all_videos = data["data"]["videos"]
            new_videos = []

            for video in all_videos:
                video_id = video["video_id"]
                if video_id not in self.video_db_tiktok["tiktok"]:
                    new_videos.append({
                        "video_id": video_id,
                        "video_url": f"https://www.tiktok.com/@{username}/video/{video_id}",
                        "cover": video["cover"],
                        "title": video["title"]
                    })

            if not new_videos:
                print("Новых видео нет.")
                return

            channel = self.bot.get_channel(channel_id)
            if not channel:
                print("❌ Discord-канал не найден.")
                return

            random_messages = [
                "Новая короткометражка от pika_dev – не пропусти!",
                "Свежак от pika_dev — жми смотреть 🎬",
                "Ты это видел? Новое TikTok-видео от pika_dev!",
                "Вот это да! Новое видео у pika_dev!",
                "🔥 Новый ролик у pika_dev! Загляни 👀"
            ]

            for video in reversed(new_videos):
                embed_title = f"🎬 {video['title'][:253]}..." if len(video['title']) > 256 else f"🎬 {video['title']}"
                embed = disnake.Embed(
                    title=embed_title,
                    description=f"{random.choice(random_messages)}\n\n🔗 [Перейти к видео]({video['video_url']})",
                    color=disnake.Color.green()
                )
                embed.set_image(url=video["cover"])

                msg = await channel.send(content="@everyone <@&1350526068494307369>", embed=embed)
                print(f"✅ Видео TikTok отправлено: {video['title']}")

                self.video_db_tiktok["tiktok"].append(video["video_id"])
                self.video_db_tiktok["messages"].append({
                    "video_id": video["video_id"],
                    "message_id": msg.id
                })
                self.save_db()

        except Exception as e:
            print(f"❌ Ошибка при обработке TikTok: {e}")

    @check_new_videos.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(TikTokNotifier(bot))
