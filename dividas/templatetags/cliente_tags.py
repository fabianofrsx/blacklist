from django import template

register = template.Library()

@register.simple_tag
def empresa_divida_principal(cliente, usuario_empresa=None):
    """
    Retorna a empresa da dívida mais relevante para mostrar.
    Prioriza: dívida ativa > empresa diferente do usuário > mais recente
    """
    if not usuario_empresa:
        # Para usuário SPC, pega a primeira empresa com dívida
        divida = cliente.dividas.first()
        return divida.empresa if divida else None
    
    # Para usuário da empresa
    dividas_cliente = cliente.dividas.all()
    
    # 1. Tenta encontrar dívida ativa em outra empresa
    for divida in dividas_cliente:
        if divida.status == 'ATIVA' and divida.empresa != usuario_empresa:
            return divida.empresa
    
    # 2. Tenta encontrar qualquer dívida em outra empresa
    for divida in dividas_cliente:
        if divida.empresa != usuario_empresa:
            return divida.empresa
    
    # 3. Se não encontrar, retorna a empresa do usuário
    return usuario_empresa