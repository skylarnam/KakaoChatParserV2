from flask import current_app as app
from flask import render_template, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename
from extensions import db
from models import ChatMessage
from services import get_left_users, process_csv_file, get_inactive_users, get_active_user_stats

@app.route('/')
def index():
    has_data = db.session.query(ChatMessage).first() is not None
    return render_template('index.html', has_data=has_data)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.config['STATIC_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다.'}), 400
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'CSV 파일만 업로드 가능합니다.'}), 400
    try:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        if process_csv_file(file_path):
            os.remove(file_path)
            return jsonify({'success': True})
        else:
            os.remove(file_path)
            return jsonify({'error': '파일 처리 중 오류가 발생했습니다.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/monthly_stats')
def monthly_stats():
    current_date = datetime.now()
    month_ago = current_date - timedelta(days=30)
    left_users = get_left_users()
    result = db.session.query(
        ChatMessage.user,
        db.func.count(ChatMessage.id).label('message_count'),
        db.func.sum(db.func.length(ChatMessage.message)).label('total_length'),
        db.func.avg(db.func.length(ChatMessage.message)).label('avg_length')
    ).filter(
        ChatMessage.date >= month_ago,
        ~ChatMessage.user.in_(left_users)
    ).group_by(
        ChatMessage.user
    ).order_by(
        db.func.count(ChatMessage.id).desc()
    ).limit(10).all()
    return jsonify([{
        'user': r.user,
        'count': r.message_count,
        'total_length': r.total_length,
        'avg_length': round(r.avg_length, 1) if r.avg_length else 0
    } for r in result])

@app.route('/api/inactive_users/<int:days>')
def inactive_users(days):
    cutoff_date = datetime.now() - timedelta(days=days)
    return jsonify(get_inactive_users(cutoff_date))

@app.route('/api/inactive_users_by_date', methods=['GET'])
def inactive_users_by_date():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except (ValueError, TypeError):
        return jsonify({'error': '올바른 날짜 형식이 아닙니다 (YYYY-MM-DD)'}), 400
    return jsonify(get_inactive_users(start_date, end_date))

@app.route('/api/chat_trend')
def chat_trend():
    left_users = get_left_users()
    result = db.session.query(
        db.func.date(ChatMessage.date).label('date'),
        db.func.count(ChatMessage.id).label('count')
    ).filter(
        ~ChatMessage.user.in_(left_users)
    ).group_by(
        db.func.date(ChatMessage.date)
    ).order_by(
        db.func.date(ChatMessage.date)
    ).all()
    return jsonify([{'date': str(r.date), 'count': r.count} for r in result])

@app.route('/api/users')
def get_users():
    left_users = get_left_users()
    users = db.session.query(
        ChatMessage.user
    ).filter(
        ~ChatMessage.user.in_(left_users)
    ).distinct().all()
    return jsonify([user.user for user in users])

@app.route('/api/user_stats/<path:username>')
def user_stats(username):
    current_date = datetime.now()
    month_ago = current_date - timedelta(days=30)
    total_messages = db.session.query(
        db.func.count(ChatMessage.id)
    ).filter(
        ChatMessage.date >= month_ago,
        ChatMessage.user == username
    ).scalar()
    daily_stats = db.session.query(
        db.func.date(ChatMessage.date).label('date'),
        db.func.count(ChatMessage.id).label('count')
    ).filter(
        ChatMessage.date >= month_ago,
        ChatMessage.user == username
    ).group_by(
        db.func.date(ChatMessage.date)
    ).order_by(
        db.func.date(ChatMessage.date)
    ).all()
    active_days = len(daily_stats)
    avg_messages = round(total_messages / active_days if active_days > 0 else 0, 1)
    return jsonify({
        'total_messages': total_messages,
        'active_days': active_days,
        'avg_messages': avg_messages,
        'daily_stats': [{'date': str(stat.date), 'count': stat.count} for stat in daily_stats]
    })

@app.route('/api/active_user_stats/<int:days>')
def active_user_stats(days):
    cutoff_date = datetime.now() - timedelta(days=days)
    return get_active_user_stats(cutoff_date)

@app.route('/api/active_user_stats_by_date')
def active_user_stats_by_date():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except (ValueError, TypeError):
        return jsonify({'error': '올바른 날짜 형식이 아닙니다 (YYYY-MM-DD)'}), 400
    return get_active_user_stats(start_date, end_date) 