# -*- coding: utf-8 -*-

# Module author: @ВашНік (або залиште порожнім)

from .. import loader, utils
import random
import asyncio
from datetime import datetime, timedelta, timezone

@loader.tds
class PidorBotMod(loader.Module):
    """Модуль для гри 'Красавчик' та 'Підор' дня з повною статистикою"""

    strings = {"name": "PidorBot"}

    def __init__(self):
        # Сет для блокування одночасного запуску команд у чаті
        self.running_games = set()
        
        # 100 фраз для красавчика
        self.handsome_phrases = [
            "Дивимося аніме...",
            "Читаємо субтитри...",
            "Фарбуємо фігурки з вархаммера...",
            "Миємо стіни...",
            "Замішуємо протеінчик...",
            "Біжимо кукурудзяними полями...",
            "Міняємо термопасту...",
            "Граємо в 4К 165 ФПС...",
            "Тусімо в VR-кафе...",
            "Ріжемо кабеля...",
            "Смажимо сирники...",
            "Купуємо червону рибу...",
            "Жуєм бутерброд зі свининою...",
            "Заходим на фудкорт...",
            "Підключаємо російські проксі...",
            "Тюнінгуємо Волгу...",
            "Залазимо в підвал...",
            "Заряджаємо піксельфон...",
            "Обираємо Сяомі — топ за свої гроші...",
            "Рахуємо калорії...",
            "Дивимося альтернативну розмірну сітку...",
            "Заряджаємо бомбер...",
            "Міняємо термопасту...",
            "Бухаємо...",
            "Наматуємося на вал...",
            "Перепливаємо Тису...",
            "Полізаємо в буса...",
            "Проходимо ВЛК...",
            "Зливаємо скріни Аліоселі...",
            "Платимо податки...",
            "Реєструємо ФОП...",
            "Дивимося тіктоки...",
            "Тремо вареник Альонки...",
            "Гуляємо з мамо Вайбера...",
            "Кладемо їбалом в асфальт...",
            "Вимітаємо нахуй двоєчкою...",
            "Заливаємо бетон...",
            "Обмазуємося сгущонкою...",
            "Повертаємо Арбуза в чат...",
            "Не общаємося з таким мусором...",
            "Отвічаємо за слова...",
            "Таримо софтом Клюєва...",
            "Сідаємо на очко за тухлий базар...",
            "Няшимося з фембойчиками...",
            "Няшимося з собакою...",
            "Випікаємо піцу з теріякі..."
        ]

        # 100 фраз для підора
        self.pidor_phrases = [
            "Дивимося аніме...",
            "Читаємо субтитри...",
            "Фарбуємо фігурки з вархаммера...",
            "Миємо стіни...",
            "Замішуємо протеінчик...",
            "Біжимо кукурудзяними полями...",
            "Міняємо термопасту...",
            "Граємо в 4К 165 ФПС...",
            "Тусімо в VR-кафе...",
            "Ріжемо кабеля...",
            "Смажимо сирники...",
            "Купуємо червону рибу...",
            "Жуєм бутерброд зі свининою...",
            "Заходим на фудкорт...",
            "Підключаємо російські проксі...",
            "Тюнінгуємо Волгу...",
            "Залазимо в підвал...",
            "Заряджаємо піксельфон...",
            "Обираємо Сяомі — топ за свої гроші...",
            "Рахуємо калорії...",
            "Дивимося альтернативну розмірну сітку...",
            "Заряджаємо бомбер...",
            "Міняємо термопасту...",
            "Бухаємо...",
            "Наматуємося на вал...",
            "Перепливаємо Тису...",
            "Полізаємо в буса...",
            "Проходимо ВЛК...",
            "Зливаємо скріни Аліоселі...",
            "Платимо податки...",
            "Реєструємо ФОП...",
            "Дивимося тіктоки...",
            "Тремо вареник Альонки...",
            "Гуляємо з мамо Вайбера...",
            "Кладемо їбалом в асфальт...",
            "Вимітаємо нахуй двоєчкою...",
            "Заливаємо бетон...",
            "Обмазуємося сгущонкою...",
            "Повертаємо Арбуза в чат...",
            "Не общаємося з таким мусором...",
            "Отвічаємо за слова...",
            "Таримо софтом Клюєва...",
            "Сідаємо на очко за тухлий базар...",
            "Няшимося з фембойчиками...",
            "Няшимося з собакою...",
            "Випікаємо піцу з теріякі..."
        ]

    async def client_ready(self, client, db):
        self.db = db
        self.client = client

    def _get_kyiv_date(self):
        tz = timezone(timedelta(hours=3))
        return datetime.now(tz).strftime("%Y-%m-%d")

    @loader.unrestricted
    async def runcmd(self, message):
        """Вибрати красавчика дня"""
        await self._find_hero(message, "handsome")

    @loader.unrestricted
    async def pidorcmd(self, message):
        """Вибрати підора дня"""
        await self._find_hero(message, "pidor")
        
    @loader.unrestricted
    async def statscmd(self, message):
        """Статистика чату"""
        await self._stats_logic(message)

    async def _find_hero(self, message, role):
        chat_id = str(message.chat_id)
        lock_key = f"{chat_id}_{role}"

        # Перевіряємо, чи вже йде пошук у цьому чаті для цієї ролі
        if lock_key in self.running_games:
            return # Просто ігноруємо команду, щоб не спамити

        # Ставимо "замок"
        self.running_games.add(lock_key)

        try:
            today = self._get_kyiv_date()
            daily_data = self.db.get("PidorBot", "daily_data", {})
            stats_data = self.db.get("PidorBot", "stats_data", {})

            if chat_id not in daily_data:
                daily_data[chat_id] = {}
            if chat_id not in stats_data:
                stats_data[chat_id] = {}

            # Перевірка на сьогодні
            if daily_data[chat_id].get("date") == today and role in daily_data[chat_id]:
                winner_text = daily_data[chat_id][role]
                emoji = "🎉" if role == "handsome" else "🌈"
                title = "красавчик" if role == "handsome" else "ПІДОР"
                final_text = f"<b>{emoji} Сьогодні {title} дня - {winner_text}</b>"
                await message.respond(final_text)
                return

            # Учасники
            try:
                users = await message.client.get_participants(message.chat_id)
            except Exception:
                await message.respond("<b>Не вдалося отримати список учасників.</b>")
                return
                
            valid_users = [u for u in users if not u.bot and not u.deleted]
            if not valid_users:
                await message.respond("<b>В чаті немає підходящих гравців!</b>")
                return

            winner = random.choice(valid_users)
            name = (winner.first_name + (f" {winner.last_name}" if winner.last_name else "")).replace("<", "").replace(">", "")
            username = f"(@{winner.username})" if winner.username else ""
            user_mention = f"<a href='tg://user?id={winner.id}'>{name}</a> {username}"

            phrases_pool = self.handsome_phrases if role == "handsome" else self.pidor_phrases
            selected_phrases = random.sample(phrases_pool, 5)

            if daily_data[chat_id].get("date") != today:
                daily_data[chat_id] = {"date": today}

            # Відправляємо кожну фразу новим повідомленням
            for i, phrase in enumerate(selected_phrases):
                await message.respond(f"<b>{5-i} - {phrase}</b>")
                await asyncio.sleep(2)

            emoji = "🎉" if role == "handsome" else "🌈"
            title = "красавчик" if role == "handsome" else "ПІДОР"
            final_text = f"<b>{emoji} Сьогодні {title} дня - {user_mention}</b>"

            # Збереження
            daily_data[chat_id][role] = user_mention
            self.db.set("PidorBot", "daily_data", daily_data)

            winner_id = str(winner.id)
            if winner_id not in stats_data[chat_id]:
                stats_data[chat_id][winner_id] = {"handsome": 0, "pidor": 0, "name": name}

            stats_data[chat_id][winner_id][role] += 1
            stats_data[chat_id][winner_id]["name"] = name
            self.db.set("PidorBot", "stats_data", stats_data)

            # Відправляємо фінальне повідомлення
            await message.respond(final_text)

        finally:
            # Знімаємо "замок", незалежно від того, як завершився код (з помилкою чи без)
            self.running_games.discard(lock_key)

    async def _stats_logic(self, message):
        chat_id = str(message.chat_id)
        stats_data = self.db.get("PidorBot", "stats_data", {})

        if message.out:
            target_message = message
        else:
            target_message = await message.respond("<b>Завантаження...</b>")

        if chat_id not in stats_data or not stats_data[chat_id]:
            await target_message.edit("<b>📊 Статистика поки порожня!</b>")
            return

        chat_stats = stats_data[chat_id]
        h_top = sorted([u for u in chat_stats.items() if u[1]["handsome"] > 0], key=lambda x: x[1]["handsome"], reverse=True)
        p_top = sorted([u for u in chat_stats.items() if u[1]["pidor"] > 0], key=lambda x: x[1]["pidor"], reverse=True)

        msg = "<b>📊 Статистика чату:</b>\n\n"
        msg += "<b>😎 Топ Красавчиків:</b>\n"
        if not h_top: msg += "Поки немає.\n"
        for i, (uid, data) in enumerate(h_top[:10], 1):
            msg += f"{i}. <a href='tg://user?id={uid}'>{data['name']}</a> — {data['handsome']} раз(ів)\n"

        msg += "\n<b>🌈 Топ Підорів:</b>\n"
        if not p_top: msg += "Поки немає.\n"
        for i, (uid, data) in enumerate(p_top[:10], 1):
            msg += f"{i}. <a href='tg://user?id={uid}'>{data['name']}</a> — {data['pidor']} раз(ів)\n"

        await target_message.edit(msg)