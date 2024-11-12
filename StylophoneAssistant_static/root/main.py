from radiant.framework.server import RadiantCore, RadiantServer
from radiant.framework import html, Element
from browser import document, svg, ajax
from browser import timer
from radiant.framework import WebComponents
from browser.local_storage import storage


sl = WebComponents('sl')


button_base = '#B3B3B3'
button_active = '#87DEAA'


equivalencia_notas = {
    # Notas de la 3ª octava (bajadas con -2)
    1: ("8", "-2"),
    1.5: ("8.5", "-2"),
    2: ("9", "-2"),
    # Notas de la 4ª octava (sin cambios, -1)
    3: ("3", "-1"),
    3.5: ("3.5", "-1"),
    4: ("4", "-1"),
    4.5: ("4.5", "-1"),
    5: ("5", "-1"),
    6: ("6", "-1"),
    6.5: ("6.5", "-1"),
    7: ("7", "-1"),
    7.5: ("7.5", "-1"),
    8: ("8", "-1"),
    8.5: ("8.5", "-1"),
    9: ("9", "-1"),
    # Notas de la 5ª octava (sin cambios, -1)
    10: ("10", "-1"),
    10.5: ("10.5", "-1"),
    11: ("11", "-1"),
    11.5: ("11.5", "-1"),
    12: ("12", "-1"),
}


def convertir_secuencia(secuencia):
    """"""
    notas = []
    for nota in secuencia.split():

        if nota.startswith('('):
            notas.append('(')
            try:
                notas.append(nota.strip('()'))
            except:
                pass

        elif nota.endswith(')'):
            try:
                notas.append(nota.strip('()'))
            except:
                pass
            notas.append(')')

        elif nota.startswith('x') or nota.endswith('x'):
            notas.append(nota)

        else:
            try:
                notas.append(float(nota))
            except:
                pass

    secuencia_convertida = []

    for nota in notas:
        if nota in equivalencia_notas:
            genx1_pos, octava = equivalencia_notas[nota]
            if octava == '-1':
                secuencia_convertida.append(f"{genx1_pos}")
            else:
                secuencia_convertida.append(f"({octava}:{genx1_pos})")
        else:
            secuencia_convertida.append(str(nota))

    secuencia_convertida = " ".join(secuencia_convertida)
    secuencia_convertida = secuencia_convertida.replace('( ', '(')
    secuencia_convertida = secuencia_convertida.replace(' )', ')')

    return secuencia_convertida


########################################################################
class StylophoneAssistant(RadiantCore):

    stop = False

    # ----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        """"""
        super().__init__(*args, **kwargs)

        with html.DIV(Class='container').context(self.body) as container:

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-12').context(row) as col:

                    col <= html.H1(
                        'Stylophone Assistant',
                        Class='--sl-font-sans --sl-font-size-2x-large',
                    )

                with html.DIV(Class='col-md-4').context(row) as col:
                    with html(
                        sl.select(pill=True, label="Stylophone", value="x1")
                    ).context(col) as self.select_gen:
                        self.select_gen <= sl.option("Gen S-1", value='s1')
                        self.select_gen <= sl.option("Gen X-1", value='x1')
                        self.select_gen <= sl.option("Both", value='both')
                        self.select_gen.bind("sl-change", self.load_stylophone)

                with html.DIV(Class='col-md-4').context(row) as col:
                    with html(
                        sl.select(pill=True, label="Style", value="tabs")
                    ).context(col) as self.select_style:
                        self.select_style <= sl.option("Tabs", value='tabs')
                        self.select_style <= sl.option("Solfège", value='solfege')
                        self.select_style <= sl.option("Kids", value='kids')
                        self.select_style.bind("sl-change", self.load_stylophone)

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-12').context(row) as col:
                    with html(sl.textarea(label="Tabs")).context(
                        col
                    ) as self.textarea_s1:
                        self.textarea_s1.bind("sl-change", self.textarea_save)

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-8').context(row) as col:
                    self.svg_container = html.DIV()
                    col <= self.svg_container

                with html.DIV(Class='col-md-2').context(row) as col:

                    with html.DIV(Class='button-group-toolbar').context(col) as toolbar:

                        with html(sl.button_group(label="group")).context(
                            toolbar
                        ) as group:

                            with html(sl.tooltip(content="Play")).context(
                                group
                            ) as tooltip:
                                with html(sl.button()).context(tooltip) as button:
                                    button <= sl.icon(
                                        name="play",
                                        label="Play",
                                        style="font-size: 2.5rem; display: flex;",
                                    )
                                    button.bind("click", self.on_button_start)

                            with html(sl.tooltip(content="Stop")).context(
                                group
                            ) as tooltip:
                                with html(sl.button()).context(tooltip) as button:
                                    button <= sl.icon(
                                        name="stop",
                                        label="Stop",
                                        style="font-size: 2.5rem; display: flex;",
                                    )
                                    button.bind("click", self.on_button_stop)

                with html.DIV(Class='col-md-2').context(row) as col:
                    with html(sl.select(pill=True, label="Delay", value="0.5")).context(
                        col
                    ) as self.select_delay:
                        for i in range(100, 5001, 100):
                            self.select_delay <= sl.option(
                                f"{i / 1000 :.1f} s", value=f"{i / 1000 :.1f}"
                            )
                        self.select_delay.bind("sl-change", self.load_stylophone)

            with html.DIV(Class='row').context(container) as row:

                with html.DIV(Class='col-md-4').context(row) as col:

                    with html(
                        sl.range(min="100", max="5000", step=100, value="1000")
                    ).context(col) as self.range_delay:
                        self.range_delay.tooltipFormatter = (
                            lambda value: f"Delay {value / 1000:.1f} s"
                        )

        try:
            self.textarea_s1.value = storage['tabs']
        except:
            pass

        self.load_stylophone(gen='x1', style='tabs')

    # ----------------------------------------------------------------------
    def textarea_save(self, event):
        """"""
        storage['tabs'] = event.target.value

    # ----------------------------------------------------------------------
    def on_button_start(self, event):
        self.stop = False
        # self.progress.value = 0

        self.counter_s1 = 0
        self.counter_x1 = 0

        self.s1_tabs = self.textarea_s1.value.split(' ')
        self.x1_tabs = convertir_secuencia(self.textarea_s1.value).split(' ')

        print(self.x1_tabs)

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
        # self.progress.value = 0

    # ----------------------------------------------------------------------
    def load_stylophone(self, event=None, gen=None, style=None):
        """"""
        if event:
            gen = self.select_gen.value
            style = self.select_style.value

        req = ajax.ajax()
        req.bind('complete', self.on_complete)
        req.open('GET', f'/root/assets/stylophone_{gen}_{style}.svg', True)
        req.send()

    # ----------------------------------------------------------------------
    def on_complete(self, req):
        """"""
        if req.status == 200:

            self.svg_container.innerHTML = req.responseText
            self.svg_container.style.width = "100%"

            svg_element = document.select("svg")[0]
            svg_element.setAttribute("width", "100%")
            svg_element.setAttribute("preserveAspectRatio", "xMidYMid meet")

            try:
                document["tab_xm1"].style.fill = button_active
            except:
                pass
            try:
                document["tab_sm2"].style.fill = button_active
            except:
                pass

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

        self.counter_s1 += 1
        # self.progress.value = 100 * self.counter_x1 / len(self.s1_tabs)

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
        # else:
        # self.progress.value = 0

    # ----------------------------------------------------------------------
    def animate_x1(self):
        """"""

        try:
            tabx_ = self.x1_tabs[self.counter_x1]
        except:
            return

        self.counter_x1 += 1
        # self.progress.value = 100 * self.counter_x1 / len(self.x1_tabs)

        if tabx_.strip('()').replace('-2:', '').replace('.', '').isdigit():

            if '-2' in tabx_:
                tabx_ = tabx_.strip('()').replace('-2:', '')
                svg_element = document[f"tab_x{tabx_.replace('.', '_')}"]
                document["tab_xm2"].style.fill = button_active
                document["tab_xm1"].style.fill = button_base
            else:
                tabx_ = tabx_.strip('()')
                svg_element = document[f"tab_x{tabx_.replace('.', '_')}"]

            svg_element.style.fill = button_active

        else:
            return self.animate_x1()

        timer.set_timeout(
            lambda: self.clear(f"tab_x{tabx_.replace('.', '_')}"),
            float(self.select_delay.value) * 0.7,
        )
        timer.set_timeout(lambda: self.clear("tab_xm2"), float(self.select_delay.value))
        timer.set_timeout(
            lambda: self.active("tab_xm1"), float(self.select_delay.value)
        )

        if not self.stop:
            timer.set_timeout(self.animate_x1, float(self.select_delay.value))
        # else:
        # self.progress.value = 0


if __name__ == '__main__':
    RadiantServer(
        'StylophoneAssistant',
        template='template.html',
        # static_app=True,
        page_title="Stylophone Assistant",
    )
