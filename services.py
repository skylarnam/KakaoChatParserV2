import re
from datetime import datetime, timedelta
import pandas as pd
from models import ChatMessage
from extensions import db

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