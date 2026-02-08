from notion_client import Client
from datetime import datetime
import os
import requests
from werkzeug.utils import secure_filename
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_image(image_url, filepath):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"[!] Не удалось скачать: {image_url}")
            return False
    except Exception as e:
        print(f"[!] Ошибка при скачивании изображения: {e}")
        return False

def process_trade_page(page, screenshot_folder, existing_trades_keys, notion, Trade):
    props = page['properties']
    try:
        symbol = props.get('Pair', {}).get('title', [])
        symbol = symbol[0]['plain_text'] if symbol else ''

        date_str = props.get('Date', {}).get('date', {})
        date_str = date_str.get('start') if date_str else None
        if not date_str:
            return None
        date = datetime.fromisoformat(date_str).date()

        if (date, symbol) in existing_trades_keys:
            print(f"[!] Сделка {symbol} {date} уже есть. Пропуск.")
            return None

        weekday = date.strftime('%A')
        session = props.get('Session', {}).get('select', {}).get('name', '')
        position = props.get('Position', {}).get('select', {}).get('name', '')
        direction = props.get('Direction', {}).get('select', {}).get('name', '')
        bias = props.get('BIAS', {}).get('select', {}).get('name', '')
        logic = props.get('LG', {}).get('select', {}).get('name', '')

        entry_details = props.get('Entry Details', {}).get('rich_text', [])
        entry_details = entry_details[0]['plain_text'] if entry_details else ''

        risk_str = props.get('Risk', {}).get('select', {}).get('name')
        if risk_str:
            try:
                risk = float(risk_str.replace('%', '')) / 100
            except ValueError:
                risk = None
        else:
            risk = None

        rr = props.get('RR', {}).get('number')
        rr = float(rr) if rr is not None else None

        result_type = props.get('Result', {}).get('select', {}).get('name', '')
        mistakes = props.get('Mistakes', {}).get('rich_text', [])
        mistakes = mistakes[0]['plain_text'] if mistakes else ''

        notes = props.get('Note', {}).get('rich_text', [])
        notes = notes[0]['plain_text'] if notes else ''

        profit = props.get('Profit', {}).get('number')
        profit = float(profit) if profit is not None else None

        win_rate = props.get('Win rate', {}).get('number')
        win_rate = float(win_rate) if win_rate is not None else None

        page_id = page['id']
        children = notion.blocks.children.list(block_id=page_id)
        image_blocks = [block for block in children['results'] if block['type'] == 'image']

        screenshots = [None, None, None]

        # Параллельно скачиваем до 3 изображений внутри сделки
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for i in range(min(len(image_blocks), 3)):
                image_url = image_blocks[i]['image']['file']['url']
                filename = secure_filename(f"{symbol}_{date}_{i+1}.png")
                filepath = os.path.join(screenshot_folder, filename)
                futures.append(executor.submit(download_image, image_url, filepath))

            for i, future in enumerate(futures):
                if future.result():
                    screenshots[i] = f"screenshots/{secure_filename(f'{symbol}_{date}_{i+1}.png')}"

        trade = Trade(
            date=date,
            symbol=symbol,
            weekday=weekday,
            session=session,
            position=position,
            direction=direction,
            bias=bias,
            logic=logic,
            entry_details=entry_details,
            risk=risk,
            rr=rr,
            result_type=result_type,
            mistakes=mistakes,
            notes=notes,
            profit=profit,
            win_rate=win_rate,
            screenshot_1h_path=screenshots[0],
            screenshot_5m_path=screenshots[1],
            screenshot_3m_path=screenshots[2]
        )

        print(f"[+] Импортирована: {symbol} {date}")
        return trade

    except Exception as e:
        print(f"[X] Ошибка при импорте сделки из Notion: {e}")
        return None

def import_notion_trades(notion_token, database_id, db, Trade):
    if not notion_token.startswith(('ntn_', 'secret_')):
        print(f"[!] Предупреждение: Необычный формат токена: {notion_token[:10]}...")

    try:
        notion = Client(auth=notion_token)
        imported_trades = []

        screenshot_folder = "static/screenshots"
        os.makedirs(screenshot_folder, exist_ok=True)

        existing_trades_keys = set(db.session.query(Trade.date, Trade.symbol).all())

        # Проверяем доступ к базе данных
        try:
            database = notion.databases.retrieve(database_id=database_id)
            print(f"[+] Подключено к базе данных: {database.get('title', [{}])[0].get('plain_text', 'Unknown')}")
        except Exception as e:
            raise Exception(f"Не удалось подключиться к базе данных: {str(e)}")

        next_cursor = None
        all_pages = []

        # Получаем все страницы целиком (с пагинацией)
        while True:
            response = notion.databases.query(
                database_id=database_id,
                start_cursor=next_cursor
            )
            all_pages.extend(response['results'])

            if not response.get('has_more'):
                break
            next_cursor = response.get('next_cursor')

        if not all_pages:
            print("[!] В базе данных не найдено сделок")
            return []

        print(f"[+] Найдено {len(all_pages)} страниц в Notion")

        # Параллельно обрабатываем страницы
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(process_trade_page, page, screenshot_folder, existing_trades_keys, notion, Trade): page
                for page in all_pages
            }

            for future in as_completed(futures):
                trade = future.result()
                if trade:
                    db.session.add(trade)
                    imported_trades.append(trade)
                    existing_trades_keys.add((trade.date, trade.symbol))

        db.session.commit()
        print(f"[+] Успешно импортировано {len(imported_trades)} сделок")
        return imported_trades

    except Exception as e:
        db.session.rollback()  # Откатываем изменения в случае ошибки
        raise Exception(f"Ошибка импорта из Notion: {str(e)}")

