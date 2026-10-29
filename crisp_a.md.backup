Aye Captain!

## Crisp language v1.0

---

### Core Model

A program is a list of **rows**. Each row executes left to right.

**Stack** is per-row, reset each row unless `;` is used.

**Execution rule:** A token is either a **literal** (pushes to stack) or an **operator** (consumes stack, produces output). Execution on a row continues as long as tokens produce output. If an operator fails to produce output, execution of that row **stops** (no error, just stops).

**Output slot:** Every operator that succeeds writes its result to the right — this result is immediately pushed onto the stack for the next token.

---

### Tokens

#### Literals
Push directly onto stack.

```
42          // integer
3.14        // float
"hello"     // string
0 1  // bool, also integers.
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
>3 a0 POW> p3ow SET
4 p3ow:            // when we dereference lambda it is considered an execution.
```

---

### Scope

`[` and `]` delimit scope blocks. Stack frame is saved on `[`, unwound on `]`.

```
val IF [
    4 ENTITY_SECTOR_CEIL_Z_SET
]
```


### Variables

```
b a SET         // set a to b
11 b SET        // set b to 11
a:              // push value of a
b: 13 2 SUM     // dereference b, then sum
```

SETV copies value (not reference):
```
b a SETV        // a = value of b
```

SETL creates a named sequence from symbols:
```
a b flist SETL  // flist is sequence of symbols |a b|
```

---

### Stack Frames

`;` sets a min stack pointer mid-row. Operators can read past it but cannot erase below it.

```
1 2 SUM _ 3 4 ; 6 3 DIV _ ; SUM _ // 1 SUM 3 3 4 ; 6 3 DIV 2 ; 4 2 SUM
// each ; moves the floor. final SUM sees 2 across the last frame.
```

---

### Switch

#### `SW` — predicate match
Each row receives the SW value injected as `_`. First row where execution does not stop wins. `_` alone = default/wildcard.

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
a b DIV     // a / b
a b POW     // a ^ b
a INC       // a = a + 1
```

Invalid arguments downgrade to `-0`. No nulls — all symbols default to `-0`(minus zero)

---

### Logic / Comparison

```
a b AND
a b OR
a NOT
a b EQ
a b NEQ
a b IFG     // if a > b, output a, else stop
a b IFL     // if a < b, output a, else stop
IFT         // if top of stack is truthy, continue, else stop
```

---

### List / Sequence Operators

Sequences are runtime values. Editor may render them visually but no literal syntax in source.

```
a b c sA SETL       // create sequence sA from symbols
sA APD c:           // append value of c to sA
sA sB ISECT         // intersection
sA sB UNION         // union
sA sB SUBT          // subtraction
a sB HAS            // 1 if a in sB
a sB HASANY         // 1 if any of a in sB
a sB HASALL         // 1 if all of a in sB
sA:idx              // index into sequence
sA: -1              // last element
```

#### Aggregation
```
li >OP> AGG         // reduce list to single value
li >OP> PAGG        // pairwise parallel aggregation, returns sequence
li >OP> PREDUCE     // parallel reduce using threads
```

#### Selection / Mapping
```
tgL >ent API_DISTANCE> SELECT    // map: apply lambda per element, return sequence
li >3 GT> WHERE                 // filter: keep elements where lambda produces output
li MINDEX                     // index of minimum value
idx li AT                        // element at index
```

#### Pick
```
idxSeq srcSeq PICK    // select elements from srcSeq by indices
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

1 3 RANGE           // produces sequence 1 2 3
```

Stop-on-fail is the primary branching mechanism. No explicit else — structure rows so the failure case simply stops.

---

### Concatenation

```
a b CAT             // concatenate symbols → ab
7 1 CAT             // 71
sA sB CAT           // join two sequences
sym DECAT           // split symbol into sequence of single-char symbols
sA GLUE             // join sequence of symbols into one symbol
```

---

### Property Access

`.` is for engine objects only.

```
profile .shared
profile .inst _ .components _ .count
```

---

### Process Handles

Deref returns state: `0` = invalid/stopped, `1` = running, `2` = paused.

```
tw PSTOP            // stop process tw
```

---

### Tween / Delay

```
from to time setter TWEENa_ tw SET
0.34 DELAY _ dly SET
```

Named arguments pulled from variables by name.

---

### IDE Panels

Four panes: **Code | Runtime | Stack | Variables**

- Runtime: shows row after execution with resolved symbols
- Stack: state at end of row
- Variables: current symbol table

```
code              | runtime            | stack
3 a SET           | 3 a SET a          | a
a: _ 7 SUM _ b SET| a: 3 7 SUM 10 b SET| b 7 1
PSTACK[0]: _      | PSTACK[0]: 1       | 1
```

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
    
tgL >ent API_DISTANCE> SELECT _ tgL >MIN> ZIPAGG
```

- `SELECT` maps each entity to its distance
- `MINDEX` returns index of minimum
- `tgL AT` gets the entity at that index
- `API_DISTANCE` recomputes distance for closest
- `50 IFL` — stops row if not less than 50
- `4 ENTITY_SECTOR_CEIL_Z_SET` fires only if threshold passed