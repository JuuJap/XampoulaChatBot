# Xampoula Chat

Chatbot web desenvolvido como projeto acadêmico usando **Google Gemini, FastAPI e MySQL**.

O usuário conversa com a IA pelo navegador e pode escolher quais respostas deseja salvar. O histórico da conversa fica temporariamente em memória, enquanto apenas as respostas marcadas com **Salvar** são gravadas no MySQL.

## Funcionalidades

- Chat com IA usando a API do Google Gemini.
- Frontend em HTML, CSS e JavaScript.
- Backend em Python com FastAPI.
- Banco de dados MySQL.
- FastAPI serve o próprio frontend: não é necessário Live Server.
- Contexto da conversa mantido apenas durante a sessão.
- Salvamento manual de respostas no banco.
- Listagem, exclusão individual e limpeza das respostas salvas.
- Criação automática do banco e das tabelas.
- Limpeza de sessões antigas por tempo de expiração (TTL).
- Tela de status da IA e do MySQL.
- Tratamento amigável para limite de uso da API (`429`).
- Personalidade da IA configurável em `backend/system_prompt.txt`.
- Scripts para configuração e inicialização no Windows.

## Tecnologias

| Camada | Tecnologias |
| --- | --- |
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python, FastAPI, Uvicorn |
| IA | Google Gemini / Google Gen AI SDK |
| Banco | MySQL, MySQL Connector/Python |

## Arquitetura

```text
Navegador
   |
   |  HTML / CSS / JavaScript
   v
FastAPI
   |---------------------> Google Gemini API
   |
   '---------------------> MySQL
                              |
                              |-- sessoes
                              '-- respostas_salvas
```

A chave da API e as credenciais do banco ficam somente no backend. O JavaScript nunca recebe a chave Gemini.

## Estrutura do projeto

```text
Xampoula-Chat/
|-- index.html
|-- css/
|   '-- style.css
|-- js/
|   '-- script.js
|-- backend/
|   |-- main.py
|   |-- config.py
|   |-- database.py
|   |-- gemini_service.py
|   |-- schemas.py
|   |-- system_prompt.txt
|   |-- .env.example
|   '-- requirements.txt
|-- database/
|   '-- banco.sql
|-- CONFIGURAR.bat
|-- INICIAR.bat
|-- MELHORIAS.md
|-- .gitignore
'-- README.md
```

> O arquivo `backend/.env` e a pasta `backend/venv/` **não fazem parte do repositório**. Eles são criados/configurados localmente.

# Instalação no Windows

## 1. Pré-requisitos

Instale:

- **Python 3.10 ou superior** (testado com Python 3.13);
- **MySQL**, ou XAMPP com o módulo MySQL;
- uma chave da **Gemini API**;
- Git, caso queira clonar o repositório pelo terminal.

Para instalar Python pelo PowerShell com WinGet:

```powershell
winget install Python.Python.3.13
```

Depois da instalação, feche e abra o terminal novamente e teste:

```powershell
python --version
```

Se o Windows mostrar a mensagem da Microsoft Store mesmo depois de instalar Python, desative os aliases `python.exe` e `python3.exe` em:

```text
Configurações > Aplicativos > Configurações avançadas do aplicativo >
Aliases de execução do aplicativo
```

## 2. Baixe o projeto

Pelo Git:

```powershell
git clone URL_DO_SEU_REPOSITORIO
cd Xampoula-Chat
```

Ou baixe o ZIP pelo GitHub e extraia a pasta.

## 3. Ligue o MySQL

Se estiver usando XAMPP:

1. Abra o XAMPP Control Panel.
2. Clique em **Start** no MySQL.

O backend tenta criar automaticamente o banco `chatbot_ia` e as tabelas na primeira inicialização.

O arquivo `database/banco.sql` também está disponível caso você queira criar a estrutura manualmente no phpMyAdmin.

## 4. Configure o Python

Na raiz do projeto, execute:

```powershell
.\CONFIGURAR.bat
```

Esse script:

1. localiza uma instalação válida do Python;
2. cria `backend/venv`;
3. atualiza o `pip`;
4. instala `backend/requirements.txt`;
5. cria `backend/.env` a partir de `.env.example`, se necessário.

### Configuração manual

Caso prefira fazer sem o `.bat`:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## 5. Configure o `.env`

Abra:

```text
backend/.env
```

Preencha sua chave do Gemini:

```env
# Gemini
GEMINI_API_KEY=COLE_SUA_CHAVE_AQUI
GEMINI_MODEL=gemini-3.8-flash
GEMINI_THINKING_LEVEL=low

# MySQL / XAMPP
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=chatbot_ia
DB_SESSION_TTL_HOURS=24

# Servidor local
APP_HOST=127.0.0.1
APP_PORT=8000
```

Se o seu MySQL tiver senha, coloque-a em `DB_PASSWORD`.

**Nunca publique `backend/.env`.** O `.gitignore` deste projeto já está preparado para ignorá-lo.

## 6. Inicie o projeto

Com o MySQL ligado, execute na raiz:

```powershell
.\INICIAR.bat
```

O navegador deve abrir automaticamente em:

```text
http://127.0.0.1:8000
```

Se ele não abrir, digite esse endereço manualmente no navegador.

### Inicialização manual

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python main.py
```

Depois acesse `http://127.0.0.1:8000`.

Para encerrar o servidor, pressione `Ctrl + C` no terminal.

# Banco de dados

O banco padrão é:

```text
chatbot_ia
```

O sistema usa duas tabelas principais:

### `sessoes`

Registra sessões temporárias do navegador e a última atividade.

### `respostas_salvas`

Armazena somente respostas que o usuário escolheu salvar:

```text
id
session_id
pergunta
resposta
criado_em
```

Quando uma sessão é encerrada corretamente, a aplicação tenta remover os registros daquela sessão. Sessões abandonadas também podem ser limpas pelo TTL configurado em `DB_SESSION_TTL_HOURS`.

# Personalidade do chatbot

A personalidade fica em:

```text
backend/system_prompt.txt
```

Você pode editar esse arquivo sem alterar o código Python. As novas instruções são lidas nas próximas perguntas.

# API

Principais rotas:

| Método | Endpoint | Função |
| --- | --- | --- |
| `GET` | `/` | Interface web |
| `GET` | `/api/health` | Status da aplicação |
| `POST` | `/api/chat` | Envia uma pergunta à IA |
| `POST` | `/api/chat/reset` | Zera o contexto da conversa |
| `POST` | `/api/save` | Salva uma resposta no MySQL |
| `GET` | `/api/saved/{session_id}` | Lista respostas salvas |
| `DELETE` | `/api/saved/{response_id}` | Exclui uma resposta |
| `DELETE` | `/api/saved/session/{session_id}` | Limpa as respostas da sessão |
| `POST` | `/api/session/close` | Encerra a sessão |

O FastAPI também disponibiliza documentação automática em:

```text
http://127.0.0.1:8000/docs
```

# Problemas comuns

## `Python não foi encontrado`

Instale Python e abra um terminal novo:

```powershell
winget install Python.Python.3.13
python --version
```

O `CONFIGURAR.bat` também tenta localizar instalações do Python que não entraram corretamente no `PATH`.

## `MySQL offline`

Confirme que o MySQL/XAMPP está iniciado e verifique os valores `DB_HOST`, `DB_PORT`, `DB_USER` e `DB_PASSWORD` no `.env`.

O chat pode continuar funcionando sem MySQL, mas o recurso **Salvar** fica indisponível.

## Erro `429` da Gemini API

O erro significa que a cota ou o limite temporário do projeto Gemini foi atingido. O frontend mostra uma mensagem amigável e, quando disponível, um contador para nova tentativa.

Criar outra chave dentro do mesmo projeto Google não necessariamente cria uma nova cota.

## Modelo indisponível / erro `404`

O modelo é configurado em:

```env
GEMINI_MODEL=gemini-3.8-flash
```

Se esse identificador deixar de estar disponível para seu projeto, altere `GEMINI_MODEL` para um modelo compatível com sua conta/API.

# Segurança e GitHub

Não envie para o GitHub:

```text
backend/.env
backend/venv/
__pycache__/
*.pyc
```

Esses itens já estão cobertos pelo `.gitignore`.

Pode enviar normalmente:

```text
backend/.env.example
backend/*.py
backend/requirements.txt
backend/system_prompt.txt
css/
js/
database/banco.sql
index.html
CONFIGURAR.bat
INICIAR.bat
README.md
```

Se uma chave da API já tiver sido publicada ou compartilhada, revogue-a e gere outra antes de disponibilizar o repositório.

# Objetivo acadêmico

O projeto demonstra, em uma aplicação única:

- desenvolvimento frontend;
- criação de API REST com FastAPI;
- integração com uma API de inteligência artificial;
- persistência em banco de dados relacional;
- gerenciamento de sessões;
- tratamento de erros e limites de serviço;
- separação de configurações e segredos;
- organização de código em múltiplas camadas.

---

Projeto acadêmico desenvolvido com **Python, FastAPI, Gemini e MySQL**.
