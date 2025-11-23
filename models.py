import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'

# --- CONFIGURAÇÃO DO MYSQL ---
# ATENÇÃO: Você precisa alterar os dados abaixo para os do SEU banco MySQL.
# Se estiver usando XAMPP local, geralmente user='root' e senha='' (vazia).
# Se não tiver criado o banco ainda, entre no MySQL e rode: CREATE DATABASE timesend_db;

usuario = "root"        # Seu usuário do MySQL
senha = "root"              # Sua senha do MySQL
host = "127.0.0.1:3306"      # O endereço (localhost ou IP da nuvem)
banco = "timesend_db"   # O nome do banco que você criou

# Monta a URL de conexão
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{usuario}:{senha}@{host}/{banco}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280

db = SQLAlchemy(app)

# --- CLASSES (AS TABELAS DO BANCO) ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) 
    is_admin = db.Column(db.Boolean, default=False) 

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False, unique=True)
    criado_em = db.Column(db.String(20))

class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    destinatario = db.Column(db.String(20), nullable=False)
    mensagem = db.Column(db.Text, nullable=True)
    imagem_path = db.Column(db.String(200), nullable=True)
    dias_semana = db.Column(db.String(50)) 
    horario = db.Column(db.String(5)) 
    ativo = db.Column(db.Boolean, default=True)

# --- BLOCO DE INICIALIZAÇÃO (SEM EMOJIS PARA NÃO TRAVAR O WINDOWS) ---
if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
            print("[OK] Sucesso! Tabelas criadas no MySQL.")
        except Exception as e:
            print(f"[ERRO] Erro ao conectar no MySQL: {e}")
            print("DICA: Verifique se o MySQL está ligado e se o banco 'timesend_db' foi criado.")
            print("DICA 2: Verifique se colocou a senha correta no arquivo models.py")