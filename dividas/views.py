from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.contrib import messages
from django.db.models import (
    Q, Count, Sum, Case, When,
    IntegerField, Max
)
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
import csv
from decimal import Decimal, InvalidOperation


from .models import Cliente, Divida, Empresa, UsuarioEmpresa, HistoricoDivida
from .forms import ClienteForm, DividaForm, ClienteDividaForm


# =============== DASHBOARD ===============
@login_required
def dashboard(request):
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
        is_empresa_user = True

        estatisticas = {
            'total_clientes': Cliente.objects.filter(dividas__empresa=empresa).distinct().count(),
            'dividas_ativas': Divida.objects.filter(empresa=empresa, status='ATIVA').count(),
            'dividas_pagas': Divida.objects.filter(empresa=empresa, status='PAGA').count(),
            'valor_total': Divida.objects.filter(
                empresa=empresa, status='ATIVA'
            ).aggregate(total=Sum('valor_atual'))['total'] or 0,
            'dividas_vencidas': Divida.objects.filter(
                empresa=empresa,
                status='ATIVA',
                data_vencimento__lt=timezone.now().date()
            ).count(),
        }

        clientes_recentes = Cliente.objects.filter(
            dividas__empresa=empresa
        ).distinct().order_by('-dividas__data_cadastro')[:10]  # Aumentei para 10

    except UsuarioEmpresa.DoesNotExist:
        empresa = None
        is_empresa_user = False
        estatisticas = {}
        clientes_recentes = []

    return render(request, 'dividas/dashboard.html', {
        'empresa': empresa,
        'is_empresa_user': is_empresa_user,
        'estatisticas': estatisticas,
        'clientes': clientes_recentes,  # Mudei para 'clientes' para usar no template
        'clientes_recentes': clientes_recentes,  # Mantém também o nome original
    })


# =============== CADASTRO ===============
@login_required
def cadastrar_cliente(request):
    # 🔐 Garantir que o usuário pertence a uma empresa
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
    except UsuarioEmpresa.DoesNotExist:
        return HttpResponseForbidden("Apenas usuários de empresa podem cadastrar clientes.")

    cliente_existente = None

    if request.method == 'POST':
        form_cliente = ClienteForm(request.POST)
        form_divida = DividaForm(request.POST, empresa=empresa)

        if form_cliente.is_valid() and form_divida.is_valid():
            try:
                with transaction.atomic():
                    cpf = form_cliente.cleaned_data['cpf']

                    # 🔍 Buscar cliente pelo CPF formatado
                    cliente_existente = Cliente.objects.filter(cpf=cpf).first()

                    if not cliente_existente:
                        # ➕ Criar novo cliente
                        cliente_existente = Cliente.objects.create(
                            nome_completo=form_cliente.cleaned_data['nome_completo'],
                            cpf=cpf,
                            data_nascimento=form_cliente.cleaned_data['data_nascimento'],
                            email=form_cliente.cleaned_data['email'],
                            telefone=form_cliente.cleaned_data['telefone'],
                            endereco=form_cliente.cleaned_data['endereco'],
                        )

                    # 💰 Criar dívida
                    divida = form_divida.save(commit=False)
                    divida.cliente = cliente_existente
                    divida.empresa = empresa
                    divida.cadastrado_por = request.user
                    divida.valor_atual = divida.valor_original
                    divida.save()

                    # 🧾 Histórico
                    HistoricoDivida.objects.create(
                        divida=divida,
                        tipo_acao='CADASTRO',
                        valor_atualizado=divida.valor_original,
                        descricao=f'Dívida cadastrada na empresa {empresa.nome}',
                        usuario=request.user
                    )

                    messages.success(
                        request,
                        f'Dívida cadastrada com sucesso para {cliente_existente.nome_completo}'
                    )
                    return redirect(
                        'dividas:detalhes_cliente',
                        cliente_id=cliente_existente.id
                    )

            except Exception as e:
                messages.error(request, f'Erro ao salvar os dados: {str(e)}')

        else:
            # 🔥 IMPORTANTE: aqui evita falha silenciosa
            messages.error(request, 'Corrija os erros abaixo antes de continuar.')

    else:
        form_cliente = ClienteForm()
        form_divida = DividaForm(empresa=empresa)

    context = {
        'form_cliente': form_cliente,
        'form_divida': form_divida,
        'empresa': empresa,
        'cliente_existente': cliente_existente,
        'is_empresa_user': True,
    }

    return render(request, 'dividas/cadastrar_cliente.html', context)

@login_required
def adicionar_divida_cliente_existente(request, cliente_id):
    """Adicionar nova dívida a um cliente já cadastrado"""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
    except UsuarioEmpresa.DoesNotExist:
        return HttpResponseForbidden("Apenas usuários de empresa podem adicionar dívidas.")
    
    # Verificar se já existe dívida ativa nesta empresa
    divida_existente = cliente.dividas.filter(empresa=empresa, status='ATIVA').first()
    
    if request.method == 'POST':
        form = ClienteDividaForm(request.POST or None, empresa=empresa, user=request.user)

        
        if form.is_valid():
            try:
                divida = form.save(commit=False)
                divida.cliente = cliente
                divida.empresa = empresa
                divida.cadastrado_por = request.user
                divida.valor_atual = divida.valor_original
                divida.save()
                
                # Criar histórico
                HistoricoDivida.objects.create(
                    divida=divida,
                    tipo_acao='CADASTRO',
                    valor_atualizado=divida.valor_original,
                    descricao=f'Nova dívida adicionada na empresa {empresa.nome}',
                    usuario=request.user
                )
                
                messages.success(request, f'Nova dívida adicionada ao cliente {cliente.nome_completo}.')
                return redirect('dividas:detalhes_cliente', cliente_id=cliente.id)
            except Exception as e:
                messages.error(request, f'Erro ao adicionar dívida: {str(e)}')
    else:
        form = DividaForm(empresa=empresa)
    
    context = {
        'cliente': cliente,
        'form': form,
        'empresa': empresa,
        'divida_existente': divida_existente,
    }
    return render(request, 'dividas/adicionar_divida.html', context)

# =============== CONSULTA/LISTAGEM ===============
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Max, Case, When, IntegerField
from django.shortcuts import render

from .models import Cliente, Divida, UsuarioEmpresa


# dividas/views.py
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from .models import Cliente, Divida, UsuarioEmpresa, Empresa
from .utils import buscar_por_cpf_flexivel  # Importe a função
from django.db.models import (
    Q, Count, Sum, Max, Case, When, IntegerField,
    Exists, OuterRef
)

@login_required
def lista_clientes(request):
    # ----------------------------------
    # Identificação do usuário
    # ----------------------------------
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
        is_empresa_user = True
    except UsuarioEmpresa.DoesNotExist:
        empresa = None
        is_empresa_user = False

    search_query = request.GET.get('search', '').strip()
    empresa_filter = request.GET.get('empresa', '').strip()
    empresa_filter_int = int(empresa_filter) if empresa_filter.isdigit() else None
    
    # Obter todas as empresas para o dropdown
    empresas = Empresa.objects.all()
    clientes = Cliente.objects.none()

    # ----------------------------------
    # USUÁRIO DA EMPRESA
    # ----------------------------------
    if is_empresa_user:

        # 🔹 SEM CPF → lista clientes com dívidas NÃO PAGAS na própria empresa
        if not search_query:
            clientes = Cliente.objects.filter(
                dividas__empresa=empresa,
                dividas__status__in=['ATIVA', 'NEGOCIACAO']
            ).distinct()

        # 🔹 COM BUSCA → usa a função flexível
        else:
            # Usa a função de busca flexível por CPF
            clientes = buscar_por_cpf_flexivel(search_query)
            
            # Aplica filtro de status conforme regra de negócio
            tem_divida_nao_paga = Exists(
                Divida.objects.filter(
                    cliente=OuterRef('pk'),
                    status__in=['ATIVA', 'NEGOCIACAO']
                )
            )
            
            tem_divida_paga_empresa = Exists(
                Divida.objects.filter(
                    cliente=OuterRef('pk'),
                    empresa=empresa,
                    status__in=['PAGA', 'CANCELADA']
                )
            )
            
            clientes = clientes.annotate(
                tem_divida_nao_paga=tem_divida_nao_paga,
                tem_divida_paga_empresa=tem_divida_paga_empresa
            ).filter(
                Q(tem_divida_nao_paga=True) | Q(tem_divida_paga_empresa=True)
            )

    # ----------------------------------
    # USUÁRIO EXTERNO (SPC)
    # ----------------------------------
    else:
        if search_query:
            # Para usuário SPC
            clientes = buscar_por_cpf_flexivel(search_query).annotate(
                possui_divida_nao_paga=Exists(
                    Divida.objects.filter(
                        cliente=OuterRef('pk'),
                        status__in=['ATIVA', 'NEGOCIACAO']
                    )
                )
            ).filter(
                possui_divida_nao_paga=True
            )
        
        # Aplicar filtro de empresa se selecionado
        if empresa_filter_int:
            clientes = clientes.filter(dividas__empresa_id=empresa_filter_int)

    # ----------------------------------
    # AGREGAÇÕES
    # ----------------------------------
    clientes = clientes.annotate(
        total_dividas=Count('dividas', distinct=True),
        qtd_dividas_ativas=Count(
            Case(
                When(dividas__status__in=['ATIVA', 'NEGOCIACAO'], then=1),
                output_field=IntegerField()
            )
        ),
        valor_total=Sum(
            Case(
                When(dividas__status__in=['ATIVA', 'NEGOCIACAO'], then='dividas__valor_atual')
            )
        ),
        ultima_divida_data=Max('dividas__data_vencimento')
    ).order_by('-ultima_divida_data').distinct()

    # ----------------------------------
    # PAGINAÇÃO
    # ----------------------------------
    paginator = Paginator(clientes, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'dividas/lista_clientes.html', {
        'clientes': page_obj,
        'page_obj': page_obj,
        'empresa': empresa,
        'empresas': empresas,
        'empresa_filter': empresa_filter,
        'empresa_filter_int': empresa_filter_int,
        'is_empresa_user': is_empresa_user,
        'search_query': search_query,
    })

# =============== DETALHES DO CLIENTE ===============
@login_required
def detalhes_cliente(request, cliente_id):
    from django.db.models import Exists, OuterRef, Sum

    cliente = get_object_or_404(Cliente, id=cliente_id)

    # =====================================
    # Identificar usuário
    # =====================================
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
        is_empresa_user = True
    except UsuarioEmpresa.DoesNotExist:
        empresa = None
        is_empresa_user = False

    # =====================================
    # USUÁRIO DA EMPRESA
    # =====================================
    if is_empresa_user:
        todas_dividas = cliente.dividas.filter(
            empresa=empresa
        ).select_related('empresa').order_by('-data_cadastro')

    # =====================================
    # USUÁRIO EXTERNO (SPC)
    # =====================================
    else:
        # 🔒 só permite acesso se houver dívida ATIVA
        possui_divida_ativa = Divida.objects.filter(
            cliente=cliente,
            status='ATIVA'
        ).exists()

        if not possui_divida_ativa:
            return HttpResponseForbidden(
                "Este cliente não possui dívidas ativas."
            )

        # 🔍 externo só vê dívidas ATIVAS
        todas_dividas = cliente.dividas.filter(
            status='ATIVA'
        ).select_related('empresa').order_by('-data_cadastro')

    # =====================================
    # Agrupar por empresa
    # =====================================
    dividas_por_empresa = {}
    for divida in todas_dividas:
        dividas_por_empresa.setdefault(divida.empresa, []).append(divida)

    empresas_dividas = []
    for empresa_obj, dividas_list in dividas_por_empresa.items():
        total = sum((d.valor_atual or 0) for d in dividas_list)
        empresas_dividas.append({
            'empresa': empresa_obj,
            'dividas': dividas_list,
            'total': total,
        })

    # =====================================
    # Estatísticas
    # =====================================
    estatisticas = {
        'total_empresas': len(dividas_por_empresa),
        'total_dividas': todas_dividas.count(),
        'dividas_ativas': todas_dividas.filter(status='ATIVA').count(),
        'valor_total_ativas': todas_dividas.aggregate(
            total=Sum('valor_atual')
        )['total'] or 0,
    }

    # =====================================
    # Permissões
    # =====================================
    pode_adicionar_divida = (
        is_empresa_user and
        not cliente.tem_divida_na_empresa(empresa)
    )

    context = {
        'cliente': cliente,
        'empresas_dividas': empresas_dividas,
        'todas_dividas': todas_dividas,
        'empresa': empresa,
        'is_empresa_user': is_empresa_user,
        'estatisticas': estatisticas,
        'pode_adicionar_divida': pode_adicionar_divida,
    }

    return render(request, 'dividas/detalhes_cliente.html', context)


# =============== BAIXA DE DÍVIDA ===============
@login_required
def baixar_divida(request, divida_id):
    """Registrar pagamento/baixa de uma dívida"""
    divida = get_object_or_404(Divida, id=divida_id)

    # Verificar permissões
    try:
        UsuarioEmpresa.objects.get(usuario=request.user, empresa=divida.empresa)
    except UsuarioEmpresa.DoesNotExist:
        return HttpResponseForbidden("Você não tem permissão para baixar esta dívida.")

    if request.method == 'POST':
        valor_pago_raw = request.POST.get('valor_pago', '').strip()
        observacoes = request.POST.get('observacoes', '')

        try:
            # Converter para Decimal corretamente
            valor_pago = Decimal(valor_pago_raw.replace(',', '.'))

            if valor_pago <= Decimal('0.00'):
                messages.error(request, 'O valor pago deve ser maior que zero.')
                return redirect(request.path)

            if valor_pago > divida.valor_atual:
                messages.error(
                    request,
                    'O valor pago não pode ser maior que o valor atual da dívida.'
                )
                return redirect(request.path)

            # Calcular novo valor
            novo_valor = divida.valor_atual - valor_pago

            # Registrar histórico
            HistoricoDivida.objects.create(
                divida=divida,
                tipo_acao='PAGAMENTO_TOTAL' if novo_valor == Decimal('0.00') else 'PAGAMENTO_PARCIAL',
                valor_anterior=divida.valor_atual,
                valor_atualizado=novo_valor,
                descricao=f'Pagamento registrado. {observacoes}',
                usuario=request.user
            )

            # Atualizar dívida
            divida.valor_atual = novo_valor

            if novo_valor == Decimal('0.00'):
                divida.status = 'PAGA'
                divida.data_pagamento = timezone.now().date()
                divida.baixado_por = request.user

            divida.save()

            messages.success(request, 'Pagamento registrado com sucesso!')
            return redirect('dividas:detalhes_cliente', cliente_id=divida.cliente.id)

        except (InvalidOperation, ValueError):
            messages.error(request, 'Valor inválido. Use apenas números.')
            return redirect(request.path)

    context = {
        'divida': divida,
        'empresa': divida.empresa,
    }
    return render(request, 'dividas/baixar_divida.html', context)

# =============== APIS ===============
# dividas/views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .utils import buscar_por_cpf_flexivel  # Importe a função
from django.db.models import Case, When, Count, Sum

@login_required
def api_buscar_cliente_cpf(request):
    """
    API de busca estilo SPC usando a função flexível de CPF
    """
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': [], 'error': 'Digite um CPF para busca'})
    
    try:
        # ===============================
        # USUÁRIO DE EMPRESA
        # ===============================
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
        
        # Usa a função de busca flexível
        clientes = buscar_por_cpf_flexivel(query)
        
        # Aplica filtro de status conforme regra de negócio
        tem_divida_nao_paga = Exists(
            Divida.objects.filter(
                cliente=OuterRef('pk'),
                status__in=['ATIVA', 'NEGOCIACAO']
            )
        )
        
        tem_divida_paga_empresa = Exists(
            Divida.objects.filter(
                cliente=OuterRef('pk'),
                empresa=empresa,
                status__in=['PAGA', 'CANCELADA']
            )
        )
        
        clientes = clientes.annotate(
            tem_divida_nao_paga=tem_divida_nao_paga,
            tem_divida_paga_empresa=tem_divida_paga_empresa
        ).filter(
            Q(tem_divida_nao_paga=True) | Q(tem_divida_paga_empresa=True)
        )

    except UsuarioEmpresa.DoesNotExist:
        # ===============================
        # USUÁRIO EXTERNO (SPC)
        # ===============================
        clientes = buscar_por_cpf_flexivel(query).annotate(
            possui_divida_nao_paga=Exists(
                Divida.objects.filter(
                    cliente=OuterRef('pk'),
                    status__in=['ATIVA', 'NEGOCIACAO']
                )
            )
        ).filter(
            possui_divida_nao_paga=True
        )

    # Limita a 10 resultados para performance
    clientes = clientes[:10]

    results = []
    for cliente in clientes:
        # Agrega informações das dívidas
        dividas_info = cliente.dividas.aggregate(
            total=Count('id'),
            ativas=Count(Case(When(status__in=['ATIVA', 'NEGOCIACAO'], then=1))),
            valor_total=Sum(
                Case(
                    When(status__in=['ATIVA', 'NEGOCIACAO'], then='valor_atual')
                )
            ),
            empresas_count=Count('empresa', distinct=True)
        )
        
        # Formata o CPF para exibição
        cpf_formatado = cliente.cpf
        if len(cliente.cpf) == 11:
            cpf_formatado = f"{cliente.cpf[:3]}.{cliente.cpf[3:6]}.{cliente.cpf[6:9]}-{cliente.cpf[9:]}"
        
        results.append({
            'id': str(cliente.id),
            'nome': cliente.nome_completo,
            'cpf': cpf_formatado,
            'cpf_raw': cliente.cpf,
            'total_dividas': dividas_info['total'] or 0,
            'dividas_ativas': dividas_info['ativas'] or 0,
            'valor_total': float(dividas_info['valor_total'] or 0),
            'empresas_count': dividas_info['empresas_count'] or 0,
            'email': cliente.email or '',
            'telefone': cliente.telefone or '',
        })

    return JsonResponse({
        'results': results,
        'count': len(results),
        'query': query
    })


@login_required
def api_dividas_cliente(request, cliente_id):
    """API para obter dívidas de um cliente específico"""
    cliente = get_object_or_404(Cliente, id=cliente_id)
    
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
        is_empresa_user = True  # Adicione esta linha
    except UsuarioEmpresa.DoesNotExist:
        return HttpResponseForbidden("Apenas usuários de empresa podem acessar estatísticas.")
        # Filtrar por empresa do usuário
        dividas = cliente.dividas.filter(empresa=empresa)
    except UsuarioEmpresa.DoesNotExist:
        # Consultor: vê todas as dívidas
        dividas = cliente.dividas.all()
    
    dividas_data = []
    for divida in dividas:
        dividas_data.append({
            'id': str(divida.id),
            'empresa': divida.empresa.nome,
            'valor_original': float(divida.valor_original),
            'valor_atual': float(divida.valor_atual),
            'vencimento': divida.data_vencimento.strftime('%d/%m/%Y'),
            'status': divida.get_status_display(),
            'status_codigo': divida.status,
            'observacoes': divida.observacoes or '',
            'cadastrada_em': divida.data_cadastro.strftime('%d/%m/%Y'),
            'pode_baixar': divida.status == 'ATIVA' and hasattr(request.user, 'usuario_empresa') and 
                          request.user.usuario_empresa.empresa == divida.empresa,
        })
    
    return JsonResponse({
        'cliente': {
            'id': str(cliente.id),
            'nome': cliente.nome_completo,
            'cpf': cliente.cpf,
        },
        'dividas': dividas_data,
        'total_dividas': len(dividas_data),
        'valor_total': sum(d['valor_atual'] for d in dividas_data),
    })

# =============== ESTATÍSTICAS ===============
@login_required
def dashboard_estatisticas(request):
    """Dashboard com estatísticas detalhadas"""
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
        is_empresa_user = True  # ADICIONE ESTA LINHA
    except UsuarioEmpresa.DoesNotExist:
        # Usuários sem empresa não podem acessar estatísticas
        return HttpResponseForbidden("Apenas usuários de empresa podem acessar estatísticas.")
    
    hoje = timezone.now().date()
    
    # ======================================================
    # Dívidas por status COM DISPLAY NAME
    # ======================================================
    dividas_por_status_raw = Divida.objects.filter(empresa=empresa).values('status').annotate(
        total=Count('id'),
        valor_total=Sum('valor_atual')
    ).order_by('status')
    
    # Mapeamento dos status para display
    STATUS_DISPLAY = {
        'ATIVA': 'Dívida Ativa',
        'NEGOCIACAO': 'Em Negociação',
        'PAGA': 'Dívida Paga',
        'CANCELADA': 'Cancelada'
    }
    
    # Adiciona display name a cada item
    dividas_por_status = []
    for item in dividas_por_status_raw:
        item_dict = dict(item)  # Converte para dicionário mutável
        item_dict['status_display'] = STATUS_DISPLAY.get(item['status'], item['status'])
        dividas_por_status.append(item_dict)
    
    # ======================================================
    # Dívidas vencidas (ATIVA ou NEGOCIACAO)
    # ======================================================
    dividas_vencidas = Divida.objects.filter(
        empresa=empresa,
        status__in=['ATIVA', 'NEGOCIACAO'],
        data_vencimento__lt=hoje
    ).count()
    
    # ======================================================
    # Dívidas a vencer (próximos 7 dias)
    # ======================================================
    semana_seguinte = hoje + timedelta(days=7)
    dividas_a_vencer = Divida.objects.filter(
        empresa=empresa,
        status__in=['ATIVA', 'NEGOCIACAO'],
        data_vencimento__range=[hoje, semana_seguinte]
    ).count()
    
    # ======================================================
    # Top 5 clientes com maiores dívidas (ativas)
    # ======================================================
    top_clientes = Cliente.objects.filter(
        dividas__empresa=empresa,
        dividas__status__in=['ATIVA', 'NEGOCIACAO']
    ).annotate(
        total_divida=Sum('dividas__valor_atual'),
        num_dividas=Count('dividas')
    ).order_by('-total_divida')[:10]
    
    # ======================================================
    # Evolução mensal de dívidas cadastradas
    # ======================================================
    from django.db.models.functions import TruncMonth
    
    evolucao_mensal_raw = Divida.objects.filter(
        empresa=empresa,
        data_cadastro__gte=hoje - timedelta(days=365)
    ).annotate(
        mes=TruncMonth('data_cadastro')
    ).values('mes').annotate(
        total=Count('id'),
        valor=Sum('valor_original')
    ).order_by('mes')
    
    # Converte para lista
    evolucao_mensal = []
    for item in evolucao_mensal_raw:
        item_dict = dict(item)
        evolucao_mensal.append(item_dict)
    
    # ======================================================
    # Valor total de dívidas ativas (inclui negociação)
    # ======================================================
    valor_total_dividas = Divida.objects.filter(
        empresa=empresa,
        status__in=['ATIVA', 'NEGOCIACAO']
    ).aggregate(total=Sum('valor_atual'))['total'] or 0
    
    # ======================================================
    # Taxa de recuperação (dívidas pagas / total)
    # ======================================================
    total_dividas = Divida.objects.filter(empresa=empresa).count()
    total_pagas = Divida.objects.filter(empresa=empresa, status='PAGA').count()
    taxa_recuperacao = (total_pagas / total_dividas * 100) if total_dividas > 0 else 0
    
    context = {
        'empresa': empresa,
        'is_empresa_user': is_empresa_user,  # AGORA ESTÁ DEFINIDA
        'dividas_por_status': dividas_por_status,
        'dividas_vencidas': dividas_vencidas,
        'dividas_a_vencer': dividas_a_vencer,
        'top_clientes': top_clientes,
        'evolucao_mensal': evolucao_mensal,
        'valor_total_dividas': valor_total_dividas,
        'taxa_recuperacao': round(taxa_recuperacao, 1),
        'hoje': hoje.strftime('%d/%m/%Y'),
        'STATUS_DISPLAY': STATUS_DISPLAY,
    }
    
    # DEBUG
    print(f"DEBUG dashboard_estatisticas:")
    print(f"  is_empresa_user: {is_empresa_user}")
    print(f"  empresa: {empresa.nome if empresa else 'None'}")
    print(f"  total variáveis: {len(context)}")
    
    return render(request, 'dividas/dashboard_estatisticas.html', context)

# =============== FUNÇÕES AUXILIARES ===============
@login_required
def exportar_clientes(request):
    """Exportar lista de clientes para CSV"""
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
        is_empresa_user = True
    except UsuarioEmpresa.DoesNotExist:
        empresa = None
        is_empresa_user = False
    
    # Obter clientes baseado no tipo de usuário
    if is_empresa_user:
        clientes = Cliente.objects.filter(dividas__empresa=empresa).distinct()
    else:
        clientes = Cliente.objects.all()
    
    # Filtrar se necessário
    search_query = request.GET.get('search', '')
    if search_query:
        clientes = clientes.filter(
            Q(nome_completo__icontains=search_query) |
            Q(cpf__icontains=search_query)
        )
    
    # Preparar dados para CSV
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="clientes.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Nome', 'CPF', 'Email', 'Telefone', 'Total Dívidas', 'Valor Total'])
    
    for cliente in clientes:
        total_dividas = cliente.dividas.count()
        valor_total = cliente.dividas.aggregate(total=Sum('valor_atual'))['total'] or 0
        writer.writerow([
            cliente.nome_completo,
            cliente.cpf,
            cliente.email or '',
            cliente.telefone or '',
            total_dividas,
            f'R$ {valor_total:.2f}'
        ])
    
    return response

@login_required
def relatorio_dividas_vencidas(request):
    """Relatório de dívidas vencidas"""
    try:
        usuario_empresa = UsuarioEmpresa.objects.get(usuario=request.user)
        empresa = usuario_empresa.empresa
    except UsuarioEmpresa.DoesNotExist:
        return HttpResponseForbidden("Apenas usuários de empresa podem acessar relatórios.")
    
    hoje = timezone.now().date()
    
    # Dívidas vencidas
    dividas_vencidas = Divida.objects.filter(
        empresa=empresa,
        status='ATIVA',
        data_vencimento__lt=hoje
    ).select_related('cliente').order_by('data_vencimento')
    
    context = {
        'empresa': empresa,
        'dividas_vencidas': dividas_vencidas,
        'total_vencidas': dividas_vencidas.count(),
        'valor_total': dividas_vencidas.aggregate(total=Sum('valor_atual'))['total'] or 0,
        'hoje': hoje.strftime('%d/%m/%Y'),
    }
    return render(request, 'dividas/relatorio_dividas_vencidas.html', context)