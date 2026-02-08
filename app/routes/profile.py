from flask import Blueprint, render_template
from ..models import Trade


profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/profile')
def profile():
    trades = Trade.query.order_by(Trade.date).all()
    total_trades = len(trades)
    tp_trades = sum(1 for t in trades if t.result_type == 'TP')
    loss_trades = total_trades - tp_trades

    winrate_data = {
        'labels': ['TP', 'Loss'],
        'data': [tp_trades, loss_trades],
    }
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
    max_win_streak = max_loss_streak = current_win = current_loss = 0
    for t in trades:
        if t.result_type == 'TP':
            current_win += 1
            current_loss = 0
        elif t.result_type in ['SL', 'BE']:
            current_loss += 1
            current_win = 0
        max_win_streak = max(max_win_streak, current_win)
        max_loss_streak = max(max_loss_streak, current_loss)

    equity = 10000
    equity_data = [equity]
    equity_dates = ['Start']
    for t in trades:
        risk = float(t.risk) if t.risk else 0
        rr = float(t.rr) if t.rr else 0
        pnl = equity * rr * risk if t.result_type == 'TP' else -equity * risk if t.result_type in ['SL', 'BE'] else 0
        equity += pnl
        equity = round(equity, 2)
        equity_data.append(equity)
        equity_dates.append(t.date.strftime('%d.%m'))

    return render_template('profile/profile.html', total_trades=total_trades, winrate_data=winrate_data,
                           rr_sum=round(rr_sum, 2), rr_avg=rr_avg,
                           max_win_streak=max_win_streak, max_loss_streak=max_loss_streak,
                           equity_data=equity_data, equity_labels=equity_dates)