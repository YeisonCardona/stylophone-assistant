from browser import html


# ----------------------------------------------------------------------
def fa(icon, mode='solid', *args, **kwargs):
    """"""
    if icon.startswith('fa-'):
        icon = icon[3:]
    extra_class = kwargs.pop('Class', '')
    return html.I(Class=f'fa-{mode} fa-{icon} {extra_class}', *args, **kwargs)


# ----------------------------------------------------------------------
def bi(icon, *args, **kwargs):
    """"""
    if icon.startswith('bi-'):
        icon = icon[3:]
    extra_class = kwargs.pop('Class', '')
    return html.I(Class=f'bi bi-{icon} {extra_class}', *args, **kwargs)


# ----------------------------------------------------------------------
def mi(icon, size=48, *args, **kwargs):
    """"""
    if icon.startswith('md-'):
        icon = icon[3:]
    extra_class = kwargs.pop('Class', '')
    return html.SPAN(icon, Class=f'material-icons md-{size} {extra_class}', *args, **kwargs)
