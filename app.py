import os
import time
import re
from datetime import datetime
from flask import request, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

# --- IMPORTAÇÕES DO SELENIUM ---
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from models import app, db, User, Agendamento

# --- Configuração do Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

scheduler = BackgroundScheduler()
scheduler.start()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
@login_required
def index():
    if current_user.is_admin:
        tarefas = Agendamento.query.all()
    else:
        tarefas = Agendamento.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', nome=current_user.username, tarefas=tarefas)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login inválido.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/criar_usuario', methods=['POST'])
@login_required
def criar_usuario():
    if not current_user.is_admin:
        return "ACESSO NEGADO", 403
    novo_user = request.form.get('new_username')
    novo_pass = request.form.get('new_password')
    if User.query.filter_by(username=novo_user).first():
        flash('Usuário já existe!')
        return redirect(url_for('index'))
    senha_hash = generate_password_hash(novo_pass)
    db.session.add(User(username=novo_user, password=senha_hash, is_admin=False))
    db.session.commit()
    flash(f'Usuário {novo_user} criado!')
    return redirect(url_for('index'))

@app.route('/agendar', methods=['POST'])
@login_required
def agendar_mensagem():
    destinatario = request.form.get('numero') 
    mensagem = request.form.get('texto')
    hora_envio = request.form.get('horario') 
    frequencia = request.form.get('frequencia') 
    
    imagem = request.files.get('imagem_upload')
    caminho_absoluto = None
    
    if imagem and imagem.filename != '':
        # Sanitização básica do nome do arquivo para evitar problemas futuros
        safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '', imagem.filename)
        # Adiciona timestamp para evitar duplicatas
        safe_filename = f"{int(time.time())}_{safe_filename}"
        
        caminho_final = os.path.join(UPLOAD_FOLDER, safe_filename)
        imagem.save(caminho_final)
        caminho_absoluto = os.path.abspath(caminho_final)

    nova_tarefa = Agendamento(
        user_id=current_user.id, destinatario=destinatario, mensagem=mensagem,
        imagem_path=caminho_absoluto, horario=hora_envio, dias_semana=frequencia
    )
    db.session.add(nova_tarefa)
    db.session.commit()

    hora, minuto = map(int, hora_envio.split(':'))
    
    if frequencia == 'seg-sex':
        scheduler.add_job(robo_enviar_zap, 'cron', day_of_week='mon-fri', hour=hora, minute=minuto, args=[destinatario, mensagem, caminho_absoluto])
    elif frequencia == 'diaria':
        scheduler.add_job(robo_enviar_zap, 'cron', hour=hora, minute=minuto, args=[destinatario, mensagem, caminho_absoluto])
    else:
        scheduler.add_job(robo_enviar_zap, 'date', run_date=datetime.now().replace(hour=hora, minute=minuto, second=0), args=[destinatario, mensagem, caminho_absoluto])

    flash('Mensagem agendada!')
    return redirect(url_for('index'))

# --- FUNÇÃO DO ROBÔ: O HÍBRIDO (Texto Manual + Imagem Input) ---
def robo_enviar_zap(numero, texto, caminho_imagem):
    numero_limpo = re.sub(r'\D', '', numero)
    print(f"--- ROBÔ INICIADO: Enviando para {numero_limpo} ---")
    driver = None 
    try:
        options = webdriver.ChromeOptions()
        dir_path = os.getcwd()
        profile_path = os.path.join(dir_path, "sessao_zap")
        options.add_argument(f"user-data-dir={profile_path}") 
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        link = f"https://web.whatsapp.com/send?phone={numero_limpo}"
        driver.get(link)
        
        print("Aguardando carregamento (Máximo 60s)...")
        
        # --- AQUI ESTÁ A CORREÇÃO ---
        # Usamos WebDriverWait para esperar a caixa CORRETA aparecer.
        # Se demorar, ele espera. Não tenta adivinhar.
        try:
            wait = WebDriverWait(driver, 60)
            
            # Espera explícita pela caixa de texto DENTRO DO RODAPÉ (#main footer)
            caixa_texto = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#main footer div[contenteditable='true']")
            ))
            
            # Clica para garantir o foco
            caixa_texto.click()
            print("Chat localizado e focado no Rodapé.")
            
        except Exception as e:
            print(f"ERRO FATAL: Não encontrei a caixa de texto do chat. O número pode ser inválido ou a internet está lenta. Erro: {e}")
            return # Para tudo se não achar a certa

        # --- 1. ENVIO DE TEXTO ---
        if texto:
            print("Digitando texto...")
            for linha in texto.split('\n'):
                caixa_texto.send_keys(linha)
                caixa_texto.send_keys(Keys.SHIFT + Keys.ENTER)
            time.sleep(1)
            
            caixa_texto.send_keys(Keys.ENTER)
            print("Texto enviado!")
            time.sleep(3) 

        # --- 2. ENVIO DE IMAGEM (Input Oculto) ---
        if caminho_imagem and os.path.exists(caminho_imagem):
            print(f"Injetando imagem: {caminho_imagem}")
            try:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                anexou = False
                for inp in inputs:
                    if "image/" in inp.get_attribute("accept") or "":
                        inp.send_keys(caminho_imagem)
                        anexou = True
                        print("Imagem carregada no input!")
                        break
                
                if anexou:
                    print("Aguardando pré-visualização (10s)...")
                    time.sleep(10) # Tempo extra para carregar a imagem
                    ActionChains(driver).send_keys(Keys.ENTER).perform()
                    time.sleep(5)
                    print("Imagem ENVIADA!")
                else:
                    print("FALHA: Input de arquivo não encontrado.")
                    
            except Exception as e:
                print(f"Erro no envio de imagem: {e}")
        
        print("Processo finalizado com sucesso!")
        time.sleep(5)
        
    except Exception as e:
        print(f"Erro crítico no robô: {e}")
    
    finally:
        if driver:
            driver.quit()
            
if __name__ == '__main__':
    app.run(debug=True, port=5000)