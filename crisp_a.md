## Crisp Language Spec v1.3

---

### Core Model

A program is a list of **rows**. Each row executes left to right.

**Stack** is per-row, reset each row unless `;` is used.

**Execution rule:** A token is either a **literal** (pushes to stack) or an **operator** (consumes stack, produces output). Execution continues as long as tokens produce output.

**Default values:** All variables default to `0`. Uninitialized reads return `0`.

---

### Stop Symbol `^`

`^` is an error sentinel — a typed value distinct from all numeric values including `0`.

`^` originates only from:
- Math operations with undefined results (`DIV` by zero, `SQRT` of negative)
- API calls that receive `^` as any argument — banned, return `^`
- API calls that fail (invalid object, missing property, bad state)
- Explicit user push: bare `^` token

`^` is **not** produced by uninitialized variable reads (those return `0`).

**Propagation rule:** `^` is a value on the stack. Operators that cannot process `^` return `^`. This naturally propagates through a row until the row ends or a `^`-aware operator handles it.

Inside `[ ]`: if `^` reaches the end of a scope without being handled, the scope exits and pushes `^` onto the parent stack. Parent row then encounters `^` and propagates the same way.

**No special unwinding.** `^` propagates by value, not by exception mechanism.

```
5 0 DIV _ c SET     // DIV produces ^, SET receives ^, returns ^, row ends
player.weapon: a SET // weapon missing -> ^ -> a = ^
a: API_FIRE         // API receives ^, returns ^, row ends
```

---

### `^`-Aware Operators

These operators explicitly handle `^` and do not propagate it:

```
a: ISOK             // pushes 1 if a is not ^, 0 if a is ^
a: 0 ORDEF          // pushes a if not ^, else pushes 0
a: ^ EQ             // 1 if a is ^, 0 otherwise — EQ handles ^ on both sides
a: ^ NEQ            // inverse
```

`SW` and `SWEQ` can match `^` as a case:

```
val SW [
    _ ^ EQ   "error"  PRIN 1
    _ 5 LESS "lt5"    PRIN 1
    _         "else"  PRIN 1
]
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
_           // empty space placeholder, cannot be stored or pushed onto stack. interpreter just skips it or writes over it.
```

#### Sigils

| Sigil | Role |
|---|---|
| `_` | capture result inline — binds last output to next token |
| `a:` | dereference — evaluate symbol a, push its value |
| `;` | stack frame marker — sets min stack pointer, stack below readable but not erasable |

#### Lambdas
```
>OP>                // operator as data, single op
>a0 a1 ADD>         // closure with positional args
4 p3ow              // apply: expands positional args left to right
```

---

### Scope

`[` and `]` delimit scope blocks. Stack frame is saved on `[`, unwound on `]`.

`^` reaching scope end exits scope and pushes `^` to parent stack.

```
val IF [
    5 0 DIV         // ^ here, scope exits, ^ pushed to parent
    4 API_CALL      // never fires
]
// parent stack now has ^ on top
```

---

### Variables

All variables default to `0`. No uninitialized errors.

```
b a SET         // set a to b
11 b SET        // set b to 11
a:              // push value of a (0 if never set)
b: 13 2 SUM     // dereference b, then sum
INC b           // increment b in place
```

`SETV` copies value (not reference):
```
b a SETV        // a = value of b
```

`SETL` creates a named sequence from symbols:
```
a b flist SETL  // flist is sequence of symbols [a, b]
```

---

### Stack Frames

`;` sets a min stack pointer mid-row. Operators can read past it but cannot erase below it.

```
1 2 SUM _ 3 4 ; 6 3 DIV _ ; SUM _
```

---

### Property Access

`.` is for engine objects only. Accessing a nonexistent property produces `^`.

```
profile .shared
profile .inst _ .components _ .count
pos.x:              // dereference field x of pos
3 pos.x SET         // write 3 to field x of pos
```

User-defined variables do not support `.` syntax. Attempting it produces `^`.

---

### Switch

#### `SW` — predicate match
```
val SW [
    _ 5  LESS  "lt5"  PRIN 1
    _ 7  LESS  "lt7"  PRIN 1
    _          "else" PRIN 1
]
```

#### `SWEQ` — equality match
```
val SWEQ [
    5    "five"  PRIN 1
    7    "seven" PRIN 1
    ^    "error" PRIN 1
    _    "else"  PRIN 1  // using placeholder as 'anything else'
]
```

---

### Math Operators

```
a b ADD     // a + b
a b SUB     // a - b
a b MUL     // a * b
a b DIV     // a / b  — produces ^ if b is 0
a b POW     // a ^ b
a SQRT      // produces ^ if a < 0
a INC     // a = a + 1
a b ADDv    // b = a + b  (in-place)
```

---

### Logic / Comparison

```
a b AND
a b OR
NOT a
a b EQ      // handles ^ on either side
a b NEQ     // handles ^ on either side
a b IFG     // if a > b, output a, else ^
a b IFL     // if a < b, output a, else ^
IFT         // if top of stack is truthy, continue, else ^
a ISOK      // 1 if a is not ^, 0 if a is ^
a SAFE   // 0 if a is ^, a if a is not ^
```

---

### List / Sequence Operators

```
a b c sA SETL
sA APD c:
sA sB ISECT
sA sB UNION
sA sB SUBT
a sB HAS
a sB HASANY
a sB HASALL
sA:idx              // index into sequence — ^ if out of bounds
sA: -1              // last element
```

#### Aggregation
```
li >OP> AGG
li >OP> PAGG
li >OP> PREDUCE
```

#### Selection / Mapping
```
tgL >ent API_DISTANCE> SELECT
li >3 GT> SELECT
li a0 MINDEX
li idx AT
```

#### Pick
```
idxSeq srcSeq PICK
```

---

### Control Flow

```
val IF [
    ...
]

1 3 i FOR [
    ...
]

1 3 RANGE
```

---

### Concatenation

```
1 2 3 sA SET
a b 5 sB SET
a b CAT ab
7 1 CAT 71
sA: sB: CAT [1 2 3 a b 5]
sym DECAT
sA: GLUE 123
```

---

### Process Handles

Deref returns state: `0` = invalid/stopped, `1` = running, `2` = paused.

```
tw PSTOP
```

---

### Tween / Delay

```
from to time setter TWEENa_ tw SET
0.34 DELAY _ dly SET
```

---

### IDE Panels

Four panes: **Code | Runtime | Stack | Variables**

```
code              | runtime              | stack
3 a SET           | 3 a SET              | a=3
a: _ 7 SUM _ b SET| a: 3 7 SUM 10 b SET  | b=10
5 0 DIV _ c SET   | 5 0 DIV ^            | (unchanged)
```

`^` shown in runtime column at point execution stopped. Variables panel shows `^` for any variable holding the sentinel.

---

### Fibonacci Example

```
0 a SET
1 b SET
0 s SET
a b flist SETL
13 i FOR [
    a b SUM _ c SETV
    c: flist APD:
    c s SUM _ s SETV
    b a SETV
    c b SETV
]
s LOG
flist LOG
```

---

### Min Distance + Threshold Example

```
API_GET_TARGETS tgL SET
tgL >ent API_DISTANCE> SELECT _ MINDEX _ tgL AT _ closest SET
closest API_DISTANCE _ 50 IFL
    4 ENTITY_SECTOR_CEIL_Z_SET
```