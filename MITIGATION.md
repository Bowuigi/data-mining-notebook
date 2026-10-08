# MITIGATION.md — mitigation plan for `FOUND.md`

**Inputs.** `FOUND.md`, then `FOUND-VERIFIER.md` and `FOUND-VERIFIER-2.md`, in that order.
Where the three disagree, the two verifiers win; §1 summarises the reconciled state so the rest
can be read on its own.

**Role.** Decide what to change and how to restructure the derived tables so the class of defect
behind the big findings cannot recur. This is a plan — **no notebook cell has been modified.**

**Priority stance.** 47k rows, KDD coursework. One-match fixes carry ~0 statistical weight and
are done only because they are cheap and document a *class* of error. The leverage is
structural: one unique key per table, goals separated from match metadata, one honest score
pair, honest coverage flags.

---

## 1. Reconciled ground truth

| # | Finding | Status | Action |
|---|---|---|---|
| F1 | 20 duplicated `(date, home_team, away_team)` keys in `match_results` | **real** (47,379 distinct) | fix — §3.1 |
| F2 | 128 "duplicated" `goal_scorers` rows | **refuted** — genuine repeat scorings (Lewandowski/Buksa hat-tricks; `Peter Sharne` ×4 is *correct*) | **do not touch** — §3.5 |
| F3 | 37 shootouts on non-drawn matches | **refuted as errors** — 33/37 provably two-legged play-off second legs (reverse-orientation fixture within 120 days, aggregate exactly level) | **do not drop**; fix the label — §4.1 |
| F4 | `minute = 122` "impossible" | **refuted** — Friedenreich, 1919 Copa América play-off | **do not special-case** |
| F5 | 29,208 matches scored but zero goal rows (62%) | real, unfixable | flag + document — §6 |
| F6 | `matches_ir` 107 phantom rows; Guyana self-contradiction | real, caused by F1 | disappears with F1 |
| F7 | `goals_ir` double-counts goals | **refuted** — 0 duplicated goal identities; only 112 duplicated *kickoff* rows, all from F1 | disappears with F1 |
| F8 | `_df` inflated +63% | **refuted** — inflation is exactly **+20** | disappears with F1 |
| F9 | `Tananarive` / `Antananarivo` | real alias | normalise — §3.2 |
| F10 | `Åland` vs `Åland Islands`; `Saare County` vs `Saaremaa` | real aliases; Saare row also transposed | normalise + fix orientation — §3.3 |
| F11 | NULL `minute` 259 rows; real range `1960-10-16 → 1997-03-31` | real | doc + flag — §5 |
| F12 | NULL `scorer` 49; NULL `first_shooter` 414/644 | real, unfixable | doc + flag — §6 |
| F13 | `won_by` is two-valued and cannot express reality | real schema defect | third value — §4.1 |
| F14 | Retroactive / obsolete country names | real (found while verifying F10) | `normalized_country` — §3.4 |

The fact the refactor is built around: **`goal_scorers` reconciles with `match_results` on every
match except `2024-06-27 Uruguay–Bolivia` (4-0 recorded, 5 goals).** The current design cannot
express that disagreement, which is why `quirks_doc` says "joining both tables should fix it" and
it does not.

---

## 2. The refactor

### 2.1 Why

`matches_ir` (cell `bkHC`) does two jobs in one table: it carries **match facts** (who, where,
final score, `neutral`) and it materialises the **goal sequence** by exploding the score into
`1..N` rows. Because the score is copied onto every exploded row, three unrelated defects become
one: a wrong score produces a missing/phantom goal row (Uruguay–Bolivia's 5th goal survives
`goals_ir` with NULL scores — *visible* but never *corrected*); a duplicated match key multiplies
every downstream join (F1); an alias-broken match produces a ghost with NULL metadata.

### 2.2 Target: three tables, one key

```
matches_keyed   1 row per match   key: match_id        (from match_results, after §3)
goal_events     1 row per goal    key: (match_id, scorer_team, goal_no)
goals_ir        1 row per goal    = goal_events + match metadata, one row per goal
```

That is the whole refactor. **`match_id` replaces the text triple everywhere.**
`date`/`home_team`/`away_team` stay on `matches_keyed` as payload for reading and for
re-joining to archives, but are never a join key again.

Why this matters mechanically: `match_id` is unique, so **every join becomes provably
many-to-one**. Fan-out is not "fixed", it is unrepresentable — F1/F6/F7/F8 cannot be written.
That is the durable value here, and it is one line of code.

### 2.3 `goal_events`

```python
goal_events = (
    goal_scorers.lazy()
    .sort("date", "minute", nulls_last=True)          # stable: keeps source order on ties
    .with_columns(
        goal_no=pl.int_range(1, pl.len() + 1).over("date", "home_team", "away_team", "team"),
        has_incomplete_minute_data=pl.col("minute").is_null()
                                        .over("date", "home_team", "away_team"),
    )
    .rename({"team": "scorer_team", "minute": "goal_minute",
             "own_goal": "goal_was_own_goal", "penalty": "goal_was_penalty"})
    .join(matches_keyed.select("match_id", "date", "home_team", "away_team"),
          on=["date", "home_team", "away_team"], how="left")
    .select("match_id", "scorer_team", "goal_no", "scorer", "goal_minute",
            "goal_was_own_goal", "goal_was_penalty", "has_incomplete_minute_data")
    .collect()
)
```

`has_incomplete_minute_data` is a **per-match** flag, not a per-row `minute IS NULL`. A per-row
flag invites
"drop the NULL rows", which is wrong (§5). A per-match flag says the true thing: *this match's
goal ordering is not fully determined by the data*. `goal_no` is the authoritative sequence
position; nothing downstream recomputes it.

`assert goal_events.filter(pl.col("match_id").is_null()).height == 0` — "no orphan goals"
promoted from a finding to a hard assertion (notably when the Singapore–Malaysia date moves,
§3.1).

### 2.4 `goals_ir` — and the one automatic repair

`goals_ir` is goal rows joined to match metadata on `match_id`. For matches with **no** goal
rows, goal rows are synthesised from the score (today's `bkHC` explosion, minus every column
except `match_id`, `scorer_team`, `current_team_score`), so 0-0 and N-0 matches survive and the
table keeps the "one row per moment" grain the project documents.

```python
# goal rows where they exist; score-derived rows where they don't
goals_ir = (
    goal_events.join(matches_keyed.drop("date", "home_team", "away_team"),
                     on="match_id", how="left")            # many-to-one: no fan-out possible
    .join(score_derived_goal_rows, on=["match_id", "scorer_team", "current_team_score"],
          how="full", coalesce=True)
    .join(goal_events, on=["match_id", "scorer_team", "current_team_score"],
          how="left", coalesce=True)                        # brings goal detail onto skeleton rows
    ...
)
```

The repair, in one expression and **in place** — no `_raw`, no `_effective`, no `_counted`:

```python
.with_columns(
    # a match has goal rows if any goal row carries a scorer-side identifier
    has_goal_detail=pl.col("goal_no").is_not_null().any().over("match_id"),
)
.with_columns(
    home_score=pl.when(pl.col("has_goal_detail"))
                 .then(pl.col("goals_from_rows"))     # counted from goal rows
                 .otherwise(pl.col("home_score")),
    away_score=pl.when(pl.col("has_goal_detail"))
                 .then(pl.col("goals_from_rows_away"))
                 .otherwise(pl.col("away_score")),
)
```

`goals_from_rows` / `goals_from_rows_away` are windowed counts computed in the preceding
`with_columns` and then **dropped**. Net effect on the schema: **two score columns, exactly as
today**, plus `match_id`.

What it buys: `2024-06-27 Uruguay–Bolivia` gets its **5th goal row back** (the skeleton only
generated 4), the count is 5, so `home_score` becomes **5** — the `quirks_doc` claim is
discharged mechanically with no hard-coded fixture.

The repair is one-directional: goal rows only ever *add* information, so it can never rewrite a
score for a match with thin coverage.

The corrected value is trusted unconditionally, so no repair-tracking column is carried. The
audit trail is instead the §9 assertion that pins the repair to the one match it should affect
(`score == 5` on `2024-06-27`), which fails loudly if a second match ever diverges — a stronger
guarantee than a flag nobody filters on.

---

## 3. Data-level fixes

Negligible model impact; cheap; and they erase every high-severity finding that survived
verification. Do them before §2.3, since §2's uniqueness assertion needs them.

### 3.1 `match_results` — 20 keys, 17 rows touched

| keys | edit |
|---|---|
| 12 | Far Eastern Championship Games / Friendly pairs 1923–1934: keep the tournament row, drop the `Friendly` row |
| 5 | 1960-04-14/15: `Tananarive` → `Antananarive` (direction settled: reverted only in 1976) |
| 1 | `1973-09-04 Singapore–Malaysia` `0-3` → move to `1973-09-07` |
| 1 | `1974-02-17 Tahiti–New Caledonia`: **both rows are real matches** on one date (three friendlies that month: 1-2, 2-1, 2-2). Split the date — which row keeps `1974-02-17` is open (§7) |
| 1 | `1977-10-22 Guyana–Barbados`: **both rows are real.** `2-0 / Linden` → `1977-10-21`; the `0-0 / Georgetown` row at `10-22` duplicates the one already at `10-26`, drop it |
| 1 | `2024-06-27 Uruguay–Bolivia` `4-0` → `5-0` — optional if §2.4 ships, still worth it so the raw data is right |

**Do not** "choose a winner" among the 3 score conflicts: in 2 of 3 both rows are true matches
and the *date* is wrong.

Guard the Singapore–Malaysia edit: there are no `goal_scorers` rows on `1973-09-04` today, so
the move is safe *now*, but afterwards that match's goals either join by `match_id` or surface
as orphans and the §2.3 assertion fires. Re-run it right after.

### 3.2 Cities

One `replace` in the load path: `{"Tananarive": "Antananarive"}`.

### 3.3 Team names

Two one-offs, both fixing real join breakage:

* `penalty_shootouts` `2023-07-13`: `Åland` → `Åland Islands` (removes the ghost row in `matches`;
  `winner = Åland` is already correct).
* `2011-06-29 Saare County vs Åland Islands` is **transposed** — the official fixture is
  `Åland v Saaremaa`, a shoot-out-only tiebreak on a rest day with no 90-minute match. Fix the
  orientation; **do not invent a score** for it.

Beyond these, teams are left alone except where the same entity is spelled two ways. Cities and
countries get proper lookup tables (§3.4); teams do not need one at 336 names.

### 3.4 `normalized_country`

`country` stays exactly as recorded — it is the source field and belongs in the raw table.
Add one derived column that answers "which present-day country is this?", so every
geographic feature (continent, confederation, World Cup eligibility, Elo lookup) joins on one
stable key instead of a shifting name.

```python
COUNTRY_ALIASES = {
    # successor-state renames — one unambiguous present-day country
    "Netherlands Antilles": "Curaçao",
    "Zaire":               "DR Congo",
    "German DR":           "Germany",
    "Republic of Ireland": "Ireland",
    "Burma":               "Myanmar",
    "Rhodesia":            "Zimbabwe",
    "South Yemen":         "Yemen",
    "Ceylon":              "Sri Lanka",
    "Tanganyika":          "Tanzania",
    "Upper Volta":         "Burkina Faso",
    "Dahomey":             "Benin",
    "Gold Coast":          "Ghana",
    # multi-successor / dissolved — NOT collapsed, kept verbatim (see §7)
    # "USSR", "Yugoslavia", "Czechoslovakia", "Zanzibar", "Serbia and Montenegro"
}

match_results = match_results.with_columns(
    pl.col("country").replace(COUNTRY_ALIASES).alias("normalized_country")
)
```

Notes that matter:

* `normalized_country` is a **country** concern. `Åland`/`Åland Islands`, `Saare County`/
  `Saaremaa` are *teams*; they are handled in §3.3 and are a separate list. Do not conflate
  the two — `German DR` appears as a team name *and* a country value.
* Derived once, at load, and never recomputed in analysis cells — that removes the
  "two analyses, two continent mappings" failure mode.

### 3.5 Multi-successor countries — old name kept, region made current

For `USSR`, `Yugoslavia`, `Czechoslovakia`, `Zanzibar`, `Serbia and Montenegro` there is no
single present-day country, so `normalized_country` **keeps the historical name verbatim** —
this is the honest value and it is also the value that makes historical joins work. What gets
corrected is the **region**: it must be the successor state's actual current region, under its
current name, not the historical entity's name and not an arbitrary pick among successors.

Two separate outputs, therefore:

```python
# normalized_country : single unambiguous successor, else the historical name verbatim
# region             : present-day geographic bucket, always under a current name
REGION = {   # keyed on normalized_country; current names only
    "USSR": "Europe",                  # most successors + bulk of the entity's matches
    "Yugoslavia": "Europe",
    "Czechoslovakia": "Europe",
    "Serbia and Montenegro": "Europe",
    "Zanzibar": "Africa",              # -> Tanzania, current name
    "Netherlands Antilles": "Caribbean",
    "Curaçao": "Caribbean",
    "Zaire": "Africa",
    "DR Congo": "Africa",
    "German DR": "Europe",
    "Germany": "Europe",
    "Republic of Ireland": "Europe",
    "Ireland": "Europe",
    "Burma": "Asia",
    "Myanmar": "Asia",
    "Rhodesia": "Africa",
    "Zimbabwe": "Africa",
    "Ceylon": "Asia",
    "Sri Lanka": "Asia",
    # ... remaining present-day countries, one line each
}
```

Rules that follow:

* `normalized_country` is **never** silently rewritten to one successor. A model that wants
  "did the Soviet Union become Russia" filters on `normalized_country`; a model that wants
  present-day geography filters on `region`. Neither has to guess.
* `region` uses **current** region names only — no `USSR Europe` / `Yugoslavia Balkans`
  pseudo-values. A row is `(normalized_country = "USSR", region = "Europe")` and reads correctly
  in a table, a chart axis and a groupby.
* `USSR` spans Europe and Asia; `Europe` is the defensible majority bucket (Russia, Ukraine,
  Belarus, and the whole of the pre-1991 European core). Where a per-match region is genuinely
  needed, that is a `successor_state` lookup, not a change to `normalized_country`.
* Multi-successor entities are **excluded from `COUNTRY_ALIASES`** and handled only here. Do not
  put `USSR` in the alias map.
* `region` is derived from `normalized_country` in the same load cell, so it survives every
  downstream join — and unlike team names, a country value is stored in only one table.

---

## 4. Remaining code changes

### 4.0 Connect `penalty_shootouts` to `goals_ir`

Today `penalty_shootouts` reaches only `matches` (cell `RGSE`), via its own text-triple join —
the last join still keyed on `(date, home_team, away_team)`. `goals_ir` carries no shootout
information at all, so any goal-level analysis is blind to how the match was decided. Fix it by
keying shootouts on `match_id` too, then joining once and reusing.

```python
shootout_events = (
    penalty_shootouts.lazy()
    .join(matches_keyed.select("match_id", "date", "home_team", "away_team"),
          on=["date", "home_team", "away_team"], how="left")   # many-to-one
    .rename({"winner": "shootout_winner",
             "first_shooter": "penalty_first_shooter"})
    .select("match_id", "shootout_winner", "penalty_first_shooter")
    .collect()
)
assert shootout_events["match_id"].n_unique() == shootout_events.height   # 644 rows, 644 ids
```

`penalty_shootouts` is already unique on its key (644/644), so after the two alias/orientation
edits in §3.3 **all 644 rows resolve to a `match_id`** and the `how="left"` never yields NULL.
Assert that; if it ever fires, §3.3 has regressed.

Then `won_by` becomes a **plain column lookup instead of a second join**:

```python
matches = matches_keyed.join(shootout_events, on="match_id", how="left").with_columns(
    won_by=pl.when(pl.col("shootout_winner").is_null()).then(pl.lit("goals"))
           .when(pl.col("has_shootout_only")).then(pl.lit("shootout_tiebreak"))
           .when(pl.col("home_score") != pl.col("away_score"))
                 .then(pl.lit("penalties_after_aggregate"))
           .otherwise(pl.lit("penalties"))
)
```

and `goals_ir` gains the same two columns from the same `shootout_events`, so a goal row knows
whether its match went to penalties:

```python
goals_ir = goals_ir.join(shootout_events, on="match_id", how="left") \
                    .join(match_level, on="match_id", how="left")   # won_by, has_goal_detail
```

`won_by` is **match-level**, not goal-level, so it must not be recomputed inside the goal join —
it is joined in from `match_level` once, and every goal row of a match inherits it. That keeps
one definition instead of two.

Two consequences worth stating, because the raw table alone is misleading here:

* **the 2 shoot-out-only rows have no `goals_ir` representation.** They have no match in
  `match_results`, so no `match_id`, so no goal rows — by design, and correctly so, because no
  90-minute match was played. They must not be forced into `goals_ir` with NULL `scorer_team`
  rows: that would reintroduce exactly the phantom rows the split is meant to eliminate. They
  live in `matches` only, with `won_by = 'shootout_tiebreak'`. Document this, or the next pass
  will "fix" the gap.
* `penalty_first_shooter` is 64% NULL and is now on every goal row of a decided match. It is
  **match-level data, not goal-level** — keep it out of any per-goal feature set, or it will
  look like a per-goal attribute with a 64% missing rate.

### 4.1 `RGSE` → `matches`, three-valued `won_by`

```sql
case
    when penalty_shootouts.date is null                then 'goals'                   -- 46,757
    when match_results.date is null                    then 'shootout_tiebreak'       -- 2
    when match_results.home_score <> match_results.away_score
                                                          then 'penalties_after_aggregate' -- 37
    else 'penalties'                                                          -- 605
end as won_by
```

**605 / 37 / 2** instead of a flat 644. `winner` stays derived from the score with the `else`
branch falling through to `shootout_winner` — already correct for the 37 (those teams
*lost the leg and won the tie*, which the new label now names instead of hiding) and for the 2
shoot-out-only rows. `matches` also gains `has_goal_detail`, and its scores are the repaired
ones from §2.4 so the two tables never disagree.

The SQL above is the `won_by` logic; §4.0 is how the join it needs stops being a second
text-triple join. Prefer §4.0 — keep the SQL only as the specification of the four cases.

Do not recompute `won_by` from the score alone — that destroys 37 legitimate records.

### 4.2 Delete `BYtC` / `_df`

`_df` is `match_results ⋈ goal_scorers` on the raw text triple: a strictly worse version of
`goals_ir` with no `match_id`, no repair, no flags. Delete it rather than fix it — that removes
the last place in the notebook where a non-unique text key is used as a join key.

### 4.3 `quirks_doc` — correct, not just extend

* NULL-minute window is **`1960-10-16 → 1997-03-31`**, not 1963–1980.
* Uruguay–Bolivia: now repaired in `goals_ir` (§2.4); keep the note, mark it handled, and drop
  the list of goal scorers — the repair is mechanical and the value is now simply `5-0`.
* Extra-time goals are generally recorded at their **true** minute — 163 rows > 100. The doc's
  "folded to 45/90" claim is only true for the cases it lists.
* Add: 37 shootout rows are aggregate play-off second legs; `won_by` distinguishes them.
* Add: team aliases fixed; `normalized_country` / `region` applied; multi-successor countries
  keep their historical name.
* Add: the 2 shoot-out-only rows have **no** goal rows and no `goals_ir` entry, by design.

---

## 5. NULL minutes (259) — flag, don't repair

`goal_scorers_ir` sorts `("date", "minute", nulls_last=True)` then numbers `1..N` per
(match, team), so a NULL-minute goal is numbered as that team's **last** goal. For **101
(match, team) groups every goal has a NULL minute**, so the numbering is input order —
arbitrary, though still contiguous and still reaching the correct final tally.

Unfixable from the data. Make the uncertainty explicit instead:

* keep `has_incomplete_minute_data` (§2.3) and **never** drop those rows — dropping them breaks
  40 matches by leaving teams short of their score;
* for **sequence-sensitive** features (opening goal, k-th goal, running-scoreline
  reconstruction) filter on `~has_incomplete_minute_data`; those 101 groups are well under
  0.5% of goals;
* for **count** features (goals scored, goal rate, scorer tallies) keep everything — those are
  correct for all 259;
* derive `current_team_score` from `goal_no`, never from a minute sort containing NULLs.

The original "entanglement" claim (dedup without handling NULLs is insufficient) was a
consequence of the refuted duplication finding and does not survive.

---

## 6. Coverage — document, flag, never inner-join

`goal_scorers` covers **14,376 of 47,379 matches (30%)**; `first_shooter` is 64% NULL. No code
changes this; what code can do is stop analysis assuming otherwise:

* carry `has_goal_detail` on every match-level table;
* **never inner-join `match_results` to `goal_scorers`** for anything match-level — that
  silently drops 70% of the dataset. Every join here is `full`/`left` today; make it a written
  rule, because it is invisible when it breaks;
* per-team goal rates are *per match with recorded scorers*, never per match played;
* the 30% subsample is not missing-at-random (era- and competition-dependent). Any goal-level
  feature must carry the coverage flag as an input rather than being silently imputed.

---

## 7. Still open (low urgency, listed so they are not lost)

1. `1974-02-17 Tahiti–New Caledonia` — which of `1-2` / `2-1` keeps the date. Both are real.
2. `1977-10-21 Guyana 2-0 Barbados` — confirm from a second source (eloratings only).
3. `1977-08-31 Paraguay 2-0 Argentina`, `1983-02-06 Senegal 2-0 Niger` — aggregate not level
   from the data; likely a wrong *other-leg* score or a wrong `tournament` label.
4. `Saaremaa` vs `Saare County` — which spelling is canonical (15 rows say `Saare County`).
5. `USSR` spans Europe and Asia. `region = "Europe"` is the defensible majority bucket; if a
   per-match successor is ever needed that is a separate `successor_state` lookup, not a change
   to `normalized_country` (§3.5).
6. The 35-of-37 aggregate play-offs could optionally become a small `aggregate_ties` table
   (pair each non-drawn shootout with its reverse-orientation fixture inside 120 days) — 15
   lines, and it turns the dataset's largest apparent anomaly into a labelled subset for
   modelling. Optional.

Nothing here blocks §2–§5.

---

## 8. Sequenced plan

| # | step | effort | kills |
|---|---|---|---|
| 1 | team/city aliases + 2 `penalty_shootouts` edits (§3.2, §3.3) | 1 | ghost rows, split city dimension |
| 2 | `normalized_country` + `region` at load (§3.4, §3.5) | 1 | shifting geographic keys |
| 3 | `match_results` 20-key fixes (§3.1) | 1 | 107 phantom rows, 112 kickoff dupes, +20 `_df` inflation, Guyana contradiction |
| 4 | `match_id` + uniqueness assertion (§2.2) | 0.5 | makes fan-out unrepresentable, permanently |
| 5 | `goal_events` (numbered, keyed, `has_incomplete_minute_data`) (§2.3) | 1 | orphan-goal risk; NULL-minute ambiguity |
| 6 | `goals_ir` rebuild + in-place score repair (§2.4) | 1.5 | repairs Uruguay–Bolivia mechanically |
| 7 | `shootout_events` on `match_id`; join into `goals_ir` + `matches` (§4.0) | 1 | last text-triple join; `goals_ir` blind to shootouts |
| 8 | three-valued `won_by` (§4.1) | 0.5 | the `won_by` lie on 39 rows |
| 9 | delete `BYtC` / `_df` (§4.2) | 0.2 | redundant table |
| 10 | `quirks_doc` rewrite (§4.3) | 0.5 | prevents re-deriving refuted findings |
| 11 | invariants cell (§9) | 1 | silent regression of any of the above |

1–4 are the "must" set: under a day, and they remove every high-severity finding that survived
verification. 5–8 are the structural fix. 9–11 are cheap polish.

---

## 9. Invariants to assert permanently

One validation cell. Each corresponds to a finding a human had to discover by hand — that is
the argument for writing them down.

```python
# key / grain
assert matches_keyed["match_id"].n_unique() == matches_keyed.height
assert matches_keyed.select(K).is_duplicated().sum() == 0
assert goal_events.filter(pl.col("match_id").is_null()).height == 0        # no orphan goals
assert goal_events.select(["match_id","scorer_team","goal_no"]).is_duplicated().sum() == 0

# every shootout resolves to a match, exactly once
assert shootout_events["match_id"].n_unique() == shootout_events.height == 644
assert shootout_events.filter(pl.col("match_id").is_null()).height == 0
assert goals_ir.filter(pl.col("shootout_winner").is_not_null()) \
         ["match_id"].n_unique() == 642      # 644 - the 2 shoot-out-only rows

# the repair: pinned to the one match it should ever affect
_urb = goals_ir.filter(pl.col("date") == date(2024, 6, 27))                 # Uruguay-Bolivia
assert _urb.filter(pl.col("scorer_team") == "Uruguay").height == 5           # 5th goal restored
assert _urb.filter(pl.col("scorer_team") == "Uruguay")["home_score"].eq(5).all()
# and nowhere else: no other match may diverge from its recorded score
assert (
    goals_ir.group_by("match_id")
    .agg(
        pl.col("goal_no").is_not_null().any().alias("det"),
        pl.col("scorer_team").filter(pl.col("scorer_team") == "home_team").len().alias("h"),
        pl.col("home_score").first(),
    )
    .filter(pl.col("det") & (pl.col("h") != pl.col("home_score")))
    .height == 1                                                             # only Uruguay-Bolivia
)

# geographic normalisation
assert matches_keyed["normalized_country"].is_null().sum() == 0
assert matches_keyed["region"].is_null().sum() == 0
assert matches_keyed.filter(pl.col("normalized_country") == "USSR")["region"].eq("Europe").all()

# shootout labels
assert (matches["won_by"] == "penalties").sum() == 605
assert (matches["won_by"] == "penalties_after_aggregate").sum() == 37
assert (matches["won_by"] == "shootout_tiebreak").sum() == 2

# documented invariants that must NOT be "fixed"
assert goals_ir.filter(pl.col("goal_minute") == 122).height == 1     # Friedenreich, 1919
assert goal_scorers.is_duplicated().sum() == 128                      # real repeat scorings
```

The last two are deliberate: they encode *refuted* findings so nobody tidies them away. Cheapest
possible defence against re-introducing the two most expensive mistakes available here.

---

## 10. One-paragraph summary

Fix the 20 duplicated `match_results` keys and the two alias/orientation shootout rows, and add
`normalized_country` plus a current-name `region` — cheap, and together they erase every
high-severity finding that survived verification. Countries with a single successor get the
modern name; multi-successor entities (`USSR`, `Yugoslavia`, `Czechoslovakia`, `Zanzibar`) keep
their historical name in `normalized_country` and are corrected only in `region`, so no analysis
has to guess which successor to pick. Do **not** touch `goal_scorers` duplicates, the 37
aggregate play-off shootouts, or `minute = 122`; all three are correct data that two verification
passes confirmed externally. Then spend the effort on structure, not on new columns: give every
match a surrogate `match_id`, split `matches_ir` into a goal table keyed on it plus match
metadata, key `penalty_shootouts` on the same id so `goals_ir` learns how a match was decided,
and reconcile goals against score **in place** — one score pair, exactly as today. That
reconciliation is what restores `2024-06-27 Uruguay–Bolivia`'s missing 5th goal and takes the
score from 4-0 to 5-0 automatically, with no hard-coded fixture and no way for a future
one-match score error to hide. Flag the 30% goal-coverage subsample and the 259 NULL-minute
goals rather than pretending they are recoverable, and encode all of it as assertions so the next
pass does not have to rediscover it.
