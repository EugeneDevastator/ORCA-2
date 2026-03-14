Aye Captain!

## Crisp Language Spec v1.4

---

### Core Model

A program is a list of **rows**. Each row executes left to right.

**Stack** is per-row. Operators consume from stack. `;` preserves stack across operator consumption.

**Execution rule:** A token is either a **literal** (pushes to stack) or an **operator** (consumes stack, produces output). Operators write output into the next `_` slot if present, otherwise push to stack.

**Default values:** All variables default to `0`. Uninitialized reads return `0`.

---

### Stop Symbol `^`

`^` is an error sentinel — a typed value distinct from all numeric values including `0`.

`^` originates only from:
- Math operations with undefined results (`DIV` by zero, `SQRT` of negative)
- API calls that receive `^` as any argument — return `^`
- API calls that fail (invalid object, missing property, bad state)
- Explicit user push: bare `^` token

`^` is **not** produced by uninitialized variable reads (those return `0`).

**Propagation rule:** `^` is a value on the stack. Operators that cannot process `^` return `^`. Propagates through a row until the row ends or a `^`-aware operator handles it.

Inside `{ }`: if `^` reaches the end of a scope without being handled, the scope exits and pushes `^` onto the parent stack.

**No special unwinding.** `^` propagates by value, not by exception mechanism.

```
5 0 DIV _ c SET     // DIV produces ^, _ captures ^, SET stores ^, row ends
player.weapon: a SET // weapon missing -> ^ -> a = ^
a: API_FIRE         // API receives ^, returns ^, row ends
```

---

### Operator Output Contract

Every operator produces output. No silent operators except X-variants.

| Outcome | Output |
|---|---|
| Success | result value pushed to stack or written to `_` slot |
| Failure | `^` pushed to stack |
| X-variant success | no output, execution continues |
| X-variant failure | no output, row stops |

---

### Stack and `_` Slots

`_` is a positional placeholder. It cannot be stored or pushed. When an operator executes, if the next token is `_`, the result is written there and consumed. Otherwise result goes to stack.

```
5 3 ADD _ x SET     // ADD writes to _, SET reads it
5 3 ADD x SET       // ADD pushes to stack, SET reads stack
```

`_` in switch default case: see Switch section.

---

### Stack Consumption

Operators consume exactly their required inputs from the top of stack. Remaining stack below consumed values is cleared unless protected by `;`.

```
1 2 3 ADD            // consumes 2 and 3, 1 is cleared. stack: [5]
1 ; 2 3 ADD          // ; protects 1. stack: [1 ; 5]
1 ; 5 ; ADD          // ADD sees 1 and 5. stack: [6]
```

---

### Stack Frames and `$`

`;` sets a minimum stack pointer mid-row. Operators cannot erase below it.

`$` is a symbol referring to the current stack as a list. It is readable and writable.

```
$:          // push entire stack as list
$:0         // first element
$:-1        // last element
$:-2        // second from last
3 $ SET     // replace stack with [3], ; moves to position 0
```

`$` always sees the full current stack including below `;` frames. `;` only prevents operators from clearing below it — `$` reads all.

```
1 2 3 ; 4 5 ADD      // stack: [1 2 3 ; 9]
$:                   // [1 2 3 9]
```

---

### Check-Based Executors (X-Operators)

Operators ending in `X` consume inputs, produce no stack output.
- On success: execution continues.
- On failure: row stops.

**X-operators must be followed by a scope `{ }`.**

```
1 1 EQX { "equal" PRN }
1 1 ANDX { "all good" PRN }
```

Bare X before non-scope is a compile error.

---

### `^`-Aware Operators

```
a: ISOK     // 1 if a is not ^, 0 if a is ^
a: SAFE     // a if a is not ^, 0 if a is ^
a: ^ EQ     // 1 if a is ^, 0 otherwise
a: ^ NEQ    // 0 if a is ^, 1 otherwise
```

---

### Tokens

#### Literals
```
42          // integer
3.14        // float
"hello"     // string
1 0         // bool (1 = true, 0 = false)
^           // error sentinel
_           // positional placeholder — not storable, not pushable
```

#### Sigils

| Sigil | Role |
|---|---|
| `_` | positional output slot — operator writes result here |
| `a:` | dereference — evaluate symbol a, push its value |
| `;` | stack frame marker — protects stack below from operator erasure |
| `$` | stack reference — current stack as readable/writable list |
#### Lambdas
```
>OP>                // operator as data, single op
>$:0 $:1 ADD>         // closure with positional args
4 p3ow              // apply: expands positional args left to right---

### Scope

`{` and `}` delimit scope blocks. Stack frame is saved on `{`, unwound on `}`.

`^` reaching scope end exits scope and pushes `^` to parent stack.

```
val IF {
    5 0 DIV         // ^ here, scope exits, ^ pushed to parent
    4 API_CALL      // never fires
}
// parent stack now has ^
```

---

### Variables

All variables default to `0`. No uninitialized errors.

```
b a SET         // set a to b
11 b SET        // set b to 11
a:              // push value of a
b: 13 2 ADD     // dereference b, then add 13+2
b: 1 ADD _ b SET  // increment b
```

---

### Stack Frames

```
1 2 ADD _ 3 4 ; 6 3 DIV _ ; ADD _
```

---

### Property Access

`.` is for engine objects only. Accessing a nonexistent property produces `^`.

```
profile.shared:
profile.inst: _ .components _ .count
pos.x:              // dereference field x of pos
3 pos.x SET         // write 3 to field x of pos
```

User-defined variables do not support `.` syntax. Attempting it produces `^`.

---

### Switch

#### `SW` — predicate match
```
val SW {
    _ 5  LESS  "lt5"  PRN
    _ 7  LESS  "lt7"  PRN
    *          "else" PRN
}
```

#### `SWEQ` — equality match
```
val SWEQ {
    5    "five"  PRN
    7    "seven" PRN
    ^    "error" PRN
    *    "else"  PRN
}
```

`*` is the default/fallthrough case. Only valid inside `SW` and `SWEQ`. Not a general token.

---

### Math Operators

```
a b ADD     // a + b
a b SUB     // a - b
a b MUL     // a * b
a b DIV     // a / b  — ^ if b is 0
a b POW     // a ^ b
a SQRT      // ^ if a < 0
a b SUM     // sum of all stack values (variadic)
```

---

### Logic / Comparison

```
a b AND
a b OR
a NOT
a b EQ      // handles ^ on either side
a b NEQ     // handles ^ on either side
a b IFG     // if a > b, output a, else ^
a b IFL     // if a < b, output a, else ^
a ISOK      // 1 if a is not ^, 0 if a is ^
a SAFE      // a if not ^, 0 if ^
```

---

### List / Sequence Operators

```
a b c sA SETL       // create list sA from values a b c
$: sA SETL          // create list sA from full stack
sA: APD c:          // append c to sA
sA: sB: ISECT
sA: sB: UNION
sA: sB: SUBT
a sB: HAS
sA:n                // index n into sA — ^ if out of bounds
sA:-1               // last element
```

#### Inline Lists

`[1 2 3 4]` — no spaces around brackets — is a single list literal token.
`{ 1 2 3 }` with spaces is a scope block. Parser rule: `[` with no preceding whitespace starts a list literal.

```
[1 2 3]     // list literal token
{ 1 2 3 }   // scope block
```

#### Indexing

```
1 3 2 5 a SETL  // a = [1 3 2 5]
a:0             // 1
a:-1            // 5
a:1             // 3
a: 1 -1 SLICE   // [3 2]
```

#### Aggregation
```
li: >OP> AGG
li: >OP> PAGG
li: >OP> PREDUCE
```

#### Selection / Mapping
```
tgL: >ent API_DISTANCE> SELECT
li: >3 GT> SELECT
li: a0 MINDEX
li: idx AT
```

#### Pick
```
idxSeq: srcSeq: PICK
```

---

### Control Flow

```
val IF {
    ...
}

1 3 i FOR {
    ...
}

1 3 RANGE
```

---

### Concatenation

```
1 2 3 sA SETL
a b 5 sB SETL
sA: sB: CAT     // [1 2 3 a b 5]
sA: GLUE        // 123
sym DECAT
```

---

## API Process Handles

A process handle is returned by async operations. `@handle` is a display annotation — not user-typed.

```
from to time setter TWEEN _ tw SET
```

Handle states via `tw.state`:

| Value | Meaning |
|---|---|
| 0 | not started / cold |
| 1 | running |
| 2 | paused |
| 3 | ended |
| 4 | at start (rewound) |

Invalid handle: `tw:` returns `^`.

```
tw: ISOK { ... }    // check before use
tw.prog             // progress 0.0–1.0
```

### Process Operators

```
tw PLAY     // play or resume — 1 ok, 0 cant, ^ invalid
tw PAUSE    // pause — 1 ok, 0 cant, ^ invalid
tw RESTART  // stop + play with same args, handle stays valid
tw KILL     // stop + deallocate, handle becomes ^
```

### Process Chaining

`THEN` attaches a scope to fire when a process finishes.

```
dly.state 3 EQX {
    dly RESTART
    dly THEN {
        turret API_SHOOT
    }
}
turret API_TRACK_TARGET
```

`THEN` rules:
- Takes handle + scope block
- Scope fires once on state reaching `3`
- If handle is killed before firing, scope is discarded
- `THEN` returns the handle (chainable)
- Replaces any previously attached `THEN` scope on that handle

---

### Delay

```
0.34 DELAY _ dly SET
```

---

### Triggers

Triggers fire from API only. User defines handler scope.

```
ON_USED {
    ...
}
```

---

### IDE Panels

Four panes: **Code | Runtime | Stack | Variables**

```
code              | runtime              | stack
3 a SET           | 3 a SET              | a=3
a: _ 7 ADD _ b SET| a: 3 7 ADD 10 b SET  | b=10
5 0 DIV _ c SET   | 5 0 DIV ^            | (unchanged)
```

---

### Fibonacci Example

```
0 a SET
1 b SET
0 s SET
a b flist SETL
13 i FOR {
    a: b: ADD _ c SET
    c: flist: APD
    c: s: ADD _ s SET
    b: _ a SET
    c: _ b SET
}
s: LOG
flist: LOG
```

---

### Min Distance + Threshold Example

```
API_GET_TARGETS _ tgL SET
tgL: >ent API_DISTANCE> SELECT _ MINDEX _ tgL: AT _ closest SET
closest: API_DISTANCE _ 50 IFL _ 4 ENTITY_SECTOR_CEIL_Z_SET
```

---

### Open Items

- `SETL` from symbols vs values: both use same syntax, disambiguation is by whether tokens are bare symbols or dereferenced. Bare `a b c sA SETL` stores symbol references. Dereferenced `a: b: c: sA SETL` stores values. Needs runtime confirmation.
- `SUM` variadic behavior with `;` frames: does SUM consume only above the frame or all? TBD.