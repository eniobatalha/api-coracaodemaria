# Guia de Setup — API Coração de Maria

Use este guia sempre que precisar configurar o projeto em uma nova máquina ou retomar o trabalho em outro PC.

---

## Pré-requisitos

Instale as ferramentas abaixo antes de começar:

| Ferramenta | Download |
|---|---|
| Git | https://git-scm.com/downloads |
| Python 3.11+ | https://www.python.org/downloads |
| Docker Desktop | https://www.docker.com/products/docker-desktop |

Verifique as instalações:

```bash
git --version
python --version
docker --version
docker compose version
```

---

## 1. Clonar o repositório

```bash
git clone https://github.com/eniobatalha/api-coracaodemaria.git
cd api-coracaodemaria
```

---

## 2. Criar e ativar o ambiente virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

O prefixo `(venv)` aparece no terminal quando o ambiente está ativo.

---

## 3. Instalar as dependências Python

```bash
pip install -r requirements.txt
```

---

## 4. Configurar as variáveis de ambiente

Copie o arquivo de exemplo e edite com seus valores:

**Windows:**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Abra o `.env` e substitua ao menos:

```env
SECRET_KEY=uma-chave-secreta-longa-e-aleatoria
JWT_SECRET_KEY=outra-chave-jwt-longa-e-aleatoria
```

Os demais valores já funcionam para desenvolvimento local sem alteração.

> O arquivo `.env` nunca é commitado (está no `.gitignore`). Cada máquina tem o seu.

---

## 5. Subir o banco de dados com Docker

```bash
docker compose up -d
```

Verifique se o container está saudável:

```bash
docker compose ps
```

A coluna `STATUS` deve mostrar `healthy` para o serviço `postgres`.

Para parar o banco sem apagar os dados:

```bash
docker compose stop
```

Para parar e apagar tudo (dados incluídos):

```bash
docker compose down -v
```

---

## 6. Rodar as migrations

Aplica todas as migrations existentes para criar as tabelas no banco:

```bash
flask db upgrade
```

> Se aparecer erro de `FLASK_APP` não definida, execute antes:
> - Windows: `$env:FLASK_APP = "run.py"`
> - macOS/Linux: `export FLASK_APP=run.py`

---

## 7. Popular o banco com dados iniciais (opcional)

```bash
python seeds.py
```

---

## 8. Rodar o servidor de desenvolvimento

```bash
python run.py
```

A API estará disponível em `http://localhost:5000`.  
A documentação Swagger estará em `http://localhost:5000/apidocs`.

---

## Fluxo de trabalho Git (commitar e enviar)

### Antes de começar a codar (em qualquer máquina)

Sempre puxe as atualizações mais recentes:

```bash
git pull origin main
```

### Depois de fazer alterações

```bash
# Ver o que mudou
git status

# Adicionar os arquivos alterados
git add .

# Criar o commit com uma mensagem descritiva
git commit -m "feat: descrição do que foi feito"

# Enviar para o repositório remoto
git push origin main
```

### Nomenclatura de commits recomendada

| Prefixo | Quando usar |
|---|---|
| `feat:` | Nova funcionalidade |
| `fix:` | Correção de bug |
| `refactor:` | Refatoração sem mudar comportamento |
| `docs:` | Alterações em documentação |
| `chore:` | Tarefas de manutenção (deps, config) |

---

## Checklist para nova máquina

- [ ] Git instalado e configurado (`git config --global user.name` e `user.email`)
- [ ] Python 3.11+ instalado
- [ ] Docker Desktop instalado e rodando
- [ ] Repositório clonado
- [ ] Ambiente virtual criado e ativado
- [ ] `pip install -r requirements.txt` executado
- [ ] Arquivo `.env` criado a partir do `.env.example`
- [ ] `docker compose up -d` executado (banco saudável)
- [ ] `flask db upgrade` executado
- [ ] `python run.py` funcionando em `http://localhost:5000`

---

## Solução de problemas comuns

**`ModuleNotFoundError`** — ambiente virtual não está ativo. Ative com `venv\Scripts\Activate.ps1` (Windows) ou `source venv/bin/activate` (macOS/Linux).

**`connection refused` no banco** — o Docker não está rodando ou o container não subiu. Execute `docker compose up -d` e aguarde o status `healthy`.

**`FLASK_APP not set`** — defina a variável: `$env:FLASK_APP = "run.py"` (Windows) ou `export FLASK_APP=run.py` (macOS/Linux).

**Porta 5432 já em uso** — outra instância de PostgreSQL está rodando. Pare-a ou mude `POSTGRES_PORT` no `.env` (ex: `5433`) e reinicie o Docker com `docker compose up -d`.

**Migration com erro** — se o banco está vazio após `git pull`, rode `flask db upgrade` novamente para aplicar migrations novas adicionadas por outro dev.
