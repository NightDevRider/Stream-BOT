import disnake
from disnake.ext import commands, tasks
import aiohttp
import json
import os

DB_PATH = "data/video_db_youtube.json"
CONFIG_PATH = "config/youtube.json"

class YouTubeNotifier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.video_db_youtube = self.load_db()
        self.check_new_videos.start()

    def load_config(self):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_db(self):
        if not os.path.exists(DB_PATH):
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            with open(DB_PATH, "w", encoding="utf-8") as f:
                json.dump({"youtube": [], "messages": []}, f, indent=2)
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_db(self):
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(self.video_db_youtube, f, indent=2)

    @tasks.loop(minutes=10)
    async def check_new_videos(self):
        channel_id = self.config.get("channel_id")
        api_key = self.config.get("api_key")
        discord_channel_id = self.config.get("discord_channel_id")

        if not channel_id or not api_key or not discord_channel_id:
            print("❌ Не указан channel_id, api_key или discord_channel_id в config/youtube.json")
            return

        url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?key={api_key}&channelId={channel_id}"
            f"&part=snippet,id&order=date&maxResults=5"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        print(f"❌ Ошибка от YouTube API ({resp.status}): {data}")
                        return
        except Exception as e:
            print(f"❌ Ошибка при запросе к YouTube API: {e}")
            return

        if "items" not in data:
            print("❌ Нет поля 'items' в ответе YouTube API.")
            return

        new_items = [
            item for item in data["items"]
            if item["id"]["kind"] == "youtube#video"
            and item["id"]["videoId"] not in self.video_db_youtube["youtube"]
        ]

        if not new_items:
            print("📭 Нет новых видео для отправки.")
            return

        channel = self.bot.get_channel(discord_channel_id)
        if not channel:
            print("❌ Не удалось найти канал Discord.")
            return

        for item in reversed(new_items):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            thumbnail = item["snippet"]["thumbnails"]["high"]["url"]

            embed = disnake.Embed(
                title="📺 Новое видео на YouTube!",
                description=f"**{title}**\nСмотри сейчас 👉 [перейти к видео]({video_url})",
                color=disnake.Color.red()
            )
            embed.set_image(url=thumbnail)

            try:
                sent = await channel.send(content="@everyone <@&1350526068494307369>", embed=embed)
                print(f"✅ Видео отправлено: {title}")

                # Только после успешной отправки — сохраняем в базу
                self.video_db_youtube["youtube"].append(video_id)
                self.video_db_youtube["messages"].append({
                    "video_id": video_id,
                    "message_id": sent.id
                })
                self.save_db()

            except Exception as e:
                print(f"❌ Ошибка при отправке видео {video_id}: {e}")

    @check_new_videos.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

def setup(bot):
    bot.add_cog(YouTubeNotifier(bot))
