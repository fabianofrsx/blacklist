from django.contrib import admin
from .models import Empresa, UsuarioEmpresa, Cliente, Divida, HistoricoDivida

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cnpj', 'telefone', 'email', 'data_cadastro', 'ativo')
    list_filter = ('ativo', 'data_cadastro')
    search_fields = ('nome', 'cnpj', 'email')
    list_editable = ('ativo',)

@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'is_admin_empresa', 'data_associacao')
    list_filter = ('empresa', 'is_admin_empresa')
    search_fields = ('usuario__username', 'usuario__email', 'empresa__nome')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'cpf', 'data_nascimento', 'email', 'telefone', 'data_cadastro')
    list_filter = ('data_cadastro', 'data_nascimento')
    search_fields = ('nome_completo', 'cpf', 'email', 'telefone')
    readonly_fields = ('data_cadastro', 'atualizado_em')

@admin.register(Divida)
class DividaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'empresa', 'valor_original', 'valor_atual', 'data_vencimento', 'status', 'data_cadastro')
    list_filter = ('status', 'empresa', 'data_vencimento', 'data_cadastro')
    search_fields = ('cliente__nome_completo', 'cliente__cpf', 'empresa__nome')
    readonly_fields = ('data_cadastro', 'cadastrado_por', 'baixado_por', 'data_pagamento')
    list_editable = ('status',)
    raw_id_fields = ('cliente', 'empresa')

@admin.register(HistoricoDivida)
class HistoricoDividaAdmin(admin.ModelAdmin):
    list_display = ('divida', 'tipo_acao', 'valor_anterior', 'valor_atualizado', 'usuario', 'data_acao')
    list_filter = ('tipo_acao', 'data_acao')
    search_fields = ('divida__cliente__nome_completo', 'usuario__username', 'descricao')
    readonly_fields = ('data_acao',)