# 🚀 TimeSend - Automação de Marketing para WhatsApp

**TimeSend** é uma aplicação web (SaaS interno) desenvolvida em Python e Flask para gerenciar, agendar e disparar mensagens automáticas (texto e imagem) via WhatsApp Web. O sistema utiliza Selenium para automação e MySQL para persistência de dados.

---

##⚠️ Estrutura de Pastas
/TimeSend
│
├── app.py              # Aplicação principal e lógica do robô
├── models.py           # Configuração do Banco de Dados e Classes
├── cria_admin.py       # Script utilitário para criar superusuário
├── zap_interno.db      # (Se usar SQLite, senão usa conexão MySQL)
│
├── /templates          # Arquivos HTML
│   ├── login.html
│   └── dashboard.html
│
├── /static             # Arquivos CSS e Imagens estáticas
│   └── style.css
│
├── /uploads            # Pasta temporária para imagens enviadas
└── /sessao_zap         # Pasta onde o Login do WhatsApp fica salvo

--

## 📋 Funcionalidades

* **🔐 Sistema de Login Seguro:** Autenticação de usuários com senhas criptografadas.
* **👑 Controle de Acesso:** Apenas usuários Administradores podem criar novos acessos.
* **👥 Gerenciamento de Clientes:** Cadastro de clientes no banco de dados para disparos em massa.
* **📅 Agendamento Flexível:**
    * Envio Único (Data e Hora específica).
    * Recorrente (Diário).
    * Dias Úteis (Segunda a Sexta).
* **📢 Disparo em Massa Inteligente:** Opção "Enviar para Todos" com fila de espera automática (evita bloqueios).
* **🤖 Robô Híbrido:** Algoritmo robusto que combina digitação humana simulada com injeção de arquivos, garantindo alta taxa de entrega.

---

##🤖 Como funciona o Robô
O sistema abre uma instância do Google Chrome controlada pelo Selenium.

Na primeira execução, será necessário escanear o QR Code do WhatsApp (a sessão ficará salva na pasta sessao_zap).

O robô acessa a conversa, digita o texto simulando um humano e envia.

Se houver imagem, o robô utiliza injeção direta no input oculto do WhatsApp para garantir o envio sem depender de menus visuais.

---

## 🛠️ Tecnologias Utilizadas

* **Backend:** Python 3.x, Flask.
* **Banco de Dados:** MySQL (via SQLAlchemy).
* **Automação:** Selenium WebDriver (Chrome).
* **Agendamento:** APScheduler.
* **Frontend:** HTML5, CSS3.

---

## ⚙️ Pré-requisitos

Antes de começar, certifique-se de ter instalado:
* [Python 3.10+](https://www.python.org/)
* [Google Chrome](https://www.google.com/chrome/)
* Servidor MySQL (Local via XAMPP/Workbench ou na Nuvem)

---

## 🐛 Solução de Problemas Comuns
Erro Data too long for column 'password': Ocorre se a coluna de senha no MySQL for muito curta. Execute no banco: ALTER TABLE user MODIFY COLUMN password VARCHAR(255);

Erro DevToolsActivePort file doesn't exist: Geralmente ocorre se o Chrome já estiver aberto ou travado. Feche todas as janelas do Chrome e tente novamente.

---

##⚖️ Aviso Legal
Este software é para fins de estudo e automação interna. O uso para SPAM ou envio não solicitado viola os termos de serviço do WhatsApp. Use com responsabilidade.

---

### 📦 Arquivo Extra: `requirements.txt`

Para facilitar a vida de quem vai instalar (inclusive você no futuro), crie um arquivo chamado `requirements.txt` na mesma pasta e cole isso:

```text
flask
flask-sqlalchemy
flask-login
selenium
webdriver-manager
apscheduler
pymysql
cryptography
Werkzeug

## 🚀 Instalação e Configuração

### 1. Clone o repositório (ou baixe os arquivos)
```bash
git clone [https://github.com/seu-usuario/timesend.git](https://github.com/seu-usuario/timesend.git)
cd TimeSend





