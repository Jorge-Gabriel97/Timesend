Markdown

# 🚀 TimeSend - Automação e Gestão de Marketing para WhatsApp

**TimeSend** é uma plataforma **SaaS (Software as a Service)** de uso interno desenvolvida para automatizar, agendar e gerenciar campanhas de comunicação via WhatsApp Web.

Diferente de scripts simples de automação, o TimeSend é uma aplicação Full-Stack robusta que combina um **Painel Administrativo Web** com um **Robô de Automação Inteligente**, capaz de operar de forma híbrida (simulação humana e injeção de dados) para garantir alta taxa de entrega e estabilidade.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3-green?style=for-the-badge&logo=flask)
![Selenium](https://img.shields.io/badge/Selenium-Automation-yellow?style=for-the-badge&logo=selenium)
![MySQL](https://img.shields.io/badge/MySQL-Database-orange?style=for-the-badge&logo=mysql)
![Bootstrap](https://img.shields.io/badge/Frontend-Bootstrap%205-purple?style=for-the-badge&logo=bootstrap)

---

## 📋 Funcionalidades Principais

### 🔐 Gestão e Segurança
* **Sistema de Login Seguro:** Autenticação de usuários com criptografia de senha (`scrypt`).
* **Controle de Acesso (RBAC):** Sistema hierárquico onde apenas Administradores podem criar novos acessos.
* **Persistência de Dados:** Banco de Dados MySQL para armazenar histórico de envios, cadastro de clientes e tarefas agendadas.

### 📢 Automação de Disparos Avançada
* **Envio Híbrido:** O robô identifica automaticamente o destino:
    * **Números:** Usa API de Link Direto.
    * **Grupos:** Usa Navegação via Barra Lateral de Pesquisa.
* **Múltiplos Destinatários:** Seleção de contatos em massa via Checkbox no painel.
* **Suporte a Mídia:** Envio de Texto e Imagens (JPG/PNG) simultaneamente.
* **Fila Inteligente (Anti-Bloqueio):** Sistema de escalonamento automático que insere intervalos de segurança entre os envios, evitando o comportamento de SPAM detectável pelo WhatsApp.

### 💻 Interface e Usabilidade
* **Dashboard Profissional:** Interface moderna e responsiva construída com **Bootstrap 5**.
* **Gestão de Clientes:** Cadastro, visualização e seleção rápida de contatos.
* **Modo Servidor Local:** Configurado para rodar na rede local (LAN), permitindo acesso ao painel via celular ou outros computadores no mesmo Wi-Fi.

---

## 🛠️ Stack Tecnológica

* **Backend:** Python 3, Flask, SQLAlchemy.
* **Database:** MySQL (Driver `pymysql`).
* **Automação:** Selenium WebDriver, ChromeDriverManager.
* **Agendamento:** APScheduler (Background Tasks).
* **Frontend:** HTML5, CSS3, Bootstrap 5 (CDN), Jinja2.

---

## ⚙️ Instalação e Configuração

### 1. Pré-requisitos
Antes de começar, certifique-se de ter instalado:
* [Python 3.10+](https://www.python.org/)
* [Google Chrome](https://www.google.com/chrome/)
* Servidor MySQL rodando (Local via XAMPP/Workbench ou Nuvem)

### 2. Clonar o Repositório
```bash```

git clone [https://github.com/Jorge-Gabriel97/Timesend.git](https://github.com/Jorge-Gabriel97/Timesend.git)
cd Timesend
3. Instalar Dependências
Bash

pip install -r requirements.txt
4. Configurar Banco de Dados
Abra o arquivo models.py e edite as credenciais do seu MySQL:

Python

## models.py
usuario = ""        # Seu usuário MySQL
senha = ""              # Sua senha MySQL
host = "localhost"      # Endereço do banco (ou IP da nuvem)
banco = ""   # Nome do banco de dados
Nota: Crie o banco vazio no seu gerenciador MySQL antes de prosseguir: CREATE DATABASE timesend_db;

5. Inicializar o Sistema
Execute os scripts para criar as tabelas e o usuário admin inicial:

Bash

# 1. Cria as tabelas no MySQL
python models.py

# 2. Cria o admin padrão (Login: admin / Senha: 123)
python cria_admin.py
6. Executar o Servidor
Bash

python app.py
O sistema estará acessível em:

No PC: http://localhost:5000

No Celular/Rede: http://SEU_IP_LOCAL:5000 (Ex: 192.168.0.15:5000)

## 🤖 Lógica do Robô (Como funciona?)
O TimeSend utiliza uma estratégia de "Busca Resiliente" para lidar com as atualizações constantes do DOM do WhatsApp Web:

Detecção de Destino: O robô analisa o input. Se for numérico, usa a URL API. Se contiver letras, assume que é um Grupo e utiliza a busca visual.

Sessão Persistente: O Login (QR Code) é salvo na pasta /sessao_zap, evitando a necessidade de escanear o código a cada envio.

Injeção de Arquivos: Para enviar imagens, o robô não depende do mouse para abrir menus. Ele localiza o input[type='file'] oculto no código do WhatsApp e injeta o arquivo diretamente, garantindo compatibilidade.

Recuperação de Erros: Se o elemento da caixa de texto não for encontrado imediatamente, o robô utiliza WebDriverWait para aguardar o carregamento dinâmico da página.

## 🐛 Solução de Problemas Comuns
Erro Data too long for column:

Causa: A coluna do banco é muito pequena para o texto ou senha criptografada.

Solução: Rode no MySQL: ALTER TABLE user MODIFY COLUMN password VARCHAR(255);

Erro de Conexão (Celular não acessa):

Causa: Firewall do Windows bloqueando a porta.

Solução: Libere a porta 5000 nas configurações avançadas do Firewall ("Regras de Entrada").

Robô não acha o Grupo:

Solução: Certifique-se de digitar o nome do grupo EXATAMENTE como ele aparece no WhatsApp (respeitando emojis, espaços e traços).

## 📄 Licença
Este projeto foi desenvolvido para fins de estudo e automação interna. O uso indevido para SPAM ou envio não solicitado viola os termos de serviço do WhatsApp. Use com responsabilidade.

Desenvolvido por Jorge Gabriel 🚀
