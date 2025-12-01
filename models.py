import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'

# --- CONFIGURAÇÃO DO MYSQL ---
# Confirme se a senha e usuário estão corretos aqui
usuario = "root"
senha = "root" 
host = "127.0.0.1:3306"
banco = "timesend_db"

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{usuario}:{senha}@{host}/{banco}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280

db = SQLAlchemy(app)

# --- CLASSES ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) 
    is_admin = db.Column(db.Boolean, default=False) 

# AQUI ESTAVA O POSSÍVEL ERRO: O nome correto é 'telefone', não 'destinatario'
class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    criado_em = db.Column(db.String(20))

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    destinatario = db.Column(db.String(255), nullable=False) # Aqui sim é destinatario
    mensagem = db.Column(db.Text, nullable=True)
    imagem_path = db.Column(db.String(200), nullable=True)
    dias_semana = db.Column(db.String(50)) 
    horario = db.Column(db.String(5)) 
    ativo = db.Column(db.Boolean, default=True)

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
            print("[OK] Tabelas sincronizadas.")
        except Exception as e:
            print(f"[ERRO] {e}")