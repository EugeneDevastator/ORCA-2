from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.layout.containers import VSplit, Window, HSplit
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame

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

def deref(x, env):
    if x is None: return x
    if x[0] == 'sym':
        return env.get(x[1], x)
    return x

def popd(stack, env):
    return deref(stack.pop() if stack else None, env)

# ── Tokenizer ─────────────────────────────────────────────────────────────────
OP_NAMES = {'SET','SETV','SETL','SETL*','SUM','SUB','MUL','DIV','MOD','INC','DEC','APD','LOG','PSTACK','FOR','END'}

def classify_token(tok):
    import re
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:$', tok):
        return ('deref', tok[:-1])
    if tok == 'true':  return ('lit', mk_bool(True))
    if tok == 'false': return ('lit', mk_bool(False))
    if tok == '_':     return ('op', '_')
    if tok == ';':     return ('op', ';')
    if re.match(r'^-?\d+$', tok):      return ('lit', mk_int(int(tok)))
    if re.match(r'^-?\d+\.\d+$', tok): return ('lit', mk_flt(float(tok)))
    if tok in OP_NAMES:                return ('op', tok)
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

# ── Ops ───────────────────────────────────────────────────────────────────────
def op_set(stack, env, logs, rt):
    nm = stack.pop() if stack else None
    val = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append('SET!'); return
    env[nm[1]] = deref(val, env)
    stack.append(nm); rt.append('SET')

def op_setl(stack, env, logs, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append('SETL!'); return
    items = [deref(x, env) for x in stack]
    stack.clear()
    env[nm[1]] = mk_list(items)
    stack.append(nm); rt.append('SETL')

def op_sum(stack, env, logs, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append('SUM!'); return
    res = mk_num(to_num(a) + to_num(b))
    stack.append(res); rt.append('SUM ' + val_str(res))

def op_sub(stack, env, logs, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append('SUB!'); return
    res = mk_num(to_num(a) - to_num(b))
    stack.append(res); rt.append('SUB ' + val_str(res))

def op_mul(stack, env, logs, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append('MUL!'); return
    res = mk_num(to_num(a) * to_num(b))
    stack.append(res); rt.append('MUL ' + val_str(res))

def op_div(stack, env, logs, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None or to_num(b) == 0: rt.append('DIV!'); return
    res = mk_num(to_num(a) / to_num(b))
    stack.append(res); rt.append('DIV ' + val_str(res))

def op_mod(stack, env, logs, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append('MOD!'); return
    res = mk_int(int(to_num(a)) % int(to_num(b)))
    stack.append(res); rt.append('MOD ' + val_str(res))

def op_inc(stack, env, logs, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append('INC!'); return
    cur = env.get(nm[1], mk_int(0))
    env[nm[1]] = mk_num(to_num(cur) + 1)
    stack.append(env[nm[1]]); rt.append('INC')

def op_dec(stack, env, logs, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append('DEC!'); return
    cur = env.get(nm[1], mk_int(0))
    env[nm[1]] = mk_num(to_num(cur) - 1)
    stack.append(env[nm[1]]); rt.append('DEC')

def op_apd(stack, env, logs, rt):
    list_nm = stack.pop() if stack else None
    val = popd(stack, env)
    if not list_nm or list_nm[0] != 'sym': rt.append('APD!'); return
    if list_nm[1] not in env or env[list_nm[1]][0] != 'list':
        env[list_nm[1]] = mk_list([])
    env[list_nm[1]][1].append(val)
    stack.append(list_nm); rt.append('APD')

def op_log(stack, env, logs, rt):
    val = popd(stack, env)
    if val is None: rt.append('LOG!'); return
    logs.append(val_str(val))
    rt.append('LOG ' + val_str(val))

def op_pstack(stack, env, logs, rt):
    s = ' '.join(val_str(deref(x,env)) for x in stack)
    logs.append('STACK: ' + s)
    rt.append('PSTACK')

OP_MAP = {
    'SET': op_set, 'SETV': op_set, 'SETL': op_setl, 'SETL*': op_setl,
    'SUM': op_sum, 'SUB': op_sub, 'MUL': op_mul, 'DIV': op_div, 'MOD': op_mod,
    'INC': op_inc, 'DEC': op_dec, 'APD': op_apd, 'LOG': op_log, 'PSTACK': op_pstack,
}

# ── Execution ─────────────────────────────────────────────────────────────────
def make_state(src):
    prog = parse_program(src)
    display = [{'rt_parts': [], 'stack_snap': [], 'visited': False} for _ in prog]
    return {'prog': prog, 'display': display, 'pc': 0, 'op_idx': 0,
            'stack': [], 'env': {}, 'logs': [], 'loop_stack': [], 'done': False}

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
        step  = to_num(popd(S['stack'], S['env']))
        to_v  = to_num(popd(S['stack'], S['env']))
        from_v= to_num(popd(S['stack'], S['env']))
        if not var_tok or var_tok[0] != 'sym':
            rt.append('FOR!')
        else:
            S['env'][var_tok[1]] = mk_num(from_v)
            S['loop_stack'].append({'var': var_tok[1], 'to': to_v, 'step': step,
                                    'for_pc': S['pc'], 'end_pc': line['end_pc']})
            rt.append('FOR')
            if (step > 0 and from_v > to_v) or (step < 0 and from_v < to_v):
                S['pc'] = line['end_pc'] + 1; S['op_idx'] = 0; S['stack'] = []; jumped = True
        disp['rt_parts'].extend(rt)
        if not jumped: S['op_idx'] += 1
        disp['stack_snap'] = list(S['stack'])
        return True

    if tok == ('op', 'END'):
        if not S['loop_stack']:
            rt.append('END!')
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
        rt.append('END')
        disp['rt_parts'].extend(rt)
        disp['stack_snap'] = list(S['stack'])
        return True

    # normal token
    exec_tok(tok, S['stack'], S['env'], S['logs'], rt)
    disp['rt_parts'].extend(rt)
    S['op_idx'] += 1
    if S['op_idx'] >= len(line['tokens']):
        disp['stack_snap'] = list(S['stack'])
        S['pc'] += 1; S['op_idx'] = 0; S['stack'] = []
    else:
        disp['stack_snap'] = list(S['stack'])
    return True

def exec_tok(tok, stack, env, logs, rt):
    kind = tok[0]
    if kind == 'lit':
        stack.append(tok[1]); rt.append(val_str(tok[1])); return
    if kind == 'deref':
        val = env.get(tok[1])
        if val is not None: stack.append(val); rt.append(tok[1] + ':')
        else: rt.append(tok[1] + ':?')
        return
    if kind == 'sym':
        stack.append(mk_sym(tok[1])); rt.append(tok[1]); return
    if kind == 'unknown':
        rt.append(tok[1] + '?'); return
    op = tok[1]
    if op == '_':
        top = stack.pop() if stack else None
        if top is None: rt.append('_!'); return
        val = deref(top, env)
        stack.append(val); rt.append(val_str(val)); return
    if op == ';':
        rt.append(';'); return
    handler = OP_MAP.get(op)
    if handler: handler(stack, env, logs, rt); return
    rt.append(op + '?')

# ── App ───────────────────────────────────────────────────────────────────────
FIB = """0 a SET
1 b SET
0 s SET
a b flist SETL
0 13 1 i FOR
    a b SUM _ c SETV
    c: flist APD
    c s SUM _ s SETV
    b a SETV
    c b SETV
END
s LOG
flist LOG"""

state = {'S': None, 'status': 'Ready. F5=Run F6=StepLine F7=StepOp F8=Reset'}

code_buf = Buffer(name='code', multiline=True)
code_buf.set_document(Document(FIB))

def get_runtime_text():
    S = state['S']
    if S is None:
        src = code_buf.text
        lines = src.split('\n')
        return [('class:dim', '\n'.join(lines))]
    result = []
    prog = S['prog']
    for i, line in enumerate(prog):
        disp = S['display'][i]
        is_cur = (i == S['pc'] and not S['done'])
        prefix = ('class:cursor_line', '▶ ') if is_cur else ('', '  ')
        if disp['rt_parts']:
            text = ' '.join(disp['rt_parts'])
            style = 'class:cursor_line' if is_cur else ''
            result.append(prefix)
            result.append((style, text + '\n'))
        elif not disp['visited']:
            result.append(prefix)
            for tok in line['tokens']:
                result.append((tok_style(tok), tok_raw(tok) + ' '))
            result.append(('', '\n'))
        else:
            result.append(prefix)
            result.append(('class:dim', '\n'))
    return result

def tok_style(tok):
    k = tok[0]
    if k == 'lit':     return 'class:tok_lit'
    if k == 'sym':     return 'class:tok_sym'
    if k == 'op':      return 'class:tok_op'
    if k == 'deref':   return 'class:tok_deref'
    if k == 'unknown': return 'class:tok_err'
    return ''

def tok_raw(tok):
    k = tok[0]
    if k == 'lit':   return val_str(tok[1])
    if k == 'deref': return tok[1] + ':'
    return tok[1]

def get_stack_text():
    S = state['S']
    if S is None: return [('', '')]
    result = []
    prog = S['prog']
    for i in range(len(prog)):
        disp = S['display'][i]
        is_cur = (i == S['pc'] and not S['done'])
        style = 'class:cursor_line' if is_cur else ''
        snap_str = ' '.join(val_str(x) for x in disp['stack_snap'])
        result.append((style, snap_str + '\n'))
    return result

def get_vars_text():
    S = state['S']
    if S is None: return [('', '')]
    result = []
    for k, v in S['env'].items():
        result.append(('class:var_name', k))
        result.append(('', '='))
        result.append(('class:var_val', val_str(v) + '\n'))
    return result

def get_status_text():
    return [('class:status', ' ' + state['status'] + ' ')]

runtime_ctrl = FormattedTextControl(get_runtime_text, focusable=False)
stack_ctrl   = FormattedTextControl(get_stack_text,   focusable=False)
vars_ctrl    = FormattedTextControl(get_vars_text,    focusable=False)
status_ctrl  = FormattedTextControl(get_status_text,  focusable=False)

def set_status(s):
    state['status'] = s

def ensure_state():
    if state['S'] is None:
        state['S'] = make_state(code_buf.text)

def do_run():
    ensure_state()
    S = state['S']
    limit = 2_000_000
    while not S['done'] and limit > 0:
        step_one_op(S); limit -= 1
    set_status('Done. logs=' + str(len(S['logs'])) if limit > 0 else 'ERR: step limit')

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
    set_status('Reset.')

kb = KeyBindings()

@kb.add('f5')
def _(event): do_run(); event.app.invalidate()

@kb.add('f6')
def _(event): do_step_line(); event.app.invalidate()

@kb.add('f7')
def _(event): do_step_op(); event.app.invalidate()

@kb.add('f8')
def _(event): do_reset(); event.app.invalidate()

@kb.add('c-q')
def _(event): event.app.exit()

style = Style.from_dict({
    '':              'bg:#f8f8f8 #222222',
    'frame.border':  '#aaaaaa',
    'frame.label':   '#0055cc bold',
    'cursor_line':   'bg:#ddeeff #000000',
    'tok_lit':       '#007700',
    'tok_sym':       '#000088',
    'tok_op':        '#880000 bold',
    'tok_deref':     '#886600',
    'tok_err':       'bg:#ffcccc #cc0000',
    'var_name':      '#000088',
    'var_val':       '#007700',
    'dim':           '#aaaaaa',
    'status':        'bg:#dddddd #333333',
})

layout = Layout(
    HSplit([
        VSplit([
            Frame(Window(BufferControl(buffer=code_buf), wrap_lines=False), title='Code'),
            Frame(Window(runtime_ctrl, wrap_lines=False), title='Runtime'),
            Frame(Window(stack_ctrl,   wrap_lines=False, width=20), title='Stack'),
            Frame(Window(vars_ctrl,    wrap_lines=False, width=20), title='Vars'),
        ]),
        Window(status_ctrl, height=1),
    ])
)

app = Application(layout=layout, key_bindings=kb, style=style,
                  full_screen=True, mouse_support=True)
app.run()
