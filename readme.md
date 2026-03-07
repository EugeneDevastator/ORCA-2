# ORCA-2 Grid Lang
## Grid Lang — Fundamental Rules
## how about CRISP for a name? like lisp but crisp
---

## Execution Model

- Grid scans **left to right**, **top to bottom**, once per tick
- Every cell executes exactly once per tick - improve with execution on change only.
- Writes are **collected during scan**, applied **after full scan completes**
- No operator reads from below — bottom is write-only 

---

## Core principles:
1. **Observable Debuggability**
	- this means that all outputs are transparent, and only references are implicit. no functions silently consumes or passes stuff around.
	- for ex. 2 3 SUMR SET b - is invalid. SUMR will just overwrite SET kw.
2. **Parallel spotwise-execution**.
	- some fuunctions are processes that can start end and terminate, and execute more that once per tick. but output only at tick rate.
	- nothing is executed without a BANG *
3. **English letters only**. Time and again - strings are NAMES, or IDENTIFIERS not text not languages. we can have string as separate obj, but all language is ANSI charset.
4. Nightmare of Fon Neuman - references can store functions, code can become mangled. SET a SUMR - valid.
5. Write once, Debug twice, read never. 


## Cell Types

| Content | Type | Behavior |
|---|---|---|
| empty / `.` | empty | ignored |
| numeric literal | number | readable value |
| known keyword | operator | executes on scan |
| anything else | string | readable value, no execution |

---

## Operator I/O Contract

| Direction | Role |
|---|---|
| LEFT | read inputs (up to 2, nearest non-empty) |
| TOP | read input or trigger |
| RIGHT | write output — continues same row same tick |
| BOTTOM | write output — deposits to row below, next tick |

An operator writing right AND down does both simultaneously. Bottom write is fire-and-forget.

---

## Input Reading

- Operator reads up to 2 nearest non-empty cells to its left
- `B` = immediate left neighbor
- `A` = second left neighbor
- Empty cells and `.` are skipped during read

---

## Output Suffixes

| Suffix | Write target |
|---|---|
| `R` | next cell to the right |
| `D` | cell directly below |
| none | reads Left and Right, writes below. default Orca like behavior |
						  
---

## Cell Expansion

- A cell may expand rightward, spanning multiple columns
- Expanded cell reads its input from the first non-occupied cell to its right edge
- Writes expand **leftward** — result lands at left edge of operator
- A literal or any non-empty cell blocks expansion

---

## Routing

- `F` — forwards left value to next non-empty cell to the right, skipping empty cells
- Without `F`, operators use whatever neighbors they have — no implicit long-range reads
- Gaps are bridged explicitly with `F`

---

## Stack Row

- Each row's downward writes land in the row below as a logical list
- Row below is not fixed-position — scanner reads it as ordered sequence
- Multiple operators in one row each deposit independently into row below

---

## Timing and Latency

- Same-row chain: **zero latency** — right-writes propagate within same tick
- Cross-row: **one tick latency per depth level**
- Feedback (writing back upward): visible **next tick**

---

## Operator Reference

| Operator | Reads | Writes | Notes |
|---|---|---|---|
| `SUMR` | A, B left | A+B right | |
| `SUMD` | A, B left | A+B down | |
| `MULR` | A, B left | A×B right | |
| `MULD` | A, B left | A×B down | |
| `IFGR` | A, B left | 1 if A>B else 0, right | |
| `PICKD` | index left | nth non-empty right → down | 1-based index |
| `F` | B left | B → next non-empty right | skips empty cells |

---

## Example

```
[10][25][IFGR][1][PICKD][slow][fast]
                  ↓
              [slow]          ← 10 > 25 is false → index 1 → "slow"
```

```
[3][4][SUMR][2][MULR]
        ↓         ↓
       [7]       [14]         ← SUMR writes 7 right into MULR, MULR writes 7×2=14 down
```

# types
- Number - always signed float.
- text  - a symbol, not a real string, used for variable names, coments, etc.
- /var - resolves variable to a number or reference.
	- some references can be hidden, for ex `GET x entity` - will get x value of entity.
	- both x and entity - are hidden, but exposed as text.
	
## Nulls
There is no nulls. most i can think of is emitting -0 (minus zero) as replacement for a null. but no NO FUCKING NULLS AND NULL CHECKS.

## References
- dereferencing is done by / slash. not sure if it will be parsed ok so think more.
- symbols are only resolved on slash.

```
SET a 124
/ a SHOWR 124
/
set a b
set b 11
/ a b
/ a _ / 11
// a 11
/// a 0
b 2 SUMR _ SET b
/ b 13
INC b
/ b 14

```

beter option - use ":"
a: means 'unpack' 'dereference' a
:a means 'value of' - probably the only implicit stuff. not sure
```
SET a b // set a to b
SET b 11 // set b to 11
a : b
a : b : 11
:: a 11
::: a 0
b : 11 2 SUM: 13 >> b
b : 13
INC b
b : 14 >> a 
a : 14
a: 14 // shorthand for value read.
:a    // doesnt execute on its own, unless holds operator.
LISTD :a b
[] : 14 b



```



## Lists
list variables can be formed like this:
```
a b c d f LISTR []

LIST a b c d f g h |
[] >> a // great no we have recursive list :D

a : a b c d f g h   // will write list to the right. can also do down
 // note that this unfold is still valid. and a still holds the list
```

Any operations that dont expect list will operate on first element or 0.
aggregated lists are not shown by default.

### parsing
```
SET water 77.3
fire water erth LIST: [] SET descs
SETLIST nums 4 2 3 1 // count differs.
nums MINDEXR 3 ITEM descs // ITEM gets item at index: idx ITEM list
               -0    // because no such index

LEND descs LEND nums
3    MIN   4
  0  3     nums SLICE: [] MINDEX: 1 ITEM descs   // sliced[] can be linq style 
                                    water : 77.3   // q. essentially wrapping
                                                // some iterator

```

## Switch/case
```
SET cmd lock

    *
cmd SWITCHD
    act
    lock * TWEEN_TO PROP_ENTITY_CEIL_Z someheight 2 // over 2 sec
         R * PRINT 'hey hey'
    
    nop
    ; // stops propagation down for switchd,
     
                
```


## Custom functions
functions are defined by:
1. number of parameters
2. intake source
3. output destinations.
a0 and b0 are mulptiple params references.
```
              [u]
DEF x y z [b] FNAME p q r [a]
DEF FNAME
	[l0] [l1] ADD
	          * 3 [r0] MAXD
	                   * RET d 2 // writes down 2   
	                   R * RET r 0 // writes same to the right.
	          
ENDEF
```               

### Directionality.
- _R means results are always next to the right of the function. it can only take in left or up. OR EVEN BETTER - use : to signify that output is on the right.
- RR means it will write many potentially corrupting rest of row.
- _D means it will output down. can take l,r,up
- no suffix = default Orca func - read l AND r, write down.




# Processes.
processes have few things  to keep:  
- they run internally, regardless of bang.
- loop is a process. even tho it apparently executes in same frame

## Loops

```
/fibonacci n
SET a 1
SET b 1
LOOP 4   // whenever in same tick compiler encounters it will be in same tick.
	SUMD a b
	? SETTO c
	b >> a
	c >> b
	c ]] res // pushes into the list implicitly. var becomes list if it isnt.
ENDL
RETD res
```
