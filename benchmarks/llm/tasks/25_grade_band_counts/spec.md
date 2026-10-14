# How many in each grade band

Count how many scores fall in each grade band.

**Inputs**
- `scores`: a list of integers from 0 to 100.

**Output**
- A list of (grade, count) pairs. A score's grade is `"A"` if it is at least 90, otherwise `"B"` if it is at least 75,
  otherwise `"C"`. Include only grades that occur, in the order in which each grade first occurs when going through
  `scores` in order.

**Edge cases**
- An empty list gives an empty list.
