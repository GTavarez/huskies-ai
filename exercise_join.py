"""Step 18 — write the join yourself. Guided, with checks.

    python exercise_join.py

Four tasks. Each one prints what to do, then checks your answer and tells you
what is wrong if it is wrong. Edit the lines marked  >>> YOUR LINE  and re-run
after each one. Nothing here is graded; the checks are just faster than me.

Why this exercise exists: you already ran my version in cost_table.py. Running
someone else's script teaches you nothing about pandas. Writing four lines does.
"""
import pandas as pd

OK, BAD = "  OK  ", " NOPE ",


def head(n, title):
    print(f"\n{'=' * 66}\nTASK {n} — {title}\n{'=' * 66}")


def stop(msg):
    print(f"[{BAD}] {msg}")
    print("\nFix the line above, save, and run this file again.")
    raise SystemExit(1)


def good(msg):
    print(f"[{OK}] {msg}")


# ----------------------------------------------------------------- setup
counts = pd.read_csv("out/token_counts.csv")
meta = pd.read_csv("data/metadata.csv")

print("Two tables. A DataFrame is just a table with named columns.\n")
print("counts  — one row per document, produced by tokenizers_compare.py")
print(counts.head(3).to_string(index=False))
print(f"\n  shape: {counts.shape[0]} rows x {counts.shape[1]} columns")
print(f"  columns: {list(counts.columns)}")

print("\nmeta  — one row per document, hand-maintained")
print(meta.head(3).to_string(index=False))
print(f"\n  shape: {meta.shape[0]} rows x {meta.shape[1]} columns")
print(f"  columns: {list(meta.columns)}")

print("\nThey share one column: doc_id. That is the key you join on.")


# ----------------------------------------------------------------- task 1
head(1, "Merge the two tables on doc_id")
print("""
A merge glues rows together where a key matches — the same idea as a SQL JOIN.
The shape is:

    left.merge(right, on="column_name", how="inner")

  on    the column both tables share
  how   "inner" keeps only rows found in BOTH tables
        "left"  keeps every row from the left table, even unmatched ones

Use how="inner" here.
""")

df = counts.merge(meta, on="doc_id", how="inner")  # >>> YOUR LINE: replace None with counts.merge(...)

if df is None:
    stop("df is still None. Write the merge.")
if not isinstance(df, pd.DataFrame):
    stop(f"df should be a DataFrame, got {type(df).__name__}.")
if "source_type" not in df.columns or "subword" not in df.columns:
    stop("df is missing columns from one side. Did you merge both tables?")
good(f"merged: {df.shape[0]} rows x {df.shape[1]} columns")


# ----------------------------------------------------------------- task 2
head(2, "Check nothing was lost")
print("""
This is the most important task on the page, and the easiest to skip.

A merge that drops rows raises NO error. If a doc_id is spelled differently in
the two files, that row silently vanishes and every number you compute afterwards
is quietly wrong.

So: compare the row count before and after. They should be equal.

Store the answer as a boolean.
""")

rows_match = df.shape[0] == counts.shape[0]# >>> YOUR LINE: True if df has the same number of rows as counts

if rows_match is None:
    stop("rows_match is still None. Compare df.shape[0] with counts.shape[0].")
if not isinstance(rows_match, (bool,)):
    stop(f"rows_match should be True or False, got {type(rows_match).__name__}.")
if rows_match is not (df.shape[0] == counts.shape[0]):
    stop("That is not what the comparison actually evaluates to. Check it again.")
good(f"rows_match = {rows_match}  ({counts.shape[0]} before, {df.shape[0]} after)")
if not rows_match:
    print("       Rows were lost. In real work you would stop here and find out why.")


# ----------------------------------------------------------------- task 3
head(3, "Which single document is the most expensive?")
print("""
Sort the table by the subword column, largest first, and take the top row.

    df.sort_values("column", ascending=False)

Assign the SORTED TABLE (not the row) so the check can look at it.
""")

by_size = df.sort_values('subword', ascending=False)  # >>> YOUR LINE: sort df by "subword", biggest first

if by_size is None:
    stop("by_size is still None. Sort the table.")
if list(by_size["subword"]) != sorted(df["subword"], reverse=True):
    stop("Not sorted largest-first on subword. Did you set ascending=False?")
top = by_size.iloc[0]
good(f"most expensive: {top['doc_id']}  ({top['subword']} tokens, {top['source_type']})")


# ----------------------------------------------------------------- task 4
head(4, "What share of the corpus is policy documents?")
print("""
Two steps.

  1. Total tokens per source_type:
         df.groupby("column")["other_column"].sum()

     groupby splits the table into groups sharing a value, then sums each group.
     The result is a Series — one number per group, labelled by group name.

  2. Turn the policy number into a percentage of the whole corpus.
""")

by_type = df.groupby('source_type')["subword"].sum()   # >>> YOUR LINE: total subword tokens for each source_type
policy_pct = by_type['policy'] / by_type.sum() * 100  # >>> YOUR LINE: policy's share of all tokens, as a percentage 0-100

if by_type is None:
    stop("by_type is still None. Use groupby.")
expected = df.groupby("source_type")["subword"].sum()
if not by_type.sort_index().equals(expected.sort_index()):
    stop("by_type is not tokens summed per source_type. Check the two column names.")
good("tokens per source_type:\n" + by_type.sort_values(ascending=False).to_string())

if policy_pct is None:
    stop("policy_pct is still None.")
expected_pct = expected["policy"] / expected.sum() * 100
if abs(policy_pct - expected_pct) > 0.05:
    stop(f"policy_pct = {policy_pct:.2f}, expected about {expected_pct:.2f}. "
         "Divide policy's tokens by the total, then multiply by 100.")
good(f"policy is {policy_pct:.1f}% of the corpus")


# ----------------------------------------------------------------- done
print(f"\n{'=' * 66}")
print("All four done. You just wrote the core of cost_table.py.")
print("Open src/cost_table.py now and compare — you will recognise every line.")
print(f"{'=' * 66}\n")
print("For your week note:")
print(f"  most expensive document : {top['doc_id']} ({top['subword']} tokens)")
print(f"  policy share of corpus  : {policy_pct:.1f}%")
print(f"  rows survived the merge : {rows_match}")
