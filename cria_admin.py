from models import app, db, User
from werkzeug.security import generate_password_hash

# Configurações do seu Admin inicial
USERNAME = ""  
PASSWORD = ""  

def criar_super_admin():
    with app.app_context():
        
        usuario_existente = User.query.filter_by(username=USERNAME).first()
        
        if usuario_existente:
            print(f"O usuário '{USERNAME}' já existe!")
        else:
            
            senha_criptografada = generate_password_hash(PASSWORD)
            
            
            novo_admin = User(username=USERNAME, password=senha_criptografada, is_admin=True)
            
            
            db.session.add(novo_admin)
            db.session.commit()
            print(f"Sucesso! Super Admin '{USERNAME}' criado.")

if __name__ == "__main__":
    criar_super_admin()
