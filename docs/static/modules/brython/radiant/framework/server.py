import os

from browser import document, timer
from .utils import LocalInterpreter
from .html_ import select, html
from browser.template import Template
from interpreter import Interpreter

RadiantServer = None


########################################################################
class RadiantCore:
    """"""
    endpoints = []

    # ----------------------------------------------------------------------
    def __init__(self, class_, python=[[None, None, None]], **kwargs):
        """"""
        for module, class_, endpoint in python:
            if module and module != 'None':
                setattr(self, class_, LocalInterpreter(endpoint=endpoint))

        self.body = select('body')
        self.head = select('head')

    # ----------------------------------------------------------------------
    def add_css_file(self, file):
        """"""
        document.select('head')[0] <= html.LINK(
            href=os.path.join('root', file), type='text/css', rel='stylesheet')

    # # ----------------------------------------------------------------------
    # def on_load(self, callback, evt='DOMContentLoaded'):
        # """"""
        # logging.warning('#' * 30)
        # logging.warning('#' * 30)
        # document.addEventListener('load', callback)
        # logging.warning('#' * 30)
        # logging.warning('#' * 30)

    # ----------------------------------------------------------------------
    def map_value(self, x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    # ----------------------------------------------------------------------
    def welcome(self):
        """"""
        parent = html.DIV(style={'width': '90vw', 'margin-left': '5vw', 'margin-right': '5vw'})

        links_style = {
            'color': '#28BDB8',
            'text-decoration': 'none',
            'font-weight': '400',
        }

        buttons_style = {
            'background-color': '#28bdb8',
            'border': 'none',
            'padding': '10px 15px',
            'color': 'white',
        }

        with parent.context as parent:
            parent <= html.H1('Radiant Framework', style={'font-weight': '300', 'color': '#28bdb8'})
            documentation = html.A(' documentation ', href='https://radiant-framework.readthedocs.io', style=links_style)
            repository = html.A(' repository ', href='https://github.com/dunderlab/python-radiant_framework', style=links_style)
            brython = html.A(' Brython ', href='https://brython.info/', style=links_style)

            with html.SPAN().context as tagline:
                tagline <= html.SPAN('Visit the')
                tagline <= documentation
                tagline <= html.SPAN('for more information or the')
                tagline <= repository
                tagline <= html.SPAN('to get the source code.')

            with html.DIV(style={'padding': '20px 0px'}).context as container:
                with html.BUTTON('Open Terminal', style=buttons_style).context as button:
                    button.bind('click', lambda evt: Interpreter(title="Radiant Framework", cols=80))

            with html.IMG(src='https://radiant-framework.readthedocs.io/en/latest/_static/logo.svg').context as image:
                image.style.width = '100vw'
                image.style.height = '25vh'
                image.style['background-color'] = '#F2F2F2'
                image.style['border-top'] = '1px solid #cdcdcd'
                image.style['margin-top'] = '5vh'
                image.style['margin-left'] = '-5vw'

            with html.DIV(style={'text-align': 'center', 'font-size': '110%', 'width': '100%', }).context as container:
                container <= html.SPAN('Radiant Framework is running succesfully!<br>')

                with html.SPAN().context as tagline:
                    tagline <= brython
                    tagline <= html.SPAN('powered!')

        self.body.style = {
            'background-color': '#F2F2F2',
            'font-family': 'Roboto',
            'font-weight': '300',
            'margin': '0px',
            'padding': '0px',

        }
        self.body <= parent

    # ----------------------------------------------------------------------
    def hide(self, selector):
        """"""
        def inset(evt):
            document.select_one(selector).style = {'display': 'none'}
        return inset

    # ----------------------------------------------------------------------
    def show(self, selector):
        """"""
        def inset(evt):
            document.select_one(selector).style = {'display': 'block'}
        return inset

    # ----------------------------------------------------------------------
    def toggle(self, selector):
        """"""
        def inset(evt):
            if document.select_one(selector).style['display'] == 'none':
                document.select_one(selector).style['display'] = 'block'
            else:
                document.select_one(selector).style['display'] = 'none'
        return inset



########################################################################
class RadiantAPI(RadiantCore):
    """"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.body = select('body')
        self.head = select('head')


    # ----------------------------------------------------------------------
    @classmethod
    def get(cls, url):
        """"""
        def inset(fn):
            RadiantCore.endpoints.append((url, fn.__name__))
            def subinset(**arguments):
                class Wrapped(RadiantCore):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        fn(**{k:arguments[k][0] for k in arguments})
                return Wrapped
            return subinset
        return inset

    # ----------------------------------------------------------------------
    @classmethod
    def post(cls, url):
        """"""
        def inset(fn):
            RadiantCore.endpoints.append((url, fn.__name__))
            def subinset(**arguments):
                class Wrapped(RadiantCore):
                    def __init__(self, *args, **kwargs):
                        super().__init__(*args, **kwargs)
                        fn(**{k:arguments[k][0] for k in arguments})
                return Wrapped
            return subinset
        return inset




# ----------------------------------------------------------------------
def render(template, context={}):
    """"""
    placeholder = '#radiant-placeholder--templates'
    parent = document.select_one(placeholder)
    parent.attrs['b-include'] = f"root/{template}"
    document.select_one('body') <= parent
    Template(placeholder[1:]).render(**context)
    document.select_one(placeholder).style = {'display': 'block'}
    return document.select_one(placeholder).children

