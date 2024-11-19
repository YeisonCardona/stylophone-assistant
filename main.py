from radiant.framework.server import RadiantCore, RadiantServer
from radiant.framework import html, Element
from browser import document, svg, ajax
from browser import timer
from radiant.framework import WebComponents
from browser.local_storage import storage
import re

sl = WebComponents('sl')

button_base = '#B3B3B3'
button_active = '#c2733e'
max_tabs = 5
ignore_chars = ',-–—()<>'
domain = '/stylophone-assistant'

header_text = """
<strong>Stylophone Assistant</strong> is your go-to platform for enhancing your <strong>Stylophone</strong> practice. This tool allows you to input <strong>tabs</strong> for your favorite melodies and generates a dynamic <strong>animation</strong> compatible with both the <strong>S-1</strong> and <strong>Gen X-1</strong> models. Whether you're a <strong>beginner</strong> or an <strong>experienced player</strong>, the interactive interface helps you <strong>visualize</strong> and follow along with ease. Practice at your own pace, toggle <strong>octaves</strong>, and refine your <strong>skills</strong> while having fun with your <strong>Stylophone</strong>.
"""

default_tabs = """# Write tabs here

"""

# Con el switch en la posición 2 en el S-1 y sin modificador de octavas en la X-1
# Asume que la octava central del S-1, corresponde con la primera octava del X-1
equivalencia_notas_mode1 = {
    # tab(S-1): (tab X-1, modificador de octava)
    # Notas de la 3ª octava (Al no estar en el X-1 necesitan modificador)
    "1": ("8", "-1"),
    "1.5": ("8.5", "-1"),
    "2": ("9", "-1"),
    # Notas de la 4ª octava
    "3": ("3", "0"),
    "3.5": ("3.5", "0"),
    "4": ("4", "0"),
    "4.5": ("4.5", "0"),
    "5": ("5", "0"),
    "6": ("6", "0"),
    "6.5": ("6.5", "0"),
    "7": ("7", "0"),
    "7.5": ("7.5", "0"),
    "8": ("8", "0"),
    "8.5": ("8.5", "0"),
    "9": ("9", "0"),
    # Notas de la 5ª octava
    "10": ("10", "0"),
    "10.5": ("10.5", "0"),
    "11": ("11", "0"),
    "11.5": ("11.5", "0"),
    "12": ("12", "0"),
    # Notas de la 5ª octava que no están en la S1
    "13": ("13", "0"),
    "13.5": ("13.5", "0"),
    "14": ("14", "0"),
    "14.5": ("14.5", "0"),
    "15": ("15", "0"),
    "15.5": ("15.5", "0"),
    "16": ("16", "0"),
}


# Con el switch en la posición 2 en el S-1 y sin modificador de octavas en la X-1
# Asume que la octava central del S-1, corresponde con la segunda octava del X-1, es decir que por defecto esta en el modificador -1
equivalencia_notas_mode2 = {
    # Notas de la 3ª octava
    "1": ("1", "0"),
    "1.5": ("1.5", "0"),
    "2": ("2", "0"),
    # Notas de la 4ª octava
    "3": ("3", "0"),
    "3.5": ("3.5", "0"),
    "4": ("4", "0"),
    "4.5": ("4.5", "0"),
    "5": ("5", "0"),
    "6": ("6", "0"),
    "6.5": ("6.5", "0"),
    "7": ("7", "0"),
    "7.5": ("7.5", "0"),
    "8": ("8", "0"),
    "8.5": ("8.5", "0"),
    "9": ("9", "0"),
    # Notas de la 5ª octava que no están en esta configuración del X-1
    "10": ("3", "-2"),
    "10.5": ("3.5", "-2"),
    "11": ("4", "-2"),
    "11.5": ("4.5", "-2"),
    "12": ("5", "-2"),
}


# ----------------------------------------------------------------------
def convertir_secuencia(secuencia, equivalencia, modificador):
    """"""
    notas = secuencia.split(' ')
    secuencia_convertida = []

    for nota in notas:
        if nota in equivalencia:
            genx1_pos, octava = equivalencia[nota]
            if modificador == '-1':
                octava = str(int(octava) - int(modificador) - 1)

            if octava == '0':
                secuencia_convertida.append(f"{genx1_pos}")
            else:
                secuencia_convertida.append(f"({octava}:{genx1_pos})")
        else:
            secuencia_convertida.append(nota)

    secuencia_convertida = " ".join(secuencia_convertida)
    return secuencia_convertida


# ----------------------------------------------------------------------
def load_tabs():
    """"""
    import os
    import json

    files = os.listdir('tabs')

    tabs = {}
    for filename in filter(lambda f: f.endswith('.txt'), files):
        with open(os.path.join('tabs', filename), 'r') as file:
            tabs[filename] = file.read()

    with open('tabs/tabs.json', 'w') as file:
        json.dump(tabs, file, indent='  ')


# ----------------------------------------------------------------------
def descomprimir_texto(texto):
    """
    Descomprime líneas que contienen patrones como '(contenido)x2' o '(contenido) x2'
    replicando la línea anterior.

    Args:
        texto (str): El texto de entrada con posibles patrones '(...)xN'.

    Returns:
        str: El texto con los patrones descomprimidos.
    """
    lineas = texto.split("\n")
    resultado = []

    for linea in lineas:
        # Verificar si hay un patrón de repetición (xN) con o sin espacio
        match = re.search(r'\((.*?)\)\s*x(\d+)', linea)
        if match:
            # Extraer la línea dentro del paréntesis y el número de repeticiones
            contenido = match.group(1).strip()
            repeticiones = int(match.group(2))

            # Agregar la línea descomprimida al resultado
            resultado.extend([contenido] * repeticiones)
        else:
            # Si no hay patrón de repetición, agregar la línea tal cual
            resultado.append(linea)

    return "\n".join(resultado)


########################################################################
class StylophoneAssistant(RadiantCore):

    stop = False

    # ----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """"""
        super().__init__(*args, **kwargs)
        self.loaded = False

        with html.DIV(Class='container').context(self.body) as container:

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-12 text-top').context(row) as col:

                    col <= html.H1('Stylophone Assistant', Class='page-title')
                    col <= html.SPAN(header_text, Class='page-header')
                    col <= html.HR()

                with html.DIV(Class='col-md-4').context(row) as col:
                    with html(
                        sl.select(
                            pill=True,
                            label="Stylophone",
                            value="x1",
                            style="margin-top: 15px;",
                        )
                    ).context(col) as self.select_gen:
                        self.select_gen <= sl.option("Gen S-1", value='s1')
                        self.select_gen <= sl.option("Gen X-1", value='x1')
                        self.select_gen <= sl.option("Both", value='both')
                        self.select_gen.bind("sl-change", self.load_stylophone)

                with html.DIV(Class='col-md-4').context(row) as col:
                    with html(
                        sl.select(
                            pill=True,
                            label="Style",
                            value="tabs",
                            style="margin-top: 15px;",
                        )
                    ).context(col) as self.select_style:
                        self.select_style <= sl.option("Tabs", value='tabs')
                        self.select_style <= sl.option("Solfège", value='solfege')
                        self.select_style <= sl.option("Kids", value='kids')
                        self.select_style.bind("sl-change", self.load_stylophone)

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-4').context(row) as col:
                    with html(
                        sl.select(
                            pill=True,
                            label="Load tabs",
                            value="custom",
                            style="margin-top: 15px;",
                        )
                    ).context(col) as self.select_tab:
                        self.select_tab <= sl.option("Custom", value='custom')
                        self.select_tab.bind("sl-change", self.load_tab_in_textarea)

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-12', style='margin-top: 15px;').context(
                    row
                ) as col:
                    with html(
                        sl.textarea(label="Tabs", resize="auto", spellcheck="false")
                    ).context(col) as self.textarea_s1:
                        self.textarea_s1.bind("sl-input", self.textarea_save)

            with html.DIV(Class='row', style='margin-top: 20px;').context(
                container
            ) as row:

                with html.DIV(Class='col-md-3', style='margin-top: 15px;').context(
                    row
                ) as col:
                    self.switch_transpose = sl.switch("Transpose Tabs")
                    col <= self.switch_transpose
                    self.switch_transpose.bind("sl-input", self.activate_transpose)

                with html.DIV(Class='col-md-9', style='margin-top: -5px;').context(
                    row
                ) as col:

                    self.range_transpose = sl.range(
                        min="-12",
                        max="+12",
                        step=1,
                        value="0",
                        style="--track-active-offset: 50%; --track-color-active: var(--sl-color-primary-600);  --track-color-inactive: var(--sl-color-primary-100);margin-top: 20px;",
                    )
                    col <= self.range_transpose
                    self.range_transpose.bind("sl-input", self.update_transposed_tabs)
                    self.range_transpose.tooltipFormatter = (
                        lambda value: f"{'+' if value > 0 else ''}{value} semitone{'' if value in [1, 1 , 0] else 's'}"
                    )
                    self.range_transpose.style.display = 'none'

                with html.DIV(Class='col-md-12', style='margin-top: 15px;').context(
                    row
                ) as col:

                    with html(
                        sl.textarea(
                            label="Transposed Tabs", resize="auto", spellcheck="false"
                        )
                    ).context(col) as self.textarea_transpose:
                        self.textarea_transpose.bind("sl-input", self.textarea_save)
                        self.textarea_transpose.style.display = 'none'

                    self.switch_transpose_model = sl.switch(
                        "Transpose for X-1", checked=True, style='margin-top: 10px;'
                    )
                    col <= self.switch_transpose_model
                    self.switch_transpose_model.style.display = 'none'
                    self.switch_transpose_model.bind(
                        "sl-input", self.update_transposed_tabs
                    )

                    col <= html.HR()

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-12', style='margin-top: 15px;').context(
                    row
                ) as col:
                    self.switch_x1_8va = sl.switch("Gen X-1 -1 Octave")
                    col <= self.switch_x1_8va
                    self.switch_x1_8va.bind("sl-input", self.load_stylophone)

                with html.DIV(Class='col-md-12', style='margin-top: 15px;').context(
                    row
                ) as col:
                    self.svg_container = html.DIV()
                    col <= self.svg_container

            with html.DIV(Class='row tabs-line').context(container) as row:

                with html.DIV(
                    Class='col-5',
                    style='text-align: right; margin-top: 10px;',
                ).context(row) as col:

                    self.span_tabs_pre = html.SPAN(
                        '...',
                        Class='--sl-font-sans',
                        style='flex: none',
                    )
                    col <= self.span_tabs_pre

                with html.DIV(
                    Class='col-2',
                    style='text-align: center;',
                ).context(row) as col:

                    self.span_tabs_current = html.SPAN(
                        '#',
                        Class='--sl-font-sans',
                        style=f'flex: none; color: var(--sl-color-primary-600); font-size: 2rem;',
                    )
                    col <= self.span_tabs_current

                with html.DIV(
                    Class='col-5',
                    style='text-align: left; margin-top: 10px;',
                ).context(row) as col:

                    self.span_tabs_post = html.SPAN(
                        '...',
                        Class='--sl-font-sans',
                        style='flex: none',
                    )
                    col <= self.span_tabs_post

            with html.DIV(Class='row', style='margin-top: 30px;').context(
                container
            ) as row:

                with html.DIV(
                    Class='col-4 col-sm-6 icon-button-color', style="display: flex;"
                ).context(row) as col:

                    with html(
                        sl.icon_button(name="play-circle", style="font-size: 2rem;")
                    ).context(col) as button:
                        button.bind("click", self.on_button_start)

                    with html(
                        sl.icon_button(name="stop-circle", style="font-size: 2rem;")
                    ).context(col) as button:
                        button.bind("click", self.on_button_stop)

                with html.DIV(Class='col-8 col-sm-6', style="margin-top: 4px;").context(
                    row
                ) as col:
                    with html(sl.select(pill=True, value="500")).context(
                        col
                    ) as self.select_delay:
                        for i in range(100, 5001, 100):
                            self.select_delay <= sl.option(
                                f"Delay: {i / 1000 :.1f} s", value=f"{i}"
                            )
                        self.select_delay.bind("sl-change", self.load_stylophone)

                with html.DIV(Class='col-12', style="margin-top: 14px;").context(
                    row
                ) as col:

                    with html(
                        sl.range(
                            min="0",
                            max="100",
                            step=1,
                            value="0",
                            # tooltip="bottom",
                            style="  --track-color-active: var(--sl-color-primary-600);  --track-color-inactive: var(--sl-color-primary-100);margin-top: 20px;",
                        )
                    ).context(col) as self.range_progress:
                        self.range_progress.tooltipFormatter = (
                            lambda value: f"Tab {value + 1}"
                        )
                        self.range_progress.bind("sl-input", self.range_progress_change)

        timer.set_timeout(self.set_loaded, 500)

    # ----------------------------------------------------------------------
    def set_loaded(self):
        """"""
        self.loaded = True
        self.counter_s1 = 0
        self.counter_x1 = 0

        self.textarea_s1.value = storage.get('tabs', default_tabs)
        self.update_tabs_preview()

        self.load_stylophone(gen='x1', style='tabs', x1_8va='')
        self.load_tabs()

    # ----------------------------------------------------------------------
    @property
    def normalized_tabs(self):
        """"""
        tabs = self.textarea_s1.value
        tabs = descomprimir_texto(tabs)

        tabs_decomented = []
        for line in tabs.split('\n'):
            if '#' in line:
                tabs_decomented.append(line[: line.find('#')])
            else:
                tabs_decomented.append(line)

        tabs = ' \n '.join(tabs_decomented)

        for char in ignore_chars:
            tabs = tabs.replace(char, ' ')

        tabs_clear = []
        for line in tabs.split('\n'):
            tabs_clear.append(' '.join(line.split()))

        return '\n'.join(tabs_clear).strip('\n')

    # ----------------------------------------------------------------------
    @property
    def tabla_equivalencias(self):
        """"""
        if self.switch_x1_8va.checked:
            return equivalencia_notas_mode2
        else:
            return equivalencia_notas_mode1

    # ----------------------------------------------------------------------
    def textarea_save(self, event=None):
        """"""
        if self.select_tab.value == 'custom':
            storage['tabs'] = self.textarea_s1.value

        self.counter_s1 = 0
        self.counter_x1 = 0
        self.update_tabs_preview()

        self.range_progress.min = 0
        self.range_progress.max = len(self.normalized_tabs.split(' ')) - 1

        print("Input tabs:", self.textarea_s1.value)
        print("Normalized tabs:", self.normalized_tabs)
        print('S-1 tabs:', ' '.join(self.s1_tabs))
        print('X-1 tabs:', ' '.join(self.x1_tabs))

    # ----------------------------------------------------------------------
    def range_progress_change(self, event):
        """"""
        self.counter_s1 = event.target.value
        self.counter_x1 = event.target.value
        self.update_tabs_preview()

    # ----------------------------------------------------------------------
    def update_tabs_preview(self):
        """"""
        if self.switch_transpose.checked:
            self.update_transposed_tabs()

            self.s1_tabs = self.textarea_transpose.value.split(' ')
            self.x1_tabs = convertir_secuencia(
                self.textarea_transpose.value,
                self.tabla_equivalencias,
                '-1' if self.switch_x1_8va.checked else '0',
            ).split(' ')

        else:
            self.s1_tabs = self.normalized_tabs.split(' ')
            self.x1_tabs = convertir_secuencia(
                self.normalized_tabs,
                self.tabla_equivalencias,
                '-1' if self.switch_x1_8va.checked else '0',
            ).split(' ')

        if self.select_gen.value == 's1':
            tab = self.s1_tabs[self.counter_s1]
            self.span_tabs_pre.text = ' - '.join(
                self.s1_tabs[max(0, self.counter_s1 - max_tabs) : self.counter_s1]
            )
            self.span_tabs_current.text = f" {tab.strip('()')} "
            self.span_tabs_post.text = ' - '.join(
                self.s1_tabs[
                    self.counter_s1
                    + 1 : min(len(self.s1_tabs), self.counter_s1 + max_tabs)
                ]
            )

        elif self.select_gen.value in ['both', 'x1']:
            tab = self.x1_tabs[self.counter_x1]
            self.span_tabs_pre.text = ' - '.join(
                self.x1_tabs[max(0, self.counter_x1 - max_tabs) : self.counter_x1]
            )
            self.span_tabs_current.text = f" {tab.strip('()')} "
            self.span_tabs_post.text = ' - '.join(
                self.x1_tabs[
                    self.counter_x1
                    + 1 : min(len(self.x1_tabs), self.counter_x1 + max_tabs)
                ]
            )

    # ----------------------------------------------------------------------
    def on_button_start(self, event):
        self.stop = False

        self.counter_s1 = self.range_progress.value
        self.counter_x1 = self.range_progress.value

        self.update_tabs_preview()

        match self.select_gen.value:

            case 's1':
                self.animate_s1()

            case 'x1':
                self.animate_x1()

            case 'both':
                self.animate_s1()
                self.animate_x1()

    # ----------------------------------------------------------------------
    def on_button_stop(self, event):
        self.stop = True
        self.range_progress.value = 0

    # ----------------------------------------------------------------------
    def load_stylophone(self, event=None, gen=None, style=None, x1_8va=None):
        """"""
        if not self.loaded:
            return

        if event:
            gen = self.select_gen.value
            style = self.select_style.value
            x1_8va = '-1' if self.switch_x1_8va.checked else ''

        if gen == 's1':
            x1_8va = ''

        req = ajax.ajax()
        req.bind('complete', self.on_complete_load_stylophone)
        req.open(
            'GET', f'{domain}/root/assets/stylophone_{gen}_{style}{x1_8va}.svg', True
        )
        req.send()

    # ----------------------------------------------------------------------
    def on_complete_load_stylophone(self, req):
        """"""
        if req.status == 200:

            self.svg_container.innerHTML = req.responseText
            self.svg_container.style.width = "100%"

            svg_element = document.select("svg")[0]
            svg_element.setAttribute("width", "100%")
            svg_element.setAttribute("preserveAspectRatio", "xMidYMid meet")

            try:
                document["tab_sm2"].style.fill = button_active
            except:
                pass

            if self.switch_x1_8va.checked:
                try:
                    document["tab_xm1"].style.fill = button_active
                except:
                    pass

            self.textarea_save()

    # ----------------------------------------------------------------------
    def load_tabs(self):
        """"""
        req = ajax.ajax()
        req.bind('complete', self.on_complete_load_tabs)
        req.open('GET', f'{domain}/root/tabs/tabs.json', True)
        req.send()

    # ----------------------------------------------------------------------
    def on_complete_load_tabs(self, req):
        """"""
        if req.status == 200:
            tabs = req.json

            for i, tab in enumerate(tabs):
                option = sl.option(
                    tab.replace('.txt', ''),
                    value=f'tab-{i}',
                    id=f'id-tab-{i}',
                )
                option.attrs['tabs'] = tabs[tab]
                self.select_tab <= option

    # ----------------------------------------------------------------------
    def load_tab_in_textarea(self, event):
        """"""
        tab = event.target.value
        if tab == 'custom':
            self.textarea_s1.value = storage.get('tabs', default_tabs)
        else:
            option = document[f'id-{tab}']
            self.textarea_s1.value = option.attrs['tabs']
        self.textarea_save()
        if self.switch_transpose.checked:
            self.update_transposed_tabs()

    # ----------------------------------------------------------------------
    def clear(self, tab):
        svg_element = document[tab]
        svg_element.style.fill = button_base

    # ----------------------------------------------------------------------
    def active(self, tab):
        svg_element = document[tab]
        svg_element.style.fill = button_active

    # ----------------------------------------------------------------------
    def animate_s1(self):

        try:
            tab = self.s1_tabs[self.counter_s1]
        except:
            return

        self.update_tabs_preview()
        self.counter_s1 += 1
        self.range_progress.value = self.counter_s1

        if tab.replace('.', '').isdigit():
            svg_element = document[f"tab_s{tab.replace('.', '_')}"]
            svg_element.style.fill = button_active
        else:
            return self.animate_s1()

        timer.set_timeout(
            lambda: self.clear(f"tab_s{tab.replace('.', '_')}"),
            float(self.select_delay.value) * 0.7,
        )

        if not self.stop:
            timer.set_timeout(self.animate_s1, float(self.select_delay.value))
        else:
            self.range_progress.value = 0

    # ----------------------------------------------------------------------
    def animate_x1(self):
        """"""
        try:
            tab = self.x1_tabs[self.counter_x1]
        except:
            return

        if self.select_gen.value == 'x1':
            self.update_tabs_preview()
            self.counter_x1 += 1
            self.range_progress.value = self.counter_x1
        else:
            self.counter_x1 += 1

        if (
            tab.strip('()')
            .replace('-1:', '')
            .replace('-2:', '')
            .replace('.', '')
            .isdigit()
        ):

            if '-1' in tab:
                tab = tab.strip('()').replace('-1:', '')
                svg_element = document[f"tab_x{tab.replace('.', '_')}"]
                document["tab_xm1"].style.fill = button_active
                self.clear("tab_xm2")

            if '-2' in tab:
                tab = tab.strip('()').replace('-2:', '')
                svg_element = document[f"tab_x{tab.replace('.', '_')}"]
                document["tab_xm2"].style.fill = button_active
                self.clear("tab_xm1")

            else:
                tab = tab.strip('()')
                svg_element = document[f"tab_x{tab.replace('.', '_')}"]

            svg_element.style.fill = button_active

        else:
            return self.animate_x1()

        timer.set_timeout(
            lambda: self.clear(f"tab_x{tab.replace('.', '_')}"),
            float(self.select_delay.value) * 0.7,
        )

        if not self.switch_x1_8va.checked:
            timer.set_timeout(
                lambda: self.clear("tab_xm1"), float(self.select_delay.value)
            )
        timer.set_timeout(lambda: self.clear("tab_xm2"), float(self.select_delay.value))

        if not self.stop:
            timer.set_timeout(self.animate_x1, float(self.select_delay.value))
        else:
            self.range_progress.value = 0

    # ----------------------------------------------------------------------
    def activate_transpose(self, event=None):
        """"""
        if not event.target.checked:
            self.range_transpose.style.display = 'none'
            self.textarea_transpose.style.display = 'none'
            self.switch_transpose_model.style.display = 'none'
        else:
            self.range_transpose.style.display = 'block'
            self.textarea_transpose.style.display = 'block'
            self.switch_transpose_model.style.display = 'block'
            self.update_transposed_tabs()

    # ----------------------------------------------------------------------
    def update_transposed_tabs(self, event=None):
        """"""
        value = self.range_transpose.value
        if self.switch_transpose_model.checked:
            scale = "1 1.5 2 3 3.5 4 4.5 5 6 6.5 7 7.5 8 8.5 9 10 10.5 11 11.5 12 13 13.5 14 14.5 15 15.5 16".split()
        else:
            scale = (
                "1 1.5 2 3 3.5 4 4.5 5 6 6.5 7 7.5 8 8.5 9 10 10.5 11 11.5 12".split()
            )

        tabs_lines = self.normalized_tabs.split('\n')
        transposed_tabs = []

        for line in tabs_lines:

            for tab in line.split(' '):
                if tab in scale:

                    index = scale.index(tab) + value

                    if index < 0:
                        new_tab = f'+1:{scale[index+12]}'

                    elif 0 <= index < len(scale):
                        new_tab = scale[index]

                    elif index >= len(scale):
                        new_tab = f'-1:{scale[index-12]}'

                    transposed_tabs.append(new_tab)

                elif tab:
                    transposed_tabs.append(f'E:{tab}')
                else:
                    transposed_tabs.append(tab)

            transposed_tabs.append('\n')

        tabs_clear = []
        for line in (' '.join(transposed_tabs)).split('\n'):
            tabs_clear.append(' '.join(line.split()))
        self.textarea_transpose.value = '\n'.join(tabs_clear).strip('\n')


if __name__ == '__main__':
    load_tabs()

    RadiantServer(
        'StylophoneAssistant',
        host='0.0.0.0',
        template='template.html',
        page_title="Stylophone Assistant",
        static_app='docs',
        domain=domain,
        # domain='/stylophone-assistant',
    )
