from models import app, db
from sqlalchemy import text

with app.app_context():
    print("Resetando tabela Cliente...")
    try:
        with db.engine.connect() as connection:
            # Apaga a tabela antiga se existir
            connection.execute(text("DROP TABLE IF EXISTS cliente"))
            connection.commit()
            print("Tabela antiga apagada.")
            
        # Cria a nova tabela correta
        db.create_all()
        print("[OK] Nova tabela Cliente criada com campo 'telefone'!")
        
    except Exception as e:
        print(f"[ERRO] Erro: {e}")