import os
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from werkzeug.utils import secure_filename
from flask_cors import CORS
from collections import defaultdict
import numpy as np
import json
import re

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['STATIC_FOLDER'] = 'static'

db = SQLAlchemy(app)
for folder in [app.config['UPLOAD_FOLDER'], app.config['STATIC_FOLDER']]:
    if not os.path.exists(folder):
        os.makedirs(folder)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    user = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

def get_left_users():
    # Get all status messages (join/leave/remove) and all user messages
    status_messages = db.session.query(
        ChatMessage.user,
        ChatMessage.message,
        ChatMessage.date
    ).filter(
        db.or_(
            ChatMessage.message.like('%left this chatroom%'),
            ChatMessage.message.like('%joined this chatroom%'),
            ChatMessage.message.like('%has been removed from this chatroom%')
        )
    ).order_by(
        ChatMessage.date
    ).all()

    # Track the last status for each user
    user_status = {}
    user_status_time = {}
    for msg in status_messages:
        if 'left this chatroom' in msg.message:
            user_status[msg.user] = 'left'
            user_status_time[msg.user] = msg.date
        elif 'has been removed from this chatroom' in msg.message:
            # Extract the removed user from the message
            m = re.match(r'(.+?) has been removed from this chatroom', msg.message)
            if m:
                removed_user = m.group(1)
                user_status[removed_user] = 'removed'
                user_status_time[removed_user] = msg.date
        elif 'joined this chatroom' in msg.message:
            user_status[msg.user] = 'joined'
            user_status_time[msg.user] = msg.date

    # Now, for each user whose last status is 'left' or 'removed',
    # check if they have any message after that time. If not, exclude them.
    left_or_removed_users = [user for user, status in user_status.items() if status in ('left', 'removed')]
    truly_left_users = set()
    for user in left_or_removed_users:
        last_status_time = user_status_time[user]
        # Check if this user has any message after last_status_time
        later_message = db.session.query(ChatMessage).filter(
            ChatMessage.user == user,
            ChatMessage.date > last_status_time
        ).first()
        if not later_message:
            truly_left_users.add(user)
    return list(truly_left_users)

def process_csv_file(file_path):
    try:
        db.session.query(ChatMessage).delete()
        db.session.commit()
        df = pd.read_csv(file_path)
        df['Date'] = pd.to_datetime(df['Date'])
        for _, row in df.iterrows():
            message = ChatMessage(
                date=row['Date'],
                user=row['User'],
                message=row['Message']
            )
            db.session.add(message)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error processing CSV: {str(e)}")
        return False

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
        db.func.count(ChatMessage.id).label('message_count')
    ).filter(
        ChatMessage.date >= month_ago,
        ~ChatMessage.user.in_(left_users)
    ).group_by(
        ChatMessage.user
    ).order_by(
        db.func.count(ChatMessage.id).desc()
    ).limit(10).all()
    return jsonify([{'user': r.user, 'count': r.message_count} for r in result])

@app.route('/api/inactive_users/<int:days>')
def inactive_users(days):
    cutoff_date = datetime.now() - timedelta(days=days)
    return get_inactive_users(cutoff_date)

@app.route('/api/inactive_users_by_date', methods=['GET'])
def inactive_users_by_date():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    except (ValueError, TypeError):
        return jsonify({'error': '올바른 날짜 형식이 아닙니다 (YYYY-MM-DD)'}), 400
    return get_inactive_users(start_date, end_date)

def get_inactive_users(start_date, end_date=None):
    if end_date is None:
        end_date = datetime.now()
    left_users = get_left_users()
    active_users = db.session.query(
        ChatMessage.user
    ).filter(
        ChatMessage.date.between(start_date, end_date),
        ~ChatMessage.user.in_(left_users)
    ).distinct().all()
    active_users = [u.user for u in active_users]
    all_users = db.session.query(
        ChatMessage.user
    ).filter(
        ~ChatMessage.user.in_(left_users)
    ).distinct().all()
    all_users = [u.user for u in all_users]
    inactive_users = list(set(all_users) - set(active_users))
    return jsonify(inactive_users)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 