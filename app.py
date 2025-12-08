import os
import time
import re
from datetime import datetime, timedelta
from threading import Thread
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

# Cria pasta para os QRCodes se não existir
if not os.path.exists('static'):
    os.makedirs('static')

scheduler = BackgroundScheduler()
scheduler.start()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# ==========================================
#              ROTAS PRINCIPAIS
# ==========================================

@app.route('/')
@login_required
def index():
    if current_user.is_admin:
        tarefas = Agendamento.query.order_by(Agendamento.id.desc()).all()
    else:
        tarefas = Agendamento.query.filter_by(user_id=current_user.id).order_by(Agendamento.id.desc()).all()

    clientes = Cliente.query.all()
    return render_template('dashboard.html', nome=current_user.username, tarefas=tarefas, clientes=clientes)


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


# ==========================================
#           GESTÃO DE CLIENTES E TAREFAS
# ==========================================

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


@app.route('/excluir_tarefa/<int:id>')
@login_required
def excluir_tarefa(id):
    tarefa = db.session.get(Agendamento, id)
    if tarefa:
        # Validação de segurança: só dono ou admin apaga
        if not current_user.is_admin and tarefa.user_id != current_user.id:
            flash('Acesso negado.')
            return redirect(url_for('index'))

        db.session.delete(tarefa)
        db.session.commit()
        flash('Agendamento cancelado com sucesso!')
    else:
        flash('Tarefa não encontrada.')
    return redirect(url_for('index'))


@app.route('/editar_tarefa', methods=['POST'])
@login_required
def editar_tarefa():
    tarefa_id = request.form.get('tarefa_id')
    nova_mensagem = request.form.get('nova_mensagem')

    tarefa = db.session.get(Agendamento, int(tarefa_id))

    if tarefa:
        if not current_user.is_admin and tarefa.user_id != current_user.id:
            flash('Acesso negado.')
            return redirect(url_for('index'))

        tarefa.mensagem = nova_mensagem
        db.session.commit()
        flash('Mensagem atualizada!')
    return redirect(url_for('index'))


# ==========================================
#           CONEXÃO WHATSAPP (QR CODE)
# ==========================================

@app.route('/conectar_whatsapp')
@login_required
def conectar_whatsapp():
    return render_template('conectar.html')


@app.route('/gerar_qrcode')
@login_required
def gerar_qrcode():
    # Roda em thread separada para não travar o site
    t = Thread(target=thread_qrcode_selenium, args=(current_user.id,))
    t.start()
    return "Iniciando processo..."


def thread_qrcode_selenium(user_id):
    driver = None
    try:
        options = webdriver.ChromeOptions()
        dir_path = os.getcwd()

        # Garante a estrutura de pastas correta
        pasta_base = os.path.join(dir_path, "sessoes_usuarios")
        if not os.path.exists(pasta_base): os.makedirs(pasta_base)

        nome_pasta = f"sessao_zap_{user_id}"
        profile_path = os.path.join(pasta_base, nome_pasta)

        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://web.whatsapp.com")

        print(f"--- Capturando QR Code para Usuário {user_id} ---")
        time.sleep(5)

        # Tenta pegar o QR Code por cerca de 90 segundos
        for i in range(30):
            try:
                # O WhatsApp geralmente usa um <canvas> para desenhar o QR Code
                qr_element = driver.find_element(By.CSS_SELECTOR, "canvas")

                # Salva na pasta static com o ID do usuário
                caminho_img = os.path.join('static', f'qrcode_{user_id}.png')
                qr_element.screenshot(caminho_img)
                print(f"QR Code atualizado ({i})")
            except:
                print("QR Code não encontrado (Talvez já tenha conectado?)")

            time.sleep(3)

        print("Tempo de conexão finalizado.")

    except Exception as e:
        print(f"Erro na thread do QR Code: {e}")
    finally:
        if driver:
            driver.quit()


# ==========================================
#           AGENDAMENTO E ROBÔ
# ==========================================

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
    # 1. Adiciona contatos do banco
    for cliente_id in ids_selecionados:
        c = db.session.get(Cliente, int(cliente_id))
        if c: lista_final.append(c.telefone)

    # 2. Adiciona grupos manuais (separados por vírgula)
    if grupo_manual:
        grupos = re.split(r'[;,]', grupo_manual)
        for g in grupos:
            if g.strip(): lista_final.append(g.strip())

    if not lista_final:
        flash('Selecione pelo menos um contato ou grupo.')
        return redirect(url_for('index'))

    hora_base, minuto_base = map(int, hora_envio.split(':'))
    data_base = datetime.now().replace(hour=hora_base, minute=minuto_base, second=0)

    incremento = 0
    usuario_atual_id = current_user.id

    for destino in lista_final:
        # A. Salva no Banco primeiro
        nova_tarefa = Agendamento(
            user_id=usuario_atual_id, destinatario=destino, mensagem=mensagem,
            imagem_path=caminho_absoluto, horario=hora_envio, dias_semana=frequencia
        )
        db.session.add(nova_tarefa)
        db.session.commit()  # Commitamos para gerar o ID

        # B. Agenda passando o ID da tarefa (para permitir edição/cancelamento)
        tempo_ajustado = data_base + timedelta(minutes=incremento * 2)

        # Verifica se já passou do horário hoje
        if frequencia == 'unica' and tempo_ajustado < datetime.now():
            # Se for passado, executa em 10 segundos
            tempo_ajustado = datetime.now() + timedelta(seconds=10 + (incremento * 10))

        if frequencia == 'seg-sex':
            scheduler.add_job(robo_inteligente, 'cron', day_of_week='mon-fri', hour=tempo_ajustado.hour,
                              minute=tempo_ajustado.minute, args=[nova_tarefa.id])
        elif frequencia == 'diaria':
            scheduler.add_job(robo_inteligente, 'cron', hour=tempo_ajustado.hour, minute=tempo_ajustado.minute,
                              args=[nova_tarefa.id])
        else:
            scheduler.add_job(robo_inteligente, 'date', run_date=tempo_ajustado, args=[nova_tarefa.id])

        incremento += 1

    flash(f'Agendado para {len(lista_final)} destinos!')
    return redirect(url_for('index'))


# --- ROBÔ INTELIGENTE (Verifica o Banco) ---
def robo_inteligente(agendamento_id):
    with app.app_context():
        # Busca a tarefa no banco na hora da execução
        tarefa = db.session.get(Agendamento, agendamento_id)

        # Se foi excluída, aborta
        if not tarefa:
            print(f"Tarefa {agendamento_id} não encontrada (Excluída). Cancelando.")
            return

        print(f"--- Executando Tarefa {agendamento_id} para {tarefa.destinatario} ---")
        # Chama o Selenium com os dados atualizados
        executar_selenium(tarefa.destinatario, tarefa.mensagem, tarefa.imagem_path, tarefa.user_id)


# --- FUNÇÃO DO SELENIUM (O Motor) ---
def executar_selenium(destinatario, texto, caminho_imagem, user_id):
    driver = None
    try:
        options = webdriver.ChromeOptions()
        dir_path = os.getcwd()

        pasta_base = os.path.join(dir_path, "sessoes_usuarios")
        if not os.path.exists(pasta_base): os.makedirs(pasta_base)

        nome_pasta = f"sessao_zap_{user_id}"
        profile_path = os.path.join(pasta_base, nome_pasta)

        options.add_argument(f"user-data-dir={profile_path}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Identifica se é Número ou Grupo
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
                barra = wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='3']")
                ))
                barra.click()
                time.sleep(1)
                barra.send_keys(destinatario)
                time.sleep(2)
                barra.send_keys(Keys.ENTER)
                time.sleep(3)
                caixa_texto = driver.find_element(By.CSS_SELECTOR, "#main footer div[contenteditable='true']")
                caixa_texto.click()
        except Exception as e:
            print(f"Erro ao achar chat: {e}")
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
            except:
                pass

        print("Envio concluído!")
        time.sleep(3)

    except Exception as e:
        print(f"Erro Selenium: {e}")
    finally:
        if driver:
            driver.quit()


if __name__ == '__main__':
    # Modo Servidor (Acessível na Rede)
    app.run(host='0.0.0.0', port=5000, debug=True)