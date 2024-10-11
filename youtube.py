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
        """Завантажує відео з YouTube, використовуючи yt-dlp, вибираючи якість за лімітом 50 МБ"""
        ydl_opts = {
            'outtmpl': 'video.mp4',         # Ім'я вихідного файлу
            'quiet': True,
            'username': 'oauth2',           # Використовуємо OAuth2 для авторизації
            'password': '',                 # Порожній пароль для OAuth2
        }

        # Використання to_thread для запуску блокуючого коду
        return await asyncio.to_thread(self._select_and_download_video, url, ydl_opts)

    def _select_and_download_video(self, url, ydl_opts):
        """Вибирає відповідний формат відео і завантажує його"""
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if info['duration'] > 300:  # Перевірка тривалості (до 5 хв)
                raise Exception("Відео перевищує 5 хвилин")

            # Отримуємо всі доступні формати і сортуємо за якістю
            formats = sorted(info['formats'], key=lambda x: x.get('height', 0), reverse=True)

            # Обираємо формат, який підходить за розміром
            suitable_format = None
            for f in formats:
                if f.get('filesize') and f['filesize'] <= 50 * 1024 * 1024:  # Ліміт 50 МБ
                    suitable_format = f
                    break

            if not suitable_format:
                raise Exception("Не вдалося знайти формат, який відповідає ліміту 50 МБ")

            # Оновлюємо параметри для завантаження вибраного формату
            ydl_opts['format'] = suitable_format['format_id']

            # Завантажуємо відео
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        return 'video.mp4'

    async def watcher(self, message):
        """Автоматичний завантажувач відео з YouTube"""
        chat_id = str(message.chat_id)

        # Перевіряємо, чи група дозволена
        if chat_id not in self.allowed_groups:
            return

        # Шукаємо посилання на YouTube в повідомленні
        yt_link_pattern = r'(https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w-]+)'
        yt_links = re.findall(yt_link_pattern, message.text)

        if yt_links:
            url = yt_links[0]
            try:
                video_file = await self.download_video(url)
                await self.client.send_file(message.chat_id, video_file, reply_to=message.id)
                os.remove(video_file)
            except Exception as e:
                await message.reply(f"Помилка: {e}")
