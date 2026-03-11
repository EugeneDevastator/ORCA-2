a SWITCH
	usd _ 5
	eur _ 4 a SET
	gbp _ 7 8 9 10
ENDSW // here we'll have stack from executed row.

4 ENTITY_SECTOR_CEIL_Z_SET


Aye Captain!

## Language Spec v1.0

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
true false  // bool
```

# referencing draft:
a: means 'unpack' 'dereference' a
:a means 'value of' - probably the only implicit stuff. not sure
```
b a SET // set a to b
11 b SET // set b to 11
a : _ // executes as a : b
a : _ : _ // executes as a : b : 11
a :: 11
b : 11 2 SUM: 13 b SET
b : 13
INC b
b : 14 a SET
a : 14
a: 14 // shorthand for value read.
:a b c list SETL // sets list to 14 b c;

**Fibonacci, 15 numbers:**
```
0 a SET 
1 b SET
0 s SET
a b flist SETL // makes flist [a: b:]
a b reflist SETL* // makes reflist of symbols [a b]
a b s SUM _ s SET // sum implicity dereferencfes variables.
13 i FOR
    a b SUM _ c SETV
    c: flist APD: // append value of c.
    c s SUM _ s SETV
    b a SETV // SETV is equal to b: a SET
    c b SETV
END
s LOG 
flist LOG // prints every element to console
```

# IDE draft.
ide consists of 4 panes:
Code, runtime code, stack at the end of line execution, variable view.
in runtime code view we see what line looked like after execution, and symbols are wwrritten there after each step.
example, panels are separated by |
code | run | stack
3 a SET | 3 a SET a | a
a: _ 7 SUM _ b SET _ 7 1 | a: 3 7 SUM 10 b SET b | b 7 1
PSTACK[0]: _ | PSTACK[0]: 1 | 1

# stack preserve
';' preserves stack
1 2 SUM _ 3 4 ; 6 3 DIV _ ; SUM _ | 4 1 SUM 5 ; 6 3 DIV 2 ; SUM 7 ; // each time l is called min stack pointer moves. operators can read past it, but cant erase stack past last ;


# closures

1 0 1 1 OR 1 0 1 1 NOT> [wole stack] AND 
        or consumes prev. stack

4*(2+ (7/4))

7 4 DIV . 2 ADD . 4 MUL

7 4 DIV . 2 ADD . 4 MUL

; 7 4 DIV ; 7 3 DIV ; 2 SUM

stack has min range - ';' sets 
a b c d e f g

3 4 5 6 7 2 MUL 14
stack: 3 4 5 6 14
3 4 5 6 3 DIV

b: _ c SET
b c SET

sym.

b c SET
/b c SET
a b MUL
/a /b c SETL

/MUL c SET
3 4 c: 12
/SET c SET
3 b c: // b is set to 3

c: - means unpack / execute.
/c - means use symbol.

MATH operators.
TRUTH AND FALSE: * ^

implicitly unpack variables.
a b c .. SUM 
a b c .. PROD
a b ADD b+a
a b SUB a-b
a b DIV a/b
a b IFG 0
a b ADDv b= a+b



a b IFG
0. 3 4 SUB
1.

LAMBDAS

/0 3 /DIV myfun SETC // set closure.
7 myfun: 7/3 
myfunc SETC /0 /1 ADD _ /2 DIV _ SQR



PROCESS HANDLES.
deref return state: 0 = invalid/stopped. 1 = is running. 2 = is paused.
ENT_GET_SECT: _ sec SET

API_SET_CEIL_Z_AT_SEC sec _0 _ setter SET // creates lambda

a SW
open. tw: _ ; dl: _ NOT _ ; PROD _ IFT | from to time setter TWEEN _ tw SET _ 0.34 DELAY _ dly SET | tw PSTOP
lock. islocked FLIPv
stop. tw PSTOP


