from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame

style = Style.from_dict({
    'frame.border': '#888888',
    'frame.label': '#0000ff bold',
    '': 'bg:#ffffff #000000',
})

buf1 = Buffer(name='buf1', multiline=True)
buf2 = Buffer(name='buf2', multiline=True)
buf3 = Buffer(name='buf3', multiline=True)

buf1.set_document(Document('Panel 1\nEdit me'))
buf2.set_document(Document('Panel 2\nEdit me'))
buf3.set_document(Document('Panel 3\nEdit me'))

kb = KeyBindings()

@kb.add('tab')
def focus_next(event):
    event.app.layout.focus_next()

@kb.add('s-tab')
def focus_prev(event):
    event.app.layout.focus_previous()

@kb.add('c-q')
def exit(event):
    event.app.exit()

layout = Layout(
    VSplit([
        Frame(Window(BufferControl(buffer=buf1), wrap_lines=False), title='File 1'),
        Frame(Window(BufferControl(buffer=buf2), wrap_lines=False), title='File 2'),
        Frame(Window(BufferControl(buffer=buf3), wrap_lines=False), title='File 3'),
    ])
)

app = Application(layout=layout, key_bindings=kb, style=style, full_screen=True, mouse_support=True)
app.run()
