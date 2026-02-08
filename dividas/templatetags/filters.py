from django import template

register = template.Library()

@register.filter
def sum_valor_atual(queryset):
    """Soma o valor atual de uma queryset de dívidas"""
    return sum(d.valor_atual for d in queryset)

@register.filter
def group_by_status(queryset):
    """Agrupa dívidas por status"""
    from collections import Counter
    from django.utils.translation import gettext as _
    
    status_map = {
        'ATIVA': _('Ativa'),
        'PAGA': _('Paga'),
        'NEGOCIACAO': _('Negociação'),
        'CANCELADA': _('Cancelada'),
    }
    
    counter = Counter(d.status for d in queryset)
    return [(status_map[status], count) for status, count in counter.items()]

@register.filter
def map(queryset, attr):
    """Mapeia um atributo de uma queryset"""
    return [getattr(obj, attr) for obj in queryset]

@register.filter
def unique(list_obj):
    """Remove duplicados de uma lista"""
    return list(set(list_obj))

@register.filter
def get_item(dictionary, key):
    """Obtém um item de um dicionário"""
    return dictionary.get(key, '')