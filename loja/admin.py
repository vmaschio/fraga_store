from django.contrib import admin
from .models import *

class ImagemProdutoInline(admin.TabularInline):
    model = ImagemProduto
    extra = 1

class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'preco_fragacoin', 'ativo')
    inlines = [ImagemProdutoInline]

# Register your models here.
admin.site.register(Produto, ProdutoAdmin)
admin.site.register(Cliente)
admin.site.register(Categoria)
admin.site.register(Tipo)
admin.site.register(ItemEstoque)
admin.site.register(Endereco)
admin.site.register(Pedido)
admin.site.register(ItensPedido)
admin.site.register(Banner)
admin.site.register(Cor)
admin.site.register(Estado)
admin.site.register(Cidade)