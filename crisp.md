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
open. tw: _ ; dl: _ NOT _ ; PROD _ IFT | from to time setter TWEENa_ tw SET _ 0.34 DELAY _ dly SET | tw PSTOP
lock. islocked FLIPv
stop. tw PSTOP


// implicit setters
2 from 
1 to
0.4 sec
&ENTITY_COLOR_A_SET setter
TWEEN _ tw SET // TWEEN uses named arguments from variables.

& /0 ENTITY_PAL_GET . 7 EQ . filter SET // lambda wrapped in [& .. varname SET]
ENTITY_PAL_GET 7 EQ filter SET // implicit insertion of results. unwraps to: /0 ENTITY_PAL_GET . 7 EQ . filter SET
    
// MATH SETS. list is a sequence of elements.   we dont distinguish sets and list in memory. 
// equals always compares whatever it sees 1 x SET; x == x;	x: == x false ; 1 != x
// Key datatypes:
// literal - numbers or engine objects. engine object displayed as #TypeName
// symbol - any lowercase word
// list - sequence of any above.
// nested lists are allowed. [a b [c d] e]
// invalid arguments are always downplayed to -0 minus zero:  3 [a b] SUM > sum treats them as 3 0, and result is 3.
// no nulls. all symbols are automatically set to -0 minus zero.
	
a b c sA SETL
c d e sB SETL
//mset operations are just symbolic comparisons.//
sA sB ISECT [c]
sA sB UNION [a b c d e]
sA sB SUBT [d e]
a sB HAS 0
[a c] sB HASANY 1
[a c] sB HASALL 0
// ============ LISTS


a sA AGGEQ 1 // aggregate on equals.
1 2 ADD _ exp SET 7 base SET base exp POW  
v1 v2 ADD _ exp SET; 7 base SET; base exp POW _ pwed SET;
[a b c d] [1 2 3 4] li SET; // lists retain visual order li0 is [a b c d]
li1 /SUM AGG 10 // Aggregate reduces list to a single non-list output.
li1 /MIN AGG 1
li1 /MAXDEX AGG 3 // max index
li1 /MAXDEX AGG 
li1 /SUM PAGG [3 7] // PAGG = pairwise parallel aggregation. returns list.
[1 1 1 1 1] /SUM PAGG [2 2 1] // on odd, retains last element.
li1 /SUM PREDUCE // parallel reduce using threads. 
>1 ADD> adder SET // linear lambda. arrows signify input and output.

li1 adder FILTER [2 3 4 5]
li1 >1 ADD> FILTER [2 3 4 5] // same
[a b c d] [0 0 1] PICK [a a b]


>3 a0 POW> p3ow SET // lambda with positional argument; a0 a1 are reserved.
4 p3ow // expands into 3 4 POW

// =============== CONCATENATION
2 a SET
7 ab SET
a b CAT ab : 7
7 1 CAT 71
[a b] c CAT [a b c]
[a b] [c d] CAT [a b c d]

abcd DECAT [a b c d]
[a b c d] GLUE abcd
[a ab 3 1] /: FILTER [2 7 3 1]				





