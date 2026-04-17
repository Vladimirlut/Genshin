# -*- coding: utf-8 -*-
# requires: emoji

from .. import loader
import re
import emoji
from collections import Counter

@loader.tds
class AntiSpamCleanerMod(loader.Module):
    """Automatically deletes spam/scam messages"""

    strings = {"name": "AntiSpamCleaner"}
    requires = ["emoji"]  # Юзербот автоматично встановить цю бібліотеку

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    def normalize_text(self, text: str) -> str:
        """Замінює латинські символи на схожі кириличні"""
        replace_map = str.maketrans({
            "a": "а", "e": "е", "o": "о", "p": "р", "c": "с",
            "y": "у", "x": "х", "k": "к", "b": "в", "m": "м",
            "t": "т", "i": "і", "h": "н", "A": "А", "B": "В",
            "C": "С", "E": "Е", "H": "Н", "K": "К", "M": "М",
            "O": "О", "P": "Р", "T": "Т", "X": "Х", "Y": "У",
        })
        return text.translate(replace_map)

    async def watcher(self, message):
        allowed_chats = [-1002104028407, -1001562619309]  # додавай свої чати

        if message.chat_id not in allowed_chats:
            return

        # ╔════════════════════════════════════════════╗
        # ║ 1️⃣ Умова №1 — переслано від каналу з короткою назвою ║
        # ╚════════════════════════════════════════════╝
        if getattr(message, "fwd_from", None):
            try:
                if getattr(message.fwd_from, "channel_id", None):
                    channel = await self.client.get_entity(message.fwd_from.channel_id)
                    title = str(getattr(channel, "title", "")).strip()
                    if len(title) == 1:  # лише 1 символ
                        await message.delete()
                        return
                elif getattr(message.fwd_from, "from_id", None):
                    sender = await self.client.get_entity(message.fwd_from.from_id)
                    title = str(getattr(sender, "title", "")).strip()
                    if len(title) == 1:
                        await message.delete()
                        return
            except Exception:
                pass

        # ╔════════════════════════════════════════════╗
        # Отримуємо ОРИГІНАЛЬНИЙ текст (до нормалізації)
        # ╚════════════════════════════════════════════╝
        orig_text = ""
        if getattr(message, "raw_text", None):
            orig_text = message.raw_text
        elif getattr(message, "caption", None):
            orig_text = message.caption

        if not orig_text:
            return

        lower_orig = orig_text.lower()

        # --- Витяг прихованих лінків (ССЫЛОЧКА, кнопки) ---
        hidden_links = []
        if getattr(message, "entities", None):
            for entity in message.entities:
                url = getattr(entity, "url", None)
                if url:
                    hidden_links.append(url.lower())

        if getattr(message, "reply_markup", None):
            try:
                for row in message.reply_markup.rows:
                    for button in row.buttons:
                        if getattr(button, "url", None):
                            hidden_links.append(button.url.lower())
            except Exception:
                pass

        # --- Регекс для доменів/посилань (використовуємо надалі) ---
        domain_regex = re.compile(r"(?:[a-z0-9-]+\.)+[a-z]{2,}", re.IGNORECASE)
        link_pattern = re.compile(r"(https?://|t\.me/|@|www\.|(?:[a-z0-9-]+\.)+[a-z]{2,})", re.IGNORECASE)

        # ╔════════════════════════════════════════════╗
        # ║ 4️⃣ Умова №4 — 70% емодзі та наявність лінка ║
        # ╚════════════════════════════════════════════╝
        # Видаляємо пробіли та переноси рядків для точного підрахунку співвідношення
        text_without_spaces = orig_text.replace(" ", "").replace("\n", "")
        if len(text_without_spaces) > 0:
            emoji_count = emoji.emoji_count(orig_text)
            emoji_ratio = emoji_count / len(text_without_spaces)
            
            # Якщо емодзі 70% або більше, І є будь-який лінк
            if emoji_ratio >= 0.70 and (link_pattern.search(lower_orig) or hidden_links):
                try:
                    await message.delete()
                    return
                except Exception:
                    pass

        # ╔════════════════════════════════════════════╗
        # 3️⃣ Умова №3 — 3 однакові лінки (перевіряємо ПЕРШИМ)
        # ╚════════════════════════════════════════════╝
        all_links = domain_regex.findall(lower_orig)

        for u in hidden_links:
            found = domain_regex.findall(u.lower())
            if found:
                all_links.extend(found)

        if all_links:
            link_counts = Counter([l.lower() for l in all_links])
            if any(count >= 3 for count in link_counts.values()):
                try:
                    await message.delete()
                    return
                except Exception:
                    pass

        # ╔════════════════════════════════════════════╗
        # 2️⃣ Умова №2 — підозрілі слова + лінк
        # ╚════════════════════════════════════════════╝
        text = self.normalize_text(lower_orig)

        bad_words = [
            "казино", "каз", "зарабатывай", "заработок", "выигр", "вийграл", "выигрыш",
            "залетело", "залет", "деп", "крут", "словил", "игра",
            "ставки", "ставка", "slot", "слот", "рулетка", "покер", "вулкан",
            "победа", "интим", "голые", "девушки", "18+", "эротика",
            "sex", "btc", "crypto", "ставь", "бонус", "ссылочка", "ссылку", "отлет", "отлёт", "тут", "фриспин", "спин", "👉", "сделка", "гарант", "банк", "ваучер", "цифр", "хорошие", "лимон", "ловл", "👍", "ка3"
        ]

        if any(word in text for word in bad_words) and (link_pattern.search(lower_orig) or hidden_links):
            try:
                await message.delete()
                return
            except Exception:
                pass