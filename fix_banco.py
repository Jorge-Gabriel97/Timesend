from models import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # Cria uma conexão direta e manda o comando SQL
        with db.engine.connect() as connection:
            # Comando para aumentar a coluna password para 255 caracteres
            connection.execute(text("ALTER TABLE user MODIFY COLUMN password VARCHAR(255)"))
            connection.commit()
            
        print("[OK] Coluna 'password' atualizada com sucesso para 255 caracteres!")
        
    except Exception as e:
        print(f"[ERRO] Não foi possível atualizar: {e}")