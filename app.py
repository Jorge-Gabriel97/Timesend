import os
import csv
import io
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
    # Admin vê tudo
    if current_user.is_admin:
        tarefas = Agendamento.query.order_by(Agendamento.id.desc()).all()
        # Admin também recebe a lista de TODOS os usuários para gerenciar
        todos_usuarios = User.query.all()
    else:
        tarefas = Agendamento.query.filter_by(user_id=current_user.id).order_by(Agendamento.id.desc()).all()
        todos_usuarios = []  # Usuário comum não vê lista de usuários

    clientes = Cliente.query.all()
    return render_template('dashboard.html', nome=current_user.username, tarefas=tarefas, clientes=clientes,
                           usuarios=todos_usuarios)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            # --- VERIFICAÇÃO DE BLOQUEIO ---
            if user.is_blocked:
                flash('Sua conta está BLOQUEADA. Contate o administrador.')
                return render_template('login.html')
            # -------------------------------

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


# ==========================================
#           GESTÃO DE USUÁRIOS (ADMIN)
# ==========================================

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
    # Cria desbloqueado por padrão
    db.session.add(User(username=novo_user, password=senha_hash, is_admin=False, is_blocked=False))
    db.session.commit()
    flash(f'Usuário {novo_user} criado!')
    return redirect(url_for('index'))


@app.route('/bloquear_usuario/<int:id>')
@login_required
def bloquear_usuario(id):
    if not current_user.is_admin: return "Acesso Negado", 403

    user = db.session.get(User, id)
    if user:
        if user.id == current_user.id:
            flash('Você não pode bloquear a si mesmo!')
        else:
            # Inverte o status (Se tá livre, bloqueia. Se tá bloqueado, libera)
            user.is_blocked = not user.is_blocked
            db.session.commit()
            status = "bloqueado" if user.is_blocked else "desbloqueado"
            flash(f'Usuário {user.username} foi {status}!')
    return redirect(url_for('index'))


@app.route('/excluir_usuario/<int:id>')
@login_required
def excluir_usuario(id):
    if not current_user.is_admin: return "Acesso Negado", 403

    user = db.session.get(User, id)
    if user:
        if user.id == current_user.id:
            flash('Você não pode excluir a si mesmo!')
        else:
            # Apaga também os agendamentos desse usuário para não ficar lixo no banco
            Agendamento.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            flash(f'Usuário {user.username} excluído com sucesso!')
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
        if not current_user.is_admin and tarefa.user_id != current_user.id:
            flash('Acesso negado.')
            return redirect(url_for('index'))
        db.session.delete(tarefa)
        db.session.commit()
        flash('Agendamento cancelado!')
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
    t = Thread(target=thread_qrcode_selenium, args=(current_user.id,))
    t.start()
    return "Iniciando processo..."


def thread_qrcode_selenium(user_id):
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
        driver.get("https://web.whatsapp.com")

        time.sleep(5)
        for i in range(30):
            try:
                qr_element = driver.find_element(By.CSS_SELECTOR, "canvas")
                caminho_img = os.path.join('static', f'qrcode_{user_id}.png')
                qr_element.screenshot(caminho_img)
            except:
                pass
            time.sleep(3)
    except:
        pass
    finally:
        if driver: driver.quit()

        # --- ROTA: IMPORTAÇÃO DE CSV (Forma Segura) ---
        @app.route('/importar_csv', methods=['POST'])
        @login_required
        def importar_csv():
            arquivo = request.files.get('arquivo_csv')

            if not arquivo or arquivo.filename == '':
                flash('Nenhum arquivo selecionado.')
                return redirect(url_for('index'))

            if not arquivo.filename.endswith('.csv'):
                flash('Erro: O arquivo deve ser do tipo .CSV')
                return redirect(url_for('index'))

            try:
                # Lê o arquivo na memória
                stream = io.StringIO(arquivo.stream.read().decode("UTF8"), newline=None)
                csv_input = csv.reader(stream)

                # Pula a primeira linha (cabeçalho: Nome, Telefone)
                next(csv_input, None)

                count_sucesso = 0
                count_erro = 0

                for linha in csv_input:
                    if len(linha) >= 2:
                        nome = linha[0].strip()
                        telefone = linha[1].strip()

                        # Limpeza do telefone (apenas números)
                        telefone_limpo = re.sub(r'\D', '', telefone)

                        # Validação básica: tem que ter pelo menos 10 dígitos (DDD + numero)
                        if len(telefone_limpo) < 10:
                            count_erro += 1
                            continue

                        # Verifica se já existe no banco
                        if not Cliente.query.filter_by(telefone=telefone_limpo).first():
                            novo_cliente = Cliente(
                                nome=nome,
                                telefone=telefone_limpo,
                                criado_em=datetime.now().strftime("%d/%m/%Y")
                            )
                            db.session.add(novo_cliente)
                            count_sucesso += 1
                        else:
                            count_erro += 1  # Já existia

                db.session.commit()
                flash(
                    f'Importação concluída! {count_sucesso} novos contatos salvos. ({count_erro} ignorados/duplicados)')

            except Exception as e:
                flash(f'Erro ao ler o arquivo: {e}. Verifique se é um CSV válido.')

            return redirect(url_for('index'))


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
    for cliente_id in ids_selecionados:
        c = db.session.get(Cliente, int(cliente_id))
        if c: lista_final.append(c.telefone)

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
        nova_tarefa = Agendamento(
            user_id=usuario_atual_id, destinatario=destino, mensagem=mensagem,
            imagem_path=caminho_absoluto, horario=hora_envio, dias_semana=frequencia
        )
        db.session.add(nova_tarefa)
        db.session.commit()

        tempo_ajustado = data_base + timedelta(minutes=incremento * 2)

        if frequencia == 'unica' and tempo_ajustado < datetime.now():
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


def robo_inteligente(agendamento_id):
    with app.app_context():
        tarefa = db.session.get(Agendamento, agendamento_id)
        if not tarefa: return
        executar_selenium(tarefa.destinatario, tarefa.mensagem, tarefa.imagem_path, tarefa.user_id)


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

        apenas_numeros = re.sub(r'\D', '', destinatario)
        is_telefone = len(apenas_numeros) > 10 and not re.search(r'[a-zA-Z]', destinatario)

        if is_telefone:
            link = f"https://web.whatsapp.com/send?phone={apenas_numeros}"
            driver.get(link)
            wait_time = 60
        else:
            driver.get("https://web.whatsapp.com")
            wait_time = 60

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
        except:
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
        time.sleep(3)
    except:
        pass
    finally:
        if driver: driver.quit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)