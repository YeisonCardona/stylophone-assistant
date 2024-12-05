"""
Radiant

"""

import sys
import shutil
import inspect
import traceback

try:
    # Prevent this file to be imported from Brython
    import browser

    sys.exit()
except:
    pass

import os
import json
import jinja2
import pathlib
import importlib.util
from os.path import abspath
from inspect import getsourcefile
from xml.etree import ElementTree
from typing import Union, List, Tuple, Optional

from tornado.web import Application, url, RequestHandler, StaticFileHandler
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

DEBUG = True
PATH = Union[str, pathlib.Path]
URL = str
DEFAULT_IP = '0.0.0.0'
DEFAULT_PORT = '5000'
DEFAULT_BRYTHON_VERSION = '3.11.3'
DEFAULT_BRYTHON_DEBUG = 0
MAIN = sys.argv[0]


########################################################################
class RadiantCore:
    """Rename Radiant with a new class."""

    endpoints = []

    # ---------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ----------------------------------------------------------------------
    def __new__(cls, **kwargs):
        """"""
        return RadiantServer(cls.__name__, **kwargs)


########################################################################
class RadiantAPI:
    """"""

    # ----------------------------------------------------------------------
    @classmethod
    def run(self, **kwargs):
        """"""
        return RadiantServer(self.__name__, **kwargs)

    # ----------------------------------------------------------------------
    @classmethod
    def get(cls, url):
        def inset(fn):
            RadiantCore.endpoints.append((url, fn.__name__, 'GET', fn))

        return inset

    # ----------------------------------------------------------------------
    @classmethod
    def post(cls, url):
        def inset(fn):
            RadiantCore.endpoints.append((url, fn.__name__, 'POST', fn))

        return inset


########################################################################
class PythonHandler(RequestHandler):
    def post(self):
        name = self.get_argument('name')
        args = tuple(json.loads(self.get_argument('args')))
        kwargs = json.loads(self.get_argument('kwargs'))

        if v := getattr(self, name, None)(*args, **kwargs):
            if v is None:
                data = json.dumps(
                    {
                        '__RDNT__': 0,
                    }
                )
            else:
                data = json.dumps(
                    {
                        '__RDNT__': v,
                    }
                )
            self.write(data)

    # ----------------------------------------------------------------------
    def test(self):
        """"""
        return True

    # ----------------------------------------------------------------------

    def prepare(self):
        """"""


########################################################################
class JSONHandler(RequestHandler):

    # ----------------------------------------------------------------------
    def initialize(self, **kwargs):
        self.json_data = kwargs

    # ----------------------------------------------------------------------
    def get(self):
        self.write(self.json_data)

    # ----------------------------------------------------------------------
    def test(self):
        """"""
        return True


########################################################################
class ThemeHandler(RequestHandler):

    # ----------------------------------------------------------------------
    def get(self):
        theme = self.get_theme()
        loader = jinja2.FileSystemLoader(
            os.path.join(os.path.dirname(__file__), 'templates')
        )
        env = jinja2.Environment(autoescape=True, loader=loader)
        env.filters['vector'] = self.hex2vector
        stylesheet = env.get_template('theme.css.template')
        self.write(stylesheet.render(**theme))

    # ----------------------------------------------------------------------
    @staticmethod
    def hex2vector(hex_: str):
        return ', '.join([str(int(hex_[i : i + 2], 16)) for i in range(1, 6, 2)])

    # ----------------------------------------------------------------------
    def get_theme(self):
        theme = self.settings['theme']

        if (not theme) or (not os.path.exists(theme)):
            theme = os.path.join(
                os.path.dirname(__file__), 'templates', 'default_theme.xml'
            )

        tree = ElementTree.parse(theme)
        theme_css = {child.attrib['name']: child.text for child in tree.getroot()}
        return theme_css


########################################################################
class RadiantHandler(RequestHandler):
    """"""
    domain = ''

    # ----------------------------------------------------------------------
    def initialize(self, **kwargs):
        self.initial_arguments = kwargs

    # ----------------------------------------------------------------------
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')

    # ----------------------------------------------------------------------
    def get(self):
        variables = self.settings.copy()
        variables.update(self.initial_arguments)

        variables['argv'] = json.dumps(variables['argv'])

        if variables['static_app']:
            html = self.render_string(
                f"{os.path.realpath(variables['template'])}", **variables
            )

            if isinstance(variables['static_app'], str):
                parent_dir = variables['static_app']
            else:
                parent_dir = f"{variables['class_']}_static"

            if os.path.exists(parent_dir):
                shutil.rmtree(parent_dir)

            shutil.copytree(os.path.dirname(MAIN), os.path.join(parent_dir, 'root'))
            shutil.copytree(
                os.path.join(os.path.dirname(__file__), 'static'),
                os.path.join(parent_dir, 'static'),
            )

            for element in ['.git', '.gitignore']:
                if os.path.exists(os.path.join(parent_dir, 'root', element)):
                    try:
                        shutil.rmtree(os.path.join(parent_dir, 'root', element))
                    except:
                        os.remove(os.path.join(parent_dir, 'root', element))

            with open(os.path.join(parent_dir, 'index.html'), 'wb') as file:
                file.write(html)
                
            environ_path = os.path.join(parent_dir, self.domain.lstrip("/"))
            if not os.path.exists(environ_path):
                os.mkdir(environ_path)
            
            with open(os.path.join(environ_path, 'environ.json'), 'w') as file:
                json.dump(self.initial_arguments, file)

            for element in ['CNAME', '.nojekyll']:
                if os.path.exists(element):
                    shutil.copyfile(element, os.path.join(parent_dir, element))

        variables['arguments'] = self.request.arguments

        self.render(f"{os.path.realpath(variables['template'])}", **variables)


# ----------------------------------------------------------------------
def RadiantHandlerPost(fn):
    """"""

    class RadiantHandler_(RadiantHandler):

        # ----------------------------------------------------------------------
        def post(self):
            """"""
            data = {key: self.get_argument(key) for key in self.request.arguments}
            response = fn(**data)
            self.set_header("Content-Type", "application/json")
            self.write(json.dumps(response))

    return RadiantHandler_


# ----------------------------------------------------------------------
def make_app(
    class_: str,
    /,
    brython_version: str,
    debug_level: int,
    pages: Tuple[str],
    endpoints: Tuple[str],
    template: PATH = os.path.join(os.path.dirname(__file__), 'templates', 'index.html'),
    environ: dict = {},
    mock_imports: Tuple[str] = [],
    handlers: Tuple[URL, Union[List[Union[PATH, str]], RequestHandler], dict] = (),
    python: Tuple[PATH, str] = ([None, None, None]),
    theme: PATH = None,
    path: List = [],
    autoreload: bool = False,
    static_app: bool = False,
    domain: Optional[str] = '',
    templates_path: PATH = None,
    modules: Optional[list] = [],
    page_title: Optional[str] = '',
    page_favicon: Optional[str] = '',
    page_description: Optional[str] = '',
    page_image: Optional[str] = '',
    page_url: Optional[str] = '',
    page_summary_large_image: Optional[str] = '',
    page_site: Optional[str] = '',
    page_author: Optional[str] = '',
    page_copyright: Optional[str] = '',
):
    """
    Parameters
    ----------
    class_ :
        The main class name as string.
    template :
        Path for HTML file with the template.
    environ :
        Dictionary with arguments accessible from the template and main class.
    mock_imports :
        List with modules that exist in Python but not in Brython, this prevents
        imports exceptions.
    handlers :
        Custom handlers for server.
    python :
        Real Python scripting handler.
    theme :
        Path for the XML file with theme colors.
    path :
        Custom directory accesible from Brython PATH.
    autoreload :
        Activate the `autoreload` Tornado feature.
    """

    settings = {
        "debug": DEBUG,
        'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        'static_url_prefix': f'{domain}/static/',
        "xsrf_cookies": False,
        'autoreload': autoreload,
    }

    if templates_path:
        settings['template_path'] = templates_path

    environ.update(
        {
            'class_': class_,
            # 'python_': python if python else [(None, None)],
            'python_': python,
            'module': os.path.split(sys.path[0])[-1],
            'file': os.path.split(MAIN)[-1].replace('.py', ''),
            'file_path': os.path.join(f'{domain}/root', os.path.split(MAIN)[-1]),
            'theme': theme,
            'argv': [MAIN],
            # 'argv': sys.argv,
            'template': template,
            'mock_imports': mock_imports,
            'path': [f'{domain}/root/', f'{domain}/static/modules/brython'] + path,
            'brython_version': brython_version,
            'debug_level': debug_level,
            'static_app': static_app,
            'domain': domain,
            'modules': modules,
            'page_title': page_title,
            'page_favicon': page_favicon,
            'page_description': page_description,
            'page_image': page_image,
            'page_url': page_url,
            'page_summary_large_image': page_summary_large_image,
            'page_site': page_site,
            'page_author': page_author,
            'page_copyright': page_copyright,
            'wrapped': False,
        }
    )

    app = []
    if class_ != 'RadiantAPI':
        RadiantHandler.domain = domain
        app += [url(r'^/$', RadiantHandler, environ)]

    app += [
        url(rf'^{domain}/theme.css$', ThemeHandler),
        url(rf'^{domain}/root/(.*)', StaticFileHandler, {'path': sys.path[0]}),
        url(rf'^{domain}/environ.json$', JSONHandler, environ),
        # url(r'^/manifest.json$', ManifestHandler),
    ]

    if isinstance(pages, str):
        *package, module_name = pages.split('.')
        module = importlib.import_module('.'.join(package))
        pages = getattr(module, module_name)

    for url_, module in pages:

        if issubclass(module, RadiantCore):

            environ_tmp = environ.copy()
            environ_tmp['file'] = os.path.split(sys.argv[0])[-1].rstrip('.py')
            environ_tmp['class_'] = module.__name__
            app.append(
                url(url_, RadiantHandler, environ_tmp),
            )

        else:
            if '.' in module:
                *file_, class_ = module.split('.')
            else:
                *file_, class_ = f'{os.path.split(MAIN)[-1][:-3]}.{module}'.split('.')

            environ_tmp = environ.copy()
            file_ = '.'.join(file_)
            environ_tmp['file'] = file_
            environ_tmp['class_'] = class_
            app.append(
                url(url_, RadiantHandler, environ_tmp),
            )

    if isinstance(endpoints, str):
        *package, module_name = endpoints.split('.')
        module = importlib.import_module('.'.join(package))
        endpoints = getattr(module, module_name)

    reference_order = ['POST', 'GET']
    sorted_endpoints = sorted(
        RadiantCore.endpoints,
        key=lambda x: (
            reference_order.index(x[2]) if x[2] in reference_order else float('inf')
        ),
    )

    handlers_ = {}
    for url_, module, method, fn in sorted_endpoints:
        environ_tmp = environ.copy()
        environ_tmp['file'] = os.path.split(sys.argv[0])[-1].rstrip('.py')
        environ_tmp['class_'] = module
        environ_tmp['wrapped'] = True

        if method == 'POST':
            handlers_[url_] = RadiantHandlerPost(fn)
        elif method == 'GET':
            handler = handlers_.get(url_, RadiantHandler)
            app.append(
                url(url_, handler, environ_tmp),
            )

    for module, class_, endpoint in python:

        if not os.path.isabs(module):
            python_path = os.path.join(sys.path[0], module)
        else:
            python_path = module

        spec = importlib.util.spec_from_file_location(
            '.'.join([module, class_]).replace('.py', ''), python_path
        )
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)
        app.append(url(f'^{endpoint}', getattr(foo, class_)))

    for handler in handlers:
        if isinstance(handler[1], tuple):
            spec = importlib.util.spec_from_file_location(
                '.'.join(handler[1]).replace('.py', ''),
                os.path.abspath(handler[1][0]),
            )
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)
            app.append(url(handler[0], getattr(foo, handler[1][1]), handler[2]))
        else:
            app.append(url(*handler))

    for dir_ in path:
        app.append(
            url(
                fr'^/{os.path.split(dir_)[-1].strip("/")}/(.*)',
                StaticFileHandler,
                {'path': dir_},
            ),
        )

    settings.update(environ)

    return Application(app, **settings)


# ----------------------------------------------------------------------
def RadiantServer(
    class_: Optional[str] = None,
    host: str = DEFAULT_IP,
    port: str = DEFAULT_PORT,
    pages: Tuple[str] = (),
    endpoints: Tuple[str] = (),
    brython_version: str = DEFAULT_BRYTHON_VERSION,
    debug_level: int = DEFAULT_BRYTHON_DEBUG,
    template: PATH = os.path.join(os.path.dirname(__file__), 'templates', 'index.html'),
    environ: dict = {},
    mock_imports: Tuple[str] = [],
    handlers: Tuple[URL, Union[List[Union[PATH, str]], RequestHandler], dict] = (),
    python: Tuple[PATH, str] = (),
    theme: Optional[PATH] = None,
    path: Optional[list] = [],
    autoreload: Optional[bool] = False,
    callbacks: Optional[tuple] = (),
    static_app: Optional[bool] = False,
    domain: Optional[str] = '',
    templates_path: PATH = None,
    modules: Optional[list] = ['roboto'],
    page_title: Optional[str] = '',
    page_favicon: Optional[str] = '',
    page_description: Optional[str] = '',
    page_image: Optional[str] = '',
    page_url: Optional[str] = '',
    page_summary_large_image: Optional[str] = '',
    page_site: Optional[str] = '',
    page_author: Optional[str] = '',
    page_copyright: Optional[str] = '',
    **kwargs,
):
    """Python implementation for move `class_` into a Bython environment.

    Configure the Tornado server and the Brython environment for run the
    `class_` in both frameworks at the same time.

    Parameters
    ----------
    class_ :
        The main class name as string.
    host :
        The host for server.
    port :
        The port for server.
    template :
        Path for HTML file with the template.
    environ :
        Dictionary with arguments accessible from the template and main class.
    mock_imports :
        List with modules that exist in Python but not in Brython, this prevents
        imports exceptions.
    handlers :
        Custom handlers for server.
    python :
        Real Python scripting handler.
    theme :
        Path for the XML file with theme colors.
    path :
        Custom directory accesible from Brython PATH.
    autoreload :
        Activate the `autoreload` Tornado feature.

    """

    print("Radiant server running on port {}".format(port))
    application = make_app(
        class_,
        python=python,
        template=template,
        handlers=handlers,
        theme=theme,
        environ=environ,
        mock_imports=mock_imports,
        path=path,
        brython_version=brython_version,
        pages=pages,
        endpoints=endpoints,
        debug_level=debug_level,
        static_app=static_app,
        domain=domain,
        templates_path=templates_path,
        modules=modules,
        page_title=page_title,
        page_favicon=page_favicon,
        page_description=page_description,
        page_image=page_image,
        page_url=page_url,
        page_summary_large_image=page_summary_large_image,
        page_site=page_site,
        page_author=page_author,
        page_copyright=page_copyright,
    )
    http_server = HTTPServer(
        application,
    )
    http_server.listen(port, host)

    for handler in callbacks:
        if isinstance(handler, tuple):
            spec = importlib.util.spec_from_file_location(
                '.'.join(handler).replace('.py', ''),
                os.path.abspath(handler[0]),
            )
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)
            getattr(foo, handler[1])()
        else:
            handler()

    IOLoop.instance().start()


# ----------------------------------------------------------------------
def render(*args, **kwargs):
    """"""
    return None
