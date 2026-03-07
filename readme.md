# ORCA-2 Grid Lang
## Grid Lang — Fundamental Rules

---

## Execution Model

- Grid scans **left to right**, **top to bottom**, once per tick
- Every cell executes exactly once per tick - improve with execution on change only.
- Writes are **collected during scan**, applied **after full scan completes**
- No operator reads from below — bottom is write-only 

---

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