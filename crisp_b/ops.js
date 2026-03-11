// ── Value constructors ────────────────────────────────────────────────────────
function mkInt(v)  { return { t:'int',  v: v|0 }; }
function mkFlt(v)  { return { t:'flt',  v: +v }; }
function mkStr(v)  { return { t:'str',  v: String(v) }; }
function mkBool(v) { return { t:'bool', v: !!v }; }
function mkList(v) { return { t:'list', v: v }; }
function mkSym(v)  { return { t:'sym',  v: v }; }
function mkNum(v)  { return Number.isInteger(v) ? mkInt(v) : mkFlt(v); }

function valStr(x) {
  if (!x) return 'nil';
  if (x.t === 'list') return '[' + x.v.map(valStr).join(', ') + ']';
  if (x.t === 'bool') return x.v ? 'true' : 'false';
  return String(x.v);
}
function toNum(x) {
  if (!x) return 0;
  if (x.t === 'int' || x.t === 'flt') return x.v;
  if (x.t === 'bool') return x.v ? 1 : 0;
  return parseFloat(x.v) || 0;
}
function deref(x, env) {
  if (!x) return x;
  if (x.t === 'sym') { let v = env[x.v]; return v !== undefined ? v : x; }
  return x;
}

// ── Operator table ────────────────────────────────────────────────────────────
// Each entry: { name, handle(stack, env, logs, rt) }
// rt  = string array to push display tokens into
// Return value ignored; mutate stack/env/logs directly.
//
// Stack convention (top = last element, pop() takes top):
//   push with stack.push(val)
//   pop  with stack.pop()
//
// Helper: pop and deref in one step
function popd(stack, env) { return deref(stack.pop(), env); }

const OP_TABLE = [

  { name: 'SET',
    // usage: <val> <sym> SET  →  assigns val to sym (val NOT dereffed)
    handle(stack, env, logs, rt) {
      let nm = stack.pop(), val = stack.pop();
      if (!nm || nm.t !== 'sym') { rt.push('SET!'); return; }
      env[nm.v] = deref(val, env);
      stack.push(nm); rt.push('SET');
    }
  },

  { name: 'SETV',
    // usage: <val> <sym> SETV  →  same as SET (alias, kept for compat)
    handle(stack, env, logs, rt) {
      let nm = stack.pop(), val = stack.pop();
      if (!nm || nm.t !== 'sym') { rt.push('SETV!'); return; }
      env[nm.v] = deref(val, env);
      stack.push(nm); rt.push('SETV');
    }
  },

  { name: 'SETL',
    // usage: <v0> <v1> ... <sym> SETL  →  collects all stack items into list, assigns to sym
    handle(stack, env, logs, rt) {
      let nm = stack.pop();
      if (!nm || nm.t !== 'sym') { rt.push('SETL!'); return; }
      let items = stack.splice(0).map(x => deref(x, env));
      env[nm.v] = mkList(items);
      stack.push(nm); rt.push('SETL');
    }
  },

  { name: 'SETL*',
    // usage: <v0> <v1> ... <sym> SETL*  →  like SETL but no deref of items
    handle(stack, env, logs, rt) {
      let nm = stack.pop();
      if (!nm || nm.t !== 'sym') { rt.push('SETL*!'); return; }
      let items = stack.splice(0);
      env[nm.v] = mkList(items);
      stack.push(nm); rt.push('SETL*');
    }
  },

  { name: 'SUM',
    // usage: <a> <b> SUM  →  a + b
    handle(stack, env, logs, rt) {
      let b = popd(stack,env), a = popd(stack,env);
      if (!a || !b) { rt.push('SUM!'); return; }
      let res = mkNum(toNum(a) + toNum(b));
      stack.push(res); rt.push('SUM ' + valStr(res));
    }
  },

  { name: 'SUB',
    // usage: <a> <b> SUB  →  a - b
    handle(stack, env, logs, rt) {
      let b = popd(stack,env), a = popd(stack,env);
      if (!a || !b) { rt.push('SUB!'); return; }
      let res = mkNum(toNum(a) - toNum(b));
      stack.push(res); rt.push('SUB ' + valStr(res));
    }
  },

  { name: 'MUL',
    // usage: <a> <b> MUL  →  a * b
    handle(stack, env, logs, rt) {
      let b = popd(stack,env), a = popd(stack,env);
      if (!a || !b) { rt.push('MUL!'); return; }
      let res = mkNum(toNum(a) * toNum(b));
      stack.push(res); rt.push('MUL ' + valStr(res));
    }
  },

  { name: 'DIV',
    // usage: <a> <b> DIV  →  a / b
    handle(stack, env, logs, rt) {
      let b = popd(stack,env), a = popd(stack,env);
      if (!a || !b || toNum(b) === 0) { rt.push('DIV!'); return; }
      let res = mkNum(toNum(a) / toNum(b));
      stack.push(res); rt.push('DIV ' + valStr(res));
    }
  },

  { name: 'MOD',
    // usage: <a> <b> MOD  →  a % b (integer)
    handle(stack, env, logs, rt) {
      let b = popd(stack,env), a = popd(stack,env);
      if (!a || !b) { rt.push('MOD!'); return; }
      let res = mkInt(toNum(a) % toNum(b));
      stack.push(res); rt.push('MOD ' + valStr(res));
    }
  },

  { name: 'INC',
    // usage: <sym> INC  →  env[sym]++
    handle(stack, env, logs, rt) {
      let nm = stack.pop();
      if (!nm || nm.t !== 'sym') { rt.push('INC!'); return; }
      let cur = env[nm.v] || mkInt(0);
      env[nm.v] = mkNum(toNum(cur) + 1);
      stack.push(env[nm.v]); rt.push('INC');
    }
  },

  { name: 'DEC',
    // usage: <sym> DEC  →  env[sym]--
    handle(stack, env, logs, rt) {
      let nm = stack.pop();
      if (!nm || nm.t !== 'sym') { rt.push('DEC!'); return; }
      let cur = env[nm.v] || mkInt(0);
      env[nm.v] = mkNum(toNum(cur) - 1);
      stack.push(env[nm.v]); rt.push('DEC');
    }
  },

  { name: 'APD',
    // usage: <val> <listSym> APD  →  appends val to list at listSym
    handle(stack, env, logs, rt) {
      let listNm = stack.pop(), val = popd(stack, env);
      if (!listNm || listNm.t !== 'sym') { rt.push('APD!'); return; }
      if (!env[listNm.v] || env[listNm.v].t !== 'list') env[listNm.v] = mkList([]);
      env[listNm.v].v.push(val);
      stack.push(listNm); rt.push('APD');
    }
  },

  { name: 'LOG',
    // usage: <val> LOG  →  prints val to log
    handle(stack, env, logs, rt) {
      let val = popd(stack, env);
      if (!val) { rt.push('LOG!'); return; }
      logs.push(valStr(val));
      rt.push('LOG ' + valStr(val));
    }
  },

  { name: 'PSTACK',
    // usage: PSTACK  →  logs entire stack contents
    handle(stack, env, logs, rt) {
      let s = stack.map(x => valStr(deref(x,env))).join(' ');
      logs.push('STACK: ' + s);
      rt.push('PSTACK');
    }
  },

];

// Build fast lookup map and name set from table
const OP_MAP = {};
const OP_NAMES = new Set();
for (let i = 0; i < OP_TABLE.length; i++) {
  OP_MAP[OP_TABLE[i].name] = OP_TABLE[i].handle;
  OP_NAMES.add(OP_TABLE[i].name);
}
