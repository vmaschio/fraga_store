from django.urls import path
from .views import *
from django.contrib.auth import views

urlpatterns = [
    path('', homepage, name="homepage"),
    path('loja/', loja, name="loja"),
    path('loja/<str:filtro>/', loja, name="loja"),
    path('produto/<int:id_produto>/', ver_produto, name="ver_produto"),
    path('produto/<int:id_produto>/<int:id_cor>/', ver_produto, name="ver_produto"),
    path('carrinho/', carrinho, name="carrinho"),
    path('checkout/', checkout, name="checkout"),
    path('adicionar-carrinho/<int:id_produto>/', adicionar_carrinho, name="adicionar_carrinho"),
    path('remover-carrinho/<int:id_produto>/', remover_carrinho, name="remover_carrinho"),
    path('adicionar-endereco/', adicionar_endereco, name="adicionar_endereco"),
    path('finalizarpedido/<int:id_pedido>/', finalizar_pedido, name="finalizar_pedido"),

    path('minhaconta/', minha_conta, name="minha_conta"),
    path('meus-pedidos/', meus_pedidos, name="meus_pedidos"),
    path('fazer-login/', fazer_login, name="fazer_login"),
    path('criar-conta/', criar_conta, name="criar_conta"),
    path('fazer-logout/', fazer_logout, name="fazer_logout"),

    path('gerenciar-loja/', gerenciar_loja, name="gerenciar_loja"),
    path('exportar-relatorio/<str:relatorio>/', exportar_relatorio , name="exportar_relatorio"),

    path('gerenciar-produtos/', gerenciar_produtos, name="gerenciar_produtos"),
    path('adicionar-produto/', adicionar_produto, name="adicionar_produto"),
    path('editar-produto/<int:id_produto>/', editar_produto, name="editar_produto"),
    path('gerenciar-estoque/<int:id_produto>/', gerenciar_estoque, name="gerenciar_estoque"),

    path('gerenciar-categorias/', gerenciar_categorias, name='gerenciar_categorias'),
    path('adicionar-categoria/', adicionar_categoria, name='adicionar_categoria'),
    path('editar-categoria/<int:id_categoria>/', editar_categoria, name='editar_categoria'),
    path('excluir-categoria/<int:id_categoria>/', excluir_categoria, name='excluir_categoria'),

    path('gerenciar-tipos/', gerenciar_tipos, name='gerenciar_tipos'),
    path('adicionar-tipo/', adicionar_tipo, name='adicionar_tipo'),
    path('editar-tipo/<int:id_tipo>/', editar_tipo, name='editar_tipo'),
    path('excluir-tipo/<int:id_tipo>/', excluir_tipo, name='excluir_tipo'),

    path('gerenciar-banners/', gerenciar_banners, name='gerenciar_banners'),
    path('adicionar-banner/', adicionar_banner, name='adicionar_banner'),
    path('editar-banner/<int:id_banner>/', editar_banner, name='editar_banner'),
    path('excluir-banner/<int:id_banner>/', excluir_banner, name='excluir_banner'),

    path("password_change/", views.PasswordChangeView.as_view(), name="password_change"),
    path("password_change/done/", views.PasswordChangeDoneView.as_view(), name="password_change_done"),
    path("password_reset/", views.PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reset/done/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]