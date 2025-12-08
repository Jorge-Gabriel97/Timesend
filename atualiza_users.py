from models import app, db
from sqlalchemy import text

with app.app_context():
    print("Atualizando tabela de usuários...")
    try:
        with db.engine.connect() as connection:
            # Adiciona a coluna is_blocked
            connection.execute(text("ALTER TABLE user ADD COLUMN is_blocked BOOLEAN DEFAULT FALSE;"))
            connection.commit()
        print("[OK] Coluna 'is_blocked' criada com sucesso!")
    except Exception as e:
        print(f"[INFO] Provavelmente a coluna já existe ou erro: {e}")