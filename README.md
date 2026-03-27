# Fraga Store

Loja virtual interna construída com Django para o programa de recompensas da empresa, onde colaboradores utilizam **Fragacoins** para adquirir produtos.

## Pré-requisitos

- Python 3.12+
- PostgreSQL

## Configuração

1. Clone o repositório e crie um ambiente virtual:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` na raiz do projeto:

```env
SECRET_KEY=sua-secret-key
DB_NAME=nome_do_banco
DB_USER=usuario
DB_PASS=senha
DB_SERVER=localhost
DB_PORT=5432
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app
EMAIL_AGIDESK=email-agidesk@empresa.com
```

4. Execute as migrações e colete os arquivos estáticos:

```bash
python manage.py migrate
python manage.py collectstatic
```

5. Crie um superusuário para acessar o painel admin:

```bash
python manage.py createsuperuser
```

## Executando

```bash
# Servidor de desenvolvimento
python manage.py runserver

# Servidor de produção (Waitress)
python run_server.py
```

O servidor ficará disponível em `http://localhost:8000`.

## Funcionalidades

### Loja (público)
- Catálogo de produtos com filtros por categoria, tipo e faixa de preço (Fragacoins)
- Ordenação por menor/maior preço e mais vendidos
- Página de produto com variações de cor e tamanho
- Carrinho de compras (funciona para usuários anônimos e logados)
- Checkout com validação de saldo de Fragacoins e estoque
- E-mail de confirmação de pedido enviado ao colaborador e ao sistema Agidesk

### Conta do usuário
- Criação de conta, login e logout
- Edição de perfil e alteração de senha
- Histórico de pedidos

### Painel administrativo (grupo "Equipe")
- Dashboard com métricas (pedidos, faturamento, produtos vendidos)
- Gerenciamento de saldo de Fragacoins dos colaboradores
- CRUD de produtos, categorias, tipos e banners
- Gerenciamento de estoque por cor/tamanho
- Exportação de relatórios em CSV (pedidos, clientes, endereços)

## Estrutura do Projeto

```
ecommerce/          # Configuração do projeto Django (settings, urls)
loja/               # App principal
  models.py         # Modelos (Cliente, Produto, Pedido, ItemEstoque, etc.)
  views.py          # Views (loja, carrinho, checkout, painel interno)
  urls.py           # Rotas
  utils.py          # Filtros, ordenação, exportação CSV
  novos_context.py  # Context processors (carrinho, categorias, equipe)
  templates/        # Templates HTML
    interno/        # Templates do painel administrativo
    usuario/        # Templates de conta do usuário
static/             # CSS, JS e imagens
media/              # Uploads (imagens de produtos e banners)
run_server.py       # Servidor Waitress para produção
```

## Tecnologias

- **Django 5.2** — framework web
- **PostgreSQL** — banco de dados
- **Waitress** — servidor WSGI de produção
- **WhiteNoise** — servir arquivos estáticos
- **django-smart-selects** — selects em cascata (Estado → Cidade)
- **Pillow** — processamento de imagens
