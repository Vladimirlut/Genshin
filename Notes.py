import logging

from .. import loader, utils

@loader.tds
class NotesMod(loader.Module):
    """Stores global notes (aka snips)"""
    strings = {"name": "Notes",
               "what_note": "<b>What note should be retrieved?</b>",
               "no_note": "<b>Note not found</b>",
               "save_what": "<b>You must reply to a message to save it to a note, or type the note.</b>",
               "what_name": "<b>You must specify what the note should be called?</b>",
               "saved": "<b>Note saved</b>",
               "notes_header": "<b>Saved notes:</b>\n\n",
               "notes_item": "<b>•</b> <code>{}</code>",
               "delnote_args": "<b>What note should be deleted?</b>",
               "delnote_done": "<b>Note deleted</b>",
               "delnotes_none": "<b>There are no notes to be cleared</b>",
               "delnotes_done": "<b>All notes cleared</b>",
               "notes_none": "<b>There are no saved notes</b>"}
    
    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    @loader.unrestricted
    async def savecmd(self, message):
        """Save a new note. Must be used in reply with one parameter (note name)"""
        # Разрешить использование только пользователям с определенными ID
        allowed_user_ids = {1182891440, 207714624}
        user_id = message.sender_id
        
        if user_id not in allowed_user_ids:
            await utils.answer(message, "<b>Ви не маєте дозволу на використання цієї команди.</b>")
            return
        args = utils.get_args(message)
        if not message.is_reply:
            await utils.answer(message, self.strings("save_what", message))
            return
        target = await message.get_reply_message()
        is_media = target.media is not None
        if is_media:
            # Якщо в повідомленні є медіафайли, відправляємо їх
            await self.client.send_file(2065476852, target.media, caption=target.text, force_document=True)
        else:
            # Якщо в повідомленні немає медіа, відправляємо лише текст
            await self.client.send_message(2065476852, target.text)
        
        await utils.answer(message, self.strings("saved", message))