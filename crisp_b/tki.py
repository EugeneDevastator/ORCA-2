import tkinter as tk
from tkinter import font as tkfont
import re

# ── Constants ─────────────────────────────────────────────────────────────────
FONT_NAME = "Courier New"
FONT_SIZE = 11
PAD = 4
PANEL_WIDTHS = [46, 32, 12, 16]
PANEL_NAMES  = ["Code", "Runtime", "Stack", "Vars"]
CONSOLE_HEIGHT = 8

OP_NAMES = {'SET','SETV','SETL','SETL*','SUM','SUB','MUL','DIV','MOD',
            'INC','DEC','APD','LOG','PSTACK','FOR','END'}

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

# ── Colors ────────────────────────────────────────────────────────────────────
BG             = "#f8f8f8"
FG             = "#222222"
BG_PANEL       = "#ffffff"
BG_TITLE       = "#e0e8ff"
BG_TITLE_FOCUS = "#0055cc"
FG_TITLE_FOCUS = "#ffffff"
BG_CONSOLE     = "#f0f0f0"
BG_STATUS      = "#dddddd"
FG_STATUS      = "#333333"
COL_LIT        = "#aa6600"
COL_OP         = "#0055cc"
COL_DEREF      = "#007700"
COL_SYM        = "#222222"
COL_COMMENT    = "#999999"
COL_UNKNOWN    = "#ff0000"
COL_RT_VAL_BG  = "#ffee00"
COL_RT_ERR_BG  = "#ff4444"
COL_VAR_KEY    = "#007700"

# ── Tokenizer ─────────────────────────────────────────────────────────────────
def classify_token(tok):
    if tok == 'true':  return ('lit',   ('bool', True))
    if tok == 'false': return ('lit',   ('bool', False))
    if tok in ('_', ';', ':'): return ('op', tok)
    if re.match(r'^-?\d+$', tok):      return ('lit', ('int',   int(tok)))
    if re.match(r'^-?\d+\.\d+$', tok): return ('lit', ('flt', float(tok)))
    if tok in OP_NAMES:                return ('op',  tok)
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:$', tok): return ('deref', tok[:-1])
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', tok):  return ('sym',   tok)
    return ('unknown', tok)

def tokenize_line(line):
    s = line.split('//')[0]
    tokens = []
    i = 0
    while i < len(s):
        while i < len(s) and s[i] == ' ': i += 1
        if i >= len(s): break
        if s[i] == '"':
            j = i + 1
            while j < len(s) and s[j] != '"': j += 1
            tokens.append(('lit', ('str', s[i+1:j])))
            i = j + 1
            continue
        j = i
        while j < len(s) and s[j] != ' ': j += 1
        tokens.append(classify_token(s[i:j]))
        i = j
    return tokens

def token_spans_in_line(line):
    ci = line.find('//')
    code = line[:ci] if ci >= 0 else line
    spans = []
    i = 0
    while i < len(code):
        while i < len(code) and code[i] == ' ': i += 1
        if i >= len(code): break
        if code[i] == '"':
            j = i + 1
            while j < len(code) and code[j] != '"': j += 1
            spans.append((i, j + 1, 'lit'))
            i = j + 1
            continue
        j = i
        while j < len(code) and code[j] != ' ': j += 1
        spans.append((i, j, classify_token(code[i:j])[0]))
        i = j
    if ci >= 0:
        spans.append((ci, len(line), 'comment'))
    return spans

# ── Value helpers ─────────────────────────────────────────────────────────────
def mk_int(v):  return ('int',  int(v))
def mk_flt(v):  return ('flt',  float(v))
def mk_str(v):  return ('str',  str(v))
def mk_bool(v): return ('bool', bool(v))
def mk_list(v): return ('list', list(v))
def mk_sym(v):  return ('sym',  v)
def mk_num(v):
    if isinstance(v, int): return mk_int(v)
    return mk_int(v) if v == int(v) else mk_flt(v)

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

# ── Ops ───────────────────────────────────────────────────────────────────────
def op_set(stack, env, rt):
    nm = stack.pop() if stack else None
    val = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(('err','SET!')); return
    env[nm[1]] = val; stack.append(nm); rt.append(('op','SET'))

def op_setv(stack, env, rt):
    nm = stack.pop() if stack else None
    val = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(('err','SETV!')); return
    env[nm[1]] = full_deref(val, env); stack.append(nm); rt.append(('op','SETV'))

def op_setl(stack, env, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(('err','SETL!')); return
    env[nm[1]] = mk_list(list(stack)); stack.clear(); stack.append(nm); rt.append(('op','SETL'))

def op_sum(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(('err','SUM!')); return
    res = mk_num(to_num(a)+to_num(b)); stack.append(res); rt.append(('val',val_str(res)))

def op_sub(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(('err','SUB!')); return
    res = mk_num(to_num(a)-to_num(b)); stack.append(res); rt.append(('val',val_str(res)))

def op_mul(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(('err','MUL!')); return
    res = mk_num(to_num(a)*to_num(b)); stack.append(res); rt.append(('val',val_str(res)))

def op_div(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None or to_num(b)==0: rt.append(('err','DIV!')); return
    res = mk_num(to_num(a)/to_num(b)); stack.append(res); rt.append(('val',val_str(res)))

def op_mod(stack, env, rt):
    b = popd(stack,env); a = popd(stack,env)
    if a is None or b is None: rt.append(('err','MOD!')); return
    res = mk_int(int(to_num(a))%int(to_num(b))); stack.append(res); rt.append(('val',val_str(res)))

def op_inc(stack, env, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(('err','INC!')); return
    env[nm[1]] = mk_num(to_num(env.get(nm[1], mk_int(0)))+1)
    stack.append(env[nm[1]]); rt.append(('op','INC'))

def op_dec(stack, env, rt):
    nm = stack.pop() if stack else None
    if not nm or nm[0] != 'sym': rt.append(('err','DEC!')); return
    env[nm[1]] = mk_num(to_num(env.get(nm[1], mk_int(0)))-1)
    stack.append(env[nm[1]]); rt.append(('op','DEC'))

def op_apd(stack, env, rt):
    list_nm = stack.pop() if stack else None
    val = stack.pop() if stack else None
    if not list_nm or list_nm[0] != 'sym': rt.append(('err','APD!')); return
    if list_nm[1] not in env or env[list_nm[1]][0] != 'list':
        env[list_nm[1]] = mk_list([])
    env[list_nm[1]][1].append(val); stack.append(list_nm); rt.append(('op','APD'))

def op_log(stack, env, rt, console_cb):
    val = stack.pop() if stack else None
    if val is None: rt.append(('err','LOG!')); return
    console_cb(val_str(full_deref(val, env))); rt.append(('op','LOG'))

def op_pstack(stack, env, rt, console_cb):
    console_cb('STACK: '+' '.join(val_str(x) for x in stack)); rt.append(('op','PSTACK'))

def op_deref_op(stack, env, rt):
    top = stack.pop() if stack else None
    if top is None: rt.append(('err',':!')); return
    val = full_deref(top, env) if top[0]=='sym' else top
    stack.append(val); rt.append(('val',val_str(val)))

def op_underscore(stack, env, rt):
    top = stack.pop() if stack else None
    if top is None: rt.append(('err','_!')); return
    stack.append(top); rt.append(('val',val_str(top)))

def exec_tok(tok, stack, env, rt, console_cb):
    kind = tok[0]
    if kind == 'lit':
        stack.append(tok[1]); rt.append(('val', val_str(tok[1]))); return
    if kind == 'sym':
        stack.append(mk_sym(tok[1])); rt.append(('sym', tok[1])); return
    if kind == 'deref':
        val = full_deref(mk_sym(tok[1]), env)
        stack.append(val); rt.append(('val', val_str(val))); return
    if kind == 'unknown':
        rt.append(('err', tok[1]+'?')); return
    op_map = {
        'SET':op_set,'SETV':op_setv,'SETL':op_setl,'SETL*':op_setl,
        'SUM':op_sum,'SUB':op_sub,'MUL':op_mul,'DIV':op_div,'MOD':op_mod,
        'INC':op_inc,'DEC':op_dec,'APD':op_apd,
        ':':op_deref_op,'_':op_underscore,
    }
    log_ops = {'LOG':op_log,'PSTACK':op_pstack}
    if tok[1] in log_ops:
        log_ops[tok[1]](stack, env, rt, console_cb); return
    h = op_map.get(tok[1])
    if h: h(stack, env, rt)
    else: rt.append(('err', tok[1]+'?'))

# ── Parser ────────────────────────────────────────────────────────────────────
def parse_program(src):
    prog = []
    for i, raw in enumerate(src.split('\n')):
        t = raw.strip()
        prog.append({'src_idx':i,'tokens':tokenize_line(t),'raw':t,
                     'is_for':False,'is_end':False,'end_pc':None,'for_pc':None})
    for_stack = []
    for i, line in enumerate(prog):
        toks = line['tokens']
        if any(t==('op','FOR') for t in toks):
            for_stack.append(i); line['is_for']=True
        if len(toks)==1 and toks[0]==('op','END'):
            line['is_end']=True
            if for_stack:
                fi=for_stack.pop(); prog[fi]['end_pc']=i; line['for_pc']=fi
    return prog

def make_state(src):
    prog = parse_program(src)
    display = [{'rt_parts':[],'stack_snap':[],'visited':False} for _ in prog]
    return {'prog':prog,'display':display,'pc':0,'op_idx':0,
            'stack':[],'env':{},'loop_stack':[],'done':False}

def step_one_op(S, console_cb):
    prog = S['prog']
    while S['pc'] < len(prog):
        if not prog[S['pc']]['tokens']:
            d = S['display'][S['pc']]
            d['visited']=True; d['rt_parts']=[]; d['stack_snap']=[]
            S['pc']+=1; S['op_idx']=0; S['stack']=[]
        else: break
    if S['pc'] >= len(prog): S['done']=True; return False

    line = prog[S['pc']]; disp = S['display'][S['pc']]
    if S['op_idx']==0: disp['rt_parts']=[]; disp['stack_snap']=[]
    disp['visited']=True

    if S['op_idx'] >= len(line['tokens']):
        disp['stack_snap']=list(S['stack'])
        S['pc']+=1; S['op_idx']=0; S['stack']=[]; return True

    tok = line['tokens'][S['op_idx']]; rt=[]; jumped=False

    if tok==('op','FOR'):
        var_tok=S['stack'].pop() if S['stack'] else None
        step_v=to_num(popd(S['stack'],S['env']))
        to_v  =to_num(popd(S['stack'],S['env']))
        from_v=to_num(popd(S['stack'],S['env']))
        if not var_tok or var_tok[0]!='sym': rt.append(('err','FOR!'))
        else:
            S['env'][var_tok[1]]=mk_num(from_v)
            S['loop_stack'].append({'var':var_tok[1],'to':to_v,'step':step_v,
                                    'for_pc':S['pc'],'end_pc':line['end_pc']})
            rt.append(('op','FOR'))
            if (step_v>0 and from_v>to_v) or (step_v<0 and from_v<to_v):
                S['pc']=line['end_pc']+1; S['op_idx']=0; S['stack']=[]; jumped=True
        disp['rt_parts'].extend(rt)
        if not jumped: S['op_idx']+=1
        disp['stack_snap']=list(S['stack']); return True

    if tok==('op','END'):
        if not S['loop_stack']:
            rt.append(('err','END!')); disp['rt_parts'].extend(rt)
            S['op_idx']+=1; disp['stack_snap']=list(S['stack']); return True
        loop=S['loop_stack'][-1]
        cur=to_num(S['env'].get(loop['var'],mk_int(0)))+loop['step']
        S['env'][loop['var']]=mk_num(cur)
        cont=(cur<=loop['to']) if loop['step']>0 else (cur>=loop['to'])
        if cont: S['pc']=loop['for_pc']+1; S['op_idx']=0; S['stack']=[]
        else:    S['loop_stack'].pop(); S['pc']+=1; S['op_idx']=0; S['stack']=[]
        rt.append(('op','END')); disp['rt_parts'].extend(rt)
        disp['stack_snap']=list(S['stack']); return True

    exec_tok(tok, S['stack'], S['env'], rt, console_cb)
    disp['rt_parts'].extend(rt); S['op_idx']+=1
    if S['op_idx']>=len(line['tokens']):
        disp['stack_snap']=list(S['stack'])
        S['pc']+=1; S['op_idx']=0; S['stack']=[]
    else:
        disp['stack_snap']=list(S['stack'])
    return True

# ── App ───────────────────────────────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        root.title("Stack Editor")
        root.configure(bg=BG)

        self.mono      = tkfont.Font(family=FONT_NAME, size=FONT_SIZE)
        self.mono_bold = tkfont.Font(family=FONT_NAME, size=FONT_SIZE, weight="bold")

        self.exec_state   = None
        self.panel_widths = list(PANEL_WIDTHS)
        self.focused_panel = 0

        self._build_ui()
        self._highlight_code()
        self._update_titles()
        self._update_status("Ready.")

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # title row
        self.title_frame = tk.Frame(self.root, bg=BG)
        self.title_frame.pack(side=tk.TOP, fill=tk.X)
        self.title_labels = []
        for i, name in enumerate(PANEL_NAMES):
            lbl = tk.Label(self.title_frame, text=name,
                           font=self.mono_bold, bg=BG_TITLE, fg=FG,
                           anchor='w', padx=PAD,
                           width=self.panel_widths[i])
            lbl.pack(side=tk.LEFT)
            lbl.bind("<Button-1>", lambda e, idx=i: self._focus_panel(idx))
            self.title_labels.append(lbl)

        # panels row — use a plain Frame, pack widgets left with fixed width
        self.panels_frame = tk.Frame(self.root, bg=BG)
        self.panels_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        def make_text(w, editable=False):
            t = tk.Text(
                self.panels_frame,
                font=self.mono, bg=BG_PANEL, fg=FG,
                wrap=tk.NONE,
                width=w, relief=tk.FLAT, bd=0,
                state=tk.NORMAL if editable else tk.DISABLED,
                insertbackground=FG,
                selectbackground="#aaccff",
            )
            t.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
            return t

        self.code_text  = make_text(self.panel_widths[0], editable=True)
        self.code_text.configure(undo=True, maxundo=-1)
        self.rt_text    = make_text(self.panel_widths[1])
        self.stack_text = make_text(self.panel_widths[2])
        self.vars_text  = make_text(self.panel_widths[3])

        self._setup_code_tags()
        self._setup_rt_tags()
        self._setup_vars_tags()

        # insert demo
        self.code_text.insert("1.0", DEMO)

        # code bindings
        self.code_text.bind("<FocusIn>",    lambda e: self._focus_panel(0))
        self.code_text.bind("<KeyRelease>", self._on_code_change)
        # arrow keys — return "break" to suppress default cursor move
        self.code_text.bind("<Left>",  self._tok_left)
        self.code_text.bind("<Right>", self._tok_right)
        self.code_text.bind("<Up>",    self._tok_up)
        self.code_text.bind("<Down>",  self._tok_down)
        # printable key replaces selection
        self.code_text.bind("<Key>",   self._on_key_replace)

        # console
        tk.Label(self.root, text=" Console",
                 font=self.mono_bold, bg=BG_TITLE, fg=FG,
                 anchor='w').pack(side=tk.TOP, fill=tk.X)
        self.console_text = tk.Text(
            self.root, font=self.mono, bg=BG_CONSOLE, fg=FG,
            wrap=tk.WORD, state=tk.DISABLED,
            height=CONSOLE_HEIGHT, relief=tk.FLAT, bd=0,
        )
        self.console_text.pack(side=tk.TOP, fill=tk.X)

        # status
        self.status_var = tk.StringVar()
        tk.Label(self.root, textvariable=self.status_var,
                 font=self.mono, bg=BG_STATUS, fg=FG_STATUS,
                 anchor='w', padx=PAD).pack(side=tk.BOTTOM, fill=tk.X)

        # global keys
        self.root.bind("<F5>",        lambda e: self._do_run())
        self.root.bind("<F6>",        lambda e: self._do_step_line())
        self.root.bind("<F7>",        lambda e: self._do_step_op())
        self.root.bind("<F8>",        lambda e: self._do_reset())
        self.root.bind("<Control-q>", lambda e: self.root.destroy())
        self.root.bind("<Tab>",       self._cycle_panel)
        self.root.bind("<Alt-equal>", self._panel_wider)
        self.root.bind("<Alt-minus>", self._panel_narrower)

    # ── Tags ──────────────────────────────────────────────────────────────────
    def _setup_code_tags(self):
        t = self.code_text
        t.tag_configure("lit",     foreground=COL_LIT)
        t.tag_configure("op",      foreground=COL_OP,      font=self.mono_bold)
        t.tag_configure("deref",   foreground=COL_DEREF)
        t.tag_configure("sym",     foreground=COL_SYM)
        t.tag_configure("comment", foreground=COL_COMMENT)
        t.tag_configure("unknown", foreground=COL_UNKNOWN)

    def _setup_rt_tags(self):
        t = self.rt_text
        t.tag_configure("val",      foreground="#000000", background=COL_RT_VAL_BG)
        t.tag_configure("op",       foreground=COL_OP,    font=self.mono_bold)
        t.tag_configure("sym",      foreground="#555555")
        t.tag_configure("err",      foreground="#ffffff",  background=COL_RT_ERR_BG,
                        font=self.mono_bold)
        t.tag_configure("lit",      foreground=COL_LIT)
        t.tag_configure("code_op",  foreground=COL_OP,    font=self.mono_bold)
        t.tag_configure("deref",    foreground=COL_DEREF)
        t.tag_configure("code_sym", foreground=COL_SYM)
        t.tag_configure("comment",  foreground=COL_COMMENT)
        t.tag_configure("unknown",  foreground=COL_UNKNOWN)

    def _setup_vars_tags(self):
        t = self.vars_text
        t.tag_configure("key", foreground=COL_VAR_KEY, font=self.mono_bold)
        t.tag_configure("val", foreground="#000000",   background=COL_RT_VAL_BG)

    # ── Highlight ─────────────────────────────────────────────────────────────
    def _highlight_code(self):
        t = self.code_text
        for tag in ("lit","op","deref","sym","comment","unknown"):
            t.tag_remove(tag, "1.0", tk.END)
        lines = t.get("1.0", tk.END).split('\n')
        for r, line in enumerate(lines):
            for s, e, kind in token_spans_in_line(line):
                t.tag_add(kind, f"{r+1}.{s}", f"{r+1}.{e}")

    def _on_code_change(self, event=None):
        self._highlight_code()

    # ── Token navigation ──────────────────────────────────────────────────────
    def _all_token_positions(self):
        lines = self.code_text.get("1.0", tk.END).split('\n')
        result = []
        for r, line in enumerate(lines):
            for s, e, _ in token_spans_in_line(line):
                result.append((f"{r+1}.{s}", f"{r+1}.{e}"))
        return result

    def _current_token_index(self, tokens):
        t   = self.code_text
        cur = t.index(tk.INSERT)
        for i, (s, e) in enumerate(tokens):
            if t.compare(s, "<=", cur) and t.compare(cur, "<", e):
                return i
        # not inside any token — find first token at or after cursor
        for i, (s, e) in enumerate(tokens):
            if t.compare(s, ">=", cur):
                return i
        return len(tokens) - 1 if tokens else 0

    def _select_token(self, idx, tokens):
        if not tokens: return
        idx = max(0, min(len(tokens)-1, idx))
        s, e = tokens[idx]
        t = self.code_text
        t.tag_remove(tk.SEL, "1.0", tk.END)
        t.tag_add(tk.SEL, s, e)
        t.mark_set(tk.INSERT, s)
        t.see(s)

    def _tok_left(self, event):
        tokens = self._all_token_positions()
        idx    = self._current_token_index(tokens)
        self._select_token(idx - 1, tokens)
        return "break"

    def _tok_right(self, event):
        tokens = self._all_token_positions()
        idx    = self._current_token_index(tokens)
        self._select_token(idx + 1, tokens)
        return "break"

    def _tok_up(self, event):
        t   = self.code_text
        cur = t.index(tk.INSERT)
        row, col = map(int, cur.split('.'))
        if row > 1:
            t.mark_set(tk.INSERT, f"{row-1}.{col}")
        tokens = self._all_token_positions()
        idx    = self._current_token_index(tokens)
        self._select_token(idx, tokens)
        return "break"

    def _tok_down(self, event):
        t   = self.code_text
        cur = t.index(tk.INSERT)
        row, col = map(int, cur.split('.'))
        t.mark_set(tk.INSERT, f"{row+1}.{col}")
        tokens = self._all_token_positions()
        idx    = self._current_token_index(tokens)
        self._select_token(idx, tokens)
        return "break"

    def _on_key_replace(self, event):
        # let Ctrl combos pass through (undo, copy, etc.)
        if event.state & 0x4:
            return
        if not event.char or not event.char.isprintable():
            return
        t = self.code_text
        try:
            sel_start = t.index(tk.SEL_FIRST)
            sel_end   = t.index(tk.SEL_LAST)
            t.delete(sel_start, sel_end)
            t.insert(sel_start, event.char)
            t.mark_set(tk.INSERT, f"{sel_start}+1c")
            t.tag_remove(tk.SEL, "1.0", tk.END)
            self._highlight_code()
            return "break"
        except tk.TclError:
            pass  # no selection — normal insert

    # ── Panel focus / resize ──────────────────────────────────────────────────
    def _focus_panel(self, idx):
        self.focused_panel = idx
        if idx == 0:
            self.code_text.focus_set()
        self._update_titles()
        self._update_status()

    def _update_titles(self):
        for i, lbl in enumerate(self.title_labels):
            if i == self.focused_panel:
                lbl.configure(bg=BG_TITLE_FOCUS, fg=FG_TITLE_FOCUS)
            else:
                lbl.configure(bg=BG_TITLE, fg=FG)

    def _cycle_panel(self, event=None):
        self._focus_panel((self.focused_panel + 1) % 4)
        return "break"

    def _panel_wider(self, event=None):
        p = self.focused_panel
        self.panel_widths[p] += 2
        self._apply_widths()
        self._update_status()

    def _panel_narrower(self, event=None):
        p = self.focused_panel
        self.panel_widths[p] = max(6, self.panel_widths[p] - 2)
        self._apply_widths()
        self._update_status()

    def _apply_widths(self):
        panels = [self.code_text, self.rt_text, self.stack_text, self.vars_text]
        for i, w in enumerate(self.panel_widths):
            panels[i].configure(width=w)
            self.title_labels[i].configure(width=w)

    # ── Console ───────────────────────────────────────────────────────────────
    def _console_write(self, s):
        t = self.console_text
        t.configure(state=tk.NORMAL)
        t.insert(tk.END, s + '\n')
        t.see(tk.END)
        t.configure(state=tk.DISABLED)

    def _console_clear(self):
        t = self.console_text
        t.configure(state=tk.NORMAL)
        t.delete("1.0", tk.END)
        t.configure(state=tk.DISABLED)

    # ── Execution ─────────────────────────────────────────────────────────────
    def _ensure_state(self):
        if self.exec_state is None:
            self.exec_state = make_state(self.code_text.get("1.0", tk.END))

    def _do_run(self):
        self._console_clear()
        self.exec_state = make_state(self.code_text.get("1.0", tk.END))
        S = self.exec_state
        limit = 2_000_000
        while not S['done'] and limit > 0:
            step_one_op(S, self._console_write); limit -= 1
        self._refresh_rt_panels()
        self._update_status("Done." if limit > 0 else "ERR: step limit")

    def _do_step_line(self):
        self._ensure_state()
        S = self.exec_state
        if S['done']: self._update_status("Done."); return
        start_pc = S['pc']
        limit = 100_000
        while not S['done'] and S['pc'] == start_pc and limit > 0:
            step_one_op(S, self._console_write); limit -= 1
        self._refresh_rt_panels()
        self._update_status("pc=" + str(S['pc']))

    def _do_step_op(self):
        self._ensure_state()
        S = self.exec_state
        step_one_op(S, self._console_write)
        self._refresh_rt_panels()
        msg = "Done." if S['done'] else f"pc={S['pc']} op={S['op_idx']}"
        self._update_status(msg)

    def _do_reset(self):
        self.exec_state = None
        self._console_clear()
        self._refresh_rt_panels()
        self._update_status("Reset.")

    # ── Refresh read-only panels ──────────────────────────────────────────────
    def _refresh_rt_panels(self):
        self._refresh_runtime()
        self._refresh_stack()
        self._refresh_vars()

    def _set_ro_text(self, widget, cb):
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        cb(widget)
        widget.configure(state=tk.DISABLED)

    def _refresh_runtime(self):
        def fill(t):
            S = self.exec_state
            if S is None:
                src_lines = self.code_text.get("1.0", tk.END).split('\n')
                for line in src_lines:
                    for s, e, kind in token_spans_in_line(line):
                        tag = {'op':'code_op','sym':'code_sym'}.get(kind, kind)
                        t.insert(tk.END, line[s:e], tag)
                        t.insert(tk.END, " ")
                    t.insert(tk.END, "\n")
            else:
                tag_map = {'op':'code_op','sym':'code_sym','deref':'deref',
                           'lit':'lit','comment':'comment','unknown':'unknown'}
                for i, line in enumerate(S['prog']):
                    disp = S['display'][i]
                    if disp['rt_parts']:
                        for kind, text in disp['rt_parts']:
                            t.insert(tk.END, text, kind)
                            t.insert(tk.END, " ")
                    elif not disp['visited']:
                        raw = line['raw']
                        for s, e, kind in token_spans_in_line(raw):
                            t.insert(tk.END, raw[s:e], tag_map.get(kind, kind))
                            t.insert(tk.END, " ")
                    t.insert(tk.END, "\n")
        self._set_ro_text(self.rt_text, fill)

    def _refresh_stack(self):
        def fill(t):
            S = self.exec_state
            if S is None: return
            for i in range(len(S['prog'])):
                snap = S['display'][i]['stack_snap']
                t.insert(tk.END, ' '.join(val_str(x) for x in snap) + '\n')
        self._set_ro_text(self.stack_text, fill)

    def _refresh_vars(self):
        def fill(t):
            S = self.exec_state
            if S is None: return
            for k, v in S['env'].items():
                t.insert(tk.END, k, "key")
                t.insert(tk.END, "=")
                t.insert(tk.END, val_str(v), "val")
                t.insert(tk.END, "\n")
        self._set_ro_text(self.vars_text, fill)

    # ── Status ────────────────────────────────────────────────────────────────
    def _update_status(self, msg=None):
        if msg is not None:
            self._last_status = msg
        else:
            msg = getattr(self, '_last_status', 'Ready.')
        p = self.focused_panel
        self.status_var.set(
            f" {msg}  [{PANEL_NAMES[p]}: {self.panel_widths[p]}]"
            "    F5=Run  F6=StepLine  F7=StepOp  F8=Reset"
            "  Tab=panel  Alt+/-=width  Ctrl+Q=quit"
        )


# ── Entry ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()