from browser import html
from functools import cache
#from .html_ import Element

maketag = cache(html.maketag)

########################################################################
class WebComponents:
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, root=''):
        """"""
        self.root = root


    # ----------------------------------------------------------------------
    def __getattr__(self, attr):
        """"""
        def element(*args, **kwargs):

            if attr.startswith('_'):
                tag = maketag(f'{attr[1:].removesuffix("_").replace("_", "-")}')
            else:
                tag = maketag(f'{self.root}-{attr.removesuffix("_").replace("_", "-")}')

            kwargs = {k.rstrip('_'): v for k, v in kwargs.items()}
            return tag(*args, **kwargs)
        return element