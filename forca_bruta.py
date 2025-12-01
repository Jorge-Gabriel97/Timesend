from models import app, db
from sqlalchemy import text

with app.app_context():
    print("Tentando forcar alteracao da coluna via SQL direto...")
    try:
        with db.engine.connect() as connection:
            # Comando SQL puro para alterar a coluna para 255 chars
            connection.execute(text("ALTER TABLE agendamento MODIFY COLUMN destinatario VARCHAR(255);"))
            connection.commit()
            
        print("[OK] SUCESSO! A coluna 'destinatario' foi atualizada.")
        
    except Exception as e:
        print(f"[ERRO] Falha: {e}")