    ## Crisp Language Spec v1.7

    language primarily oriented as scripting for games and programs.
    basic math and api object management.

    ---

    ### Core Model

    A program is a list of **rows**. Each row executes left to right.
    Each row consists of positional arguments. Positions cannot be removed or added.
    Each operator writes its output to the next position, overwriting whatever token is there. Empty positions are marked as `_`. Positional separator is space.

    **Stack** is per-row. Operators consume from stack.

    **Execution rule:** A token is either a **literal** (pushes to stack) or an **operator** (consumes stack, produces output). Operators always write output into the next position AND push to stack. The next position is overwritten with the result value.

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
    5 0 DIV _ c SET     // DIV produces ^, written to _, SET stores ^
    player.weapon: a SET // weapon missing -> ^ -> a = ^
    a: API_FIRE         // API receives ^, returns ^
    ```

    ---

    ### Operator Output Contract

    Every operator produces output. No silent operators except X-variants.

    | Outcome | Output |
    |---|---|
    | Success | result written to next position and pushed to stack |
    | Failure | `^` written to next position and pushed to stack |
    | X-variant success | no output, execution continues |
    | X-variant failure | no output, row stops |

    ---

    ### Positional `_` Slots

    `_` is a positional placeholder. It cannot be stored or pushed as a value. It marks an empty position. When an operator executes, its result is written to the next position regardless — if that position is `_`, the result lands there and is available on the stack for the next operator.

    ```
    5 3 ADD _ x SET     // ADD writes result to _, result on stack, SET consumes it
    5 3 ADD x SET       // ADD writes result to x position, result on stack, SET consumes it
    _ 3 ADD             // error: ADD needs two operands, only one on stack
    1 _ 3 ADD           // _ is skipped as empty, 1 and 3 on stack, ADD produces 4
    ```

    ---

    ### Stack Consumption

    Operators consume exactly their required inputs from the top of stack.

    ```
    1 2 3 4 ADD _ ADD _ ADD   // result: 1 2 3 4 ADD 7 ADD 9 ADD 10
    ```

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

    `$` always sees the full current stack.

    ---

    ### Conditional Execution — `:` Operator

    `:` is the conditional execution operator. It consumes the top two values from the stack: a **match value** and a **test value**. If they are equal, what follows executes. If not, it is skipped.

    `:` reads the next token after itself:
    - If the next token is `{` — the entire scope block is conditionally executed or skipped. Jump addresses are compiled into IR bytecode. Never visible to the user.
    - If the next token is not `{` — execution continues to end of line only, then stops.

    ```
    str i AT _ myset HAS _

    1 : {
        str i AT _ pda PUSH
        some other ops
    }
    0 : {
        ...
    }
    ```

    Single-line form:
    ```
    str i AT _ myset HAS _
    1 : str i AT _ pda PUSH
    0 : 0 RETURN
    ```

    **Compiler behavior:** When `:` is followed by `{`, the compiler emits a conditional jump into IR with the block's end address backpatched after the block is parsed. No lookahead into source. No user-visible addresses.

    ---

    ### Scopes

    `{` and `}` delimit scope blocks. Stack frame is saved on `{`, unwound on `}`.

    Scopes may appear on multiple lines or collapsed to one line — both are valid:

    ```
    1 : { str i AT _ pda PUSH }

    1 : {
        str i AT _ pda PUSH
        some other ops
    }
    ```

    `^` reaching scope end exits scope and pushes `^` to parent stack.

    ```
    val IF {
        5 0 DIV         // ^ here, scope exits, ^ pushed to parent
        4 API_CALL      // never fires
    }
    // parent stack now has ^
    ```

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
    ^           // error sentinel — valid as literal and as match arm in SWEQ
    _           // positional placeholder — not storable, not pushable
    ```

    #### Sigils

    | Sigil | Role |
    |---|---|
    | `_` | empty positional slot |
    | `a:` | read variable a, push its value |
    | `@a` | treat a as symbol, do not dereference |
    | `$` | stack reference — current stack as readable/writable list |

    ---

    ### Variables

    All variables default to `0`. No uninitialized errors.

    ```
    0 b SET
    b a SET         // read b, store value into a
    11 b SET        // set b to 11

    1 c SET
    c a SET         // sets a to value of c
    @c a SET        // sets a to symbol c

    b 1 ADD _ b SET // increment b
    ```

    ---

    ### Symbolics

    Symbolic computation is a secondary feature requiring explicit use.

    `@` prefix marks a token as a symbol — suppresses dereferencing.

    ```
    1 b SET
    @b a SET        // a stores symbol b, not value 1
    ```

    Symbol comparison treats symbolic names as char arrays.

    ```
    @b a SET
    @b c SET
    a: c: EQ        // 1 — both hold symbol b, compared as strings
    1 @b EQ         // 0 — number never equals symbol
    1 @b LESS       // 1 — numbers sort before symbols
    ```

    #### `SETLSYM` — list of symbols

    ```
    a b c sA SETLSYM    // sA = [a b c] as symbols
    b 1 2 sB SETLSYM    // sB = [b 1 2] — symbols and literals retained as-is
    ```

    #### Forced Dereference `:`

    `:` forces dereference of a symbol value.

    ```
    a : b : 1
    ```

    Not intended for general use.

    ---

    ### Set Operations

    Set operations treat all contents as symbolic. No dereferencing.

    ```
    sA sB ISECT     // intersection
    sA sB UNION     // union
    sA sB SUBT      // sB minus sA
    a sB HAS        // 1 if a is in sB, 0 otherwise
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

    `^` is valid as a match arm in `SWEQ`. `*` is the default/fallthrough case. Only valid inside `SW` and `SWEQ`.

    ---

    ### Math Operators

    ```
    a b ADD     // a + b
    a b SUB     // a - b
    a b MUL     // a * b
    a b DIV     // a / b  — ^ if b is 0
    a b POW     // a ^ b
    a SQRT      // ^ if a < 0
    SUM         // sum of all values currently on stack — variadic, consumes entire stack
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
    a b c sA SETL       // create list sA from values a b c — arity determined by position count before name
    $ sA SETL           // create list sA from full stack
    sA c APD            // append c to sA
    sA:n                // index n into sA — ^ if out of bounds
    sA:-1               // last element
    sA:idx              // dynamic index — idx resolves at runtime
    ```

    **Note on `SETL` arity:** The compiler counts positional tokens before the destination name on the same row. This is resolved statically.

    #### Inline Lists

    ```
    [1 2 3]     // list literal token — brackets are compiler triggers
    [ 1 2 3 ]   // also valid
    ```

    #### Indexing

    ```
    1 3 2 5 a SETL  // a = [1 3 2 5]
    a:0             // 1
    a:-1            // 5
    a:1             // 3
    a:idx           // element at index idx — resolved at runtime
    a 1 -1 SLICE    // [3 2]
    ```

    #### Aggregation

    ```
    li >OP> AGG         // reduce entire list to one value
    li >OP> PAIRAGG     // pair-wise parallel: (a+b)+(c+d)+e — ends in one element
    li >OP> REDUCE2     // pair-wise step: [a+b, c+d, e] — reduces list to half length (ceiling)
    ```

    #### Selection / Mapping

    ```
    targList >$ entity API_DISTANCE> SELECT     // map: returns list of results
    li >3 GT> SELECT                            // filter: returns elements where lambda is truthy
    li: a0 MINDEX                               // index of minimum value in li
    li: idx AT                                  // element at idx
    ```

    #### `FINDEX`

    ```
    li >lambda> FINDEX      // returns index of first element where lambda returns truthy — ^ if none
    ```

    #### `SELECTN`

    ```
    li >lambda> SELECTN     // same as SELECT but feeds current index as `n` into lambda as local var. global n is not affected and not available in lambda
    ```

    #### Pick

    ```
    idxSeq srcSeq PICK      // returns list of srcSeq elements at indices in idxSeq
    ```

    ---

    ### ZIP Operators

    Zip multiple sequences. Picks all sequences from stack. Treats single variables as list of one element.

    ```
    p q r ZIPR zi SET   // [[11 a ZZ] [22 b XX] [33 c WW] [33 d WW]]
    ```

    | Operator | Behavior |
    |---|---|
    | `ZIPMIN` | clip to shortest sequence |
    | `ZIPMAX` | clip to longest, fill missing with `0` |
    | `ZIPR` | clip to longest, repeat last element of shorter sequences |

    ---

    ### Concatenation and String Operators

    ```
    sA sB CAT       // list concat: [1 2 3] + [a b 5] = [1 2 3 a b 5]
                    // string concat: "ab" "cd" CAT = "abcd"
    sA GLUE         // collapse list to single value: [1 2 3] -> 123
    sym DECAT       // split any value into list of single characters
    1 a 3 CATSP     // "1 a 3" — string with spaces between each token
    1 a 3 CAT       // 1a3 — no spaces, not a string type
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

    1 3 RANGE       // returns inclusive list [1 2 3]
    ```

    ---

    ### Lambdas

    ```
    >OP>                // operator as data, single op
    >a0 a1 ADD>         // closure with positional args a0, a1
    4 lambda APPLY      // expands positional args left to right
    ```

    ---

    ### Data Joining Example

    ```
    API_GET_TARGETLIST targlist SET
    API_GET_WEAPON_INFOS weaponlist SET
    targlist >.weapon.id> SELECT ewepids SET
    weaponlist >.id> SELECT dbids SET
    weaponlist >.name> SELECT dbnames SET
    ewepids >$:0 dbids FINDEX _ dbnames AT> SELECT perentitynames SET

    targlist perentitynames ZIPMIN _ >$:0 .name " " $:1 CAT _ PRN> SELECTN _
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

    Invalid handle access returns `^`.

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

    `THEN` attaches a scope to fire once when a process reaches state `3`.

    ```
    dly.state: 3 EQ _ 1 : {
        dly RESTART
        dly THEN {
            turret API_SHOOT
        }
    }
    turret API_TRACK_TARGET
    ```

    Rules:
    - Takes handle + scope block
    - Fires once on state `3`
    - If handle killed before firing, scope discarded
    - Returns handle (chainable)
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

    **Changes from v1.6:**
    - Removed X-Operators section — superseded by `:` conditional operator
    - Added Conditional Execution — `:` Operator section with full spec
    - Scopes section simplified — scope is now defined once, `:` operator section covers conditional scope usage
    - Process Chaining example updated to use `:` instead of removed `EQX`
    - `{ }` confirmed as sole scope delimiter — inline list literals use `[ ]` only