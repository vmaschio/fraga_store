import os
import logging
from functools import wraps

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import F
import uuid

from .models import (
    Banner, Produto, ItemEstoque, Cor, ImagemProduto, Cliente,
    Pedido, ItensPedido, Endereco, Categoria, Tipo,
)
from .utils import filtrar_produtos, preco_minimo_maximo, ordenar_produtos, exportar_csv

logger = logging.getLogger(__name__)

def equipe_required(function):
    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.groups.filter(name='Equipe').exists():
            return function(request, *args, **kwargs)
        else:
            messages.error(request, "Você não tem permissão para acessar esta página.")
            return redirect('homepage')
    return wrap

# Create your views here.
def homepage(request):
    banners = Banner.objects.filter(ativo=True)
    context = {'banners': banners}
    return render(request, 'homepage.html', context)

def loja(request, filtro=None):
    produtos = Produto.objects.filter(ativo=True)
    produtos = filtrar_produtos(produtos, filtro)
    
    # aplicar os filtros do formulário
    if request.method == "POST":
        dados = request.POST.dict()

        produtos = produtos.filter(preco_fragacoin__gte=dados.get("preco_minimo"), preco_fragacoin__lte=dados.get("preco_maximo"))
        
        if "tipo" in dados:
            produtos = produtos.filter(tipo__slug=dados.get("tipo"))
        if "categoria" in dados:
            produtos = produtos.filter(categoria__slug=dados.get("categoria"))

    ids_categorias = produtos.values_list("categoria", flat=True).distinct()
    categorias = Categoria.objects.filter(id__in=ids_categorias)
    minimo, maximo = preco_minimo_maximo(produtos)

    ordem = request.GET.get("ordem", "menor-preco")
    produtos = ordenar_produtos(produtos, ordem)
    
    context = {"produtos": produtos, "minimo": minimo, "maximo": maximo, 
               "categorias": categorias}
    return render(request, 'loja.html', context)

def ver_produto(request, id_produto, id_cor=None):
    produto = Produto.objects.get(id=id_produto)
    itens_estoque = ItemEstoque.objects.filter(produto=produto, quantidade__gt=0)
    
    has_variations = itens_estoque.exclude(tamanho__isnull=True, cor__isnull=True).exists()
    tem_estoque = itens_estoque.exists()
    cores = {}
    tamanhos = {}
    cor_selecionada = None
    
    imagem_exibicao = produto.imagem
    imagens_extras = list(produto.imagens.all()) 

    if tem_estoque and has_variations:
        cores = {item.cor for item in itens_estoque if item.cor}
        if id_cor:
            try:
                cor_selecionada = Cor.objects.get(id=id_cor)
                itens_estoque_cor = itens_estoque.filter(cor__id=id_cor)
                tamanhos = {item.tamanho for item in itens_estoque_cor if item.tamanho}
                
                imagem_especifica = ImagemProduto.objects.filter(produto=produto, cor=cor_selecionada).first()
                
                if imagem_especifica:
                    imagem_exibicao = imagem_especifica.imagem
                    imagens_extras = [img for img in imagens_extras if img.id != imagem_especifica.id]                    
                    imagens_extras.insert(0, produto) 

            except Cor.DoesNotExist:
                cor_selecionada = None
    
    similares = []
    if produto.categoria and produto.tipo:
        similares = Produto.objects.filter(categoria__id=produto.categoria.id, tipo__id=produto.tipo.id).exclude(id=produto.id)[:4]
    
    context = {
        'produto': produto,
        'imagens_extras': imagens_extras,
        'imagem_exibicao': imagem_exibicao,
        "tem_estoque": tem_estoque, 
        "cores": cores, 
        "tamanhos": tamanhos, 
        "cor_selecionada": cor_selecionada, 
        "similares": similares,
        "has_variations": has_variations,
    }
    return render(request, "ver_produto.html", context)

def adicionar_carrinho(request, id_produto):
    if request.method == "POST" and id_produto:
        produto = Produto.objects.get(id=id_produto)
        itens_estoque = ItemEstoque.objects.filter(produto=produto)
        
        has_variations = itens_estoque.exclude(tamanho__isnull=True, cor__isnull=True).exists()
        
        item_estoque = None

        if has_variations:
            dados = request.POST.dict()
            tamanho = dados.get("tamanho")
            id_cor = dados.get("cor")

            try:
                itens_possiveis = ItemEstoque.objects.filter(produto=produto, quantidade__gt=0)

                if id_cor:
                    itens_possiveis = itens_possiveis.filter(cor__id=id_cor)
                else:
                    itens_possiveis = itens_possiveis.filter(cor__isnull=True)

                busca_tamanho = tamanho or ""
                
                for item in itens_possiveis:
                    item_tamanho_db = item.tamanho or ""
                    
                    if item_tamanho_db == busca_tamanho:
                        item_estoque = item
                        break
                
                if not item_estoque:
                    raise ItemEstoque.DoesNotExist

            except ItemEstoque.DoesNotExist:
                messages.error(request, "Esta combinação de produto não está disponível ou acabou o estoque.")
                return redirect('ver_produto', id_produto=id_produto)
        else:
            item_estoque = itens_estoque.first()

        if not item_estoque:
             messages.error(request, "Produto não encontrado no estoque.")
             return redirect('ver_produto', id_produto=id_produto)

        resposta = redirect('carrinho')
        if request.user.is_authenticated:
            cliente = request.user.cliente
        else:
            if request.COOKIES.get("id_sessao"):
                id_sessao = request.COOKIES.get("id_sessao")
            else:
                id_sessao = str(uuid.uuid4())
                resposta.set_cookie(key="id_sessao", value=id_sessao, max_age=60*60*24*7)
            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
        
        pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
        item_pedido, criado = ItensPedido.objects.get_or_create(item_estoque=item_estoque, pedido=pedido)
        item_pedido.quantidade += 1
        item_pedido.save()
        
        messages.success(request, f"{item_estoque.produto.nome} foi adicionado à sacola!")
        return resposta
    else:
        return redirect('loja')

def remover_carrinho(request, id_produto):
    if request.method == "POST" and id_produto:
        dados = request.POST.dict()
        tamanho = dados.get("tamanho")
        id_cor = dados.get("cor")

        cliente = None
        if request.user.is_authenticated:
            cliente = request.user.cliente
        elif request.COOKIES.get("id_sessao"):
            id_sessao = request.COOKIES.get("id_sessao")
            cliente, _ = Cliente.objects.get_or_create(id_sessao=id_sessao)
        
        if not cliente:
            messages.error(request, "Não foi possível encontrar seu carrinho.")
            return redirect('loja')

        try:
            query_filter = {
                'produto__id': id_produto,
                'tamanho': tamanho if tamanho != 'None' else None
            }

            if id_cor:
                query_filter['cor__id'] = id_cor
            else:
                query_filter['cor__isnull'] = True

            pedido, _ = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
            item_estoque = ItemEstoque.objects.get(**query_filter)
            item_pedido = ItensPedido.objects.get(item_estoque=item_estoque, pedido=pedido)
            
            item_pedido.quantidade -= 1
            if item_pedido.quantidade <= 0:
                item_pedido.delete()
                messages.success(request, f"'{item_estoque.produto.nome}' foi removido da sacola.")
            else:
                item_pedido.save()
                messages.success(request, f"Uma unidade de '{item_estoque.produto.nome}' foi removida.")

        except (ItemEstoque.DoesNotExist, ItensPedido.DoesNotExist):
            messages.error(request, "O item que você tentou remover não foi encontrado no seu carrinho.")
        
        return redirect('carrinho')
    else:
        return redirect('loja')

def carrinho(request):
    if request.user.is_authenticated:
        cliente = request.user.cliente
    else:
        if request.COOKIES.get("id_sessao"):
            id_sessao = request.COOKIES.get("id_sessao")
            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
        else:
            context = {"cliente_existente": False, 'itens_pedido': None, 'pedido': None}
            return render(request, 'carrinho.html', context)
    pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
    itens_pedido = ItensPedido.objects.filter(pedido=pedido)
    context = {'itens_pedido': itens_pedido, 'pedido': pedido, "cliente_existente": True}
    return render(request, 'carrinho.html', context)

def checkout(request):
    if request.user.is_authenticated:
        cliente = request.user.cliente
    else:
        if request.COOKIES.get("id_sessao"):
            id_sessao = request.COOKIES.get("id_sessao")
            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
        else:
            return redirect('loja')
    pedido, criado = Pedido.objects.get_or_create(cliente=cliente, finalizado=False)
    enderecos = Endereco.objects.filter(cliente=cliente)
    context = {'pedido': pedido, "enderecos": enderecos, "erro": None}
    return render(request, 'checkout.html', context)

@login_required
def finalizar_pedido(request, id_pedido):
    pedido = get_object_or_404(Pedido, id=id_pedido, cliente=request.user.cliente)
    contexto_erro = {'pedido': pedido}

    if request.method == "POST":
        endereco_id = request.POST.get("endereco")

        if not endereco_id:
            messages.error(request, "Ocorreu um erro com o endereço de retirada. Contate o administrador.")
            contexto_erro["erro"] = "invalido"
            return render(request, "checkout.html", contexto_erro)

        try:
            endereco_retirada = Endereco.objects.get(id=endereco_id)
        except (Endereco.DoesNotExist, ValueError):
            messages.error(request, "Endereço de retirada inválido. Contate o administrador.")
            contexto_erro["erro"] = "invalido"
            return render(request, "checkout.html", contexto_erro)

        try:
            with transaction.atomic():
                cliente = Cliente.objects.select_for_update().get(id=request.user.cliente.id)
                total_pedido_fragacoins = pedido.preco_total_fragacoin

                if cliente.fragacoin < total_pedido_fragacoins:
                    messages.error(request, f"Saldo de Fragacoins insuficiente para completar a compra. Seu saldo é de {cliente.fragacoin} fragacoins.")
                    contexto_erro["erro"] = "saldo"
                    return render(request, "checkout.html", contexto_erro)

                for item_pedido in pedido.itens.all():
                    atualizado = ItemEstoque.objects.filter(
                        id=item_pedido.item_estoque.id,
                        quantidade__gte=item_pedido.quantidade
                    ).update(quantidade=F('quantidade') - item_pedido.quantidade)
                    if atualizado == 0:
                        raise ValueError(f"Estoque insuficiente para o produto: {item_pedido.item_estoque.produto.nome}")

                Cliente.objects.filter(id=cliente.id).update(
                    fragacoin=F('fragacoin') - total_pedido_fragacoins
                )

                pedido.endereco = endereco_retirada
                pedido.finalizado = True
                pedido.data_finalizacao = timezone.now()
                pedido.codigo_transacao = f"{pedido.id}-{timezone.now().timestamp()}"
                pedido.save()
            
            itens_do_pedido_texto_plain = ""
            itens_do_pedido_texto_html = "<ul>"
            for item_pedido in pedido.itens.all():
                nome_produto = item_pedido.item_estoque.produto.nome
                tamanho = f" (Tamanho: {item_pedido.item_estoque.tamanho})" if item_pedido.item_estoque.tamanho else ""
                cor = f" (Cor: {item_pedido.item_estoque.cor.nome})" if item_pedido.item_estoque.cor else ""
                quantidade = item_pedido.quantidade
                preco_total = item_pedido.preco_total_fragacoin
                itens_do_pedido_texto_plain += f"- {quantidade}x {nome_produto}{tamanho}{cor}: {preco_total} fragacoins\n"
                itens_do_pedido_texto_html += f"<li>{quantidade}x {nome_produto}{tamanho}{cor}: <strong>{preco_total} fragacoins</strong></li>"
            itens_do_pedido_texto_html += "</ul>"


            try:
                assunto = f"Confirmação do seu Pedido n°{pedido.id} - Fraga Store"
                email_remetente = settings.DEFAULT_FROM_EMAIL
                email_destinatario = [pedido.cliente.email]

                mensagem = (
                    f"Olá {cliente.nome},\n\n"
                    f"Sua compra na Fraga Store foi confirmada com sucesso!\n\n"
                    f"Resumo do Pedido n°{pedido.id}:\n"
                    f"----------------------------------\n"
                    f"{itens_do_pedido_texto_plain}"
                    f"----------------------------------\n"
                    f"Total: {pedido.preco_total_fragacoin} fragacoins\n\n"
                    f"INFORMAÇÃO IMPORTANTE:\n"
                    f"A retirada do seu pedido estará disponível a partir de {settings.DATA_RETIRADA}.\n\n"
                    f"Endereço para retirada:\n"
                    f"{settings.ENDERECO_RETIRADA}\n\n"
                    f"Obrigado por comprar conosco!"
                )

                send_mail(
                    subject=assunto,
                    message=mensagem,
                    from_email=email_remetente,
                    recipient_list=email_destinatario,
                    fail_silently=False,
                )
            except Exception as e:
                logger.error("Erro ao enviar e-mail de confirmação: %s", e)

            try:
                assunto_agidesk = f"Novo Pedido Fraga Store - n°{pedido.id} - {cliente.nome}"
                email_remetente_agidesk = settings.DEFAULT_FROM_EMAIL
                email_destinatario_agidesk = [
                    os.getenv("EMAIL_AGIDESK"), 
                ]
                
                mensagem_agidesk_plain = (
                    f"Um novo pedido foi realizado na Fraga Store e precisa de preparação.\n\n"
                    f"--- Informações do Pedido ---\n"
                    f"Pedido Nº: {pedido.id}\n"
                    f"Código Transação: {pedido.codigo_transacao}\n"
                    f"Data: {pedido.data_finalizacao.strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"--- Informações do Colaborador ---\n"
                    f"Nome: {cliente.nome}\n"
                    f"Email: {cliente.email}\n\n"
                    f"--- Itens do Pedido ---\n"
                    f"{itens_do_pedido_texto_plain}" 
                    f"----------------------------------\n"
                    f"Total: {pedido.preco_total_fragacoin} fragacoins\n\n"
                    f"--- Informações de Retirada ---\n"
                    f"Endereço: {settings.ENDERECO_RETIRADA}\n"
                    f"Disponível a partir de: {settings.DATA_RETIRADA}."
                )

                mensagem_agidesk_html = (
                    f"<p>Um novo pedido foi realizado na Fraga Store e precisa de preparação.</p>"
                    f"<h3>--- Informações do Pedido ---</h3>"
                    f"<strong>Pedido Nº:</strong> {pedido.id}<br>"
                    f"<strong>Código Transação:</strong> {pedido.codigo_transacao}<br>"
                    f"<strong>Data:</strong> {pedido.data_finalizacao.strftime('%d/%m/%Y %H:%M')}<br>"
                    
                    f"<h3>--- Informações do Colaborador ---</h3>"
                    f"<strong>Nome:</strong> {cliente.nome}<br>"
                    f"<strong>Email:</strong> {cliente.email}<br>"

                    f"<h3>--- Itens do Pedido ---</h3>"
                    f"{itens_do_pedido_texto_html}"
                    
                    f"<h3>--- Total ---</h3>"
                    f"<strong>Total: {pedido.preco_total_fragacoin} fragacoins</strong><br><br>"

                    f"<h3>--- Informações de Retirada ---</h3>"
                    f"<strong>Endereço:</strong> {settings.ENDERECO_RETIRADA}<br>"
                    f"<strong>Disponível a partir de:</strong> Janeiro de 2026."
                )

                send_mail(
                    subject=assunto_agidesk,
                    message=mensagem_agidesk_plain,
                    from_email=email_remetente_agidesk,
                    recipient_list=email_destinatario_agidesk,
                    fail_silently=False, 
                    html_message=mensagem_agidesk_html
                )
            except Exception as e:
                logger.error("Erro ao enviar e-mail para o Agidesk: %s", e)

            messages.success(request, "Compra finalizada com sucesso!")
            return redirect("meus_pedidos")

        except ValueError as e:
            messages.error(request, str(e))
            contexto_erro["erro"] = "estoque"
            return render(request, "checkout.html", contexto_erro)
        except Exception as e:
            logger.error("Erro inesperado ao finalizar pedido %s: %s", id_pedido, e)
            messages.error(request, "Ocorreu um erro inesperado ao processar seu pedido. Tente novamente.")
            return render(request, "checkout.html", contexto_erro)

    return render(request, "checkout.html", {'pedido': pedido})

def adicionar_endereco(request):
    if request.method == "POST":
        if request.user.is_authenticated:
            cliente = request.user.cliente
        else:
            if request.COOKIES.get("id_sessao"):
                id_sessao = request.COOKIES.get("id_sessao")
                cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
            else:
                return redirect('loja')
        dados = request.POST.dict()
        cep_com_mascara = dados.get("cep", "")
        cep_sem_mascara = "".join(filter(str.isdigit, cep_com_mascara))

        try:
            numero = int(dados.get("numero", 0))
        except (ValueError, TypeError):
            messages.error(request, "Número do endereço inválido.")
            return redirect('adicionar_endereco')

        if len(cep_sem_mascara) != 8:
            messages.error(request, "CEP inválido. O CEP deve conter 8 dígitos.")
            return redirect('adicionar_endereco')

        Endereco.objects.create(
            cliente=cliente,
            rua=dados.get("rua"),
            numero=numero,
            estado_id=dados.get("estado"),
            cidade_id=dados.get("cidade"),
            cep=cep_sem_mascara,
            complemento=dados.get("complemento"),
        )
        return redirect('checkout')
    else:
        context = {}
        return render(request, "adicionar_endereco.html", context)

@login_required
def minha_conta(request):
    erro = None
    alterado = False
    if request.method == "POST":
        dados = request.POST.dict()
        if "senha_atual" in dados:
            senha_atual = dados.get("senha_atual")
            nova_senha = dados.get("nova_senha")
            nova_senha_confirmacao = dados.get("nova_senha_confirmacao")
            if nova_senha == nova_senha_confirmacao:
                usuario = authenticate(request, username=request.user.email, password=senha_atual)
                if usuario:
                    usuario.set_password(nova_senha)
                    usuario.save()
                    alterado = True
                else:
                    erro = "senha_incorreta"
            else:
                erro = "senhas_diferentes"
        elif "email" in dados:
            email = dados.get("email")
            nome = dados.get("nome")
            if email != request.user.email:
                usuarios = User.objects.filter(email=email)
                if len(usuarios) > 0:
                    erro = "email_existente"
            if not erro:
                cliente = request.user.cliente
                cliente.email = email
                request.user.email = email
                request.user.username = email
                cliente.nome = nome
                cliente.save()
                request.user.save()
                alterado = True
        else:
            erro = "formulario_invalido"
    context = {"erro": erro, "alterado": alterado}
    return render(request, 'usuario/minha_conta.html', context)

@login_required
def meus_pedidos(request):
    cliente = request.user.cliente
    pedidos = Pedido.objects.filter(finalizado=True, cliente=cliente).order_by("-data_finalizacao")

    context = {"pedidos": pedidos}
    return render(request, "usuario/meus_pedidos.html", context)

def fazer_login(request):
    erro = False
    if request.user.is_authenticated:
        return redirect('loja')
    if request.method == "POST":
        dados = request.POST.dict()
        if "email" in dados and "senha" in dados:
            email = dados.get("email")
            senha = dados.get("senha")
            usuario = authenticate(request, username=email, password=senha)
            if usuario:
                login(request, usuario)
                return redirect('loja')
            else:
                erro = True
        else:
            erro = True
    context = {"erro": erro}
    return render(request, 'usuario/login.html', context)

def criar_conta(request):
    erro = None
    if request.user.is_authenticated:
        return redirect('loja')
    
    if request.method == "POST":
        dados = request.POST.dict()
        if "email" in dados and "senha" in dados and "confirmacao_senha" in dados and "nome" in dados:
            email = dados.get("email")
            senha = dados.get("senha")
            confirmacao_senha = dados.get("confirmacao_senha")
            nome = dados.get("nome")

            try:
                validate_email(email)
            except ValidationError:
                erro = "email_invalido"

            if not erro:
                try:
                    validate_password(senha)
                except ValidationError:
                    erro = "senha_fraca"

            if not erro:
                if senha == confirmacao_senha:
                    usuario, criado = User.objects.get_or_create(username=email, email=email)
                    if not criado:
                        erro = "usuario_existente"
                    else:
                        usuario.set_password(senha)
                        usuario.save()

                        usuario = authenticate(request, username=email, password=senha)
                        login(request, usuario)

                        if request.COOKIES.get("id_sessao"):
                            id_sessao = request.COOKIES.get("id_sessao")
                            cliente, criado = Cliente.objects.get_or_create(id_sessao=id_sessao)
                        else:
                            cliente, criado = Cliente.objects.get_or_create(email=email)
                        
                        cliente.usuario = usuario
                        cliente.email = email
                        cliente.nome = nome 
                        cliente.save()
                        
                        return redirect("loja")
                else:
                    erro = "senhas_diferentes"
        else:
            erro = "preenchimento"
    context = {"erro": erro}
    return render(request, 'usuario/criar_conta.html', context)

@login_required
def fazer_logout(request):
    logout(request)
    return redirect("fazer_login")

@equipe_required
def gerenciar_loja(request):
    if request.method == "POST":
        dados = request.POST
        if 'atualizar_saldo' in dados:
            cliente_id = dados.get('cliente_id')
            novo_saldo = dados.get('novo_saldo')
            
            try:
                cliente = Cliente.objects.get(id=cliente_id)
                cliente.fragacoin = int(novo_saldo)
                cliente.save()
                messages.success(request, f"Saldo de {cliente.nome} atualizado para {cliente.fragacoin} Fragacoins.")
            except Cliente.DoesNotExist:
                messages.error(request, "Cliente não encontrado.")
            except ValueError:
                messages.error(request, "Valor inválido inserido.")
            
            return redirect('gerenciar_loja')

    from django.db.models import Sum
    stats = ItensPedido.objects.filter(pedido__finalizado=True).aggregate(
        faturamento=Sum(F('quantidade') * F('item_estoque__produto__preco_fragacoin')),
        qtde_produtos=Sum('quantidade'),
    )
    qtde_pedidos = Pedido.objects.filter(finalizado=True).count()
    faturamento = stats['faturamento'] or 0
    qtde_produtos = stats['qtde_produtos'] or 0

    clientes = Cliente.objects.exclude(email__isnull=True).exclude(email='').order_by('nome')
    produtos = Produto.objects.all().order_by('nome')

    context = {
        "qtde_pedidos": qtde_pedidos, 
        "qtde_produtos": qtde_produtos, 
        "faturamento": faturamento,
        "clientes": clientes,
        "produtos": produtos
    }
    return render(request, 'interno/gerenciar_loja.html', context=context)

@equipe_required
def exportar_relatorio(request, relatorio):
    relatorios = {
        'pedido': lambda: Pedido.objects.filter(finalizado=True),
        'cliente': lambda: Cliente.objects.all(),
        'endereco': lambda: Endereco.objects.all(),
    }
    if relatorio not in relatorios:
        messages.error(request, "Relatório inválido.")
        return redirect('gerenciar_loja')
    return exportar_csv(relatorios[relatorio]())

@equipe_required
def gerenciar_produtos(request):
    produtos = Produto.objects.all()
    context = {'produtos': produtos}
    return render(request, 'interno/gerenciar_produtos.html', context)

@equipe_required
def adicionar_produto(request):
    if request.method == "POST":
        dados = request.POST
        nome = dados.get('nome')
        preco = dados.get('preco')
        preco_fragacoin = dados.get('preco_fragacoin')
        categoria_id = dados.get('categoria')
        tipo_id = dados.get('tipo')
        descricao = dados.get('descricao')
        imagem = request.FILES.get('imagem')

        categoria = Categoria.objects.get(id=categoria_id)
        tipo = Tipo.objects.get(id=tipo_id)

        produto = Produto.objects.create(
            nome=nome,
            preco=preco,
            preco_fragacoin=preco_fragacoin,
            categoria=categoria,
            tipo=tipo,
            descricao=descricao,
            imagem=imagem
        )
        imagens_adicionais = request.FILES.getlist('imagens_extras')
        for img in imagens_adicionais:
            ImagemProduto.objects.create(produto=produto, imagem=img)
        messages.success(request, "Produto adicionado com sucesso!")
        return redirect('gerenciar_produtos')

    categorias = Categoria.objects.all()
    tipos = Tipo.objects.all()
    context = {'categorias': categorias, 'tipos': tipos}
    return render(request, 'interno/adicionar_produto.html', context)


@equipe_required
def editar_produto(request, id_produto):
    produto = get_object_or_404(Produto, id=id_produto)

    if request.method == "POST":
        dados = request.POST
        produto.nome = dados.get('nome')
        produto.preco = dados.get('preco')
        produto.preco_fragacoin = dados.get('preco_fragacoin')
        produto.categoria = Categoria.objects.get(id=dados.get('categoria'))
        produto.tipo = Tipo.objects.get(id=dados.get('tipo'))
        produto.descricao = dados.get('descricao')
        produto.ativo = True if dados.get('ativo') == 'on' else False

        if request.FILES.get('imagem'):
            produto.imagem = request.FILES.get('imagem')

        produto.save()
        messages.success(request, "Produto editado com sucesso!")
        return redirect('gerenciar_produtos')

    categorias = Categoria.objects.all()
    tipos = Tipo.objects.all()
    context = {'produto': produto, 'categorias': categorias, 'tipos': tipos}
    return render(request, 'interno/editar_produto.html', context)


@equipe_required
def gerenciar_estoque(request, id_produto):
    produto = get_object_or_404(Produto, id=id_produto)
    itens_estoque = ItemEstoque.objects.filter(produto=produto)

    if request.method == "POST":
        dados = request.POST
        
        if 'adicionar_item' in dados:
            cor_id = dados.get('cor')
            tamanho = dados.get('tamanho')
            quantidade = dados.get('quantidade')

            cor = get_object_or_404(Cor, id=cor_id)

            item, criado = ItemEstoque.objects.get_or_create(produto=produto, cor=cor, tamanho=tamanho)
            item.quantidade += int(quantidade)
            item.save()
            messages.success(request, "Item adicionado ao estoque.")

        else:
            for item in itens_estoque:
                quantidade = dados.get(f'quantidade_{item.id}')
                if quantidade is not None:
                    item.quantidade = int(quantidade)
                    item.save()
            messages.success(request, "Estoque atualizado com sucesso.")
        
        return redirect('gerenciar_estoque', id_produto=id_produto)

    cores = Cor.objects.all()
    context = {'produto': produto, 'itens_estoque': itens_estoque, 'cores': cores}
    return render(request, 'interno/gerenciar_estoque.html', context)

@equipe_required
def gerenciar_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'interno/gerenciar_categorias.html', {'categorias': categorias})

@equipe_required
def adicionar_categoria(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        slug = request.POST.get('slug')
        imagem = request.FILES.get('imagem')
        Categoria.objects.create(nome=nome, slug=slug, imagem=imagem)
        messages.success(request, 'Categoria adicionada com sucesso!')
        return redirect('gerenciar_categorias')
    return render(request, 'interno/adicionar_categoria.html')

@equipe_required
def editar_categoria(request, id_categoria):
    categoria = get_object_or_404(Categoria, id=id_categoria)
    if request.method == 'POST':
        categoria.nome = request.POST.get('nome')
        categoria.slug = request.POST.get('slug')
        if request.FILES.get('imagem'):
            categoria.imagem = request.FILES.get('imagem')
        categoria.save()
        messages.success(request, 'Categoria editada com sucesso!')
        return redirect('gerenciar_categorias')
    return render(request, 'interno/editar_categoria.html', {'categoria': categoria})

@equipe_required
def gerenciar_tipos(request):
    tipos = Tipo.objects.all()
    return render(request, 'interno/gerenciar_tipos.html', {'tipos': tipos})

@equipe_required
def adicionar_tipo(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        slug = request.POST.get('slug')
        Tipo.objects.create(nome=nome, slug=slug)
        messages.success(request, 'Tipo adicionado com sucesso!')
        return redirect('gerenciar_tipos')
    return render(request, 'interno/adicionar_tipo.html')

@equipe_required
def editar_tipo(request, id_tipo):
    tipo = get_object_or_404(Tipo, id=id_tipo)
    if request.method == 'POST':
        tipo.nome = request.POST.get('nome')
        tipo.slug = request.POST.get('slug')
        tipo.save()
        messages.success(request, 'Tipo editado com sucesso!')
        return redirect('gerenciar_tipos')
    return render(request, 'interno/editar_tipo.html', {'tipo': tipo})

@equipe_required
def gerenciar_banners(request):
    banners = Banner.objects.all()
    return render(request, 'interno/gerenciar_banners.html', {'banners': banners})

@equipe_required
def adicionar_banner(request):
    if request.method == 'POST':
        link_destino = request.POST.get('link_destino')
        imagem = request.FILES.get('imagem')
        ativo = request.POST.get('ativo') == 'on'
        Banner.objects.create(link_destino=link_destino, imagem=imagem, ativo=ativo)
        messages.success(request, 'Banner adicionado com sucesso!')
        return redirect('gerenciar_banners')
    
    categorias = Categoria.objects.all()
    tipos = Tipo.objects.all()
    context = {
        'categorias': categorias,
        'tipos': tipos
    }
    return render(request, 'interno/adicionar_banner.html', context)

@equipe_required
def editar_banner(request, id_banner):
    banner = get_object_or_404(Banner, id=id_banner)
    if request.method == 'POST':
        banner.link_destino = request.POST.get('link_destino')
        banner.ativo = request.POST.get('ativo') == 'on'
        if request.FILES.get('imagem'):
            banner.imagem = request.FILES.get('imagem')
        banner.save()
        messages.success(request, 'Banner editado com sucesso!')
        return redirect('gerenciar_banners')

    categorias = Categoria.objects.all()
    tipos = Tipo.objects.all()
    context = {
        'banner': banner,
        'categorias': categorias,
        'tipos': tipos
    }
    return render(request, 'interno/editar_banner.html', context)

@require_POST
@equipe_required
def excluir_banner(request, id_banner):
    banner = get_object_or_404(Banner, id=id_banner)
    banner.delete()
    messages.success(request, 'Banner excluído com sucesso!')
    return redirect('gerenciar_banners')

@require_POST
@equipe_required
def excluir_categoria(request, id_categoria):
    categoria = get_object_or_404(Categoria, id=id_categoria)
    categoria.delete()
    messages.success(request, 'Categoria excluída com sucesso!')
    return redirect('gerenciar_categorias')

@require_POST
@equipe_required
def excluir_tipo(request, id_tipo):
    tipo = get_object_or_404(Tipo, id=id_tipo)
    tipo.delete()
    messages.success(request, 'Tipo excluído com sucesso!')
    return redirect('gerenciar_tipos')