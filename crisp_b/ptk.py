from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import VSplit, Window, HSplit
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.lexers import Lexer
import re

# ── Console ───────────────────────────────────────────────────────────────────
console_lines = []
console_buf = Buffer(name='console', multiline=True, read_only=True)

def console_write(s):
    console_lines.append(s)
    text = '\n'.join(console_lines)
    console_buf.set_document(Document(text, cursor_position=len(text)), bypass_readonly=True)

def console_clear():
    console_lines.clear()
    console_buf.set_document(Document('', cursor_position=0), bypass_readonly=True)

# ── Value constructors ────────────────────────────────────────────────────────
def mk_int(v):  return ('int',  int(v))
def mk_flt(v):  return ('flt',  float(v))
def mk_str(v):  return ('str',  str(v))
def mk_bool(v): return ('bool', bool(v))
def mk_list(v): return ('list', list(v))
def mk_sym(v):  return ('sym',  v)
def mk_num(v):  return mk_int(v) if isinstance(v, int) or (isinstance(v, float) and v == int(v)) else mk_flt(v)

def val_str(x):
    if x is None: return 'nil'
    t, v = x
    if t == 'list': return '[' + ', '.join(val_str(i) for i in v) + ']'
    if t == 'bool': return 'true' if v else 'false'
    return str(v)

def to_num(x):
    if x is None: return 0
    t, v = x
    if t in ('int', 'flt'): return v
    if t == 'bool': return 1 if v else 0
    try: return float(v)
    except: return 0

def full_deref(x, env):
    seen = set()
    while x is not None and x[0] == 'sym':
        name = x[1]
        if name in seen: break
        seen.add(name)
        nxt = env.get(name)
        if nxt is None: break
        x = nxt
    return x

def popd(stack, env):
    x = stack.pop() if stack else None
    return full_deref(x, env)

# ── Tokenizer ─────────────────────────────────────────────────────────────────
OP_NAMES = {'SET','SETV','SETL','SETL*','SUM','SUB','MUL','DIV','MOD','INC','DEC','APD','LOG','PSTACK','FOR','END'}

def classify_token(tok):
    if tok == 'true':  return ('lit', mk_bool(True))
    if tok == 'false': return ('lit', mk_bool(False))
    if tok == '_':     return ('op', '_')
    if tok == ';':     return ('op', ';')
    if tok == ':':     return ('op', ':')
    if re.match(r'^-?\d+$', tok):      return ('lit', mk_int(int(tok)))
    if re.match(r'^-?\d+\.\d+$', tok): return ('lit', mk_flt(float(tok)))
    if tok in OP_NAMES:                return ('op', tok)
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:$', tok):
        return ('deref', tok[:-1])
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tok): return ('sym', tok)
    return ('unknown', tok)

def tokenize(line):
    s = line.split('//')[0].strip()
    tokens = []
    i = 0
    while i < len(s):
        while i < len(s) and s[i] == ' ': i += 1
        if i >= len(s): break
        if s[i] == '"':
            j = i + 1
            while j < len(s) and s[j] != '"': j += 1
            tokens.append(('lit', mk_str(s[i+1:j])))
            i = j + 1
            continue
        j = i
        while j < len(s) and s[j] != ' ': j += 1
        tokens.append(classify_token(s[i:j]))
        i = j
    return tokens

# ── Syntax Lexer (plugs into BufferControl) ───────────────────────────────────
def lex_raw_line(raw):
    """Returns list of (style_str, text) for one raw source line."""
    result = []
    ci = raw.find('//')
    code_part   = raw[:ci] if ci >= 0 else raw
    comment_part = raw[ci:] if ci >= 0 else ''
    s = code_part
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == ' ': j += 1
        if j > i:
            result.append(('', s[i:j]))
            i = j
            continue
        if s[i] == '"':
            j = i + 1
            while j < len(s) and s[j] != '"': j += 1
            result.append(('class:code.lit', s[i:j+1]))
            i = j + 1
            continue
        j = i
        while j < len(s) and s[j] != ' ': j += 1
        word = s[i:j]
        tok = classify_token(word)
        k = tok[0]
        if k == 'lit':     result.append(('class:code.lit',     word))
        elif k == 'op':    result.append(('class:code.op',      word))
        elif k == 'deref': result.append(('class:code.deref',   word))
        elif k == 'sym':   result.append(('class:code.sym',     word))
        else:              result.append(('class:code.unknown', word))
        i = j
    if comment_part:
        result.append(('class:code.comment', comment_part))
    return result

class StackLexer(Lexer):
    """prompt_toolkit Lexer — lex_document returns a callable(lineno) -> tokens."""
    def lex_document(self, document):
        lines = document.lines
        def get_line(lineno):
            if lineno >= len(lines):
                return []
            return lex_raw_line(lines[lineno])
        return get_line

# ── Parser ────────────────────────────────────────────────────────────────────
def parse_program(src):
    src_lines = src.split('\n')
    prog = []
    for i, raw in enumerate(src_lines):
        trimmed = raw.strip()
        prog.append({'src_idx': i, 'tokens': tokenize(trimmed), 'raw': trimmed,
                     'is_for': False, 'is_end': False, 'end_pc': None, 'for_pc': None})
    for_stack = []
    for i, line in enumerate(prog):
        toks = line['tokens']
        has_for = any(t == ('op','FOR') for t in toks)
        has_end = len(toks) == 1 and toks[0] == ('op','END')
        if has_for:
            for_stack.append(i)
            line['is_for'] = True
        if has_end:
            line['is_end'] = True
            if for_stack:
                fi = for_stack.pop()
                prog[fi]['end_pc'] = i
                line['for_pc'] = fi
    return prog

# ── Styled rt_parts helpers ───────────────────────────────────────────────────
ST_VAL  = 'class:rt.val'
ST_OP   = 'class:rt.op'
ST_SYM  = 'class:rt.sym'
ST_ERR  = 'class:rt.err'
ST_NONE = ''

def rt_val(s):  return (ST_VAL, s)
def rt_op(s):   return (ST_OP,  s)
def rt_sym(s):  return (ST_SYM, s)
def rt_err(s):  return (ST_ERR, s)

def rt_append_op_result(rt, op_name, result_str):
    rt.append(rt_op(op_name))
    if result_str:
        rt.append((ST_NONE, ' '))
        rt.append(rt_val(result_str))

# ── Ops ───────────────────────────────────────────────────────────────────────
def op_set(stack, env, rt):
    nm  = stack.pop() if stack else None
    val = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(rt_err('SET!')); return
    env[nm[1]] = val
    stack.append(nm); rt.append(rt_op('SET'))

def op_setv(stack, env, rt):
    nm  = stack.pop() if stack else None
    val = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(rt_err('SETV!')); return
    val = full_deref(val, env)
    env[nm[1]] = val
    stack.append(nm); rt.append(rt_op('SETV'))

def op_setl(stack, env, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(rt_err('SETL!')); return
    items = list(stack)
    stack.clear()
    env[nm[1]] = mk_list(items)
    stack.append(nm); rt.append(rt_op('SETL'))

def op_sum(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(rt_err('SUM!')); return
    res = mk_num(to_num(a) + to_num(b))
    stack.append(res); rt_append_op_result(rt, 'SUM', val_str(res))

def op_sub(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(rt_err('SUB!')); return
    res = mk_num(to_num(a) - to_num(b))
    stack.append(res); rt_append_op_result(rt, 'SUB', val_str(res))

def op_mul(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(rt_err('MUL!')); return
    res = mk_num(to_num(a) * to_num(b))
    stack.append(res); rt_append_op_result(rt, 'MUL', val_str(res))

def op_div(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None or to_num(b) == 0: rt.append(rt_err('DIV!')); return
    res = mk_num(to_num(a) / to_num(b))
    stack.append(res); rt_append_op_result(rt, 'DIV', val_str(res))

def op_mod(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(rt_err('MOD!')); return
    res = mk_int(int(to_num(a)) % int(to_num(b)))
    stack.append(res); rt_append_op_result(rt, 'MOD', val_str(res))

def op_inc(stack, env, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(rt_err('INC!')); return
    cur = env.get(nm[1], mk_int(0))
    env[nm[1]] = mk_num(to_num(cur) + 1)
    stack.append(env[nm[1]]); rt.append(rt_op('INC'))

def op_dec(stack, env, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(rt_err('DEC!')); return
    cur = env.get(nm[1], mk_int(0))
    env[nm[1]] = mk_num(to_num(cur) - 1)
    stack.append(env[nm[1]]); rt.append(rt_op('DEC'))

def op_apd(stack, env, rt):
    list_nm = stack.pop() if stack else None
    val = stack.pop() if stack else None
    if not list_nm or list_nm[0] != 'sym': rt.append(rt_err('APD!')); return
    if list_nm[1] not in env or env[list_nm[1]][0] != 'list':
        env[list_nm[1]] = mk_list([])
    env[list_nm[1]][1].append(val)
    stack.append(list_nm); rt.append(rt_op('APD'))

def op_log(stack, env, rt):
    val = stack.pop() if stack else None
    if val is None: rt.append(rt_err('LOG!')); return
    resolved = full_deref(val, env)
    console_write(val_str(resolved))
    rt.append(rt_op('LOG'))

def op_pstack(stack, env, rt):
    console_write('STACK: ' + ' '.join(val_str(x) for x in stack))
    rt.append(rt_op('PSTACK'))

def op_deref_op(stack, env, rt):
    top = stack.pop() if stack else None
    if top is None: rt.append(rt_err(':!')); return
    if top[0] == 'sym':
        val = env.get(top[1], top)
        stack.append(val)
        rt.append(rt_val(val_str(val)))
    else:
        stack.append(top)
        rt.append(rt_val(val_str(top)))

def op_underscore(stack, env, rt):
    top = stack.pop() if stack else None
    if top is None: rt.append(rt_err('_!')); return
    stack.append(top)
    rt.append(rt_val(val_str(top)))

OP_MAP = {
    'SET':   op_set,   'SETV': op_setv,  'SETL': op_setl, 'SETL*': op_setl,
    'SUM':   op_sum,   'SUB':  op_sub,   'MUL':  op_mul,  'DIV':   op_div,  'MOD': op_mod,
    'INC':   op_inc,   'DEC':  op_dec,   'APD':  op_apd,
    'LOG':   op_log,   'PSTACK': op_pstack,
    ':':     op_deref_op,
    '_':     op_underscore,
}

# ── Execution ─────────────────────────────────────────────────────────────────
def make_state(src):
    prog = parse_program(src)
    display = [{'rt_parts': [], 'stack_snap': [], 'visited': False} for _ in prog]
    return {'prog': prog, 'display': display, 'pc': 0, 'op_idx': 0,
            'stack': [], 'env': {}, 'loop_stack': [], 'done': False}

def step_one_op(S):
    prog = S['prog']
    while S['pc'] < len(prog):
        if not prog[S['pc']]['tokens']:
            S['display'][S['pc']]['visited'] = True
            S['display'][S['pc']]['rt_parts'] = []
            S['display'][S['pc']]['stack_snap'] = []
            S['pc'] += 1; S['op_idx'] = 0; S['stack'] = []
        else:
            break
    if S['pc'] >= len(prog):
        S['done'] = True; return False

    line = prog[S['pc']]
    disp = S['display'][S['pc']]
    if S['op_idx'] == 0:
        disp['rt_parts'] = []; disp['stack_snap'] = []
    disp['visited'] = True

    if S['op_idx'] >= len(line['tokens']):
        disp['stack_snap'] = list(S['stack'])
        S['pc'] += 1; S['op_idx'] = 0; S['stack'] = []
        return True

    tok = line['tokens'][S['op_idx']]
    rt = []
    jumped = False

    if tok == ('op', 'FOR'):
        var_tok = S['stack'].pop() if S['stack'] else None
        step_v = to_num(popd(S['stack'], S['env']))
        to_v   = to_num(popd(S['stack'], S['env']))
        from_v = to_num(popd(S['stack'], S['env']))
        if not var_tok or var_tok[0] != 'sym':
            rt.append(rt_err('FOR!'))
        else:
            S['env'][var_tok[1]] = mk_num(from_v)
            S['loop_stack'].append({'var': var_tok[1], 'to': to_v, 'step': step_v,
                                    'for_pc': S['pc'], 'end_pc': line['end_pc']})
            rt.append(rt_op('FOR'))
            if (step_v > 0 and from_v > to_v) or (step_v < 0 and from_v < to_v):
                S['pc'] = line['end_pc'] + 1; S['op_idx'] = 0; S['stack'] = []; jumped = True
        disp['rt_parts'].extend(rt)
        if not jumped: S['op_idx'] += 1
        disp['stack_snap'] = list(S['stack'])
        return True

    if tok == ('op', 'END'):
        if not S['loop_stack']:
            rt.append(rt_err('END!'))
            disp['rt_parts'].extend(rt)
            S['op_idx'] += 1
            disp['stack_snap'] = list(S['stack'])
            return True
        loop = S['loop_stack'][-1]
        cur = to_num(S['env'].get(loop['var'], mk_int(0))) + loop['step']
        S['env'][loop['var']] = mk_num(cur)
        cont = (cur <= loop['to']) if loop['step'] > 0 else (cur >= loop['to'])
        if cont:
            S['pc'] = loop['for_pc'] + 1; S['op_idx'] = 0; S['stack'] = []
        else:
            S['loop_stack'].pop(); S['pc'] += 1; S['op_idx'] = 0; S['stack'] = []
        rt.append(rt_op('END'))
        disp['rt_parts'].extend(rt)
        disp['stack_snap'] = list(S['stack'])
        return True

    exec_tok(tok, S['stack'], S['env'], rt)
    disp['rt_parts'].extend(rt)
    S['op_idx'] += 1
    if S['op_idx'] >= len(line['tokens']):
        disp['stack_snap'] = list(S['stack'])
        S['pc'] += 1; S['op_idx'] = 0; S['stack'] = []
    else:
        disp['stack_snap'] = list(S['stack'])
    return True

def exec_tok(tok, stack, env, rt):
    kind = tok[0]
    if kind == 'lit':
        stack.append(tok[1]); rt.append(rt_val(val_str(tok[1]))); return
    if kind == 'sym':
        stack.append(mk_sym(tok[1])); rt.append(rt_sym(tok[1])); return
    if kind == 'deref':
        val = full_deref(mk_sym(tok[1]), env)
        stack.append(val); rt.append(rt_val(val_str(val))); return
    if kind == 'unknown':
        rt.append(rt_err(tok[1] + '?')); return
    op = tok[1]
    handler = OP_MAP.get(op)
    if handler: handler(stack, env, rt); return
    rt.append(rt_err(op + '?'))

# ── UI state ──────────────────────────────────────────────────────────────────
state = {'S': None, 'status': 'Ready.'}
focused_panel = [0]
panel_widths  = [46, 32, 12, 16]
PANEL_MIN     = 6
PANEL_NAMES   = ['Code', 'Runtime', 'Stack', 'Vars']
HELP_TEXT     = 'F5=Run  F6=StepLine  F7=StepOp  F8=Reset  Tab=panel  Alt+/-=width  Ctrl+Q=quit'

DEMO = """5 x SET
x y SETV
x: LOG
y: LOG

// fib with sum
0 a SET
1 b SET
0 s SET
a: b: flist SETL
0 13 1 i FOR
    a: b: SUM _ c SET
    c: flist APD
    c: s: SUM _ s SET
    b a SETV
    c b SETV
END
s: LOG
flist: LOG"""

code_buf = Buffer(name='code', multiline=True)
code_buf.set_document(Document(DEMO))

# ── Panel text getters ────────────────────────────────────────────────────────
def get_runtime_text():
    S = state['S']
    result = []
    src_lines = code_buf.text.split('\n')
    if S is None:
        for raw in src_lines:
            result.extend(lex_raw_line(raw))
            result.append(('', '\n'))
    else:
        for i, line in enumerate(S['prog']):
            disp = S['display'][i]
            if disp['rt_parts']:
                parts = list(disp['rt_parts'])
            elif not disp['visited']:
                parts = lex_raw_line(line['raw'])
            else:
                parts = []
            spaced = []
            for idx, p in enumerate(parts):
                spaced.append(p)
                if idx < len(parts) - 1:
                    spaced.append(('', ' '))
            result.extend(spaced)
            result.append(('', '\n'))
    return result

def get_stack_text():
    S = state['S']
    if S is None: return [('', '')]
    result = []
    for i in range(len(S['prog'])):
        snap_str = ' '.join(val_str(x) for x in S['display'][i]['stack_snap'])
        result.append(('', snap_str + '\n'))
    return result

def get_vars_text():
    S = state['S']
    if S is None: return [('', '')]
    result = []
    for k, v in S['env'].items():
        result.append(('class:vars.key', k))
        result.append(('', '='))
        result.append(('class:rt.val', val_str(v)))
        result.append(('', '\n'))
    return result

def get_status_text():
    p = focused_panel[0]
    msg  = ' ' + state['status'] + '  [' + PANEL_NAMES[p] + ':' + str(panel_widths[p]) + ']'
    return [('class:status.msg', msg), ('class:status.help', '  ' + HELP_TEXT + ' ')]

def set_status(s): state['status'] = s

# ── Execution helpers ─────────────────────────────────────────────────────────
def ensure_state():
    if state['S'] is None:
        state['S'] = make_state(code_buf.text)

def do_run():
    console_clear()
    state['S'] = make_state(code_buf.text)
    S = state['S']
    limit = 2_000_000
    while not S['done'] and limit > 0:
        step_one_op(S); limit -= 1
    set_status('Done.' if limit > 0 else 'ERR: step limit')

def do_step_line():
    ensure_state()
    S = state['S']
    if S['done']: set_status('Done.'); return
    start_pc = S['pc']
    limit = 100_000
    while not S['done'] and S['pc'] == start_pc and limit > 0:
        step_one_op(S); limit -= 1
    set_status('pc=' + str(S['pc']))

def do_step_op():
    ensure_state()
    S = state['S']
    step_one_op(S)
    set_status('Done.' if S['done'] else 'pc=' + str(S['pc']) + ' op=' + str(S['op_idx']))

def do_reset():
    state['S'] = None
    console_clear()
    set_status('Reset.')

# ── Style ─────────────────────────────────────────────────────────────────────
style = Style.from_dict({
    '':               'bg:#f8f8f8 #222222',
    'code.lit':       '#aa6600',
    'code.op':        '#0055cc bold',
    'code.deref':     '#007700',
    'code.sym':       '#222222',
    'code.comment':   '#999999 italic',
    'code.unknown':   'bg:#ff4444 #ffffff',
    'rt.val':         'bg:#ffee00 #000000',
    'rt.op':          '#0055cc bold',
    'rt.sym':         '#555555',
    'rt.err':         'bg:#ff4444 #ffffff bold',
    'vars.key':       '#007700 bold',
    'panel.title':    '#0055cc bold',
    'panel.title.focused': 'bg:#0055cc #ffffff bold',
    'status.msg':     'bg:#dddddd #333333',
    'status.help':    'bg:#cccccc #555555',
})

# ── Buffers for read-only panels (needed for mouse focus) ─────────────────────
runtime_buf = Buffer(name='runtime', read_only=True)
stack_buf   = Buffer(name='stack',   read_only=True)
vars_buf    = Buffer(name='vars',    read_only=True)
console_buf_ro = console_buf  # already defined above

_PANEL_BUFS = [code_buf, runtime_buf, stack_buf, vars_buf]
_BUF_TO_IDX = {'code': 0, 'runtime': 1, 'stack': 2, 'vars': 3}

# ── Title helper ──────────────────────────────────────────────────────────────
def make_title(idx, name):
    def get():
        focused = focused_panel[0] == idx
        st = 'class:panel.title.focused' if focused else 'class:panel.title'
        marker = '>' if focused else ' '
        return [(st, marker + name + marker)]
    return FormattedTextControl(get, focusable=False)

# ── Layout ────────────────────────────────────────────────────────────────────
def pw(i): return D(preferred=panel_widths[i], min=PANEL_MIN)

# Code: BufferControl with our custom Lexer — editing + highlighting in one.
col0 = HSplit([
    Window(make_title(0, 'Code'), height=1),
    Window(
        BufferControl(buffer=code_buf, lexer=StackLexer(), focusable=True),
        wrap_lines=False,
    ),
], width=lambda: pw(0))

# Runtime: FormattedTextControl (read-only display) + thin focusable strip.
col1 = HSplit([
    Window(make_title(1, 'Runtime'), height=1),
    Window(FormattedTextControl(get_runtime_text, focusable=False), wrap_lines=False),
    Window(BufferControl(buffer=runtime_buf, focusable=True), height=1),
], width=lambda: pw(1))

# Stack
col2 = HSplit([
    Window(make_title(2, 'Stack'), height=1),
    Window(FormattedTextControl(get_stack_text, focusable=False), wrap_lines=False),
    Window(BufferControl(buffer=stack_buf, focusable=True), height=1),
], width=lambda: pw(2))

# Vars
col3 = HSplit([
    Window(make_title(3, 'Vars'), height=1),
    Window(FormattedTextControl(get_vars_text, focusable=False), wrap_lines=False),
    Window(BufferControl(buffer=vars_buf, focusable=True), height=1),
])

layout = Layout(
    HSplit([
        VSplit([col0, col1, col2, col3]),
        Window(FormattedTextControl(
            lambda: [('class:panel.title', ' Console')], focusable=False), height=1),
        Window(BufferControl(buffer=console_buf, focusable=False),
               wrap_lines=True, height=8),
        Window(FormattedTextControl(get_status_text, focusable=False), height=1),
    ]),
    focused_element=code_buf,
)

# ── Key bindings ──────────────────────────────────────────────────────────────
kb = KeyBindings()

@kb.add('f5')
def _(e): do_run(); e.app.invalidate()

@kb.add('f6')
def _(e): do_step_line(); e.app.invalidate()

@kb.add('f7')
def _(e): do_step_op(); e.app.invalidate()

@kb.add('f8')
def _(e): do_reset(); e.app.invalidate()

@kb.add('c-q')
def _(e): e.app.exit()

@kb.add('tab')
def _(e):
    focused_panel[0] = (focused_panel[0] + 1) % 4
    e.app.layout.focus(_PANEL_BUFS[focused_panel[0]])
    set_status('panel: ' + PANEL_NAMES[focused_panel[0]])
    e.app.invalidate()

@kb.add('escape', '=')
def _(e):
    p = focused_panel[0]
    panel_widths[p] += 2
    set_status(PANEL_NAMES[p] + ' w=' + str(panel_widths[p]))
    e.app.invalidate()

@kb.add('escape', '-')
def _(e):
    p = focused_panel[0]
    panel_widths[p] = max(PANEL_MIN, panel_widths[p] - 2)
    set_status(PANEL_NAMES[p] + ' w=' + str(panel_widths[p]))
    e.app.invalidate()

# ── Focus sync (mouse clicks update focused_panel) ────────────────────────────
def sync_focus(app):
    try:
        buf = app.layout.current_buffer
        if buf is not None:
            idx = _BUF_TO_IDX.get(buf.name)
            if idx is not None and focused_panel[0] != idx:
                focused_panel[0] = idx
                set_status('panel: ' + PANEL_NAMES[idx])
    except Exception:
        pass

# ── Run ───────────────────────────────────────────────────────────────────────
app = Application(
    layout=layout,
    key_bindings=kb,
    style=style,
    full_screen=True,
    mouse_support=True,
)
app.after_render += sync_focus
app.run()
