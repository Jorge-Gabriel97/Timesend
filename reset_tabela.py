from models import app, db
from sqlalchemy import text

with app.app_context():
    try:
        # 1. Tenta apagar a tabela antiga
        print("Tentando apagar tabela 'agendamento' antiga...")
        with db.engine.connect() as connection:
            connection.execute(text("DROP TABLE IF EXISTS agendamento"))
            connection.commit()
        print("[OK] Tabela apagada.")

        # 2. Cria a tabela nova baseada no seu models.py atualizado
        print("Criando tabela nova (com suporte a nomes longos)...")
        db.create_all()
        print("[OK] Tabela recriada com sucesso!")
        
    except Exception as e:
        print(f"[ERRO] Falha ao resetar tabela: {e}")