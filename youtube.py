from .. import loader, utils
import os
import asyncio
from yt_dlp import YoutubeDL
import re
import json

class YouTubeDownloaderMod(loader.Module):
    """Завантажувач YouTube відео з дозволених груп"""
    strings = {"name": "YouTube Downloader"}
    allowed_groups_file = "allowed_groups.json"  # Файл для збереження списку груп

    async def client_ready(self, client, db):
        self.client = client
        self.allowed_groups = self.load_allowed_groups()

    def load_allowed_groups(self):
        """Завантажує дозволені групи з файлу"""
        if os.path.exists(self.allowed_groups_file):
            with open(self.allowed_groups_file, 'r') as f:
                return json.load(f)
        return []

    def save_allowed_groups(self):
        """Зберігає дозволені групи у файл"""
        with open(self.allowed_groups_file, 'w') as f:
            json.dump(self.allowed_groups, f)

    @loader.owner
    async def ytallowcmd(self, message):
        """Додає або видаляє групу з списку дозволених"""
        chat_id = str(message.chat_id)
        if chat_id not in self.allowed_groups:
            self.allowed_groups.append(chat_id)
            action = "дозволена"
        else:
            self.allowed_groups.remove(chat_id)
            action = "видалена"
        self.save_allowed_groups()
        await message.reply(f"Ця група тепер {action} для завантаження відео.")

    async def download_video(self, url):
        """Завантажує відео з YouTube, використовуючи yt-dlp"""
        ydl_opts = {
            'format': 'mp4[height<=1080]',  # Формат відео з обмеженням якості до 1080p
            'outtmpl': 'video.mp4',         # Ім'я вихідного файлу
            'username': 'oauth2',           # Використовуємо OAuth2 для авторизації
            'password': '',                 # Порожній пароль для OAuth2
            'max_filesize': 50 * 1024 * 1024,  # Обмеження на розмір відео (50 МБ)
            'quiet': True,
            'format_sort': ['+res:360', '+size']  # Сортування за роздільною здатністю і розміром
        }

        # Використання to_thread для запуску блокуючого коду
        return await asyncio.to_thread(self._download_video, url, ydl_opts)

    def _download_video(self, url, ydl_opts):
        """Внутрішній метод для завантаження відео, що викликається в окремому потоці"""
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if info['duration'] > 300:  # Перевірка тривалості (до 5 хв)
                raise Exception("Відео перевищує 5 хвилин")
            
            # Завантаження відео
            ydl.download([url])
            return 'video.mp4'

    async def watcher(self, message):
        """Автоматичний завантажувач відео з YouTube"""
        chat_id = str(message.chat_id)

        # Перевіряємо, чи група дозволена
        if chat_id not in self.allowed_groups:
            return

        # Шукаємо посилання на YouTube в повідомленні
        yt_link_pattern = r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+|https?://youtu\.be/[\w-]+|https?://www\.youtube\.com/shorts/[\w-]+)'
        yt_links = re.findall(yt_link_pattern, message.text)

        if yt_links:
            url = yt_links[0]
            try:
                video_file = await self.download_video(url)
                await self.client.send_file(message.chat_id, video_file, reply_to=message.id)
                os.remove(video_file)
            except Exception as e:
                await message.reply(f"Помилка: {e}")
