from django.db.models import Max, Min
from django.http import HttpResponse
import csv
from loja.models import Pedido

def filtrar_produtos(produtos, filtro):
    if filtro:
        if "-" in filtro:
            categoria, tipo = filtro.split("-", 1)
            produtos = produtos.filter(tipo__slug=tipo, categoria__slug=categoria)
        else:
            produtos = produtos.filter(categoria__slug=filtro)
    return produtos

def preco_minimo_maximo(produtos):
    if produtos.exists():
        resultado = produtos.aggregate(minimo=Min("preco_fragacoin"), maximo=Max("preco_fragacoin"))
        return resultado['minimo'] or 0, resultado['maximo'] or 0
    return 0, 0

def ordenar_produtos(produtos, ordem):
    if ordem == "menor-preco":
        produtos = produtos.order_by("preco_fragacoin")
    elif ordem == "maior-preco":
        produtos = produtos.order_by("-preco_fragacoin")
    elif ordem == "mais-vendidos":
        lista_produtos = []
        for produto in produtos:
            lista_produtos.append((produto.total_vendas(), produto))
        lista_produtos = sorted(lista_produtos, reverse=True, key=lambda tupla: tupla[0])
        produtos = [item[1] for item in lista_produtos]
    return produtos

def exportar_csv(informacoes):
    model = informacoes.model
    colunas = [field.name for field in model._meta.fields]
    
    if model == Pedido:
        colunas.append('preco_total')

    resposta = HttpResponse(content_type="text/csv")
    resposta["Content-Disposition"] = f"attachment; filename=export_{model.__name__}.csv"

    criador_csv = csv.writer(resposta, delimiter=";")
    criador_csv.writerow(colunas)

    for linha in informacoes:
        if model == Pedido:
            linha_values = [getattr(linha, col) for col in colunas if col != 'preco_total']
            linha_values.append(linha.preco_total)
            criador_csv.writerow(linha_values)
        else:
            criador_csv.writerow([getattr(linha, col) for col in colunas])

    return resposta