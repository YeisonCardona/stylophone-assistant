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

# ----------------------------------------------------------------------
# With the switch in position 2 on the S-1 and no octave modifier on the X-1
# Assumes that the central octave of S-1 corresponds to the first octave of X-1
note_equivalence_mode1 = {
    # tab(S-1): (tab X-1, octave modifier)
    # Notes from the 3rd octave (Require modifier as they are not present on X-1)
    "1": ("8", "-1"),
    "1.5": ("8.5", "-1"),
    "2": ("9", "-1"),
    # Notes from the 4th octave
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
    # Notes from the 5th octave
    "10": ("10", "0"),
    "10.5": ("10.5", "0"),
    "11": ("11", "0"),
    "11.5": ("11.5", "0"),
    "12": ("12", "0"),
    # Notes from the 5th octave not present on S-1
    "13": ("13", "0"),
    "13.5": ("13.5", "0"),
    "14": ("14", "0"),
    "14.5": ("14.5", "0"),
    "15": ("15", "0"),
    "15.5": ("15.5", "0"),
    "16": ("16", "0"),
}

# ----------------------------------------------------------------------
# With the switch in position 2 on the S-1 and no octave modifier on the X-1
# Assumes that the central octave of S-1 corresponds to the second octave of X-1
# By default, this implies a modifier of -1
note_equivalence_mode2 = {
    # Notes from the 3rd octave
    "1": ("1", "0"),
    "1.5": ("1.5", "0"),
    "2": ("2", "0"),
    # Notes from the 4th octave
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
    # Notes from the 5th octave not available in this X-1 configuration
    "10": ("3", "-2"),
    "10.5": ("3.5", "-2"),
    "11": ("4", "-2"),
    "11.5": ("4.5", "-2"),
    "12": ("5", "-2"),
}


# ----------------------------------------------------------------------
def convert_sequence(sequence: str, equivalence: dict, modifier: str) -> str:
    """
    Converts a sequence of musical notes into a modified format based on a mapping
    of equivalences and an octave modifier.

    Parameters
    ----------
    sequence : str
        A string representing a sequence of musical notes separated by spaces.
    equivalence : dict
        A dictionary where keys are note strings and values are tuples containing
        the note's position and its octave (e.g., {'C': ('1', '4')}).
    modifier : str
        A string representing the octave modification. For example, '-1' decreases
        the octave by one.

    Returns
    -------
    str
        The converted sequence as a string where each note is replaced based on
        the equivalence mapping and modified according to the octave.
    """
    notes = sequence.split(' ')
    converted_sequence = []

    for note in notes:
        if note in equivalence:
            position, octave = equivalence[note]

            # Modify octave based on the given modifier
            if modifier == '-1':
                octave = str(
                    int(octave) + int(modifier) - 1
                )  # PSS: Adjusted calculation logic

            if octave == '0':
                converted_sequence.append(f"{position}")
            else:
                converted_sequence.append(f"({octave}:{position})")
        else:
            # Append notes not in equivalence as they are
            converted_sequence.append(note)

    return " ".join(converted_sequence)


# ----------------------------------------------------------------------
def load_tabs() -> None:
    """
    Loads all `.txt` files from the 'tabs' directory, reads their content,
    and stores them in a dictionary. The dictionary is then saved as a
    JSON file named `tabs.json` in the same directory.

    Raises
    ------
    FileNotFoundError
        If the 'tabs' directory does not exist.

    Notes
    -----
    The resulting JSON file will have filenames as keys and their respective
    file contents as values.
    """
    import os
    import json

    # Ensure the 'tabs' directory exists
    if not os.path.exists('tabs'):
        raise FileNotFoundError("The 'tabs' directory does not exist.")

    # Retrieve and sort all files in the 'tabs' directory
    files = sorted(os.listdir('tabs'))

    tabs = {}
    for filename in filter(lambda f: f.endswith('.txt'), files):
        # Read the content of each `.txt` file and store it in the dictionary
        with open(os.path.join('tabs', filename), 'r') as file:
            tabs[filename] = file.read()

    # Write the dictionary to `tabs.json` with pretty formatting
    with open(os.path.join('tabs', 'tabs.json'), 'w') as file:
        json.dump(tabs, file, indent=2)


# ----------------------------------------------------------------------
def decompress_multiline_text(text: str) -> str:
    """
    Decompresses text containing patterns in the form '(content)xN' or '(content) xN',
    including cases where the content spans multiple lines.

    Parameters
    ----------
    text : str
        The input text containing patterns to be decompressed.

    Returns
    -------
    str
        The decompressed text with patterns expanded.
    """
    lines = text.split("\n")
    result = []
    buffer = []  # Buffer to handle multiline content

    for line in lines:
        # Detect the start of a multiline pattern
        if "(" in line and ")" not in line:
            buffer.append(line.strip())
            continue
        elif buffer or ")" in line:
            buffer.append(line.strip())

            if ")" not in line:
                continue

            # Combine buffered lines
            multiline_content = "\n".join(buffer)
            buffer = []  # Clear buffer

            # Find and expand multiline patterns
            patterns = re.findall(r'\((.*?)\)\s*x(\d+)', multiline_content, re.DOTALL)
            for content, repetitions in patterns:
                content_lines = content.strip().split("\n")
                for _ in range(int(repetitions)):
                    if len(content.split('\n')) > 1 and (_ < int(repetitions) - 1):
                        result.extend(content_lines + [''])
                    else:
                        result.extend(content_lines)

            # Remove processed patterns and add any extra text
            remaining_text = re.sub(
                r'\(.*?\)\s*x\d+', '', multiline_content, flags=re.DOTALL
            ).strip()
            if remaining_text:
                result.append(remaining_text)
            continue

        # Process single-line patterns '(...)xN'
        patterns = re.findall(r'\((.*?)\)\s*x(\d+)', line)
        if patterns:
            for content, repetitions in patterns:
                content_lines = content.strip().split("\n")
                for _ in range(int(repetitions)):
                    result.extend(content_lines)

            # Remove processed patterns and add any extra text
            remaining_text = re.sub(r'\(.*?\)\s*x\d+', '', line).strip()
            if remaining_text:
                result.append(remaining_text)
        else:
            # Add lines without patterns directly
            result.append(line.strip())

    return "\n".join(result)


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
                        self.select_style <= sl.option("American", value='kids')
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
                        self.textarea_s1.bind("sl-input", self.save_tabs)

            with html.DIV(Class='row', style='margin-top: 20px;').context(
                container
            ) as row:

                with html.DIV(Class='col-md-3', style='margin-top: 15px;').context(
                    row
                ) as col:
                    self.switch_transpose = sl.switch("Transpose Tabs (Chromatic)")
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
                            label="Transposed Tabs",
                            resize="auto",
                            spellcheck="false",
                        )
                    ).context(col) as self.textarea_transpose:
                        self.textarea_transpose.bind("sl-input", self.save_tabs)
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
                        sl.icon_button(name="play-circle", style="font-size: 3rem;")
                    ).context(col) as self.button_start:
                        self.button_start.bind("click", self.start_animation)

                    with html(
                        sl.icon_button(name="stop-circle", style="font-size: 3rem;")
                    ).context(col) as self.button_stop:
                        self.button_stop.bind("click", self.stop_animation)
                        self.button_stop.attrs['disabled'] = True

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
                            style="  --track-color-active: var(--sl-color-primary-600);  --track-color-inactive: var(--sl-color-primary-100);margin-top: 20px;",
                        )
                    ).context(col) as self.range_progress:
                        self.range_progress.tooltipFormatter = (
                            lambda value: f"Tab {value + 1}"
                        )
                        self.range_progress.bind("sl-input", self.range_progress_change)

        timer.set_timeout(self.initialize, 500)

    # ----------------------------------------------------------------------
    def initialize(self) -> None:
        """
        Initializes the application by setting up the initial state and loading necessary resources.

        This method sets up the internal state variables, populates the textarea
        with stored or default tabs, updates the tabs preview, and loads the
        stylophone and tabs for the application.

        Returns
        -------
        None
        """
        # Mark the application as loaded
        self.loaded = True

        # Initialize counters for S-1 and X-1
        self.counter_s1 = 0
        self.counter_x1 = 0

        # Load stored tabs into the textarea or use default tabs
        self.textarea_s1.value = storage.get('tabs', default_tabs)

        # Update the tabs preview
        self.update_tabs_preview()

        # Load the stylophone SVG and tabs
        self.load_stylophone(generation='x1', style='tabs', x1_octave_modifier='')
        self.load_tabs()

    # ----------------------------------------------------------------------
    @property
    def normalized_tabs(self) -> str:
        """
        Normalizes the tabs from the textarea by decompressing, removing comments,
        and cleaning up unwanted characters.

        This method processes the tabs entered in `textarea_s1`, removing comments,
        decompressing multiline patterns, and eliminating extra spaces or unwanted
        characters. The result is a cleaned-up, normalized string of tabs.

        Returns
        -------
        str
            A normalized string of tabs, free of comments, unwanted characters,
            and extra spaces.
        """
        # Get tabs from the textarea and decompress multiline patterns
        tabs = self.textarea_s1.value
        tabs = decompress_multiline_text(tabs)

        # Remove comments from each line
        tabs_decomented = []
        for line in tabs.split('\n'):
            if '#' in line:
                tabs_decomented.append(line[: line.find('#')])  # Exclude comments
            else:
                tabs_decomented.append(line)

        # Join lines with a consistent newline format
        tabs = ' \n '.join(tabs_decomented)

        # Remove unwanted characters defined in `ignore_chars`
        for char in ignore_chars:
            tabs = tabs.replace(char, ' ')

        # Clean up extra spaces in each line
        tabs_clear = []
        for line in tabs.split('\n'):
            tabs_clear.append(' '.join(line.split()))  # Normalize spaces

        # Return the cleaned-up and normalized tabs
        return '\n'.join(tabs_clear).strip('\n')

    # ----------------------------------------------------------------------
    @property
    def equivalence_table(self) -> dict:
        """
        Returns the appropriate note equivalence table based on the state
        of the `switch_x1_8va`.

        If the `switch_x1_8va` is checked, it uses `note_equivalence_mode2`.
        Otherwise, it defaults to `note_equivalence_mode1`.

        Returns
        -------
        dict
            The selected note equivalence table (`note_equivalence_mode1` or
            `note_equivalence_mode2`).
        """
        if self.switch_x1_8va.checked:
            return note_equivalence_mode2
        else:
            return note_equivalence_mode1

    # ----------------------------------------------------------------------
    def save_tabs(self, event=None):
        """
        Saves the current tabs and updates the UI elements accordingly.

        If the `select_tab` widget is set to 'custom', it saves the value from
        the `textarea_s1` widget into the `storage` under the 'tabs' key.
        Resets counters for S-1 and X-1 tabs, updates the tabs preview, and
        adjusts the range of the progress bar.

        Parameters
        ----------
        event : optional
            The triggering event, if applicable. Defaults to None.

        Returns
        -------
        None
        """
        if self.select_tab.value == 'custom':
            storage['tabs'] = self.textarea_s1.value

        # Reset counters
        self.counter_s1 = 0
        self.counter_x1 = 0

        # Update the tabs preview
        self.update_tabs_preview()

        # Adjust the progress bar range
        self.range_progress.min = 0
        self.range_progress.max = len(self.normalized_tabs.split(' ')) - 1

        # Debug information
        print("Input tabs:", self.textarea_s1.value)
        print("Normalized tabs:", self.normalized_tabs)
        print('S-1 tabs:', ' '.join(self.s1_tabs))
        print('X-1 tabs:', ' '.join(self.x1_tabs))

    # ----------------------------------------------------------------------
    def range_progress_change(self, event) -> None:
        """
        Handles the change event for the progress range slider.

        Updates the `counter_s1` and `counter_x1` attributes based on the current
        value of the slider, and refreshes the tabs preview accordingly.

        Parameters
        ----------
        event : object
            The event object containing the `target.value` attribute, which represents
            the new slider position.

        Returns
        -------
        None
        """
        # Update counters for S-1 and X-1 based on the slider's value
        self.counter_s1 = event.target.value
        self.counter_x1 = event.target.value

        # Refresh the tabs preview
        self.update_tabs_preview()

    # ----------------------------------------------------------------------
    def update_tabs_preview(self) -> None:
        """
        Updates the preview of tabs based on the current state of switches,
        counters, and user selections.

        This method dynamically generates the preview content for both S-1
        and X-1 tabs depending on the transpose switch, the equivalence table,
        and the selected generator. It adjusts the pre-, current-, and post-tab
        spans accordingly.

        Returns
        -------
        None
        """
        if self.switch_transpose.checked:
            # Update tabs with transpose applied
            self.update_transposed_tabs()
            self.s1_tabs = self.textarea_transpose.value.split(' ')
            self.x1_tabs = convert_sequence(
                self.textarea_transpose.value,
                self.equivalence_table,
                '-1' if self.switch_x1_8va.checked else '0',
            ).split(' ')
        else:
            # Use normalized tabs without transpose
            self.s1_tabs = self.normalized_tabs.split(' ')
            self.x1_tabs = convert_sequence(
                self.normalized_tabs,
                self.equivalence_table,
                '-1' if self.switch_x1_8va.checked else '0',
            ).split(' ')

        # Update tab spans based on the selected model
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
    def start_animation(self, event) -> None:
        """
        Starts the animation based on the selected generator (S-1, X-1, or both).

        This method initializes the animation by enabling/disabling buttons,
        setting counters, updating the tab preview, and calling the appropriate
        animation methods for the selected generator.

        Parameters
        ----------
        event : object
            The triggering event object, typically passed when the button is clicked.

        Returns
        -------
        None
        """
        # Initialize the animation state
        self.stop = False

        # Disable the start button and enable the stop button
        self.button_start.attrs['disabled'] = True
        del self.button_stop.attrs['disabled']

        # Set counters based on the current slider position
        self.counter_s1 = self.range_progress.value
        self.counter_x1 = self.range_progress.value

        # Update the tab preview
        self.update_tabs_preview()

        # Start the animation based on the selected model
        match self.select_gen.value:
            case 's1':
                self.animate_s1()
            case 'x1':
                self.animate_x1()
            case 'both':
                self.animate_s1()
                self.animate_x1()

    # ----------------------------------------------------------------------
    def stop_animation(self, event) -> None:
        """
        Stops the currently running animation.

        This method sets the `stop` attribute to `True` to signal the
        termination of the animation. It disables the stop button and
        re-enables the start button to allow restarting the animation.

        Parameters
        ----------
        event : object
            The triggering event object, typically passed when the button is clicked.

        Returns
        -------
        None
        """
        # Set the stop flag to True
        self.stop = True

        # Disable the stop button and enable the start button
        self.button_stop.attrs['disabled'] = True
        del self.button_start.attrs['disabled']

    # ----------------------------------------------------------------------
    def load_stylophone(
        self, event=None, generation=None, style=None, x1_octave_modifier=None
    ) -> None:
        """
        Loads the appropriate Stylophone SVG based on the selected generation, style,
        and octave modifier.

        This method constructs the URL for the Stylophone asset and sends an AJAX
        GET request to fetch it. If the `event` parameter is provided, the method
        will determine the generation, style, and octave modifier from the respective
        UI elements.

        Parameters
        ----------
        event : optional
            The triggering event object, if applicable. Defaults to None.
        generation : str, optional
            The generation to load ('s1', 'x1', or 'both'). Defaults to the value
            of `select_gen` if `event` is provided.
        style : str, optional
            The style of the Stylophone. Defaults to the value of `select_style`
            if `event` is provided.
        x1_octave_modifier : str, optional
            The octave modifier for X-1. Defaults to '-1' if the switch is checked,
            or an empty string otherwise.

        Returns
        -------
        None
        """
        if not self.loaded:
            return

        # Retrieve parameters from UI elements if an event is provided
        if event:
            generation = self.select_gen.value
            style = self.select_style.value
            x1_octave_modifier = '-1' if self.switch_x1_8va.checked else ''

        # Override X-1 octave modifier if the generation is 's1'
        if generation == 's1':
            x1_octave_modifier = ''

        # Construct and send the AJAX request
        req = ajax.ajax()
        req.bind('complete', self.on_complete_load_stylophone)
        req.open(
            'GET',
            f'{domain}/root/assets/stylophone_{generation}_{style}{x1_octave_modifier}.svg',
            True,
        )
        req.send()

    # ----------------------------------------------------------------------
    def on_complete_load_stylophone(self, req) -> None:
        """
        Handles the completion of the AJAX request to load the Stylophone SVG.

        This method processes the SVG response, updates the UI elements, adjusts
        the SVG's attributes for proper scaling, and highlights specific buttons
        if they exist. If the X-1 octave switch is active, additional adjustments
        are applied.

        Parameters
        ----------
        req : object
            The AJAX response object containing the HTTP status and response text.

        Returns
        -------
        None
        """
        if req.status == 200:
            # Inject the SVG into the container
            self.svg_container.innerHTML = req.responseText
            self.svg_container.style.width = "100%"

            # Adjust SVG attributes for responsive behavior
            svg_element = document.select("svg")[0]
            svg_element.setAttribute("width", "100%")
            svg_element.setAttribute("preserveAspectRatio", "xMidYMid meet")

            # Highlight specific buttons if they exist
            try:
                document["tab_sm2"].style.fill = button_active
            except Exception:
                pass

            if self.switch_x1_8va.checked:
                try:
                    document["tab_xm1"].style.fill = button_active
                except Exception:
                    pass

            # Save tabs after successful SVG load
            self.save_tabs()

    # ----------------------------------------------------------------------
    def load_tabs(self) -> None:
        """
        Initiates an AJAX request to load the available tabs from a JSON file.

        This method sends a GET request to fetch the `tabs.json` file from the server.
        Upon completion, it triggers the `on_complete_load_tabs` method to process
        the response.

        Returns
        -------
        None
        """
        req = ajax.ajax()
        req.bind('complete', self.on_complete_load_tabs)
        req.open('GET', f'{domain}/root/tabs/tabs.json', True)
        req.send()

    # ----------------------------------------------------------------------
    def on_complete_load_tabs(self, req) -> None:
        """
        Processes the server's response to populate the tabs selection dropdown.

        This method parses the JSON response containing tabs, creates `<option>`
        elements for each tab, and appends them to the `select_tab` element.

        Parameters
        ----------
        req : object
            The AJAX response object containing the HTTP status and JSON data.

        Returns
        -------
        None
        """
        if req.status == 200:
            # Parse JSON response
            tabs = req.json

            # Create and populate dropdown options
            for i, tab in enumerate(tabs):
                option = sl.option(
                    tab.replace('.txt', ''),  # Remove the file extension for display
                    value=f'tab-{i}',  # Unique value for each option
                    id=f'id-tab-{i}',  # Unique ID for each option
                )
                option.attrs['tabs'] = tabs[
                    tab
                ]  # Store tab content in the 'tabs' attribute
                self.select_tab <= option  # Append option to the dropdown

    # ----------------------------------------------------------------------
    def load_tab_in_textarea(self, event) -> None:
        """
        Loads the selected tab content into the textarea for editing or display.

        This method determines the selected tab from the event, retrieves its
        content, and populates the `textarea_s1` element. If the "custom" option
        is selected, it loads stored custom tabs or a default value. Additionally,
        it saves the current tab content and updates transposed tabs if required.

        Parameters
        ----------
        event : object
            The triggering event object, containing the selected tab value in
            `event.target.value`.

        Returns
        -------
        None
        """
        # Retrieve the selected tab value
        tab = event.target.value

        if tab == 'custom':
            # Load custom tabs from storage or default value
            self.textarea_s1.value = storage.get('tabs', default_tabs)
        else:
            # Retrieve tab content from the selected option
            option = document[f'id-{tab}']
            self.textarea_s1.value = option.attrs['tabs']

        # Save the current tab content
        self.save_tabs()

        # Update transposed tabs if the transpose switch is enabled
        if self.switch_transpose.checked:
            self.update_transposed_tabs()

    # ----------------------------------------------------------------------
    def clear(self, tab: str) -> None:
        """
        Resets the style of the specified SVG element to its default state.

        This method modifies the `fill` style of the SVG element identified by the
        `tab` parameter, setting it to the base button color.

        Parameters
        ----------
        tab : str
            The identifier of the SVG element to reset.

        Returns
        -------
        None
        """
        svg_element = document[tab]
        svg_element.style.fill = button_base

    # ----------------------------------------------------------------------
    def active(self, tab: str) -> None:
        """
        Sets the style of the specified SVG element to indicate an active state.

        This method modifies the `fill` style of the SVG element identified by the
        `tab` parameter, setting it to the active button color.

        Parameters
        ----------
        tab : str
            The identifier of the SVG element to activate.

        Returns
        -------
        None
        """
        svg_element = document[tab]
        svg_element.style.fill = button_active

    # ----------------------------------------------------------------------
    def animate_s1(self) -> None:
        """
        Animates the S-1 tabs sequence, highlighting and clearing each tab in turn.

        This method iterates through the `s1_tabs` sequence, updating the
        visual representation on the SVG element and advancing the counter.
        The animation stops if the `stop` flag is set or when the sequence ends.

        Returns
        -------
        None
        """
        try:
            # Retrieve the current tab based on the counter
            tab = self.s1_tabs[self.counter_s1]
        except IndexError:
            # Stop animation if the counter exceeds the sequence length
            return

        # Update the tab preview
        self.update_tabs_preview()
        self.counter_s1 += 1
        self.range_progress.value = self.counter_s1

        # Check if the tab is a valid number, highlight it if so
        if tab.replace('.', '').isdigit():
            svg_element = document[f"tab_s{tab.replace('.', '_')}"]
            svg_element.style.fill = button_active
        else:
            # Skip invalid tabs and recursively call the animation
            return self.animate_s1()

        # Schedule a timeout to clear the tab after a delay
        timer.set_timeout(
            lambda: self.clear(f"tab_s{tab.replace('.', '_')}"),
            float(self.select_delay.value) * 0.7,
        )

        # Continue animation if not stopped
        if not self.stop:
            timer.set_timeout(self.animate_s1, float(self.select_delay.value))
        else:
            # Reset the progress bar when animation stops
            self.range_progress.value = 0

    # ----------------------------------------------------------------------
    def animate_x1(self) -> None:
        """
        Animates the X-1 tabs sequence, highlighting and clearing each tab in turn.

        This method iterates through the `x1_tabs` sequence, updating the
        visual representation on the SVG element and advancing the counter.
        It handles octave modifiers (`-1`, `-2`) and ensures correct highlighting
        and clearing of the respective elements. The animation stops if the
        `stop` flag is set or when the sequence ends.

        Returns
        -------
        None

        Notes
        -----
        - Assumes the existence of attributes `x1_tabs`, `counter_x1`, `range_progress`,
          and `stop`.
        - Handles octave modifiers `-1` and `-2` separately.
        - Uses `select_gen` to determine if X-1 is the active generator.
        - Assumes methods like `clear` and `update_tabs_preview` exist and are functional.

        Examples
        --------
        >>> obj = YourClass()
        >>> obj.animate_x1()  # Starts animating the X-1 tabs sequence
        """
        try:
            # Retrieve the current tab based on the counter
            tab = self.x1_tabs[self.counter_x1]
        except IndexError:
            # Stop animation if the counter exceeds the sequence length
            return

        # Update preview and progress for X-1 generator
        if self.select_gen.value == 'x1':
            self.update_tabs_preview()
            self.counter_x1 += 1
            self.range_progress.value = self.counter_x1
        else:
            self.counter_x1 += 1

        # Check if the tab is valid, accounting for octave modifiers
        if (
            tab.strip('()')
            .replace('-1:', '')
            .replace('-2:', '')
            .replace('.', '')
            .isdigit()
        ):
            if '-1' in tab:
                # Handle octave -1
                tab = tab.strip('()').replace('-1:', '')
                svg_element = document[f"tab_x{tab.replace('.', '_')}"]
                document["tab_xm1"].style.fill = button_active
                self.clear("tab_xm2")

            elif '-2' in tab:
                # Handle octave -2
                tab = tab.strip('()').replace('-2:', '')
                svg_element = document[f"tab_x{tab.replace('.', '_')}"]
                document["tab_xm2"].style.fill = button_active
                self.clear("tab_xm1")

            else:
                # Handle normal tabs
                tab = tab.strip('()')
                svg_element = document[f"tab_x{tab.replace('.', '_')}"]

            # Highlight the current tab
            svg_element.style.fill = button_active
        else:
            # Skip invalid tabs and recursively call the animation
            return self.animate_x1()

        # Schedule a timeout to clear the tab after a delay
        timer.set_timeout(
            lambda: self.clear(f"tab_x{tab.replace('.', '_')}"),
            float(self.select_delay.value) * 0.7,
        )

        # Clear octave indicators if the switch is not enabled
        if not self.switch_x1_8va.checked:
            timer.set_timeout(
                lambda: self.clear("tab_xm1"), float(self.select_delay.value)
            )
        timer.set_timeout(lambda: self.clear("tab_xm2"), float(self.select_delay.value))

        # Continue animation if not stopped
        if not self.stop:
            timer.set_timeout(self.animate_x1, float(self.select_delay.value))
        else:
            # Reset the progress bar when animation stops
            self.range_progress.value = 0

    # ----------------------------------------------------------------------
    def activate_transpose(self, event=None) -> None:
        """
        Toggles the visibility of transpose-related UI elements based on the state
        of the transpose switch.

        If the `event.target.checked` is `False`, the transpose controls are hidden.
        Otherwise, they are displayed, and the transposed tabs are updated.

        Parameters
        ----------
        event : optional
            The triggering event object, which determines the checked state of the
            transpose switch. Defaults to None.

        Returns
        -------
        None
        """
        if not event.target.checked:
            # Hide transpose controls
            self.range_transpose.style.display = 'none'
            self.textarea_transpose.style.display = 'none'
            self.switch_transpose_model.style.display = 'none'
        else:
            # Show transpose controls and update transposed tabs
            self.range_transpose.style.display = 'block'
            self.textarea_transpose.style.display = 'block'
            self.switch_transpose_model.style.display = 'block'
            self.update_transposed_tabs()

    # ----------------------------------------------------------------------
    def update_transposed_tabs(self, event=None) -> None:
        """
        Updates the transposed tabs based on the transpose range value and the selected model.

        This method recalculates the tabs by shifting them up or down according
        to the value of the transpose range slider and the selected scale model.
        The results are displayed in the `textarea_transpose` element.

        Parameters
        ----------
        event : optional
            The triggering event object, if applicable. Defaults to None.

        Returns
        -------
        None
        """
        # Get the transpose value
        value = self.range_transpose.value

        # Select the appropriate scale based on the model switch
        if self.switch_transpose_model.checked:
            scale = "1 1.5 2 3 3.5 4 4.5 5 6 6.5 7 7.5 8 8.5 9 10 10.5 11 11.5 12 13 13.5 14 14.5 15 15.5 16".split()
        else:
            scale = (
                "1 1.5 2 3 3.5 4 4.5 5 6 6.5 7 7.5 8 8.5 9 10 10.5 11 11.5 12".split()
            )

        # Split the normalized tabs into lines
        tabs_lines = self.normalized_tabs.split('\n')
        transposed_tabs = []

        # Process each line of tabs
        for line in tabs_lines:
            for tab in line.split(' '):
                if tab in scale:
                    # Transpose the tab within the scale
                    index = scale.index(tab) + value

                    if index < 0:
                        # Wrap to the next octave up
                        new_tab = f'+1:{scale[index + 12]}'
                    elif 0 <= index < len(scale):
                        # Valid index within the scale
                        new_tab = scale[index]
                    else:
                        # Wrap to the next octave down
                        new_tab = f'-1:{scale[index - 12]}'

                    transposed_tabs.append(new_tab)

                elif tab:
                    # Mark tabs outside the scale as errors
                    transposed_tabs.append(f'E:{tab}')
                else:
                    # Preserve empty spaces
                    transposed_tabs.append(tab)

            # Add a line break after processing each line
            transposed_tabs.append('\n')

        # Clean up transposed tabs to remove extra spaces
        tabs_clear = []
        for line in (' '.join(transposed_tabs)).split('\n'):
            tabs_clear.append(' '.join(line.split()))

        # Update the textarea with the cleaned transposed tabs
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
    )
