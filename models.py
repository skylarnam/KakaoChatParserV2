from extensions import db

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    user = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False) 