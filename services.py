import re
from datetime import datetime, timedelta
import pandas as pd
from models import ChatMessage
from extensions import db
from flask import jsonify

def get_left_users():
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

    user_status = {}
    user_status_time = {}
    for msg in status_messages:
        if 'left this chatroom' in msg.message:
            user_status[msg.user] = 'left'
            user_status_time[msg.user] = msg.date
        elif 'has been removed from this chatroom' in msg.message:
            m = re.match(r'(.+?) has been removed from this chatroom', msg.message)
            if m:
                removed_user = m.group(1)
                user_status[removed_user] = 'removed'
                user_status_time[removed_user] = msg.date
        elif 'joined this chatroom' in msg.message:
            user_status[msg.user] = 'joined'
            user_status_time[msg.user] = msg.date

    left_or_removed_users = [user for user, status in user_status.items() if status in ('left', 'removed')]
    truly_left_users = set()
    for user in left_or_removed_users:
        last_status_time = user_status_time[user]
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
    return inactive_users

def get_active_user_stats(start_date, end_date=None):
    if end_date is None:
        end_date = datetime.now()
    
    # 활발한 사용자 기준: 해당 기간 동안 10개 이상의 메시지를 보낸 사용자
    active_users = db.session.query(
        ChatMessage.user,
        db.func.count(ChatMessage.id).label('message_count')
    ).filter(
        ChatMessage.date >= start_date,
        ChatMessage.date <= end_date,
        ~ChatMessage.user.in_(get_left_users())
    ).group_by(
        ChatMessage.user
    ).having(
        db.func.count(ChatMessage.id) >= 10
    ).all()
    
    if not active_users:
        return jsonify({
            'avg_age': None,
            'gender_ratio': None,
            'male_avg_age': None,
            'female_avg_age': None,
            'active_user_count': 0
        })
    
    # 사용자 정보 파싱
    user_stats = []
    current_year = datetime.now().year
    for user in active_users:
        # 이름/나이/성별/지역 형식에서 정보 추출
        parts = user.user.split('/')
        if len(parts) >= 3:
            try:
                birth_year = int(parts[1])
                # 00-99 형식의 연도 처리
                if birth_year < 100:
                    birth_year += 1900 if birth_year > 50 else 2000
                age = current_year - birth_year
                gender = parts[2].strip().upper()
                if gender in ['M', 'F', '남', '여']:
                    user_stats.append({
                        'age': age,
                        'gender': 'M' if gender in ['M', '남'] else 'F'
                    })
            except (ValueError, IndexError):
                continue
    
    if not user_stats:
        return jsonify({
            'avg_age': None,
            'gender_ratio': None,
            'male_avg_age': None,
            'female_avg_age': None,
            'active_user_count': len(active_users)
        })
    
    # 통계 계산
    total_age = sum(stat['age'] for stat in user_stats)
    avg_age = total_age / len(user_stats)
    
    male_stats = [stat for stat in user_stats if stat['gender'] == 'M']
    female_stats = [stat for stat in user_stats if stat['gender'] == 'F']
    
    male_avg_age = sum(stat['age'] for stat in male_stats) / len(male_stats) if male_stats else None
    female_avg_age = sum(stat['age'] for stat in female_stats) / len(female_stats) if female_stats else None
    
    gender_ratio = f"{len(male_stats)}:{len(female_stats)}" if male_stats and female_stats else None
    
    return jsonify({
        'avg_age': round(avg_age, 1),
        'gender_ratio': gender_ratio,
        'male_avg_age': round(male_avg_age, 1) if male_avg_age is not None else None,
        'female_avg_age': round(female_avg_age, 1) if female_avg_age is not None else None,
        'active_user_count': len(active_users)
    }) 