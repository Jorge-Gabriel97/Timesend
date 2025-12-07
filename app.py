import os
import time
import re
from datetime import datetime, timedelta
from threading import Thread  # IMPORTANTE: Necessário para o QR Code rodar em segundo plano
from flask import request, render_template, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler

# --- IMPORTAÇÕES DO SELENIUM ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from models import app, db, User, Agendamento, Cliente

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


# --- ROTA: DASHBOARD ---
@app.route('/')
@login_required
def index():
    if current_user.is_admin:
        tarefas = Agendamento.query.order_by(Agendamento.id.desc()).all()
    else:
        tarefas = Agendamento.query.filter_by(user_id=current_user.id).order_by(Agendamento.id.desc()).all()

    clientes = Cliente.query.all()
    return render_template('dashboard.html', nome=current_user.username, tarefas=tarefas, clientes=clientes)


# --- ROTAS DE LOGIN/LOGOUT ---
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


# --- ROTA: CADASTRAR CLIENTE ---
@app.route('/cadastrar_cliente', methods=['POST'])
@login_required
def cadastrar_cliente():
    nome = request.form.get('cliente_nome')
    telefone = request.form.get('cliente_telefone')
    telefone_limpo = re.sub(r'\D', '', telefone)

    if Cliente.query.filter_by(telefone=telefone_limpo).first():
        flash('Erro: Cliente já cadastrado.')
    else:
        novo_cliente = Cliente(nome=nome, telefone=telefone_limpo, criado_em=datetime.now().strftime("%d/%m/%Y"))
        db.session.add(novo_cliente)
        db.session.commit()
        flash(f'Cliente {nome} salvo!')
    return redirect(url_for('index'))


# --- ROTA: AGENDAR ---
@app.route('/agendar', methods=['POST'])
@login_required
def agendar_mensagem():
    ids_selecionados = request.form.getlist('destinatarios')
    grupo_manual = request.form.get('grupo_manual')
    mensagem = request.form.get('texto')
    hora_envio = request.form.get('horario')
    frequencia = request.form.get('frequencia')

    imagem = request.files.get('imagem_upload')
    caminho_absoluto = None

    if imagem and imagem.filename != '':
        safe_filename = re.sub(r'[^a-zA-Z0-9_.-]', '', imagem.filename)
        safe_filename = f"{int(time.time())}_{safe_filename}"
        caminho_final = os.path.join(UPLOAD_FOLDER, safe_filename)
        imagem.save(caminho_final)
        caminho_absoluto = os.path.abspath(caminho_final)

    lista_final = []
    for cliente_id in ids_selecionados:
        cliente = db.session.get(Cliente, int(cliente_id))
        if cliente:
            lista_final.append(cliente.telefone)

    if grupo_manual:
        grupos_extras = re.split(r'[;,]', grupo_manual)
        for g in grupos_extras:
            g = g.strip()
            if g: lista_final.append(g)

    if not lista_final:
        flash('Selecione pelo menos um contato.')
        return redirect(url_for('index'))

    # Configura data base
    hora_base, minuto_base = map(int, hora_envio.split(':'))
    data_base = datetime.now().replace(hour=hora_base, minute=minuto_base, second=0)

    incremento = 0
    usuario_atual_id = current_user.id

    for destino in lista_final:
        nova_tarefa = Agendamento(
            user_id=usuario_atual_id, destinatario=destino, mensagem=mensagem,
            imagem_path=caminho_absoluto, horario=hora_envio, dias_semana=frequencia
        )
        db.session.add(nova_tarefa)

        tempo_ajustado = data_base + timedelta(minutes=incremento * 2)
        h_exec = tempo_ajustado.hour
        m_exec = tempo_ajustado.minute

        if frequencia == 'seg-sex':
            scheduler.add_job(robo_enviar_zap, 'cron', day_of_week='mon-fri', hour=h_exec, minute=m_exec,
                              args=[destino, mensagem, caminho_absoluto, usuario_atual_id])
        elif frequencia == 'diaria':
            scheduler.add_job(robo_enviar_zap, 'cron', hour=h_exec, minute=m_exec,
                              args=[destino, mensagem, caminho_absoluto, usuario_atual_id])
        else:
            scheduler.add_job(robo_enviar_zap, 'date', run_date=tempo_ajustado,
                              args=[destino, mensagem, caminho_absoluto, usuario_atual_id])

        incremento += 1

    db.session.commit()
    flash(f'Agendado para {len(lista_final)} destinos!')
    return redirect(url_for('index'))


# === NOVAS ROTAS: ESPELHAMENTO DE QR CODE ===

@app.route('/conectar_whatsapp')
@login_required
def conectar_whatsapp():
    # Renderiza a página que mostra o QR Code
    return render_template('conectar.html')


@app.route('/gerar_qrcode')
@login_required
def gerar_qrcode():
    # Inicia a thread que abre o Chrome e tira prints
    t = Thread(target=thread_qrcode_selenium, args=(current_user.id,))
    t.start()
    return "Iniciando processo..."


# Função que roda em background para pegar o QR Code
def thread_qrcode_selenium(user_id):
    driver = None
    try:
        options = webdriver.ChromeOptions()
        dir_path = os.getcwd()

        # Garante que usa a MESMA pasta de sessão que o robô de envio usa
        nome_pasta_sessao = f"sessao_zap_{user_id}"
        profile_path = os.path.join(dir_path, nome_pasta_sessao)

        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://web.whatsapp.com")

        print(f"--- Iniciando captura de QR Code para Usuário {user_id} ---")
        time.sleep(5)

        # Tenta tirar 30 fotos (durante 90 segundos aprox)
        for i in range(30):
            try:
                # O seletor 'canvas' é onde fica o QR Code no WhatsApp Web
                qr_element = driver.find_element(By.CSS_SELECTOR, "canvas")

                # Salva na pasta static para o HTML poder ler
                # Nome do arquivo: qrcode_1.png, qrcode_2.png, etc.
                caminho_img = os.path.join('static', f'qrcode_{user_id}.png')
                qr_element.screenshot(caminho_img)
                print(f"QR Code atualizado ({i})")
            except:
                print("QR Code não encontrado (Talvez já conectou?)")

            time.sleep(3)

        print("Tempo de conexão finalizado.")

    except Exception as e:
        print(f"Erro na thread do QR Code: {e}")
    finally:
        if driver:
            driver.quit()


# === FIM DAS NOVAS ROTAS ===

# --- FUNÇÃO DO ROBÔ DE ENVIO ---
def robo_enviar_zap(destinatario, texto, caminho_imagem, user_id):
    print(f"--- ROBÔ INICIADO: Usuário {user_id} -> {destinatario} ---")
    driver = None
    try:
        options = webdriver.ChromeOptions()
        dir_path = os.getcwd()

        nome_pasta_sessao = f"sessao_zap_{user_id}"
        profile_path = os.path.join(dir_path, nome_pasta_sessao)

        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        apenas_numeros = re.sub(r'\D', '', destinatario)
        is_telefone = len(apenas_numeros) > 10 and not re.search(r'[a-zA-Z]', destinatario)

        if is_telefone:
            link = f"https://web.whatsapp.com/send?phone={apenas_numeros}"
            driver.get(link)
            wait_time = 60
        else:
            driver.get("https://web.whatsapp.com")
            wait_time = 60

        print(f"Aguardando carregamento ({wait_time}s)...")
        wait = WebDriverWait(driver, wait_time)

        try:
            if is_telefone:
                caixa_texto = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#main footer div[contenteditable='true']")
                ))
                caixa_texto.click()
            else:
                barra_pesquisa = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']")
                ))
                barra_pesquisa.click()
                time.sleep(1)
                barra_pesquisa.send_keys(destinatario)
                time.sleep(2)
                barra_pesquisa.send_keys(Keys.ENTER)
                time.sleep(3)
                caixa_texto = driver.find_element(By.CSS_SELECTOR, "#main footer div[contenteditable='true']")
                caixa_texto.click()

            print("Chat localizado.")

        except Exception as e:
            print(f"ERRO FATAL: Chat não localizado. {e}")
            return

        if texto:
            for linha in texto.split('\n'):
                caixa_texto.send_keys(linha)
                caixa_texto.send_keys(Keys.SHIFT + Keys.ENTER)
            time.sleep(1)
            try:
                driver.find_element(By.CSS_SELECTOR, "span[data-icon='send']").click()
            except:
                caixa_texto.send_keys(Keys.ENTER)
            time.sleep(3)

        if caminho_imagem and os.path.exists(caminho_imagem):
            try:
                inputs = driver.find_elements(By.TAG_NAME, "input")
                anexou = False
                for inp in inputs:
                    if "image/" in inp.get_attribute("accept") or "":
                        inp.send_keys(caminho_imagem)
                        anexou = True
                        break
                if anexou:
                    time.sleep(10)
                    ActionChains(driver).send_keys(Keys.ENTER).perform()
                    time.sleep(5)
            except Exception as e:
                print(f"Erro imagem: {e}")

        print("Finalizado!")
        time.sleep(3)

    except Exception as e:
        print(f"Erro crítico: {e}")
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)