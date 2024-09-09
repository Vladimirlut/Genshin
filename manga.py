from .. import loader, utils  # pylint: disable=relative-beyond-top-level
import aiohttp
import aiofiles
import os
import zipfile
import io
from asyncio import gather

# Базовий URL для зображень
IMAGE_BASE_URL = "https://img33.imgslib.link"
MAX_FILE_SIZE = 1.9 * 1024 * 1024 * 1024  # 1.9 ГБ

class MangaDownloaderMod(loader.Module):
    """Завантажувач манги"""
    strings = {
        "name": "Manga Downloader",
        "progress": "Завантажено {}%",
        "complete": "Усі глави завантажені. Завантажую в ТГ...",
        "file_sent": "Насолоджуйся",
        "error": "Помилка: {}",
        "no_slug": "Не вказано slug манги. Будь ласка, надайте slug після команди.",
        "file_part_sent": "Відправлено частину {} із {}."
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
        if progress_msg is None:
            await self.send_message(message.chat_id, self.strings["error"].format("Не вдалося надіслати повідомлення прогресу."), message.id)
            return

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
                    progress_msg = await self.send_message(message.chat_id, self.strings["progress"].format(progress), progress_msg.id)
                    if progress_msg is None:
                        await self.send_message(message.chat_id, self.strings["error"].format("Не вдалося оновити повідомлення прогресу."), message.id)
            else:
                await self.send_message(message.chat_id, self.strings["error"].format(f"Глава {chapter_number} тому {volume_number} не знайдена."), progress_msg.id)

        # Оновлюємо статус до завершення завантаження
        await self.send_message(message.chat_id, self.strings["complete"], progress_msg.id)

        # Конвертуємо всі завантажені зображення в частини CBZ файлу
        await self.create_split_cbz(base_folder, cbz_filename, message)

        # Видаляємо тимчасові файли
        self.remove_folder(base_folder)

    async def send_message(self, chat_id, text, reply_to_msg_id=None):
        """Надсилає повідомлення або редагує існуюче, якщо є доступ"""
        try:
            if reply_to_msg_id:
                return await self.client.edit_message(chat_id, reply_to_msg_id, text)
            else:
                return await self.client.send_message(chat_id, text)
        except Exception as e:
            print(f"Error in sending/editing message: {e}")
            # Надсилаємо нове повідомлення, якщо редагування не вдалося
            if reply_to_msg_id:
                return await self.client.send_message(chat_id, text)
            else:
                return None
    
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

    async def create_split_cbz(self, base_folder, cbz_filename, message):
        """Створює архіви розміром не більше 1.9 ГБ і відправляє їх"""
        part_num = 1
        current_size = 0
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
            for root, _, files in os.walk(base_folder):
                for file in sorted(files):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, base_folder)
                    file_size = os.path.getsize(file_path)

                    # Якщо додавання файлу перевищить обмеження, завершуємо поточний архів
                    if current_size + file_size > MAX_FILE_SIZE:
                        # Зберігаємо поточний архів як частину
                        zip_buffer.seek(0)
                        part_filename = f"{cbz_filename}.part{part_num}.cbz"
                        await self.send_cbz_part(message.chat_id, zip_buffer, part_filename, part_num)

                        # Очищаємо буфер та створюємо новий архів
                        zip_buffer = io.BytesIO()
                        current_size = 0
                        part_num += 1
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as cbz_file:
                            pass

                    # Додаємо файл до архіву
                    cbz_file.write(file_path, arcname)
                    current_size += file_size

            # Зберігаємо останню частину, якщо вона існує
            if current_size > 0:
                zip_buffer.seek(0)
                part_filename = f"{cbz_filename}.part{part_num}.cbz"
                await self.send_cbz_part(message.chat_id, zip_buffer, part_filename, part_num)

    async def send_cbz_part(self, chat_id, zip_buffer, part_filename, part_num):
        """Відправляє частину архіву"""
        zip_buffer.seek(0)
        await self.client.send_file(chat_id, zip_buffer, force_document=True, caption=self.strings["file_part_sent"].format(part_num, part_num))

    def remove_folder(self, folder):
        """Видаляє тимчасові файли і папки"""
        for root, dirs, files in os.walk(folder, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder)
