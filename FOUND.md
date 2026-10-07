# FOUND.md — Data errors in the international football results dataset

**Purpose of this document.** It is a self-contained, hand-off report. It has three audiences,
in order:

1. **A verification agent** who must independently confirm every claim, ideally against
   external sources on the web (§2 lists the specific facts worth searching for).
2. **A mitigation agent** who must decide what to do about each confirmed finding (§7 lists
   the open decisions).
3. **A human owner** of the notebook, who must arbitrate the cases where the data itself is
   wrong and no code change can fix it (§6).

Everything needed to re-derive the numbers is here: the data location, the exact notebook
logic being examined, the row counts, and the queries used. Nothing in this document depends
on conversation history.

---

## 1. The task and the context

### 1.1 What this project is

A **KDD (Knowledge Discovery and Data Mining)** coursework project, in Spanish, building a
predictive model over **international men's football (soccer) match results**. The notebook is
written in [marimo](https://marimo.io), a reactive Python notebook runtime.

Working directory: `/home/bowuigi/escuela/AyD2/data-mining-notebook`
(the course is "Análisis y Diseño 2"; the folder is named `data-mining-notebook`).

### 1.2 The goal that was set for the error-hunting pass

> Read every cell in the notebook and find as many **data errors** as possible — both
> **missing data** and **wrong data** — in the imported datasets and in the metrics derived
> from them. Some errors are **only visible at a later stage** (i.e. they only surface once
> the intermediate tables have been built, not in the raw CSVs). Errors already documented in
> the notebook's `quirks_doc` cell are out of scope and were **not** re-verified. Findings were
> to be written to `FOUND.md` as they were discovered, not batched at the end.

### 1.3 What counts as a "data error" here

Anything that makes a derived football statistic **wrong or misleading**, including:

* duplicated records that inflate counts,
* contradictory records for the same real-world entity,
* values that cannot be true (a penalty shootout on a match that was never drawn),
* values that are missing in a way that biases the surviving rows,
* **code that silently propagates or amplifies** a raw-data defect into a derived table.

This last category is why the report has a second half: several raw defects are survivable on
their own but become materially wrong once `matches_ir` / `goal_scorers_ir` / `goals_ir` are
built from them.

### 1.4 Explicitly out of scope

The notebook cell `SFPL` (named `quirks_doc`) already records the following known quirks.
Per the task these were **assumed to hold and were not re-verified**, and they are not
repeated as findings:

* Extra-time goals are recorded as minute 45 / 90, so some goals look simultaneous
  (1,797 rows at minute 90; 925 at minute 45).
* Some `minute` values are missing, attributed to the period **1963-11-26 → 1980-02-27**,
  across a listed set of countries.
* Some `scorer` values are missing, attributed to **1980-02-24 → 1980-02-29**, across a
  listed set of countries.
* `match_results`: Uruguay–Bolivia 2024-06-27 was really **5-0**, not 4-0. `goal_scorers`
  has it right, so joining the two tables should repair it.
* `match_results`: Singapore–Malaysia 0-3 on 1973-09-04 actually happened on **1973-09-07**.
  The 0-0 on the same date is correct.
* Team names may not be modern.

**One caveat that arose anyway** — see §5.6. While checking something else, the actual date
range of missing `minute` values turned out to be much wider than the doc's window. That is
reported as a new finding because it was discovered, not assumed; it does not re-litigate the
countries list.

---

## 2. The data

### 2.1 Files and schemas

Read by the notebook's `setup` cell via a helper that treats the literal string `"NA"` as null
and casts `date` to a date type:

```python
def _from_csv(filename: str):
    return pl.read_csv(
        filename, null_values=["NA"], schema_overrides={"date": pl.Date}
    )

goal_scorers    = _from_csv("data/Goal_Scorers.csv")
match_results   = _from_csv("data/Match_Results.csv")
penalty_shootouts = _from_csv("data/Penalty_Shootouts.csv")
```

| file | rows | columns |
|---|---|---|
| `data/Goal_Scorers.csv` | **44,362** | `date, home_team, away_team, team, scorer, minute, own_goal, penalty` |
| `data/Match_Results.csv` | **47,399** | `date, home_team, away_score…` → precisely: `date, home_team, away_team, home_score, away_score, tournament, city, country, neutral` |
| `data/Penalty_Shootouts.csv` | **644** | `date, home_team, away_team, winner, first_shooter` |

Types: `date` is a date; `minute`, `home_score`, `away_score` are 64-bit ints;
`own_goal`, `penalty`, `neutral` are booleans; everything else is a string.

`goal_scorers.team` is **the team the goal is credited to**, *not* necessarily the team the
scorer played for — own goals are already credited to the benefiting side. This is verified
in §6 and is the single most important thing to get right before touching this data.

### 2.2 Coverage and ranges

| | first date | last date |
|---|---|---|
| `match_results` | 1872-11-30 | 2024-07-14 |
| `goal_scorers` | 1916-07-02 | 2024-07-14 |
| `penalty_shootouts` | 1967-08-22 | 2024-07-13 |

`match_results` spans 175 tournaments, 2,064 cities, 270 countries, 336 distinct teams.
`neutral` is `True` for 12,507 rows and `False` for 34,892.

`penalty_shootouts` has **644 rows and 644 distinct `(date, home_team, away_team)` keys** —
that table is internally unique on its key. `match_results` and `goal_scorers` are not (§3, §4).

### 2.3 The notebook cells that build derived tables

Cell IDs are marimo's internal opaque ids; the names in parentheses are what the cell
defines.

| id | defines | what it does |
|---|---|---|
| `setup` | `goal_scorers`, `match_results`, `penalty_shootouts` | loads the three CSVs |
| `Hbol` | — | markdown: business objectives (empty placeholders) |
| `MJUe` | — | markdown: target-dataset phase header |
| `vblA` (`ir_doc`) | — | documents the intended intermediate tables |
| `bkHC` (`matches_ir`) | `matches_ir` | explodes each match into one row per moment |
| `lEQa` (`goal_scorers_ir`) | `goal_scorers_ir` | numbers each team's goals 1..N |
| `PKri` (`goals_ir`) | `goals_ir` | joins the two above |
| `Xref` | — | markdown: unused experiments |
| `SFPL` (`quirks_doc`) | — | the known-quirks list (§1.4) |
| `BYtC` | `_df` | `mo.sql` full outer join, match_results ⋈ goal_scorers |
| `RGSE` | `matches` | `mo.sql` full outer join, match_results ⋈ penalty_shootouts |

The two joins that matter, verbatim from the notebook:

```sql
-- BYtC
from match_results
full outer join goal_scorers on match_results.date = goal_scorers.date
  and match_results.home_team = goal_scorers.home_team
  and match_results.away_team = goal_scorers.away_team

-- RGSE
from match_results
full outer join penalty_shootouts on match_results.date = penalty_shootouts.date
  and match_results.home_team = penalty_shootouts.home_team
  and match_results.away_team = penalty_shootouts.away_team
```

**Both join on exactly `(date, home_team, away_team)`, and that triple is not unique in
`match_results`.** That single fact is the root cause of §3 and of most of the second half of
this report.

`RGSE`'s two derived columns, verbatim, because their disagreement is finding §5.1:

```sql
case when match_results.home_score > match_results.away_score then match_results.home_team
     when match_results.home_score < match_results.away_score then match_results.away_team
     else penalty_shootouts.winner end as winner,
case when penalty_shootouts.date is null then 'goals'
     else 'penalties' end as won_by
```

`winner` is derived from the **score**; `won_by` is derived from the **mere existence** of a
`penalty_shootouts` row. Those two can and do disagree (§5.1).

### 2.4 Key quantities in the derived tables

| table | rows | note |
|---|---|---|
| `matches_ir` | 186,880 | = 139,481 goals + 47,399 kickoff rows |
| `goal_scorers_ir` | 44,362 | one row per goal |
| `goals_ir` | 186,881 | `matches_ir` ⋈ `goal_scorers_ir` |

`matches_ir` is arithmetically self-consistent, but see §6.1 — it carries 107 phantom rows.

### 2.5 How to re-run any check in this report

The notebook runs in a live marimo kernel. All numbers below were obtained by evaluating
Python against the notebook's own in-memory frames (`goal_scorers`, `match_results`,
`penalty_shootouts`, `matches_ir`, `goal_scorers_ir`, `goals_ir`) — **not** by re-reading the
CSVs, so the reported figures already reflect the `setup` cell's null handling.

To reproduce, evaluate against those frames. The standard key used throughout is:

```python
K = ["date", "home_team", "away_team"]
```

Note for anyone re-checking §6: use `how="inner"` when you need right-hand columns in polars.
A `how="semi"` join silently drops the right-hand columns, which produces a confusing
`ColumnNotFoundError`.

---

## 3. Finding 1 — `match_results` has 20 duplicated match keys

**Severity: high. This is the root cause of several later findings.**

`(date, home_team, away_team)` is **not unique** in `match_results`: 20 keys occur twice, so
47,399 rows describe 47,379 distinct matches. The 20 keys break down as:

* **12** where both rows agree on score and city (same match listed twice, once as `Friendly`
  and once under a real tournament) — harmless in content, but still duplicate rows.
* **5** where the two rows agree on score but disagree on `city` (see §3.2).
* **3** where the two rows **disagree on the score** (see §3.1).

### 3.1 The 3 score-conflicting duplicates

| date | home | away | score A | score B | tournaments | cities |
|---|---|---|---|---|---|---|
| 1973-09-04 | Singapore | Malaysia | 0-0 | **0-3** | Southeast Asian Peninsular Games | Singapore |
| 1974-02-17 | Tahiti | New Caledonia | 1-2 | **2-1** | Friendly | Papeete |
| 1977-10-22 | Guyana | Barbados | 0-0 | **2-0** | Friendly | Georgetown / Linden |

* The **Singapore–Malaysia** pair is the **known** quirks_doc entry: these are two genuinely
  different matches, and the 0-3 simply has the wrong date. Not a new finding, but it *is*
  counted here because it behaves like a duplicate in every downstream join.
* The **Tahiti–New Caledonia** pair is a real, unresolved conflict: both rows are `Friendly`
  in `Papeete`, so this is not "one match, two labels" — one of the two scores is simply
  wrong. `goal_scorers` has **no rows** for this date, so it cannot arbitrate.
* The **Guyana–Barbados** pair is the same situation, and worse: the two rows also name two
  **different cities** (`Georgetown` and `Linden`). `goal_scorers` has no rows for this date
  either. One of the two rows has both a wrong score and a wrong venue.

The two `Friendly` cases need external adjudication (§6.1).

### 3.2 The 5 city-conflicting duplicates

All on **1960-04-14 / 1960-04-15**, African Friendship Games, and all with **identical
scores**:

| date | home | away | score |
|---|---|---|---|
| 1960-04-14 | Cameroon | Djibouti | 9-2 |
| 1960-04-14 | Ivory Coast | Benin | 3-2 |
| 1960-04-15 | Cameroon | Mali | 3-2 |
| 1960-04-15 | Congo | Ivory Coast | 3-2 |
| 1960-04-15 | Madagascar | Burkina Faso | 6-1 |

Each pair has one row saying `Tananarive` and the other `Antananarivo`. These are **the same
city** under its old Malagasy name and its modern one, so the score data is fine — but any
grouping by `city` splits these 5 matches in two, and the `city` dimension gains a phantom
value.

### 3.3 The 12 duplicate-only keys

Same score, same city, listed as both `Friendly` and a real tournament:

1923-05-22 China PR–Philippines (3-0) · 1923-05-24 Japan–China PR (1-5) ·
1925-05-22 Philippines–China PR (1-5) · 1927-08-27 China PR–Japan (5-1) ·
1927-08-29 Japan–Philippines (2-1) · 1927-08-31 China PR–Philippines (3-1) ·
1930-05-27 China PR–Philippines (5-0) · 1934-05-12 Philippines–China PR (0-2) ·
1934-05-13 Japan–Indonesia (1-7) · 1934-05-14 China PR–Indonesia (2-0) ·
1934-05-19 Philippines–Indonesia (3-2) · 1934-05-20 China PR–Japan (4-3)

Tournaments involved: `Far Eastern Championship Games` vs `Friendly`.

### 3.4 Why this is dangerous downstream

`BYtC` and `RGSE` both join on this non-unique triple, so the duplicate rows **multiply**
the joined output:

| frame | with duplicates | deduplicated first | inflation |
|---|---|---|---|
| `BYtC` (`_df`) | **77,385** rows | 47,379 rows | **+30,006 (+63%)** |
| `RGSE` (`matches`) | **47,401** rows | 47,381 rows | +20 |

`_df` is inflated far more than `RGSE` because it joins `goal_scorers`, which has many rows
per match: a match with 2 result rows and N goal rows produces `2 * N` rows.

**Consequence:** any per-match or per-team metric computed off `_df` counts the goals of the
19 duplicated matches roughly twice. Team goal totals, goals-per-match averages and
scoreline distributions are all wrong for those matches, and `matches` double-counts 20
matches outright.

---

## 4. Finding 2 — `goal_scorers` has 128 fully duplicated rows

`goal_scorers.is_duplicated().sum() == 128`. 128 rows repeat an existing row **exactly**
(same date, teams, team, scorer, minute, own_goal, penalty). They span **35 distinct matches**.

**They are not independent errors.** All of them fall inside the known missing-data windows
from `quirks_doc`:

* 108 of the 128 have `minute IS NULL`
* 77 fall in the `1963-11-26` → `1980-02-27` minute window
* 60 fall in the `1980-02-24` → `1980-02-29` scorer window

So they are **artifacts of the missing-data quirks**: where the source could not supply a
minute or a scorer, the row got duplicated instead. Repairing the missing-data windows should
remove them as a side effect. See §6.4 for why removing them is not straightforward.

---

## 5. Findings on `penalty_shootouts`, missing values, and coverage

### 5.1 37 shootout rows attach to matches that were never drawn — and `won_by` lies about all 37

A penalty shootout should only exist for a match that was level after extra time. Of the 644
shootout rows:

* **2** fail to join `match_results` at all → §5.3
* **605** join to a genuine draw (`home_score == away_score`) → correct
* **37** join to a match where `home_score != away_score` → **these are errors**

The 37 split into two flavours, and **both are wrong**:

#### 5.1a. 18 rows where `winner` contradicts the final score

The shootout "winner" is the team that **lost** on the scoreboard:

| date | home | away | score | shootout `winner` |
|---|---|---|---|---|
| 1973-04-21 | Senegal | Ghana | 1-0 | Ghana |
| 1974-11-22 | Libya | Tunisia | 1-0 | Tunisia |
| 1975-12-23 | Libya | Syria | 1-0 | Syria |
| 1979-04-29 | Cameroon | Guinea | 3-0 | Guinea |
| 1980-11-30 | Zambia | Morocco | 2-0 | Morocco |
| 1981-05-10 | Rwanda | Ethiopia | 1-0 | Ethiopia |
| 1983-02-20 | Gambia | Sierra Leone | 0-1 | Gambia |
| 1983-04-24 | Mauritius | Ethiopia | 1-0 | Ethiopia |
| 1984-07-15 | Senegal | Angola | 1-0 | Angola |
| 1985-04-21 | Madagascar | Egypt | 1-0 | Egypt |
| 1986-10-19 | Gabon | Angola | 1-0 | Angola |
| 1989-04-23 | Ghana | Gabon | 1-0 | Gabon |
| 1996-04-28 | Barbados | Jamaica | 2-0 | Jamaica |
| 1996-05-05 | Guyana | Suriname | 2-1 | Suriname |
| 2000-07-16 | Mozambique | Lesotho | 1-0 | Lesotho |
| 2012-10-13 | Uganda | Zambia | 1-0 | Zambia |
| 2012-11-21 | Argentina | Brazil | 2-1 | Brazil |
| 2022-03-29 | Kazakhstan | Moldova | 0-1 | Kazakhstan |

**Worth external attention:** `2012-11-21 Argentina 2-1 Brazil` and `2022-03-29 Kazakhstan
0-1 Moldova` are high-profile fixtures. That these are ordinary-looking scorelines with the
loser recorded as the winner suggests the `winner` column — or the `home_team`/`away_team`
orientation — is transposed for these rows, rather than the scores being wrong. Both
hypotheses are checkable (§6.1).

#### 5.1b. 19 rows where `winner` agrees with the score

| date | home | away | score | shootout `winner` |
|---|---|---|---|---|
| 1975-07-13 | Morocco | Ghana | 2-0 | Morocco |
| 1977-06-26 | Zambia | Algeria | 2-0 | Zambia |
| 1977-08-31 | Paraguay | Argentina | 2-0 | Paraguay |
| 1980-07-12 | Nigeria | Tunisia | 2-0 | Nigeria |
| 1983-02-06 | Senegal | Niger | 2-0 | Senegal |
| 1983-04-22 | Egypt | Congo | 2-0 | Egypt |
| 1984-11-23 | Kenya | Somalia | 1-0 | Kenya |
| 1985-09-15 | Mozambique | Libya | 2-1 | Mozambique |
| 1989-04-23 | Kenya | Sudan | 1-0 | Kenya |
| 1993-05-27 | Bolivia | Paraguay | 2-1 | Bolivia |
| 1993-08-15 | Australia | Canada | 2-1 | Australia |
| 2000-03-19 | Suriname | Saint Lucia | 1-0 | Suriname |
| 2000-07-14 | Libya | Chad | 3-1 | Libya |
| 2000-09-03 | Togo | Sierra Leone | 2-0 | Togo |
| 2005-11-16 | Australia | Uruguay | 1-0 | Australia |
| 2011-07-12 | Saint Lucia | Aruba | 4-2 | Saint Lucia |
| 2019-10-13 | Chad | Liberia | 1-0 | Chad |
| 2022-03-29 | Senegal | Egypt | 1-0 | Senegal |
| 2023-11-21 | Mexico | Honduras | 2-0 | Mexico |

Here the shootout changed nothing, so the row is simply spurious.

#### 5.1c. The consequence in the built frame

`RGSE` labels `won_by = 'penalties'` whenever a `penalty_shootouts` row merely **exists**,
while `winner` comes from the **score**. So all 37 of these matches are asserted to have been
"won on penalties" even though none of them was ever tied:

* `won_by = 'penalties'` currently counts **644** rows
* only **605** are genuine shootout decisions
* the other **37** are spurious, and for 18 of them `winner` names the team that **lost**

Any "matches won on penalties" metric is inflated by 37, and 18 rows additionally carry a
`winner` that contradicts the scoreboard.

### 5.2 Team-name inconsistency: `Åland` vs `Åland Islands`

`penalty_shootouts` contains `2023-07-13 Åland vs Falkland Islands`. `match_results` contains
that same match as:

```
2023-07-13  Åland Islands  1 - 1  Falkland Islands  Island Games  Saint Sampson  Guernsey  true
```

`Åland` appears **0 times** in `match_results` and `goal_scorers`; `Åland Islands` appears
**51 times** in `match_results`. So this is a **spelling variant of one team**, not two teams.

**Consequence:** the join key fails, and `RGSE`'s `full outer join` emits **two rows for one
real match**:

* the real one — `1-1`, `won_by = 'goals'` (**wrong**; it was decided on penalties)
* a ghost — `home_score = NULL`, `away_score = NULL`, and
  `tournament/city/country/neutral = NULL`, `won_by = 'penalties'`, `winner = 'Åland'`

So `matches` contains a duplicated match, and the ghost row introduces a team name (`Åland`)
that exists in no other table. Any per-team aggregation grows a phantom "Åland" team with
1 match, 0 goals scored, 0 goals conceded.

This is exactly the "possible non-modern names" risk the `quirks_doc` cell warns about.

### 5.3 One match that exists only in `penalty_shootouts`

`2011-06-29 Saare County vs Åland Islands` (winner: Åland Islands) has **no** row in
`match_results`. The surrounding Island Games 2011 fixtures are present — `Saare County 3-3
Åland Islands` on `2011-06-26`, and Saare County appears again on `2011-06-30` — so this one
date is simply absent.

It survives the `full outer join` with all metadata NULL. Its `winner` falls through to the
`else` branch (NULL scores are neither `>` nor `<`) and so returns `Åland Islands`, which
happens to be correct — **but only by accident**. `won_by = 'penalties'` is correct here. The
row still has no score, no tournament and no venue, so it distorts any goals, venue or
tournament aggregation.

### 5.4 `minute = 122`: one impossible value

`minute` ranges **1..122**. Exactly one row exceeds any plausible football limit:

> **1919-05-29 Brazil vs Uruguay — Arthur Friedenrich, minute 122.**

Every *other* extra-time goal in this file is folded into minute 45 or 90 (a known quirk), so
a raw 122 is an outlier of a different kind and looks like a corrupted value. It is the only
such row, so it is cheap to special-case but should not be silently averaged into
"average goal minute" statistics.

### 5.5 Missing values summary

| table | column | missing | share |
|---|---|---|---|
| `goal_scorers` | `minute` | **259** | 0.58% of 44,362 |
| `goal_scorers` | `scorer` | **49** | 0.11% of 44,362 |
| `penalty_shootouts` | `first_shooter` | **414** | **64%** of 644 |

`match_results` has **no NULLs at all** in any column.

`first_shooter` at 64% missing makes "who kicked off the shootout" unusable as a feature
without accepting a very high missing rate.

### 5.6 The missing-minute window is much wider than `quirks_doc` claims

`quirks_doc` states the missing minutes are **all** between `1963-11-26` and `1980-02-27`.
The **actual** range of `minute IS NULL` is:

> **`1960-10-16` → `1997-03-31`**

So NULL-minute goals exist both **before** the documented window and **up to 17 years after**
it. Concrete examples outside the stated window:

| date | match | team | NULL-minute goals |
|---|---|---|---|
| 1985-03-23 | Thailand vs Bangladesh | Thailand | 1, 2, 3 — **all three** |
| 1981-04-22 | Kuwait vs Thailand | Kuwait | 1..6 — **all six** |
| 1980-09-26 | Syria vs North Korea | North Korea, Syria | 1, 2 |
| 1985-01-19 | Singapore vs North Korea | Singapore | 1 |
| 1993-07-02 | Syria vs Taiwan | Taiwan | 1 |

**Consequence:** any cleanup rule derived from the documented 1963–1980 window will leave
these rows untreated, and they are not rare outliers — for some matches *every* goal has a
NULL minute. This is reported as new because it was discovered, not assumed.

### 5.7 `goal_scorers` covers only 38% of matches

* `match_results`: 47,379 distinct matches.
* **29,225** matches have a non-zero score but **zero rows in `goal_scorers`**.
* Only **14,376** distinct matches (30%) appear in `goal_scorers` at all.

So roughly 62% of matches have no goal-level detail whatsoever. Every metric that needs goals
— scorers, minutes, penalty share, own-goal share, `goals_ir` — is computed over a heavily
biased subsample, while metrics from `match_results` cover everything. The two tables must not
be inner-joined without acknowledging this, and any per-team goal rate is a rate *per match
with recorded scorers*, not per match played.

---

## 6. Errors that only appear in the derived tables

These are the "later stage" errors the task asked about. The raw CSVs look self-consistent
enough to pass a casual look; the intermediate tables carry the contradictions.

### 6.1 `matches_ir` inherits the duplicates → 107 phantom rows, and self-contradiction

`matches_ir` is arithmetically self-consistent:

```
186,880 rows = 139,481 goals + 47,399 kickoff rows
             = sum(home_score + away_score) + n_matches
```

But because `match_results` has 20 duplicated keys, the **duplicate-free** expectation is
**186,773** rows. So `matches_ir` silently carries **107 extra rows**, exact copies of
legitimate ones. It also has **112 duplicated values** of the join key
`(date, home_team, away_team, scorer_team, current_team_score)` — the fan-out source for the
`goals_ir` join in §6.3.

**Worst case — `1977-10-22 Guyana vs Barbados`, the table contradicts itself.** Because
`match_results` holds this match twice with different final scores, `matches_ir` contains two
*mutually incompatible* kickoff rows but only one set of goal rows:

```
date         home     away       scorer_team  current_team_score  final_home  final_away  city
1977-10-22   Guyana   Barbados   null         0                  0           0           Georgetown
1977-10-22   Guyana   Barbados   null         0                  2           0           Linden
1977-10-22   Guyana   Barbados   Guyana       1                  2           0           Linden
1977-10-22   Guyana   Barbados   Guyana       2                  2           0           Linden
```

The same match is recorded simultaneously as **0-0** and **2-0**, in two different cities.
Every scoreline-derived metric off `matches_ir` — goals per match, clean sheets, scoreline
distribution, mean goals — is contaminated.

`1974-02-17 Tahiti vs New Caledonia` (recorded `1-2` and `2-1`) fails the same way.

### 6.2 The duplicated goal rows corrupt goal *identity*, not just counts

This is worse than "128 extra rows". `goal_scorers_ir` numbers goals with

```python
goal_number = pl.int_range(1, pl.len() + 1).over("date", "home_team", "away_team", "team")
```

so a duplicated row is assigned its **own** `current_team_score`. The per-team tally then
still reaches the correct final score, which **hides the bug**: the counts look right while
the scorer attribution is wrong.

Example, `1963-11-26 Ghana 2-0 Ethiopia`:

```
team  scorer           minute
Ghana Edward Acquah    null
Ghana Edward Acquah    null     <- exact duplicate, but numbered as goal 2
```

Two genuinely different goals — very likely by two different players — have been collapsed
into one name. Any per-scorer or per-team goal attribution is wrong for these matches, and
because the tally still reconciles, **no aggregate count-based check will catch it.**

### 6.3 `goals_ir` double-counts the goals of the duplicated matches

Joining `matches_ir` → `goal_scorers_ir` yields 186,881 rows. **38 goal identities appear
more than once** (46 surplus rows) across **30 distinct matches**. Worst observed
multiplicities, all on `1980-02-26 Australia vs Papua New Guinea`:

* `Peter Sharne` (minute NULL) — appears **4 times**
* `Ian Hunter` (minute NULL) — appears **3 times**

So `goals_ir` counts several teams' goals multiple times. Per-team goals-scored,
goals-per-match and player-level goal tallies derived from `goals_ir` are inflated.

Reassuringly, this inflation is **contained**: comparing `goals_ir` goal counts against
`home_score + away_score` for every match yields only **2** disagreements, and only one is
new:

* `2024-06-27 Uruguay vs Bolivia` — 5 goals vs a recorded 4-0. This is the **known**
  quirks_doc entry, and it is the one case where `goal_scorers` is right and `match_results`
  is wrong.
* `1980-09-23 Malaysia 1-1 Qatar` — an apparent shortfall. Investigated: **not an error.**
  `goal_scorers` has both goals (Tukamin Bahari 33', and a Qatar goal at 52' with a NULL
  `scorer`). The discrepancy is an artifact of counting only rows with a non-NULL `scorer`.

### 6.4 `goal_scorers_ir` mis-numbers every goal that has a NULL minute

`goal_scorers_ir` sorts by `("date", "minute", nulls_last=True)` and then numbers
`current_team_score` 1..N **per (match, team)**. Any goal with a NULL minute is pushed to the
**end** of its team's list, so it is numbered as that team's **last** goal even if it was
actually the opener.

**259 goals are affected** — the same 259 from §5.5.

| date | match | team | wrong `current_team_score` |
|---|---|---|---|
| 1985-03-23 | Thailand vs Bangladesh | Thailand | 1, 2, 3 — **all three goals** |
| 1963-11-28 | Nigeria vs Sudan | Sudan | 1, 2, 3, 4 — **all four** |
| 1981-04-22 | Kuwait vs Thailand | Kuwait | 1..6 — **all six** |
| 1980-09-25 | China PR vs Bangladesh | China PR | 1, 2, 3 |
| 1973-02-17 | New Zealand vs Fiji | New Zealand | 1..5 — **all five** |

`current_team_score` is supposed to mean "this team's running tally including this goal".
Because it is derived from an ordering that NULL minutes corrupt, **it is not a trustworthy
running score for those 259 goals.** Anything derived from it inherits the error: goal
sequence position, opening-goal statistics, "who scored the kth goal", any running-scoreline
reconstruction.

For the matches in the table above, the numbering is not merely shifted — **it is arbitrary**,
since *every* goal has a NULL minute and the sort falls back to input order.

### 6.5 The duplicated rows are entangled with the NULL-value problem

§4 established that all 128 duplicated `goal_scorers` rows sit inside the known
missing-minute / missing-scorer windows. Combined with §6.4, this means a single fix —
supplying the missing minutes and scorers, or excluding those windows — would resolve §4 and
§6.4 together. **Deduplicating without also handling NULL minutes is not sufficient**, and
deduplicating by dropping one of the two identical rows is only safe if the two rows really
were the same goal (§6.2 says we cannot know that for the NULL-minute rows).

---

## 7. What was verified as clean

Recorded so the verification agent does not re-do this work, and because several of these
negative results constrain what a fix is allowed to do.

* **No orphan goal rows.** All 44,362 `goal_scorers` rows join to a `match_results` row on
  `(date, home_team, away_team)`. The `full outer join` in `BYtC` introduces no goal-side NULL
  scores. (This holds partly by luck — see the note below.)
* **`goal_scorers.team` is always `home_team` or `away_team`.** 0 violations.
* **Own goals are already credited to the benefiting team.** This was tested both ways:
  counting per-team goals against the final score gives **1** mismatch under "team = credited
  team" (the known Uruguay–Bolivia case) versus **788** mismatches under "own goals belong to
  the opponent". Conclusion: **`goal_scorers_ir` must NOT re-flip own goals**, and
  `matches_ir`'s use of `team` as the scoring team is correct. Any "fix" that flips own goals
  would introduce 788 errors.
* **No row has `own_goal = true` and `penalty = true` simultaneously.** 0 rows.
* **No negative scores and no NULL scores** anywhere in `match_results`.
* **`home_team != away_team` in every row** of both `match_results` and `goal_scorers`.
* **Team names are consistent across all three tables**, with the single exception of
  `Åland` (§5.2).
* **`goal_scorers_ir` numbering is contiguous `1..N`** for every (match, team) group — no gaps
  or repeats in the numbering itself. The problem in §6.4 is *which* goal gets *which*
  number, not gaps in the sequence.
* **Per-match goal totals in `goal_scorers` reconcile** with `home_score + away_score` for all
  but 1 match (the known Uruguay–Bolivia case). 0 matches have *fewer* goal rows than their
  score implies.

### One caveat on the "no orphan goals" result

That check passes only because both tables carry the Singapore–Malaysia fixture on
`1973-09-04`, the date the quirks_doc says is wrong. The rows line up **for the wrong
reason**. If the date is ever corrected, the join will break and that match's goal data will
become orphaned.

---

## 8. Summary table

| # | Finding | Scope | Severity |
|---|---|---|---|
| 1 | `match_results` duplicated `(date, home_team, away_team)` keys | 20 keys / 40 rows | **high** (root cause) |
| 1.1 | …of which conflicting **scores** | 3 keys (1 known, 2 new) | **high** |
| 1.2 | …of which conflicting **city** spelling (`Tananarive`/`Antananarivo`) | 5 matches | medium |
| 1.3 | …of which duplicate-only (Friendly + tournament) | 12 matches | medium |
| 2 | `goal_scorers` fully duplicated rows | 128 rows / 35 matches | medium |
| 3 | Matches with a score but zero goal rows | 29,225 (62%) | medium (bias) |
| 4 | Shootout rows on non-drawn matches | 37 (18 contradict the score) | **high** |
| 5 | `Åland` vs `Åland Islands` breaks the join | 1 match → duplicated in `matches` | medium |
| 6 | Match present only in `penalty_shootouts` | 1 match, all metadata NULL | low-medium |
| 7 | NULL `minute` | 259 goals | medium |
| 8 | NULL-minute window wider than documented | `1960-10-16`→`1997-03-31` | medium |
| 9 | `minute = 122` (Brazil–Uruguay 1919) | 1 goal | low |
| 10 | NULL `scorer` | 49 goals | low |
| 11 | NULL `first_shooter` | 414 / 644 (64%) | low-medium |
| 12 | `matches_ir` phantom rows | 107 rows | **high** |
| 13 | `matches_ir` self-contradiction (Guyana–Barbados) | 2 matches | **high** |
| 14 | Duplicated goals corrupt goal *identity* | 128 rows / 35 matches | **high** |
| 15 | `goals_ir` double-counted goals | 38 identities / 30 matches | **high** |
| 16 | `current_team_score` mis-numbered for NULL minutes | 259 goals | **high** |
| 17 | `RGSE.won_by` says 'penalties' for 37 non-shootouts | 37 rows | **high** |

---

## 9. Open decisions for the mitigation agent

These cannot be resolved by inspecting the data alone. Each needs a policy choice.

1. **Deduplicate `match_results` — which row wins?** For the 12 duplicate-only keys, merging
   the `tournament` label (e.g. prefer the real tournament over `Friendly`) is defensible. For
   the 5 city conflicts, normalise `Tananarive` → `Antananarivo`. But the 2 `Friendly`
   score conflicts (§3.1) **require external adjudication** — see §6.1 below.
2. **Repair or exclude the 259 NULL-minute goals?** Supplying minutes is impossible from the
   data; the honest options are to exclude them from minute-based metrics *while keeping them
   for goal counts*, or to exclude the whole match. Note §6.4: minute-based exclusion and
   `current_team_score` numbering interact, so this decision must be made **before**
   fixing the numbering.
3. **Fix `won_by`, or drop the 37 rows?** Recomputing `won_by` from the score is strictly
   better than trusting row existence, and would reduce 'penalties' from 644 to 605. But for
   the 18 contradicting rows, `winner` also needs correcting — which again needs external input.
4. **The 128 duplicated goal rows are entangled with NULL values** (§6.5). Decide whether to
   fix the NULL windows first and let deduplication fall out, or to deduplicate now with a
   documented and acknowledged information loss.
5. **Canonical team-name mapping.** `Åland` → `Åland Islands` is a one-off, but the
   quirks_doc explicitly warns that names may be non-modern. A general alias table is likely
   the durable fix. Decide the scope.
6. **Document the 62% coverage gap** (§5.7) as a limitation on every goal-level metric, rather
   than treating it as a bug to be patched.

---

## 10. Facts worth verifying against external sources

For a verification agent with web access. Each is a real-world fact that the data asserts and
that an independent source can settle. Ordered by how much they unblock.

### Highest value — these block all automated fixes

| # | Question | Why it matters |
|---|---|---|
| A | **1974-02-17 Tahiti vs New Caledonia: was it 1-2 or 2-1?** | `match_results` holds both, `goal_scorers` has nothing. One of the two `Friendly` rows is wrong. |
| B | **1977-10-22 Guyana vs Barbados: 0-0 in Georgetown, or 2-0 in Linden?** | Same, plus the city. Affects `matches_ir` self-contradiction (§6.1). |
| C | **2012-11-21 Argentina vs Brazil: 2-1, and who actually won?** | High-profile. If 2-1 Argentina, the shootout `winner = Brazil` is transposed. |
| D | **2022-03-29 Kazakhstan vs Moldova: 0-1, and who actually won?** | Same pattern as C. |

### Own-goal orientation (18 rows in §5.1a)

For each of these, the dataset claims the shootout winner **lost** on the scoreboard. Determine
per match whether the **score** is wrong, the **`winner` field is transposed**, or the
**home/away orientation is swapped** — these need different fixes:

`1973-04-21` Senegal–Ghana (1-0) · `1974-11-22` Libya–Tunisia (1-0) ·
`1975-12-23` Libya–Syria (1-0) · `1979-04-29` Cameroon–Guinea (3-0) ·
`1980-11-30` Zambia–Morocco (2-0) · `1981-05-10` Rwanda–Ethiopia (1-0) ·
`1983-02-20` Gambia–Sierra Leone (0-1) · `1983-04-24` Mauritius–Ethiopia (1-0) ·
`1984-07-15` Senegal–Angola (1-0) · `1985-04-21` Madagascar–Egypt (1-0) ·
`1986-10-19` Gabon–Angola (1-0) · `1989-04-23` Ghana–Gabon (1-0) ·
`1996-04-28` Barbados–Jamaica (2-0) · `1996-05-05` Guyana–Suriname (2-1) ·
`2000-07-16` Mozambique–Lesotho (1-0) · `2012-10-13` Uganda–Zambia (1-0) ·
`2012-11-21` Argentina–Brazil (2-1) · `2022-03-29` Kazakhstan–Moldova (0-1)

Note that many are 1-0 or 2-0 with the shootout winner being the losing side. A plausible
unifying hypothesis is that these rows come from a competition where the recorded
`home_score`/`away_score` is actually **the score after the shootout** or is otherwise
misaligned. Testing one or two of these against a results archive should reveal which.

### Spurious shootouts (19 rows in §5.1b)

Confirm there was **no penalty shootout** in each of these. If confirmed, the row should be
dropped entirely:

`1975-07-13` Morocco–Ghana · `1977-06-26` Zambia–Algeria · `1977-08-31` Paraguay–Argentina ·
`1980-07-12` Nigeria–Tunisia · `1983-02-06` Senegal–Niger · `1983-04-22` Egypt–Congo ·
`1984-11-23` Kenya–Somalia · `1985-09-15` Mozambique–Libya · `1989-04-23` Kenya–Sudan ·
`1993-05-27` Bolivia–Paraguay · `1993-08-15` Australia–Canada · `2000-03-19` Suriname–Saint Lucia ·
`2000-07-14` Libya–Chad · `2000-09-03` Togo–Sierra Leone · `2005-11-16` Australia–Uruguay ·
`2011-07-12` Saint Lucia–Aruba · `2019-10-13` Chad–Liberia ·
`2022-03-29` Senegal–Egypt · `2023-11-21` Mexico–Honduras

`1993-08-15 Australia 2-1 Canada` and `2005-11-16 Australia 1-0 Uruguay` are notable — both
would be well-documented fixtures, so a shootout claim is clearly wrong.

### Team identity and venues

* **Is `Åland` (§5.2) the same entity as `Åland Islands`?** Confirm Åland Islands' FIFA
  membership and that it played the 2023 Island Games against Falkland Islands, drawing 1-1
  and winning on penalties.
* **2011-06-29 Saare County vs Åland Islands (§5.3)** — confirm this fixture was actually
  played at the 2011 Island Games, and recover its score and venue, which are missing from
  `match_results` entirely.
* **`Tananarive` vs `Antananarivo` (§3.2)** — confirm these are the same city (Malagasy
  rename), which justifies normalising to one value. Applies to 5 matches on 1960-04-14/15.

### Individual data points

* **1919-05-29 Brazil vs Uruguay, Arthur Friedenrich, minute 122 (§5.4)** — verify Friedenrich
  scored, and at what minute. Brazil won that match heavily; a plausible real minute would
  both confirm the goal and give the correct value.
* **1963-11-26 Ghana 2-0 Ethiopia (§6.2)** — identify the two scorers. The dataset collapses
  them into one name (`Edward Acquah`) because one row is a duplicate with a NULL minute.
  Knowing the two names would let the row be repaired rather than dropped.
* **1980-02-26 Australia vs Papua New Guinea (§6.3)** — `Peter Sharne` appears 4 times and
  `Ian Hunter` 3 times. Confirm the true scorer list and score for this match.

### Sanity checks on the data as a whole

* **Is `Åland Islands` consistently spelled?** Any other variant in the 51 rows.
* **Are the 336 team names all current/canonical?** The quirks_doc warns about non-modern
  names; a scan for historical or alternate names (e.g. `China PR`, `Republic of Ireland`,
  `Zaire`/`DR Congo`, `Germany`/`West Germany`/`German DR`) would be worthwhile. Note
  `German DR` and `Germany` both appear — check whether these are correctly kept distinct.

---

## 11. Provenance of this report

Produced by an agent driving the live marimo kernel via the `marimo-pair` code-mode skill,
reading the in-memory notebook frames. All counts were computed against those frames; the
notebook itself was **not modified** during the error-hunting pass.

Two claims were initially written and then **corrected** during the work, and are recorded here
because both corrections are instructive:

* An early draft claimed there were **orphan goal rows** in `goal_scorers`. Verification
  showed **zero**. §3a was rewritten. (The revised version now records the *caveat* in §7
  about why the check passes for the wrong reason.)
* An early draft claimed **both** failing shootout rows were matches simply missing from
  `match_results`. Verification showed only one is; the other is a **team-name mismatch** that
  produces a *duplicate* rather than a gap. §5.2 and §5.3 were split accordingly.

A draft also asserted that `first_shooter` was "missing for the large majority" without a
figure; the measured value is **414 / 644 = 64%**, now stated precisely in §5.5.

For reference, the "later stage only" framing the task asked about turned out to be
substantive: §6 contains four findings (§6.1 phantom rows and self-contradiction, §6.4
mis-numbering, §6.5 entanglement, plus the `won_by` consequence in §5.1c) that are **not
visible from the raw CSVs at all** and only appear once the intermediate tables are built.