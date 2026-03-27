from django.db.models import Sum
from .models import Pedido, ItensPedido, Cliente, Categoria, Tipo

def carrinho(request):
    if request.user.is_authenticated:
        try:
            cliente = request.user.cliente
        except Cliente.DoesNotExist:
            return {"quantidade_produtos_carrinho": 0}
    else:
        id_sessao = request.COOKIES.get("id_sessao")
        if id_sessao:
            cliente = Cliente.objects.filter(id_sessao=id_sessao).first()
            if not cliente:
                return {"quantidade_produtos_carrinho": 0}
        else:
            return {"quantidade_produtos_carrinho": 0}
    pedido = Pedido.objects.filter(cliente=cliente, finalizado=False).first()
    if not pedido:
        return {"quantidade_produtos_carrinho": 0}
    total = ItensPedido.objects.filter(pedido=pedido).aggregate(
        total=Sum('quantidade')
    )['total'] or 0
    return {"quantidade_produtos_carrinho": total}

def categorias_tipos(request):
    categorias_navegacao = Categoria.objects.all()
    tipos_navegacao = Tipo.objects.all()
    return {"categorias_navegacao": categorias_navegacao, "tipos_navegacao": tipos_navegacao}

def faz_parte_equipe(request):
    equipe = False
    if request.user.is_authenticated:
        if request.user.groups.filter(name="Equipe").exists():
            equipe = True
    return {"equipe": equipe}