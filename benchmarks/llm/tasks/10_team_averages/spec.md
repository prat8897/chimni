# Average score per team

Average score for each team.

**Inputs**
- `players`: a list of records, each with `name` (text), `team` (text) and `score` (integer).

**Output**
- A list of (team, average) pairs: one per team, with the mean `score` of that team's players.
  Groups appear in the order their key first appears in the input.

**Edge cases**
- An empty list gives an empty list.
