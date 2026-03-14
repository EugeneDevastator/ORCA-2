Aye Captain!

## 'Crisp' Language Spec v1.2

---

### Core Model

A program is a list of **rows**. Each row executes left to right.

**Stack** is per-row, reset each row unless `;` is used.

**Execution rule:** A token is either a **literal** (pushes to stack) or an **operator** (consumes stack, produces output). Execution on a row continues as long as tokens produce output. If an operator produces `^`, execution of that row stops and unwinds through all enclosing scopes until it exits or hits a scope boundary that catches it.

**Output slot:** Every operator that succeeds writes its result to the right — this result is immediately pushed onto the stack for the next token.

---

### Stop Symbol `^`

`^` is the universal stop value. When any operator produces `^`, execution halts immediately at that point and propagates outward through enclosing `[ ]` scopes.

- Any operator receiving invalid input produces `^`
- Division by zero produces `^`
- Failed property access produces `^`
- User can push `^` explicitly to force stop
- `^` is a valid symbol name if assigned — compiler treats bare `^` as the stop command

```
5 0 DIV         // produces ^, row stops here
5 0 DIV _ c SET // ^ propagates, c SET never fires
```

State is never mutated after `^` is produced on a row.

---

### Tokens

#### Literals
Push directly onto stack.

```
42          // integer
3.14        // float
"hello"     // string
1 0  // bool
^           // stop — halts execution immediately
```

#### Sigils

| Sigil | Role |
|---|---|
| `_` | capture result inline — binds last output to next token |
| `a:` | dereference — evaluate symbol a, push its value |
| `;` | stack frame marker — sets min stack pointer, stack below is readable but not erasable |

#### Lambdas
```
>OP>              // operator as data, single op
>a0 a1 ADD>       // closure with positional args a0 a1
4 p3ow            // apply: expands positional args left to right
```

---

### Scope

`[` and `]` delimit scope blocks. Stack frame is saved on `[`, unwound on `]`.

`^` propagates through scopes — if produced inside `[ ]`, the scope exits immediately and `^` continues outward.

```
val IF [
    5 0 DIV     // ^ here exits the IF block and stops the row
    4 ENTITY_SECTOR_CEIL_Z_SET   // never fires
]
```

---

### Variables

```
b a SET         // set a to b
11 b SET        // set b to 11
a:              // push value of a
b: 13 2 SUM     // dereference b, then sum
INC b           // increment b in place
```

SETV copies value (not reference):
```
b a SETV        // a = value of b
```

SETL creates a named sequence from symbols:
```
a b flist SETL  // flist is sequence of symbols [a, b]
```

No default values. Uninitialized symbols produce `^` when read.

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
pos.x:          // dereference field x of pos
3 pos.x SET     // write 3 to field x of pos
```

User-defined variables do not support `.` property syntax. Attempting it produces `^`.

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
    _    "else"  PRIN 1
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
INC a       // a = a + 1
a b ADDv    // b = a + b  (in-place)
```

---

### Logic / Comparison

```
a b AND
a b OR
NOT a
a b EQ
a b NEQ
a b IFG     // if a > b, output a, else ^
a b IFL     // if a < b, output a, else ^
IFT         // if top of stack is truthy, continue, else ^
```

---

### List / Sequence Operators

```
a b c sA SETL       // create sequence sA from symbols
sA APD c:           // append value of c to sA
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

`^` inside any control structure exits that structure immediately and propagates outward.

---

### Concatenation

```
1 2 3 sA SET
a b 5 sB SET
a b CAT // ab
7 1 CAT //71
sA: sB: CAT // [1 2 3 a b 5]
sym DECAT // s y m
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
code              | runtime            | stack
3 a SET           | 3 a SET a          | a
a: _ 7 SUM _ b SET| a: 3 7 SUM 10 b SET| b 7 1
5 0 DIV _ c SET   | 5 0 DIV ^          | (unchanged)
```

`^` shown in runtime column at the point execution stopped.

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