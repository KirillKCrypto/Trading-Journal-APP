from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash, jsonify
from ..models import Trade
from .. import db
from datetime import datetime, date
from .import_api import import_notion_trades
import os
from werkzeug.utils import secure_filename

trades_bp = Blueprint('trades', __name__)
import_bp = Blueprint('import_api', __name__)
@trades_bp.route('/')
def index():
    query = Trade.query
    current_date = date.today().isoformat()

    # Получаем фильтры из запроса
    filters = {
        'symbol': request.args.get('symbol'),
        'session': request.args.get('session'),
        'position': request.args.get('position'),
        'result_type': request.args.get('result_type'),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
    }

    # Применяем фильтры
    if filters['symbol']:
        query = query.filter_by(symbol=filters['symbol'])
    if filters['session']:
        query = query.filter_by(session=filters['session'])
    if filters['position']:
        query = query.filter_by(position=filters['position'])
    if filters['result_type']:
        query = query.filter_by(result_type=filters['result_type'])


    # Фильтрация по дате FROM
    if filters['date_from']:
        try:
            date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
            query = query.filter(Trade.date >= date_from)
        except ValueError:
            pass

    # Фильтрация по дате TO
    if filters['date_to']:
        try:
            date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
            query = query.filter(Trade.date <= date_to)
        except ValueError:
            pass

    trades = query.order_by(Trade.date.desc()).all()

    rr_sum = 0
    rr_tp_values = []

    for t in trades:
        # Финансовый эффект от сделки в %
        pnl_percent = t.risk * t.rr * 100 if t.result_type == 'TP' else -t.risk * 100 if t.result_type == 'SL' else 0
        rr_sum += pnl_percent

        if t.result_type == 'TP':
            rr_tp_values.append(t.rr)  # тут оставляем чистый RR, не % (средний RR не должен быть в процентах)

    rr_sum = round(rr_sum, 2)
    rr_avg = round(sum(rr_tp_values) / len(rr_tp_values), 2) if rr_tp_values else 0

    # Уникальные значения для фильтров — берем по всем сделкам
    all_trades = Trade.query.all()
    unique = {
        'symbols': sorted(set(t.symbol for t in all_trades if t.symbol)),
        'sessions': sorted(set(t.session for t in all_trades if t.session)),
        'positions': sorted(set(t.position for t in all_trades if t.position)),
        'result_types': sorted(set(t.result_type for t in all_trades if t.result_type)),
    }

    return render_template('index.html',
                           trades=trades,
                           rr_sum=rr_sum,
                           rr_avg=rr_avg,
                           filters=filters,
                           unique=unique,
                           current_date=current_date)

@trades_bp.route('/trade/<int:trade_id>')
def trade_detail(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    return render_template('trades/detail.html', trade=trade)


@trades_bp.route('/add_trade', methods=['GET', 'POST'])
def add_trade():
    if request.method == 'POST':
        date = request.form.get('date')
        symbol = request.form.get('symbol')
        weekday = datetime.strptime(date, '%Y-%m-%d').strftime('%A') if date else ''
        session = request.form.get('session')
        position = request.form.get('position')
        bias = request.form.get('bias')
        logic = request.form.get('logic')
        entry_details = request.form.get('entry_details')
        risk = float(request.form.get('risk').replace('%', '')) / 100 if request.form.get('risk') else 0
        rr = float(request.form.get('rr')) if request.form.get('rr') else None
        result_type = request.form.get('result_type')
        mistakes = request.form.get('mistakes')
        notes = request.form.get('notes')

        screenshots_folder = os.path.join(current_app.static_folder, 'screenshots')
        os.makedirs(screenshots_folder, exist_ok=True)

        def save_screenshot(file_storage, prefix):
            if file_storage and file_storage.filename:
                filename = secure_filename(file_storage.filename)
                filename = f"{prefix}_{filename}"
                filepath = os.path.join(screenshots_folder, filename)
                file_storage.save(filepath)
                return f"screenshots/{filename}"
            return None

        screenshot_1h_path = save_screenshot(request.files.get('screenshot_1h'), '1h')
        screenshot_5m_path = save_screenshot(request.files.get('screenshot_5m'), '5m')
        screenshot_3m_path = save_screenshot(request.files.get('screenshot_3m'), '3m')

        trade = Trade(
            date=datetime.strptime(date, '%Y-%m-%d'),
            symbol=symbol,
            weekday=weekday,
            session=session,
            position=position,
            bias=bias,
            logic=logic,
            entry_details=entry_details,
            risk=risk,
            rr=rr,
            result_type=result_type,
            mistakes=mistakes,
            notes=notes,
            screenshot_1h_path=screenshot_1h_path,
            screenshot_5m_path=screenshot_5m_path,
            screenshot_3m_path=screenshot_3m_path
        )
        db.session.add(trade)
        db.session.commit()
        return redirect(url_for('trades.index'))

    sessions = ['ASIA', 'LONDON', 'NY']
    positions = ['Long', 'Short']
    result_types = ['TP', 'SL', 'BE']
    logics = ['Frank Manipulation', 'NY Manipulation', 'Fractal Raid', 'FVG Raid']
    risks = [0.5, 1, 2, 3]

    return render_template('trades/add.html', sessions=sessions, positions=positions,
                           result_types=result_types, logics=logics, risks=risks)


@trades_bp.route('/import_notion', methods=['GET', 'POST'])
def import_notion():
    if request.method == 'POST':
        # Получаем данные из формы
        notion_token = request.form.get('notion_token', '').strip()
        database_id = request.form.get('database_id', '').strip()

        # Если поля заполнены в форме, используем их, иначе берем из .env
        NOTION_TOKEN = notion_token if notion_token else os.getenv('NOTION_TOKEN')
        NOTION_DATABASE_ID = database_id if database_id else os.getenv('NOTION_DATABASE_ID')

        if not NOTION_TOKEN:
            flash("Необходимо указать Notion Token", 'error')
            return redirect(url_for('trades.import_notion'))

        if not NOTION_DATABASE_ID:
            flash("Необходимо указать Database ID", 'error')
            return redirect(url_for('trades.import_notion'))

        try:
            imported_trades = import_notion_trades(NOTION_TOKEN, NOTION_DATABASE_ID, db, Trade)
            flash(f"Успешно импортировано {len(imported_trades)} сделок из Notion", 'success')
            return redirect(url_for('trades.index'))
        except Exception as e:
            flash(f"Ошибка при импорте: {str(e)}", 'error')
            return redirect(url_for('trades.import_notion'))

    # GET запрос - показываем форму
    return render_template('trades/import.html')


@trades_bp.route('/delete_multiple', methods=['POST'])
def delete_multiple_trades():
    try:
        data = request.get_json()
        trade_ids = data.get('trade_ids', [])

        if not trade_ids:
            return jsonify({'success': False, 'error': 'No trades selected'}), 400

        # Преобразуем ID в integers
        trade_ids = [int(tid) for tid in trade_ids]

        # Удаляем выбранные сделки
        deleted_count = Trade.query.filter(Trade.id.in_(trade_ids)).delete()
        db.session.commit()

        return jsonify({'success': True, 'deleted_count': deleted_count})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500