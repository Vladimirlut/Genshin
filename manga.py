from .. import loader, utils  # pylint: disable=relative-beyond-top-level
import aiohttp
import aiofiles
import os
import zipfile
import io
from asyncio import gather

# Базовий URL для зображень
IMAGE_BASE_URL = "https://img33.imgslib.link"

class MangaDownloaderMod(loader.Module):
    """Завантажувач манги"""
    strings = {
        "name": "Manga Downloader",
        "progress": "Завантажено {}%",
        "complete": "Усі глави завантажені. Вивантажую в ТГ...",
        "file_sent": "Насолоджуйся",
        "error": "Помилка: {}",
        "no_slug": "Не вказано slug манги. Приклад: -manga 168691--na-honjamaen-lebel-eob-lageunalokeu"
    }

    async def client_ready(self, client, db):
        self.client = client

    @loader.unrestricted
    async def mangacmd(self, message):
        """Команда для завантаження манги"""
        # Перевіряємо, чи є достатньо аргументів
        if len(message.text.split()) < 2:
            await self.send_message(message.chat_id, self.strings["no_slug"], message.id)
            return

        manga_slug = message.text.split()[1]
        base_folder = manga_slug
        cbz_filename = f"{manga_slug}.cbz"

        # Отримуємо список глав
        api_url = f"https://api.lib.social/api/manga/{manga_slug}/chapters"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    chapters_list = await response.json()
                    chapters_list = chapters_list['data']
                else:
                    await self.send_message(message.chat_id, self.strings["error"].format("Не вдалося отримати список глав."), message.id)
                    return

        total_chapters = len(chapters_list)
        step = max(1, total_chapters // 5)  # Оновлюємо кожні 20%

        # Надсилаємо початкове повідомлення з 0%
        progress_msg = await self.send_message(message.chat_id, self.strings["progress"].format(0), message.id)

        # Завантажуємо всі глави
        for index, chapter in enumerate(chapters_list):
            chapter_number = chapter['number']
            volume_number = chapter.get('volume', '1')

            chapter_data = await self.fetch_chapter_data(manga_slug, chapter_number, volume_number)
            if chapter_data:
                await self.download_chapter_images(chapter_data, f"{volume_number}_{chapter_number}", base_folder)

                # Оновлюємо прогрес лише кожні 20%
                if (index + 1) % step == 0 or index + 1 == total_chapters:
                    progress = int((index + 1) / total_chapters * 100)
                    await self.send_message(message.chat_id, self.strings["progress"].format(progress), progress_msg.id)
            else:
                await self.send_message(message.chat_id, self.strings["error"].format(f"Глава {chapter_number} тому {volume_number} не знайдена."), progress_msg.id)

        # Оновлюємо статус до завершення завантаження
        await self.send_message(message.chat_id, self.strings["complete"], progress_msg.id)

        # Конвертуємо всі завантажені зображення в один CBZ файл
        self.convert_all_to_cbz(base_folder, cbz_filename)

        # Відправляємо файл
        with open(cbz_filename, 'rb') as cbz_file:
            await self.client.send_file(message.chat_id, cbz_file, force_document=True, caption=self.strings["file_sent"])

        # Видаляємо тимчасові файли
        os.remove(cbz_filename)
        self.remove_folder(base_folder)

    async def send_message(self, chat_id, text, reply_to_msg_id=None):
        """Надсилає повідомлення або редагує існуюче, якщо є доступ"""
        try:
            if reply_to_msg_id:
                await self.client.edit_message(chat_id, reply_to_msg_id, text)
            else:
                return await self.client.send_message(chat_id, text)
        except Exception as e:
            print(f"Error in sending/editing message: {e}")
            if reply_to_msg_id:
                # В разі помилки редагування, надсилаємо нове повідомлення
                return await self.client.send_message(chat_id, text)
    
    async def fetch_chapter_data(self, manga_slug, chapter_number, volume_number):
        api_url = f"https://api.lib.social/api/manga/{manga_slug}/chapter?number={chapter_number}&volume={volume_number}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['data']
                else:
                    return None

    async def download_chapter_images(self, chapter_data, chapter_number, base_folder):
        chapter_folder = os.path.join(base_folder, f"chapter_{chapter_number}")
        if not os.path.exists(chapter_folder):
            os.makedirs(chapter_folder)

        async def download_page(page):
            image_url = f"{IMAGE_BASE_URL}{page['url']}" if page['url'].startswith("//") else page['url']
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        image_filename = os.path.join(chapter_folder, f"page_{page['slug']}.jpg")
                        async with aiofiles.open(image_filename, 'wb') as f:
                            await f.write(image_data)

        await gather(*[download_page(page) for page in chapter_data['pages']])

    def convert_all_to_cbz(self, base_folder, cbz_filename):
        with zipfile.ZipFile(cbz_filename, 'w') as cbz_file:
            for root, _, files in os.walk(base_folder):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_folder)
                    cbz_file.write(file_path, arcname)

    def remove_folder(self, folder):
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)
