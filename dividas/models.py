from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
from decimal import Decimal

class Empresa(models.Model):
    """Model para empresas que usam o sistema"""
    nome = models.CharField(max_length=100, unique=True)
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True)
    telefone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nome
    
    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nome']
    
    @property
    def total_clientes(self):
        """Total de clientes únicos com dívidas nesta empresa"""
        return self.dividas.values('cliente').distinct().count()
    
    @property
    def total_dividas_ativas(self):
        """Valor total de dívidas ativas"""
        return self.dividas.filter(status='ATIVA').aggregate(
            total=models.Sum('valor_atual')
        )['total'] or 0
    
    @property
    def total_dividas(self):
        """Total de dívidas (todas)"""
        return self.dividas.count()

class UsuarioEmpresa(models.Model):
    """Relacionamento usuário-empresa para controle de acesso"""
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='usuario_empresa')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios')
    is_admin_empresa = models.BooleanField(default=False)
    data_associacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.usuario.username} - {self.empresa.nome}"
    
    class Meta:
        verbose_name = "Usuário da Empresa"
        verbose_name_plural = "Usuários das Empresas"
        unique_together = ['usuario', 'empresa']

class Cliente(models.Model):
    """Model para clientes que podem ter dívidas em múltiplas empresas"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome_completo = models.CharField(max_length=200)
    cpf = models.CharField(max_length=14, unique=True)
    data_nascimento = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    telefone = models.CharField(max_length=15, null=True, blank=True)
    endereco = models.TextField(null=True, blank=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.nome_completo} ({self.cpf})"
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nome_completo']
        indexes = [
            models.Index(fields=['cpf']),
            models.Index(fields=['nome_completo']),
        ]
    
    @property
    def total_dividas_ativas(self):
        """Soma de todas as dívidas ativas em todas as empresas"""
        return self.dividas.filter(status='ATIVA').aggregate(
            total=models.Sum('valor_atual')
        )['total'] or 0
    
    @property
    def numero_empresas_com_dividas(self):
        """Quantidade de empresas onde o cliente tem dívidas"""
        return self.dividas.values('empresa').distinct().count()
    
    @property
    def possui_dividas_ativas(self):
        """Verifica se tem pelo menos uma dívida ativa"""
        return self.dividas.filter(status='ATIVA').exists()
    
    @property
    def dividas_ativas(self):
        """Retorna todas as dívidas ativas"""
        return self.dividas.filter(status='ATIVA')
    
    def empresas_com_dividas(self):
        """Retorna lista de empresas onde o cliente tem dívidas"""
        return Empresa.objects.filter(
            dividas__cliente=self
        ).distinct()
    
    def tem_divida_na_empresa(self, empresa):
        """Verifica se tem dívida ativa em uma empresa específica"""
        return self.dividas.filter(empresa=empresa, status='ATIVA').exists()

class Divida(models.Model):
    """Model para dívidas dos clientes"""

    STATUS_ATIVA = 'ATIVA'
    STATUS_NEGOCIACAO = 'NEGOCIACAO'
    STATUS_PAGA = 'PAGA'
    STATUS_CANCELADA = 'CANCELADA'

    STATUS_CHOICES = [
        (STATUS_ATIVA, 'Dívida Ativa'),
        (STATUS_NEGOCIACAO, 'Em Negociação'),
        (STATUS_PAGA, 'Dívida Paga'),
        (STATUS_CANCELADA, 'Cancelada'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name='dividas'
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='dividas'
    )

    valor_original = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Saldo da dívida (vai diminuindo conforme pagamentos)
    valor_atual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    data_vencimento = models.DateField()
    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_pagamento = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ATIVA
    )

    observacoes = models.TextField(null=True, blank=True)

    cadastrado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='dividas_cadastradas'
    )

    baixado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dividas_baixadas'
    )

    # ======================================================
    # 🔎 PROPRIEDADES (USADAS NAS TELAS)
    # ======================================================

    @property
    def valor_pago(self) -> Decimal:
        """Valor total já pago"""
        return self.valor_original - self.valor_atual

    @property
    def quitada(self) -> bool:
        return self.status == self.STATUS_PAGA

    # ======================================================
    # 🧠 REGRAS DE NEGÓCIO
    # ======================================================

    def clean(self):
        """Validações de integridade"""

        if self.valor_original is None:
            raise ValidationError({
                'valor_original': 'O valor original é obrigatório.'
            })

        if self.valor_atual is None:
            self.valor_atual = self.valor_original

        if self.valor_atual > self.valor_original:
            raise ValidationError({
                'valor_atual': 'O valor atual não pode ser maior que o valor original.'
            })

        if self.valor_atual < 0:
            raise ValidationError({
                'valor_atual': 'O valor atual não pode ser negativo.'
            })

    def save(self, *args, **kwargs):
        """Blindagem total antes de salvar"""

        # Garantia absoluta de Decimal
        self.valor_original = Decimal(self.valor_original)
        self.valor_atual = Decimal(self.valor_atual)

        # Nunca permitir valor negativo
        if self.valor_atual < 0:
            self.valor_atual = Decimal('0.00')

        # Ajuste automático de status
        if self.valor_atual == Decimal('0.00'):
            self.status = self.STATUS_PAGA
            if not self.data_pagamento:
                self.data_pagamento = timezone.now().date()
        else:
            if self.status == self.STATUS_PAGA:
                self.status = self.STATUS_ATIVA
                self.data_pagamento = None

        self.full_clean()
        super().save(*args, **kwargs)

    # ======================================================
    # 🧾 REPRESENTAÇÃO
    # ======================================================

    def __str__(self):
        valor_exibicao = (
            self.valor_original if self.status == self.STATUS_PAGA else self.valor_atual
        )
        return f"{self.empresa.nome} - R$ {valor_exibicao:.2f} ({self.get_status_display()})"

    # ======================================================
    # ⚙️ META
    # ======================================================

    class Meta:
        verbose_name = "Dívida"
        verbose_name_plural = "Dívidas"
        ordering = ['-data_cadastro']
        indexes = [
            models.Index(fields=['cliente', 'empresa']),
            models.Index(fields=['status', 'data_vencimento']),
            models.Index(fields=['data_cadastro']),
        ]

class HistoricoDivida(models.Model):
    """Histórico de alterações nas dívidas"""
    TIPO_CHOICES = [
        ('CADASTRO', 'Cadastro da Dívida'),
        ('ATUALIZACAO', 'Atualização de Dados'),
        ('PAGAMENTO_PARCIAL', 'Pagamento Parcial'),
        ('PAGAMENTO_TOTAL', 'Pagamento Total'),
        ('NEGOCIACAO', 'Início de Negociação'),
        ('CANCELAMENTO', 'Cancelamento'),
        ('REATIVACAO', 'Reativação'),
        ('STATUS_ALTERADO', 'Status Alterado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    divida = models.ForeignKey(Divida, on_delete=models.CASCADE, related_name='historico')
    tipo_acao = models.CharField(max_length=20, choices=TIPO_CHOICES)
    valor_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_atualizado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    descricao = models.TextField()
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_acao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.tipo_acao} - {self.divida.cliente.nome_completo}"
    
    class Meta:
        verbose_name = "Histórico da Dívida"
        verbose_name_plural = "Históricos das Dívidas"
        ordering = ['-data_acao']