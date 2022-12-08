#   by @m4xx1m

from .. import loader, utils  # pylint: disable=relative-beyond-top-level
import io
from PIL import Image, ImageOps
from telethon.tl.types import DocumentAttributeFilename
import logging

logger = logging.getLogger(__name__)

def register(cb):
    cb(WEBPtoPNGMod())


@loader.tds
class WEBPtoPNGMod(loader.Module):
    """WEBP to PNG"""
    strings = {
        "name": "WEBP to PNG"
    }

    async def client_ready(self, client, db):
        self.client = client
    
    @loader.sudo
    async def wtpcmd(self, message):
        """WEBP to PNG"""
        reply_message = await message.get_reply_message()
        image = io.BytesIO()
        await self.client.download_media(reply_message.media.document, image)
        image = Image.open(image)
        image_stream = io.BytesIO()
        image_stream.name = "png.png"
        image.save(image_stream, "PNG")
        image_stream.seek(0)
        await self.client.delete_messages(message.to_id, message.id)
        await self.client.send_file(message.to_id, image_stream, force_document = True)
    
    @loader.sudo
    async def ptwcmd(self, message):
        """PNG to WEBP"""
        reply_message = await message.get_reply_message()
        image = io.BytesIO()
        await self.client.download_media(reply_message.media.document, image)
        image = Image.open(image)
        image_stream = io.BytesIO()
        image_stream.name = "webp.webp"
        image.save(image_stream, "WEBP")
        image_stream.seek(0)
        await self.client.delete_messages(message.to_id, message.id)
        await self.client.send_file(message.to_id, image_stream, force_document = True)

    