
    ## Crisp Language Spec v1.5
    language primarily oriented as scripting for games and programs.
    basic math and api object management.
    ---

    ### Core Model

    A program is a list of **rows**. Each row executes left to right.
    each row consists of positional arguments. positions cannot be removed or added.
    each operator writes to right of it, overwriting any tokens in front. for that reason empty positions are marked as '_' in language code. positional separator is 'space' and empty position is '_' for that reason.

    **Stack** is per-row. Operators consume from stack.

    **Execution rule:** A token is either a **literal** (pushes to stack) or an **operator** (consumes stack, produces output). Operators write output into the next slot.

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

    ---

    ### Stack Consumption

    Operators consume exactly their required inputs from the top of stack.
    for ex.
    1 2 3 4 ADD _ ADD _ ADD // will sum all numbers. resultin in 1 2 3 4 ADD 7 ADD 9 ADD 10
    
    ---

    ### Stack Frames and `$`

    `$` is a symbol referring to the current stack as a list. It is readable and writable.

    ```
    $:          // push entire stack as list
    $:0         // first element
    $:-1        // last element
    $:-2        // second from last
    3 $ SET     // replace stack with [3]
    ```

    `$` always sees the full current stack
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
    | `a:` | read variable a, push its value |
    | `$` | stack reference — current stack as readable/writable list |

    ---

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
    0 b SET
    b a SET        // read b, store value into a
    11 b SET        // set b to 11
    
    1 c SET
    c a SET         // sets a to value of c.
    @c a SET        // sets a to symbol c.

    b 1 ADD _ b SET  // increment b
    ```

    ---

    ### Property Access

    `.` is for engine objects only. Accessing a nonexistent property produces `^`.

    ```
    profile.shared:
    profile.inst: _ .components _ .count
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

    `*` is the default/fallthrough case. Only valid inside `SW` and `SWEQ`.

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
    $ sA SETL          // create list sA from full stack
    sA c APD         // append c to sA
    sA:n                // index n into sA — ^ if out of bounds
    sA:-1               // last element
    sA:idx              // dynamic index — idx resolves immediately
    ```



    #### Inline Lists

    `[1 2 3 4]` — no spaces around brackets — is a single list literal token. spaces are also allowed
    [ 1 2 3 4 ] 
    `{ 1 2 3 }` with spaces is a scope block.
    {1 2 3} also ok, brackets are comppiler trigger in itself.

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
    a:idx           // element at index idx — resolved at runtime
    a 1 -1 SLICE   // [3 2]
    ```

    #### Aggregation
    ```
    li >OP> AGG
    li >OP> PAIRAGG // pair-wise parallel aggregation, ends in one element. (a+b)+(c+d)+e
    li >OP> REDUCE2 // pair-wise operation, applies operation reducing list in half: [a+b, c+d, e]
    ```

    #### Selection / Mapping
    ```
    targList >$ entity API_DISTANCE> SELECT
    li >3 GT> SELECT
    li: a0 MINDEX
    li: idx AT
    ```

    #### Pick
    ```
    idxSeq srcSeq PICK
    ```

    ## Symbolics, and sets
    symbolic computation is secondary language feature, requires explicit use.
    for ex.
    postfix @ - marks something to be treated as symbol without default dereferencing.
    : - forced dereference operator, again not intended for general use

    1 b SET // sets b to 1
    b a  // sets a to store symbol b.
    @b a SET // sets a to store symbol b // use symbolic escape.
    a b c sA SETLSYM // makes list out of symbols
    b 1 2 sB SETLSYM // makes list out of symbols, 1 and 2 retained.
    a : b : 1

    symbol comparison works similar to stirngs, because for compiler symbolic name is just a char array.
    @b a SET
    @b c SET
    a c EQ 1 // dereferences both a and b, sees symbol b.
    1 @b EQ 0 // never equal.
    1 @b LESS 1 // numbers are less than symbols.


    ### set operations
    Set operations never dereference anything they are symbolic by default.
    sA sB ISECT // [b] // list of symbol b
    sA sB UNION // [a b c 1 2] // all symbols
    sA sB SUBT // [1 2] // b-a
    a sB HAS

    ### data joining/parsing
    API_GET_TARGETLIST targlist SET
    API_GET_WEAPON_INFOS weaponlist SET
    targlist > . weapon . id> SELECT ewepids SET
    weaponlist > . id> SELECT dbids SET
    weaponlist > . name> SELECT dbnames SET
    ewepids > $0 dbids FINDEX _ dbnames AT > SELECT _ perentitynames SET

    targlist perentitynames ZIPMIN _ >$:0 . name " " $:1 CAT _ PRN> 


    [11 22 33] p SET
    [a b c d] q SET
    [ZZ XX WW] r SET
    p q r ZIPR zi SET // zips and repats last [[11 a ZZ] [22 b XX] [33 c WW] [33 d WW]]
    zi >$:2 i "|" CATSP _ PRN> SELECTi _ // prints: ZZ 0 | XX 1 | WW 2 | WW 3
    // CATSP inserts string space between entries.

    ZIP ops
    ZIPMIN - zips clipping for min length
    ZIPMAX - zips clipping for max length, filling with 0.
    ZIPR - zips max, but repeats last.
    can zip multiple sequences, picks everything from the stack.
    treats single variables as list of one element. 


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
    sA sB CAT     // [1 2 3 a b 5]
    sA GLUE        // 123
    sym DECAT
    ```

    ---

    ### Lambdas

    ```
    >OP>                // operator as data, single op
    >a0 a1 ADD>         // closure with positional args
    4 lambda APPLY      // expands positional args left to right
    ```

    ---

    ### API Process Handles

    A process handle is returned by async operations.

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
    tw ISOK { ... }    // check before use
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
        a b ADD _ c SET
        c flist APD
        c s ADD _ s SET
        b a SET
        c b SET
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

    - `SETL` from symbols vs values: bare `a b c sA SETL` uses current values of a, b, c. 
