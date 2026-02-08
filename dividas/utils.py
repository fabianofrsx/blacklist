# dividas/utils.py
import re
from django.db.models import Q
from .models import Cliente

def buscar_por_cpf_flexivel(cpf_input):
    """
    Busca cliente por CPF de forma flexível:
    - Aceita CPF com máscara: 123.456.789-10
    - Aceita CPF sem máscara: 12345678910
    - Aceita busca parcial: 123, 456, 789
    
    Retorna um QuerySet de Cliente
    """
    if not cpf_input:
        return Cliente.objects.none()
    
    # Normaliza removendo caracteres não numéricos
    cpf_clean = re.sub(r'\D', '', cpf_input)
    
    # Se tem 11 dígitos, é um CPF completo
    if len(cpf_clean) == 11:
        # Busca pelo CPF normalizado (sem máscara)
        # E também pelo CPF formatado (com máscara)
        cpf_formatado = f"{cpf_clean[:3]}.{cpf_clean[3:6]}.{cpf_clean[6:9]}-{cpf_clean[9:]}"
        
        return Cliente.objects.filter(
            Q(cpf=cpf_clean) | 
            Q(cpf=cpf_formatado)
        )
    
    # Se tem entre 3 e 10 dígitos, é uma busca parcial
    elif len(cpf_clean) >= 3:
        # Busca pelo CPF parcial (sem máscara)
        # Também tenta buscar com a máscara original
        return Cliente.objects.filter(
            Q(cpf__icontains=cpf_clean) |
            Q(cpf__icontains=cpf_input)
        )
    
    return Cliente.objects.none()