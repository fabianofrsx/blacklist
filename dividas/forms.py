# forms.py COMPLETO
from django import forms
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
import re
from datetime import date
from .models import Cliente, Divida, Empresa

class ClienteForm(forms.ModelForm):
    cpf = forms.CharField(
        max_length=14,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000.000.000-00',
            'data-mask': '000.000.000-00'
        })
    )
    
    telefone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(00) 00000-0000',
            'data-mask': '(00) 00000-0000'
        })
    )
    
    class Meta:
        model = Cliente
        fields = ['nome_completo', 'cpf', 'data_nascimento', 'email', 'telefone', 'endereco']
        widgets = {
            'nome_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo do cliente'
            }),
            'data_nascimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemplo.com'
            }),
            'endereco': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Endereço completo'
            }),
        }
    
    def clean_cpf(self):
        cpf = self.cleaned_data['cpf']
        cpf_numeros = re.sub(r'\D', '', cpf)
        
        if len(cpf_numeros) != 11:
            raise ValidationError('CPF deve conter 11 dígitos.')
        
        # Verificar se CPF já existe (apenas se não for uma atualização)
        if not self.instance.pk:  # Se for um novo cliente
            if Cliente.objects.filter(cpf__contains=cpf_numeros).exists():
                # Não lançar erro - vamos permitir adicionar dívida ao cliente existente
                pass
        
        # Formatar CPF
        return f'{cpf_numeros[:3]}.{cpf_numeros[3:6]}.{cpf_numeros[6:9]}-{cpf_numeros[9:]}'

class DividaForm(forms.ModelForm):
    valor_original = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': '0,00'
        })
    )
    
    class Meta:
        model = Divida
        fields = ['valor_original', 'data_vencimento', 'observacoes']
        widgets = {
            'data_vencimento': forms.DateInput(attrs={
              'class': 'form-control',
              'type': 'date'
            }),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observações sobre a dívida...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if self.empresa:
            # Remover validação única por empresa se necessário
            pass
    
        
    def clean_valor_original(self):
        valor = self.cleaned_data.get('valor_original')
        
        if valor and valor <= 0:
            raise ValidationError('O valor da dívida deve ser maior que zero.')
        
        return valor

class ClienteDividaForm(forms.Form):
    """Form unificado para cliente e dívida (usado em cadastro rápido)"""
    # Campos do cliente
    nome_completo = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome completo do cliente'
        })
    )
    
    cpf = forms.CharField(
        max_length=14,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000.000.000-00',
            'data-mask': '000.000.000-00'
        })
    )
    
    data_nascimento = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'email@exemplo.com'
        })
    )
    
    telefone = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '(00) 00000-0000',
            'data-mask': '(00) 00000-0000'
        })
    )
    
    endereco = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Endereço completo'
        })
    )
    
    # Campos da dívida
    valor_original = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': '0,00'
        })
    )
    
    data_vencimento = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': str(date.today())
        })
    )
    
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observações sobre a dívida...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.empresa = kwargs.pop('empresa', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_cpf(self):
        cpf = self.cleaned_data['cpf']
        cpf_numeros = re.sub(r'\D', '', cpf)
        
        if len(cpf_numeros) != 11:
            raise ValidationError('CPF deve conter 11 dígitos.')
        
        # Formatar CPF
        return f'{cpf_numeros[:3]}.{cpf_numeros[3:6]}.{cpf_numeros[6:9]}-{cpf_numeros[9:]}'
    
    
class DividaSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nome ou CPF...'
        })
    )
    
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.filter(ativo=True),
        required=False,
        empty_label="Todas as empresas",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Todos os status')] + Divida.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    data_vencimento_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    data_vencimento_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_vencimento_inicio')
        data_fim = cleaned_data.get('data_vencimento_fim')
        
        if data_inicio and data_fim and data_inicio > data_fim:
            raise ValidationError({
                'data_vencimento_inicio': 'Data inicial não pode ser maior que data final.'
            })
        
        return cleaned_data

class ClienteSearchForm(forms.Form):
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nome, CPF, email ou telefone...'
        })
    )
    
    tem_divida = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('com_divida', 'Com dívida ativa'),
            ('sem_divida', 'Sem dívida ativa')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.filter(ativo=True),
        required=False,
        empty_label="Todas as empresas",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class BaixarDividaForm(forms.Form):
    valor_pago = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': '0,00'
        })
    )
    
    data_pagamento = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'value': str(date.today())
        })
    )
    
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observações sobre o pagamento...'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.divida = kwargs.pop('divida', None)
        super().__init__(*args, **kwargs)
        
        if self.divida:
            self.fields['valor_pago'].initial = self.divida.valor_atual
            self.fields['valor_pago'].widget.attrs['max'] = float(self.divida.valor_atual)
            
            # Sugestão de valores para pagamento
            self.fields['valor_pago'].widget.attrs['list'] = 'sugestoes_valor'
    
    def clean_valor_pago(self):
        valor_pago = self.cleaned_data['valor_pago']
        
        if self.divida:
            if valor_pago > self.divida.valor_atual:
                raise ValidationError(
                    f'O valor pago (R$ {valor_pago:.2f}) não pode ser maior que '
                    f'o valor da dívida (R$ {self.divida.valor_atual:.2f}).'
                )
            
            if valor_pago <= 0:
                raise ValidationError('O valor pago deve ser maior que zero.')
        
        return valor_pago
    
    def clean_data_pagamento(self):
        data_pagamento = self.cleaned_data['data_pagamento']
        
        if data_pagamento and data_pagamento > date.today():
            raise ValidationError('A data de pagamento não pode ser no futuro.')
        
        return data_pagamento

class EditarDividaForm(forms.ModelForm):
    """Form para editar uma dívida existente"""
    class Meta:
        model = Divida
        fields = ['valor_atual', 'data_vencimento', 'status', 'observacoes']
        widgets = {
            'valor_atual': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'data_vencimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Desabilitar edição de alguns campos se a dívida estiver paga
        if self.instance and self.instance.status == 'PAGA':
            self.fields['valor_atual'].disabled = True
            self.fields['status'].disabled = True
    
    def clean_valor_atual(self):
        valor_atual = self.cleaned_data.get('valor_atual')
        
        if valor_atual and valor_atual < 0:
            raise ValidationError('O valor atual não pode ser negativo.')
        
        if self.instance and valor_atual > self.instance.valor_original:
            raise ValidationError(
                f'O valor atual não pode ser maior que o valor original '
                f'(R$ {self.instance.valor_original:.2f}).'
            )
        
        return valor_atual

class EditarClienteForm(forms.ModelForm):
    """Form para editar informações do cliente"""
    cpf = forms.CharField(
        max_length=14,
        disabled=True,  # CPF não pode ser alterado
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000.000.000-00'
        })
    )
    
    class Meta:
        model = Cliente
        fields = ['nome_completo', 'cpf', 'data_nascimento', 'email', 'telefone', 'endereco']
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'data_nascimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

class RelatorioForm(forms.Form):
    """Form para gerar relatórios"""
    TIPO_RELATORIO_CHOICES = [
        ('dividas_vencidas', 'Dívidas Vencidas'),
        ('dividas_a_vencer', 'Dívidas a Vencer (7 dias)'),
        ('dividas_ativas', 'Todas as Dívidas Ativas'),
        ('dividas_pagas', 'Dívidas Pagas (Período)'),
        ('clientes_ativos', 'Clientes com Dívidas Ativas'),
    ]
    
    tipo_relatorio = forms.ChoiceField(
        choices=TIPO_RELATORIO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.filter(ativo=True),
        required=False,
        empty_label="Todas as empresas",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    formato = forms.ChoiceField(
        choices=[
            ('html', 'HTML (Tela)'),
            ('pdf', 'PDF'),
            ('csv', 'CSV'),
            ('xlsx', 'Excel'),
        ],
        initial='html',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        tipo_relatorio = cleaned_data.get('tipo_relatorio')
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        
        # Validações específicas por tipo de relatório
        if tipo_relatorio in ['dividas_pagas', 'dividas_ativas']:
            if not data_inicio or not data_fim:
                raise ValidationError(
                    'Para este relatório, é necessário informar o período (data início e data fim).'
                )
            
            if data_inicio and data_fim and data_inicio > data_fim:
                raise ValidationError('Data inicial não pode ser maior que data final.')
        
        return cleaned_data

class ImportarClientesForm(forms.Form):
    """Form para importar clientes de arquivo CSV"""
    arquivo = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.filter(ativo=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sobrescrever = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Sobrescrever clientes existentes com mesmo CPF'
    )
    
    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        
        if arquivo:
            # Verificar extensão
            extensao = arquivo.name.split('.')[-1].lower()
            if extensao not in ['csv', 'xlsx', 'xls']:
                raise ValidationError('Formato de arquivo não suportado. Use CSV, XLSX ou XLS.')
            
            # Verificar tamanho (máximo 5MB)
            if arquivo.size > 5 * 1024 * 1024:
                raise ValidationError('Arquivo muito grande. Tamanho máximo: 5MB.')
        
        return arquivo