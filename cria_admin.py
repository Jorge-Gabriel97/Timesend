from models import app, db, User
from werkzeug.security import generate_password_hash

# Configurações do seu Admin inicial
USERNAME = "LargeAdmin"  
PASSWORD = "0710"  

def criar_super_admin():
    with app.app_context():
        # Verifica se já existe alguém com esse nome
        usuario_existente = User.query.filter_by(username=USERNAME).first()
        
        if usuario_existente:
            print(f"O usuário '{USERNAME}' já existe!")
        else:
            # Cria o hash da senha (segurança básica)
            senha_criptografada = generate_password_hash(PASSWORD)
            
            # Cria o objeto do novo usuário
            novo_admin = User(username=USERNAME, password=senha_criptografada, is_admin=True)
            
            # Adiciona e salva no banco
            db.session.add(novo_admin)
            db.session.commit()
            print(f"Sucesso! Super Admin '{USERNAME}' criado.")

if __name__ == "__main__":
    criar_super_admin()