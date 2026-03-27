from django.db import models
from django.db.models import Sum, F
from django.contrib.auth.models import User

class Cliente(models.Model):
    nome = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    usuario = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    id_sessao = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    fragacoin = models.IntegerField(default=0)

    def __str__(self):
        return str(self.email)

class Categoria(models.Model):
    imagem = models.ImageField(null=True, blank=True)
    nome = models.CharField(max_length=70)
    slug = models.CharField(max_length=70, unique=True)

    def __str__(self):
        return str(self.nome)

class Tipo(models.Model):
    nome = models.CharField(max_length=70)
    slug = models.CharField(max_length=70, unique=True)

    def __str__(self):
        return str(self.nome)

class Produto(models.Model):
    imagem = models.ImageField(null=True, blank=True)
    nome = models.CharField(max_length=200)
    preco = models.DecimalField(max_digits=6, decimal_places=2)
    descricao = models.CharField(max_length=300, null=True, blank=True)
    preco_fragacoin = models.PositiveIntegerField()
    ativo = models.BooleanField(default=True, db_index=True)
    categoria = models.ForeignKey(Categoria, null=True, blank=True, on_delete=models.SET_NULL, related_name='produtos')
    tipo = models.ForeignKey(Tipo, null=True, blank=True, on_delete=models.SET_NULL, related_name='produtos')

    def total_vendas(self):
        return ItensPedido.objects.filter(
            pedido__finalizado=True, item_estoque__produto=self
        ).aggregate(total=Sum('quantidade'))['total'] or 0

    def __str__(self):
        return f"Nome: {self.nome}, Categoria: {self.categoria}, Tipo: {self.tipo}, Preço R$: {self.preco}, Preço fragacoin: {self.preco_fragacoin}"

class Cor(models.Model):
    nome = models.CharField(max_length=50, null=True, blank=True)
    codigo = models.CharField(max_length=30, null=True, blank=True)

    def __str__(self):
        return str(self.nome)
    
class ImagemProduto(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="imagens")
    imagem = models.ImageField(upload_to="produtos_extras")
    cor = models.ForeignKey(Cor, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Imagem extra de {self.produto.nome}"

class ItemEstoque(models.Model):
    produto = models.ForeignKey(Produto, null=True, blank=True, on_delete=models.SET_NULL)
    cor = models.ForeignKey(Cor, null=True, blank=True, on_delete=models.SET_NULL)
    tamanho = models.CharField(max_length=70, null=True, blank=True)
    quantidade = models.IntegerField(default=0)

    def __str__(self):
        nome_produto = self.produto.nome if self.produto else "Produto não definido"
        nome_cor = self.cor.nome if self.cor else "Cor não definida"
        tamanho = self.tamanho if self.tamanho else "Tamanho não definido"

        return f"{nome_produto}, Tamanho: {tamanho}, Cor: {nome_cor}"

class Estado(models.Model):
    sigla = models.CharField(max_length=2, unique=True)
    nome = models.CharField(max_length=50)

    def __str__(self):
        return self.nome

class Cidade(models.Model):
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nome} ({self.estado.sigla})"

class Endereco(models.Model):
    rua = models.CharField(max_length=400, null=True, blank=True)
    numero = models.IntegerField(default=0)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    cep = models.CharField(max_length=8, null=True, blank=True)
    cidade = models.ForeignKey(Cidade, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.ForeignKey(Estado, on_delete=models.SET_NULL, null=True, blank=True)
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.cliente} - {self.rua} - {self.cidade} - {self.estado} - {self.cep}"

class Pedido(models.Model):
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.SET_NULL)
    finalizado = models.BooleanField(default=False, db_index=True)
    codigo_transacao = models.CharField(max_length=100)
    endereco = models.ForeignKey(Endereco, null=True, blank=True, on_delete=models.SET_NULL)
    data_finalizacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        email = self.cliente.email if self.cliente else "N/A"
        return f"Cliente: {email} - id_pedido: {self.id} - Finalizado: {self.finalizado}"

    @property
    def quantidade_total(self):
        return self.itenspedido_set.aggregate(
            total=Sum('quantidade')
        )['total'] or 0

    @property
    def preco_total_fragacoin(self):
        return self.itenspedido_set.aggregate(
            total=Sum(F('quantidade') * F('item_estoque__produto__preco_fragacoin'))
        )['total'] or 0

    @property
    def preco_total(self):
        return self.itenspedido_set.aggregate(
            total=Sum(F('quantidade') * F('item_estoque__produto__preco'))
        )['total'] or 0

    @property
    def itens(self):
        return self.itenspedido_set.select_related('item_estoque__produto', 'item_estoque__cor')

class ItensPedido(models.Model):
    item_estoque = models.ForeignKey(ItemEstoque, null=True, blank=True, on_delete=models.SET_NULL)
    quantidade = models.IntegerField(default=0)
    pedido = models.ForeignKey(Pedido, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        pedido_id = self.pedido.id if self.pedido else "N/A"
        produto = self.item_estoque.produto if self.item_estoque else "N/A"
        tamanho = self.item_estoque.tamanho if self.item_estoque else "N/A"
        cor = self.item_estoque.cor.nome if self.item_estoque and self.item_estoque.cor else "N/A"
        return f"Id pedido: {pedido_id} - Produto: {produto}, {tamanho}, {cor}"

    @property
    def preco_total_fragacoin(self):
        return self.quantidade * self.item_estoque.produto.preco_fragacoin

    @property
    def preco_total(self):
        return self.quantidade * self.item_estoque.produto.preco

class Banner(models.Model):
    imagem = models.ImageField(null=True, blank=True)
    link_destino = models.CharField(max_length=400 ,null=True, blank=True)
    ativo = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.link_destino} - Ativo: {self.ativo}"