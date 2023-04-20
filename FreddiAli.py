from curses.ascii import isdigit
from distutils.file_util import move_file
from .. import loader, utils
from telethon import functions
import re
import os
import requests
import time
import urllib.parse
import hashlib
import random
import string
import json
import io

class FreddiAliMod(loader.Module):
    """
    Як юзать:
    $search m1 pg30 pr0.01 countryUA name (or file)
    m - методи:
    1. пошук на головній для новачка;
    2. звичайний пошук по алі.

    30 - кількість сторінок, за замовчуванням 30 (ДЕМО ВЕРСІЯ!!! МАКСИМАЛЬНЕ ЧИСЛО 30);
    0.01 - ціна, за замовчуванням 0.01;
    name (or file) - запит для пошуку, або реплай на файл, де більше 1-го запиту;
    
    Приклади:
    `$search` - юзає все по дефолту (країна Укр, ціна цент, сторінок 30, метод пошуку 1 (сторінка новачка))
    `$search countryIT` - ті ж центи, але в Італії
    `$search m2 член` - шукає товар по ключовому слову "член"
    """
    strings = {'name': 'FreddiAli'}
    
    async def delcmd(self, message):
        """$del"""
        allowed_chat_ids_file = 'allowed_chat_ids.txt'
        if message.reply_to:
            reply_message = await message.get_reply_message()
            user_ids = [reply_message.from_id]
            message = await utils.answer(message, f"<code>Видалено айді юзера з реплаю: {user_ids[0]}</code>")
        elif message.text:
            text = message.text
            pattern = re.compile(r'-?\d+')
            user_ids = pattern.findall(text)
            if not user_ids:
                # Якщо повідомлення порожнє, то додаємо chat_id повідомлення
                user_ids = [message.chat_id]
                message = await utils.answer(message, f"<code>Видалено айді цього чату: {message.chat_id}</code>")
            else:
                user_ids = [int(uid) for uid in user_ids] # перетворюємо на список цілих чисел

        # Відкрити файл allowed_chat_ids_file та прочитати його вміст
        with open(allowed_chat_ids_file, 'r') as f:
            allowed_chat_ids = [line.strip() for line in f]

        removed_ids = []
        for user_id in user_ids:
            if str(user_id) in allowed_chat_ids:
                allowed_chat_ids.remove(str(user_id))
                removed_ids.append(str(user_id))
        with open(allowed_chat_ids_file, 'w') as f:
            for chat_id in allowed_chat_ids:
                f.write(chat_id + '\n')
    
    async def addcmd(self, message):
        """$add"""
        allowed_chat_ids_file = 'allowed_chat_ids.txt'
        user_id = None
        # Перевірити, чи існує файл allowed_chat_ids_file
        if not os.path.exists(allowed_chat_ids_file):
            # Якщо файл не існує, то створити його та записати в нього перший айді
            with open(allowed_chat_ids_file, 'w') as f:
                f.write(str(message.chat_id) + '\n')
            return
        with open(allowed_chat_ids_file, 'r') as f:
            # Прочитати файли з айді чатів та створити з них множину
            allowed_chat_ids = set(line.strip() for line in f)

        if message.reply_to:
            reply_message = await message.get_reply_message()
            # Якщо був реплай, то додаємо айді користувача, на кого був реплай
            user_id = reply_message.from_id
            message = await utils.answer(message, f"<code>Додано айді з реплаю: {user_id}</code>")
        elif message.text:
            # Якщо не було реплая, але є текст повідомлення, то додаємо айді з повідомлення
            text = message.text
            pattern = re.compile(r'-?\d+')
            user_ids = pattern.findall(text)
            for user_id in user_ids:
                message = await utils.answer(message, f"<code>Додано айді з повідомлення: {user_id}</code>")
        if not user_id:
            # Якщо повідомлення порожнє, то додаємо chat_id повідомлення
            user_id = message.chat_id
            message = await utils.answer(message, f"<code>Додано айді цього чату: {user_id}</code>")

        if str(user_id) in allowed_chat_ids:
            # Якщо айді користувача вже міститься у множині allowed_chat_ids, то просто повідомляємо про це
            message = await utils.answer(message, f"<code>Користувач з айді {user_id} вже міститься у списку дозволених</code>")
            print(f"Користувач з айді {user_id} вже міститься у списку дозволених")
        else:
            # Якщо айді користувача ще не міститься у множині allowed_chat_ids, то додаємо його
            allowed_chat_ids.add(str(user_id))

            # Записати змінену множину в файл allowed_chat_ids_file
            with open(allowed_chat_ids_file, 'w') as f:
                f.write('\n'.join(allowed_chat_ids))
    
    @loader.unrestricted
    async def searchcmd(self, message):
        """$search шнурок"""
        messaget = message
        m_text = utils.get_args_raw(message)
        chat_id = message.chat_id
        print(chat_id)
        allowed_chat_ids_file = 'allowed_chat_ids.txt'
        with open(allowed_chat_ids_file, 'r') as f:
            # Прочитати файли з айді чатів та створити з них множину
            allowed_chat_ids = set(line.strip() for line in f)
        if str(chat_id) in allowed_chat_ids:
            try:
                productIdFile = 'productIds.txt'
                nodeFile = 'node.txt'
                start_time = time.time()
                session = requests.Session()
                P = 1
                PARSED = []

                def parse_m_text(m_text, default_m='1', default_page='30', default_price='0.01', default_country='UA', default_hour='5', default_name='dildo'):
                    m_match = re.search(r'm(\d+)', m_text)
                    page_match = re.search(r'pg(\d+)', m_text)
                    price_match = re.search(r'pr(\d+(?:\.\d+)?|\.\d+)', m_text)
                    hour_match = re.search(r'h(\d+)', m_text)
                    country_match = re.search(r'country([a-zA-Z]{2})', m_text)

                    # Remove found parameters from the string
                    m_text = re.sub(r'm\d+ ', '', m_text)
                    m_text = re.sub(r'pg\d+ ', '', m_text)
                    m_text = re.sub(r'pr\d+(\.\d+)? ', '', m_text)
                    m_text = re.sub(r'h\d+ ', '', m_text)
                    m_text = re.sub(r'country([a-zA-Z]{2}) ', '', m_text)

                    name_match = re.search(r'(.+)', m_text)

                    m = m_match.group(1) if m_match else default_m
                    if page_match:
                        page_value = int(page_match.group(1))
                        page = min(page_value, 100) if page_value > 100 else page_value
                    else:
                        page = int(default_page)
                    price = price_match.group(1) if price_match else default_price
                    hour = hour_match.group(1) if hour_match else default_hour
                    country = country_match.group(1) if country_match else default_country
                    name = name_match.group(1) if name_match else default_name

                    return m, page, price, hour, country, name

                m, page, price, hour, country, name = parse_m_text(m_text)
                filename = (country + '.html')

                def get_sign(saved_cookies, data):
                    if '_' in saved_cookies:
                        token = saved_cookies.split('_')[0]
                    else:
                        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
                    app_key = '24815441'
                    t = str(int(time.time() * 1000))
                    concatenated_string = f"{token}&{t}&{app_key}&{data}"
                    sign = hashlib.md5(concatenated_string.encode()).hexdigest()
                    rnd = t
                    return sign, rnd

                def is_price_below(t, price, m):
                    if m == '1':
                        if "freeShipping" in t and t["freeShipping"] == True:
                            price_float = float(t["minPrice"].replace("US $", "").replace(",", "").replace("$", "").strip())
                            return ("US $" in t["minPrice"] and price_float <= float(price)) or (
                                    "$" in t["minPrice"] and price_float <= float(price))
                        else:
                            return False
                    elif m == '2':
                        if "sellingPoints" in t and any(sp.get("tagContent", {}).get("tagText", "") == "Free shipping" for sp in
                                                        t.get("sellingPoints", [])):
                            price_float = float(
                                t["prices"]["salePrice"]["formattedPrice"].replace("US $", "").replace(",", "").replace("$",
                                                                                                                        "").strip())
                            return ("US $" in t["prices"]["salePrice"]["formattedPrice"] and price_float <= float(price)) or (
                                    "$" in t["prices"]["salePrice"]["formattedPrice"] and price_float <= float(price))
                        else:
                            return False
                    else:
                        return False

                def parse_search(name, P, price, nodeFile, productIdFile, PARSED, filename, m):
                    name1 = urllib.parse.quote_plus(urllib.parse.unquote_plus(name).replace(' ', '-'))
                    spm = ''.join(random.choices(string.ascii_letters, k=14))
                    url = 'https://www.aliexpress.com/w/wholesale-{}.html?spm=a2g0o.home.100000001.3.{}&SearchText={}&page={}'
                    response = session.get(url.format(name1, spm, name, P))
                    t = re.search(r'{"itemType".*"x_object_id":"[\d]+"}}}', response.text)
                    if not t:
                        t = re.search(r'{"itemType".*{"color":"#FD384F"}}}', response.text)
                        if not t:
                            return
                    t = ('[' + t[0] + ']')
                    parse_response(t, price, nodeFile, productIdFile, PARSED, filename, m)

                def parse_response(t, price, nodeFile, productIdFile, PARSED, filename, m):
                    t = json.loads(t)

                    # Filter and map results
                    result = list(
                        map(
                            lambda t: {
                                "productId": t["productId"],
                                "imgUrl": t["productImage"] if m == '1' else t["image"]["imgUrl"],
                                "salePrice": t["minPrice"] if m == '1' else t["prices"]["salePrice"]["formattedPrice"],
                            },
                            filter(
                                lambda t: is_price_below(t, price, m),
                                t,
                            ),
                        )
                    )

                    # Append new results to node.txt file
                    for t in result:
                        if os.path.isfile(productIdFile):
                            with open(productIdFile, 'r+') as file:
                                contents = file.read().strip()
                                if str(t['productId']) not in contents:
                                    PARSED.append(t)
                                    file.write(f"{t['productId']}\n")
                                    with open(nodeFile, 'a') as node_file:
                                        node_file.write(
                                            f"{t['productId']} salePrice={t['salePrice']} imgUrl={t['imgUrl'] if t['imgUrl'].startswith('https') else 'https:' + t['imgUrl']} \n")
                                    with open(filename, 'r') as html_file:
                                        contents = html_file.read()
                                    new_product = f"""<div class="product">
                                <a href="https://www.aliexpress.com/item/{t['productId']}.html">
                                    <img src="{t['imgUrl'] if t['imgUrl'].startswith('https') else 'https:' + t['imgUrl']}" alt="Product image for {t['productId']}">
                                </a>
                                <div class="product-details">
                                    <div class="price">{t['salePrice']}</div>
                                </div>
                            </div>\n"""
                                    index = contents.find('<div id="products" class="products-container">') + len(
                                        '<div id="products" class="products-container">')
                                    contents = contents[:index] + new_product + contents[index:]
                                    with open(filename, 'w') as html_file:
                                        html_file.write(contents)
                                else:
                                    continue
                        else:
                            PARSED.append(t)
                            with open(productIdFile, 'w') as file:
                                file.write(f"{t['productId']}\n")
                            with open(nodeFile, 'w') as node_file:
                                node_file.write(
                                    f"{t['productId']} salePrice={t['salePrice']} imgUrl={t['imgUrl'] if t['imgUrl'].startswith('https') else 'https:' + t['imgUrl']} \n")
                            with open(filename, 'r') as html_file:
                                contents = html_file.read()
                            new_product = f"""<div class="product">
                                <a href="https://www.aliexpress.com/item/{t['productId']}.html">
                                    <img src="{t['imgUrl'] if t['imgUrl'].startswith('https') else 'https:' + t['imgUrl']}" alt="Product image for {t['productId']}">
                                </a>
                                <div class="product-details">
                                    <div class="price">{t['salePrice']}</div>
                                </div>
                            </div>\n"""
                            index = contents.find('<div id="products" class="products-container">') + len(
                                '<div id="products" class="products-container">')
                            contents = contents[:index] + new_product + contents[index:]
                            with open(filename, 'w') as html_file:
                                html_file.write(contents)
                                # Filter out products already in PARSED
                                new_results = [t for t in result if t["productId"] not in [p["productId"] for p in PARSED]]
                                for t in new_results:
                                    PARSED.append(t)
                                    with open(productIdFile, 'a') as file:
                                        file.write(f"{t['productId']}\n")
                                    with open(nodeFile, 'a') as node_file:
                                        node_file.write(
                                            f"{t['productId']} salePrice={t['salePrice']} imgUrl={t['imgUrl'] if t['imgUrl'].startswith('https') else 'https:' + t['imgUrl']} \n")

                                    with open(filename, "r") as html_file:
                                        contents = html_file.readlines()
                                        for index, line in enumerate(contents):
                                            if '<div id="products" class="products-container">' in line:
                                                new_product = f"""<div class="product">
                                            <a href="https://www.aliexpress.com/item/{t["productId"]}.html">
                                                <img src="{t["imgUrl"] if t["imgUrl"].startswith("https") else "https:" + t["imgUrl"]}" alt="Product image for {t["productId"]}">
                                            </a>
                                            <div class="product-details">
                                                <div class="price">{t["salePrice"]}</div>
                                            </div>
                                        </div>\n"""
                                                contents.insert(index + 1, new_product)
                                                break
                                        with open(filename, "w") as html_file:
                                            contents = "".join(contents)
                                            html_file.write(contents)

                                return PARSED

                htmlf = '''<!DOCTYPE html>
                <html>
                <head>
                  <meta charset="UTF-8">
                  <title>Товари</title>
                    <style>
                        * {
                            box-sizing: border-box;
                            font-family: Arial, sans-serif;
                            margin: 0;
                            padding: 0;
                        }
                        body {
                            background-color: #222;
                            color: #fff;
                            font-size: 14px;
                            line-height: 1.5;
                        }
                        h1 {
                            font-size: 24px;
                            font-weight: bold;
                            text-align: center;
                            margin: 20px 0;
                        }
                        .products-container {
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                            grid-gap: 10px;
                            margin: 0 20px;
                        }
                        .product {
                            background-color: #333;
                            border-radius: 5px;
                            overflow: hidden;
                            padding: 10px;
                            text-align: center;
                        }
                        .product img {
                            display: block;
                            margin: 0 auto;
                            max-width: 100%;
                        max-height: 203px;}
                        .product p {
                            font-size: 14px;
                            margin-top: 10px;
                            text-align: center;
                        }
                        .product-details .old-price {
                            color: #999;
                            font-size: 12px;
                            text-decoration: line-through;
                        }
                        .product-details .price {
                            color: #F3F6F4;
                            font-size: 16px;
                            font-weight: bold;
                        margin-top: 10px;}
                        .product .prices {
                            display: flex;
                            justify-content: center;
                            margin-top: 10px;
                        }
                        .product .prices div {
                            margin: 0 10px;
                        }
                    </style>
                </head>
                <body>
                    <h1>Халява</h1>
                    <div id="products" class="products-container"></div>
                    <script src="./script.js"></script>
                </body>
                </html>'''

                headers = {
                    "Connection": "keep-alive",
                    "sec-ch-ua": '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
                    "Content-Type": "application/json;charset=UTF-8",
                    "bx-v": "2.2.3",
                    "sec-ch-ua-mobile": "?0",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
                    "sec-ch-ua-platform": "Windows",
                    "Accept": "*/*",
                    "Origin": "https://www.aliexpress.com",
                    "Sec-Fetch-Site": "same-origin",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Dest": "empty",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Accept-Language": "ru-UA,ru;q=0.9,uk-UA;q=0.8,uk;q=0.7,ru-RU;q=0.6,en-US;q=0.5,en;q=0.4",
                }
                session.headers.update(headers)

                with open(productIdFile, 'w', encoding='utf-8') as f:
                    f.write('''''')
                with open(nodeFile, 'w', encoding='utf-8') as f:
                    f.write('''''')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(htmlf)
                print(f'm={m}, page={page}, price={price}, hour={hour}, name={name}')

                url = 'https://login.aliexpress.com/setCommonCookie.htm?currency=USD&region=' + country + '&bLocale=en_US&site=glo'
                response = None
                while response is None or response.status_code != 200:
                    response = session.get(url)
                    if response.status_code == 200:
                        # Ваш код для обробки успішного запиту
                        print("Запит успішний")
                    else:
                        # Ваш код для обробки неуспішного запиту
                        print(f"Код відповіді: {response.status_code}. Повторюємо запит.")
                if m == '1':
                    message = await messaget.respond(f"<b>Виконується пошук товарів. Країна: </b><code>{country}</code></b>, ціна: </b><code>${price}</code>")
                    rnd = round(time.time() * 1000)
                    url = f"https://ae.mmstat.com/eg.js?t={rnd}"
                    response = None
                    while response is None or response.status_code != 200:
                        response = session.get(url)
                        if response.status_code == 200:
                            # Ваш код для обробки успішного запиту
                            print("Запит успішний")
                        else:
                            # Ваш код для обробки неуспішного запиту
                            print(f"Код відповіді: {response.status_code}. Повторюємо запит.")
                    pattern = re.compile(r'goldlog\.Etag="(.+?)";goldlog\.stag')
                    match = pattern.search(response.text)
                    if match:
                        # якщо знайдено, зберігаємо збіг в змінну cna
                        cna = match.group(1)
                    else:
                        cna = 'kg426kfuf5v743f5f436u34fv7i34f'
                    data = '{"appVersion":"292","clientType":"web","positionId":"NewUserZoneLanding_page","deviceId":"' + cna + '","lang":"en_US","currency":"USD","shipToCountry":"' + country + '","ext":"{\\"pageParam\\":{\\"widgetId\\":null,\\"productId\\":null,\\"zoneBenefitType\\":\\"gift\\"}}"}'
                    dataurl = urllib.parse.quote(data)
                    sign, rnd = get_sign('', data)

                    url = 'https://acs.aliexpress.com/h5/mtop.aliexpress.usertouch.houyi.launchrule.runtime.pull/2.0/?jsv=2.7.0&appKey=24815441&t={}&sign={}&api=mtop.aliexpress.usertouch.houyi.launchRule.runtime.pull&v=2.0&isMajorRequest=true&type=jsonp&dataType=jsonp&callback=mtopjsonp2&data={}'
                    response = session.get(url.format(rnd, sign, dataurl))
                    saved_cookies = response.cookies.get('_m_h5_tk', '')
                    sign, rnd = get_sign(saved_cookies, data)
                    response = session.get(url.format(rnd, sign, dataurl))
                    saved_cookies = session.cookies.get('_m_h5_tk', '')

                    # Find postback value
                    postback = re.search(r'"postback":"([a-f0-9-]+)"', response.text)
                    if postback:
                        postback = postback.group(1)

                    response = response.text.replace('\\"', '"')
                    response = response.replace('"{"pricePre"', '{"pricePre"')
                    response = response.replace('}","productImage', '},"productImage')

                    # Parse JSON string and extract relevant data
                    t = re.findall(r'{"widgetOrigin":"tpp","onClick".*productAverageStar":"\d.\d"}', response)
                    t = ('[' + t[0] + ']')
                    t = re.sub(r'\],"showDiscount".*"productList":\[\s*', ',', t)
                    parse_response(t, price, nodeFile, productIdFile, PARSED, filename, m)
                    # Було тут

                    P = 2
                    page = int(page)
                    while P < page:
                        data = '{{"widget_id":101001177891,"postback":"{}","limit":12,"offset":12,"page":{},"locale":"en_US","currency":"USD","shipToCountry":"{}","platform":"pc","imageSize":"350x350"}}'.format(
                            postback, P, country)
                        sign, rnd = get_sign(saved_cookies, data)
                        dataurl = urllib.parse.quote(data)
                        url = 'https://acs.aliexpress.com/h5/mtop.aliexpress.usertouch.products.query/1.0/?jsv=2.7.0&appKey=24815441&t={}&sign={}&api=mtop.aliexpress.usertouch.products.query&v=1.0&type=jsonp&dataType=jsonp&callback=mtopjsonp{}&data={}'
                        response = session.get(url.format(rnd, sign, P, dataurl))
                        saved_cookies = session.cookies.get('_m_h5_tk', '')
                        response = response.text.replace('\\"', '"')
                        response = response.replace('"{"pricePre"', '{"pricePre"')
                        response = response.replace('}","widgetId', '},"widgetId')
                        response = re.sub(r'(?<="productTitle":")(.*?)(?=","trace")', 'Name', response)

                        # Parse JSON string and extract relevant data
                        t = re.findall(r'{"discount".*"widgetOrigin":"tpp"}', response)
                        t = ('[' + t[0] + ']')
                        parse_response(t, price, nodeFile, productIdFile, PARSED, filename, m)
                        # Збільшення P на 1
                        P += 1
                    with open(filename, "rb") as file:
                        requestText = ('<b>Пошук був з такими параметрами: метод - </b><code>пошук на сторінці новачка</code><b>, макс. ціна - </b><code>$' + str(
                            price) + '</code><b>, сторінок/запитів - </b><code>' + str(P) + '</code><b>)</b>')
                        out = io.BytesIO(file.read())
                        out.name = filename
                        out.seek(0)
                        await message.delete()
                        await messaget.respond(requestText, file=out)
                    # hour = int(hour)
                    # while (time.time() - start_time) < (hour * 60 * 60):
                if m == '2':
                    message = await messaget.respond(f"<b>Виконується пошук товарів. Ключове слово: </b><code>{name}</code><b>, країна: </b><code>{country}</code><b>, ціна: </b><code>${price}</code>")
                    page = int(page)
                    reply = await message.get_reply_message()
                    if messaget.is_reply:
                        items = await messaget.get_reply_message()
                        if items.document:
                            if not reply or not reply.file:
                                await messaget.respond("<b>Не вдалося знайти файл у відповіді.</b>")
                                return
                            file = await reply.download_media(bytes)
                            content = file.decode('utf-8')  # змінна content міститиме зміст файлу
                            lines = content.split('\n')
                            count = 0  # змінна-лічильник
                            for line in lines:
                                if count >= 5:  # перевірка кількості прочитаних рядків
                                    break
                                name = line.strip()  # змінна name міститиме поточний рядок з файлу без пробілів на початку та в кінці
                                P = 1
                                await message.edit(f"<b>Шукаю :</b><code>{name}</code>")
                                while P <= page:
                                    parse_search(name, P, price, nodeFile, productIdFile, PARSED, filename, m)
                                    P += 1
                            with open(filename, "rb") as file:
                                requestText = (
                                            '<b>Пошук був з такими параметрами: метод - пошук по ключовим словам в файлі, макс. ціна - </b><code>$' + str(
                                        price) + '</code><b>, сторінок/запитів - </b><code>' + str(P) + '</code><b>)</b>')
                                out = io.BytesIO(file.read())
                                out.name = filename
                                out.seek(0)
                                await message.delete()
                                await messaget.respond(requestText, file=out)
                    else:
                        while P <= page:
                            parse_search(name, P, price, nodeFile, productIdFile, PARSED, filename, m)
                            P += 1
                        with open(filename, "rb") as file:
                            requestText = ('<b>Пошук був з такими параметрами: метод - пошук по ключовому слову </b><code>' + name + '</code><b>, макс. ціна - </b><code>$' + str(price) + '</code><b>, сторінок/запитів - </b><code>' + str(P) + '</code><b>)</b>')
                            out = io.BytesIO(file.read())
                            out.name = filename
                            out.seek(0)
                            await message.delete()
                            await messaget.respond(requestText, file=out)

            except Exception as e:
                await messaget.edit('Error ' + str(e))
                reply = await messaget.get_reply_message()
                return
        else:
            return