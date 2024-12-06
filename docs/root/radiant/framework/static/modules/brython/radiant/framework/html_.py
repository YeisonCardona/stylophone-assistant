from browser import html as html_
from browser import document as document_


########################################################################
class style_context:
    """"""
    # ----------------------------------------------------------------------

    def __init__(self, element):
        """"""
        self.style = element.style

    # # ----------------------------------------------------------------------
    def __getattr__(self, attr):
        """"""
        attr = attr.replace('_', '-')
        return getattr(self.style, attr)

    # ----------------------------------------------------------------------
    def __setattr__(self, attr, value):
        """"""
        if attr in ['style']:
            return super().__setattr__(attr, value)

        attr = attr.replace('_', '-')
        return setattr(self.style, attr, value)


########################################################################
class class_context(list):
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, element, classes):
        """"""
        super().__init__(filter(None, classes.split(' ')))
        self.element = element

    # ----------------------------------------------------------------------
    def __setitem__(self, key, value):
        """"""
        ret = super().__setitem__(key, value)
        self.element.class_name = ' '.join(self)
        return ret

    # ----------------------------------------------------------------------
    def append(self, item):
        """"""
        ret = super().append(item.strip())
        self.element.class_name = ' '.join(self)
        return ret

    # ----------------------------------------------------------------------
    def extend(self, items):
        """"""
        ret = super().extend([item.strip() for item in items])
        self.element.class_name = ' '.join(self)
        return ret

    # ----------------------------------------------------------------------
    def insert(self, index, item):
        """"""
        ret = super().insert(index, item.strip())
        self.element.class_name = ' '.join(self)
        return ret

    # ----------------------------------------------------------------------
    def remove(self, value):
        """"""
        if value in self:
            ret = super().remove(value.strip())
            self.element.class_name = ' '.join(self)
            return ret


########################################################################
class select(list):
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, selector):
        """Constructor"""
        super().__init__(document_.select(selector))

    # ----------------------------------------------------------------------
    def __getattr__(self, attr):
        """"""
        if attr == 'style':
            return self.style_()

        if attr == 'styles':
            return self.styles_()

        if attr == 'classes':
            return self.classes_()

        if attr == 'bind':
            return self.bind_()

        def inset(*args, **kwargs):
            return [getattr(element, attr)(*args, **kwargs) for element in self]

        return inset

    # ----------------------------------------------------------------------
    def __setattr__(self, attr, value):
        """"""
        for element in self:
            setattr(element, attr, value)

    # ----------------------------------------------------------------------
    def style_(self):
        """"""
        class Style:
            def __setattr__(cls, attr, value):
                """"""
                for element in self:
                    setattr(element.style, attr, value)
        return Style()

    # ----------------------------------------------------------------------
    def classes_(self):
        """"""
        class Classes_:
            def __getattr__(cls, attr):
                """"""
                def inset(*args, **kwargs):
                    [setattr(element, 'classes', class_context(
                        element, element.class_name)) for element in self]
                    return [getattr(element.classes, attr)(*args, **kwargs) for element in self]
                return inset
        return Classes_()

    # ----------------------------------------------------------------------
    def styles_(self):
        """"""
        class Styles_:
            def __getattr__(cls, attr):
                """"""
                [setattr(element, 'styles', style_context(element))
                 for element in self]
                return [getattr(element.styles, attr) for element in self]

            def __setattr__(cls, attr, value):
                """"""
                [setattr(element, 'styles', style_context(element))
                 for element in self]
                [setattr(element.styles, attr, value) for element in self]

        return Styles_()

    # ----------------------------------------------------------------------
    def bind_(self):
        """"""
        class Bind_:
            def __call__(cls, event, fn):
                """"""
                return [element.bind(event, fn) for element in self]

        return Bind_()


    # ----------------------------------------------------------------------
    def __le__(self, other):
        """"""
        for element in self:
            element <= other


########################################################################
class html_context:
    """"""
    _context = []

    # ----------------------------------------------------------------------
    def __init__(self, element):
        self._element = element
        self._parent = html_context._context[-1] if html_context._context else None

    # ----------------------------------------------------------------------
    def __enter__(self):
        if hasattr(self._element, 'child_'):
            self._element = self._element.child_

        if self._parent:
            self._parent <= self._element

        html_context._context.append(self._element)
        return self._element

    # ----------------------------------------------------------------------
    def __exit__(self, exc_type, exc_val, exc_tb):
        html_context._context.pop()

    # ----------------------------------------------------------------------
    def __setattr__(self, attr, value):
        """"""
        if attr.startswith('_'):
            return super().__setattr__(attr, value)
        if hasattr(self._element, attr):
            setattr(self._element, attr, value)
        else:
            super().__setattr__(attr, value)

    # ----------------------------------------------------------------------
    def __call__(self, parent):
        """"""
        self._parent = parent
        self._parent <= self._element
        return self


########################################################################
class Element:
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, element=None):
        """"""
        self._element = element

    # ----------------------------------------------------------------------
    def __getattribute__(self, attr):
        """"""
        if attr.startswith('_'):
            return super().__getattribute__(attr)

        def inset(*args, **kwargs):
            kwargs_ = {k.removesuffix("_").replace(
                "_", "-"): kwargs[k] for k in kwargs}

            if self._element:
                html_e = self._element
            else:
                html_e = getattr(html_, attr)(*args, **kwargs_)

            html_e.classes = class_context(html_e, kwargs_.get('Class', ''))
            html_e.context = html_context(html_e)
            try:
                html_e.styles = style_context(html_e)
            except:
                html_e.styles = None

            return html_e

        return inset

    # ----------------------------------------------------------------------
    def __call__(self, element):
        """"""
        cont = html.DIV(element)
        cont.child_ = element
        return cont



html = Element()
