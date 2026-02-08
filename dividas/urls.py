from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'dividas'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
     # Authentication URLs
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('accounts/logout/', auth_views.LogoutView.as_view(
        template_name='logout.html'
    ), name='logout'),
    
    path('cadastrar/', views.cadastrar_cliente, name='cadastrar_cliente'),
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('cliente/<uuid:cliente_id>/', views.detalhes_cliente, name='detalhes_cliente'),
    path('divida/<uuid:divida_id>/baixar/', views.baixar_divida, name='baixar_divida'),
    path('cliente/<uuid:cliente_id>/adicionar-divida/', 
         views.adicionar_divida_cliente_existente, 
         name='adicionar_divida_cliente_existente'),
    path('api/cliente/<uuid:cliente_id>/dividas/', views.api_dividas_cliente, name='api_dividas_cliente'),
    path('estatisticas/', views.dashboard_estatisticas, name='dashboard_estatisticas'),
    path(
        'api/buscar-cliente-cpf/',
        views.api_buscar_cliente_cpf,
        name='api_buscar_cliente_cpf'
    ),
    path(
        'cliente/<uuid:cliente_id>/',
        views.detalhes_cliente,
        name='detalhes_cliente'
    ),
]
