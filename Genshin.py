from .. import loader, utils
from requests import get
from io import BytesIO
from random import randint, choice
from PIL import Image, ImageFont, ImageDraw
from textwrap import wrap

class GenshinMod(loader.Module):
	"""Лольки геншина.
	Как использовать:
	.gi@vladimirlut *лолька* текст
	Пример:
	.gi@vladimirlut diona го бухать"""
	strings = {
		"name": "Genshin"
	}

	async def client_ready(self, client, db):
		self.client = client

	
	@loader.owner
	async def gicmd(self, message):
		"""Злая Паймон: pai
	Добрая Паймон: paim
	Смущающаяся Паймон: paimm
	Добрая Кли: klee
        Кли в маске: kleea
	Диона со стаканом: diona
	Просто Диона: dionaa
	Цици "Понимаю": qiqi
	Голодная Цици: qiqia
	Записывающая Цици: qiqiq
        New: Саю: sayu"""
		clrs = {'klee1': 101, 'klee': 2, 'qiqi': 3, 'qiqia': 4, 'diona1': 105, 'diona': 1, 'paim': 5, 'pai': 6, 'paimm': 7, 'qiqiq': 8, 'dionaa': 9, 'kleea': 10, 'sayu':11}
		"""текст или реплай"""
		clr = randint(1,11)
		text = utils.get_args_raw(message)
		reply = await message.get_reply_message()
		if text in clrs:
			clr = clrs[text]
			text = None
		if not text:
			if not reply:
				await bruh(message, message.sender)
				return
			if not reply.text:
				await bruh(message, reply.sender)
				return
			text = reply.raw_text
		
		if text.split(" ")[0] in clrs:
			clr = clrs[text.split(" ")[0]]
			text = " ".join(text.split(" ")[1:])
			
		if text == "colors":
			await message.edit("Доступные цвета:\n"+("\n".join([f"• <code>{i}</code>" for i in list(clrs.keys())])))
			return
		
		url = "https://raw.githubusercontent.com/Vladimirlut/Genshin/main/"
		font = ImageFont.truetype(BytesIO(get(url+"bold.ttf").content), 60)
		imposter = Image.open(BytesIO(get(f"{url}{clr}.png").content))
		text_ = "\n".join(["\n".join(wrap(part, 12)) for part in text.split("\n")])
		w, h = ImageDraw.Draw(Image.new("RGB", (1,1))).multiline_textsize(text_, font, stroke_width=2)
		text = Image.new("RGBA", (w+30, h+60))
		ImageDraw.Draw(text).multiline_text((15,15), text_, "#FFF", font, stroke_width=2, stroke_fill="#000")
		w = imposter.width + text.width + 10
		h = max(imposter.height, text.height)
		image = Image.new("RGBA", (w, h))
		image.paste(imposter, (0, h-imposter.height), imposter)
		image.paste(text, (w-text.width, 0), text)
		image.thumbnail((512, 512))
		output = BytesIO()
		output.name = "lolifromgenshin.webp"
		image.save(output)
		output.seek(0)
		await message.delete()
		await message.client.send_file(message.to_id, output, reply_to=reply)
		
async def bruh(message, user):
	fn = user.first_name
	ln = user.last_name
	name = fn + (" "+ln if ln else "")
	name = "<b>"+name
	await message.edit(name+"не отправил текст! Ответь на текстовое сообщение, либо напиши после команды свой текст</b>")
