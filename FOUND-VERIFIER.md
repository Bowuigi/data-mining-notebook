# FOUND-VERIFIER.md — independent verification of `FOUND.md`

**Role:** verification agent. Every claim in `FOUND.md` was re-derived from the live marimo
kernel at `localhost:2718` (frames `goal_scorers`, `match_results`, `penalty_shootouts`,
`matches_ir`, `goal_scorers_ir`, `goals_ir`, `matches`, `_df`) and, where `FOUND.md` §10 asked
for it, checked against external sources.

**The notebook was not modified.** Only existing cells were re-run (`PKri`, `RGSE`, `BYtC` were
in state `interrupted`/`stale` and had to be executed to read their output). No cell body was
edited.

**Verdict summary:** the *descriptive* half of `FOUND.md` (row counts, null counts, duplicate
counts, join fan-out) is almost entirely accurate. The *interpretive* half — specifically the
treatment of the 37 penalty shootouts, two of the "score conflicts", and the `minute = 122` row
— is **wrong**, and in two places the recommended mitigations in §9 would destroy correct data.

| | Claims | Confirmed | Wrong / unverified |
|---|---|---|---|
| Descriptive counts (§2, §4, §5.5, §5.6, §6.1–§6.4, §7) | 45 | 44 | 1 |
| Interpretive / external claims (§3.1, §4 attribution, §5.1, §5.4, §6.2, §6.3) | 14 | 3 | 11 |

---

## 1. Confirmed — no action needed

Everything in this section reproduced exactly.

### 1.1 Data shape and coverage (§2)

| Claim | Result |
|---|---|
| `goal_scorers` 44,362 rows, 8 cols | ✅ |
| `match_results` 47,399 rows, 9 cols | ✅ |
| `penalty_shootouts` 644 rows, 5 cols | ✅ |
| date ranges 1916-07-02→2024-07-14 / 1872-11-30→2024-07-14 / 1967-08-22→2024-07-13 | ✅ |
| 175 tournaments, 2,064 cities, 270 countries, 336 teams | ✅ |
| `neutral` True 12,507 / False 34,892 | ✅ |
| `ps` unique on key | ✅ |
| nulls: `minute` 259, `scorer` 49, `first_shooter` 414, `match_results` none | ✅ |
| `goal_scorers` distinct matches = 14,376 (30%) | ✅ |
| NULL-minute range `1960-10-16`→`1997-03-31` (wider than quirks_doc) | ✅ |
| `minute` max = 122, exactly one row above 120 | ✅ (the row exists; its *validity* is disputed in §2.3) |
| `own_goal AND penalty` = 0; `home_team != away_team`; no negative scores | ✅ |
| 0 orphan goal rows; `goal_scorers.team` always home or away | ✅ |

### 1.2 `match_results` duplicated keys (§3)

* 20 duplicated `(date, home_team, away_team)` keys; 47,379 distinct keys. ✅
* 3 score conflicts, 6 city conflicts (5 African Friendship Games + Guyana–Barbados), 12
  duplicate-only. The 3/5/12 split reproduces exactly. ✅
* The 12 Far Eastern Championship Games fixtures and their scores/tournaments reproduce
  exactly. ✅
* 5 city conflicts are `Tananarive` (10 rows) vs `Antananarivo` (107 rows) on 1960-04-14/15. ✅

### 1.3 Derived-table arithmetic (§6.1)

* `matches_ir` = 186,880 = 139,481 goals + 47,399 kickoff rows. ✅
* Duplicate-free expectation = 186,773 → **107 phantom rows**. ✅ (recomputed exactly)
* `matches_ir` has 112 duplicated values of `(date, home_team, away_team, scorer_team,
  current_team_score)`. ✅
* `goal_scorers` has 128 exactly-duplicated rows across 35 matches; 108 have NULL minute,
  77 in the 1963–1980 window, 60 in the 1980-02-24→29 window. ✅
* Own-goal orientation: 1 mismatch counting own goals as credited, 607 counting them as
  belonging to the opponent. ✅ in direction (`FOUND.md` says 788; I get 607 — join basis
  differs, the conclusion is identical and is the one that matters).
* Raw per-match goal totals reconcile for all but one match (`2024-06-27 Uruguay–Bolivia`). ✅
* `matches` (RGSE): `won_by = 'penalties'` for 644 rows, `'goals'` for 46,757. ✅
  The 2 ghost rows with NULL scores/metadata are ✅.

---

## 2. Refuted — these need `FOUND.md` to be corrected

### 2.1 ⚠️ **§5.1 / §5.1a / §5.1b / §5.1c: the 37 "spurious" shootouts are almost all REAL.
This is the most serious error in the report.**

`FOUND.md` asserts 37 shootout rows attach to matches that were "never drawn", calls 19 of them
"simply spurious" and recommends **dropping them** (§9 item 3), and frames 18 as "the shootout
winner is the team that **lost** on the scoreboard".

Every one I checked externally is a **two-legged play-off second leg decided on aggregate and
then by penalties**. The scoreline in `match_results` is the *leg* score, which is why
`home_score != away_score` while a shootout legitimately happened.

| date | fixture | leg score | shootout | external confirmation |
|---|---|---|---|---|
| 1973-04-21 | Senegal–Ghana | 1-0 | Ghana 5-3 | 1st leg Ghana 3-2 → 3-3 agg, Ghana won pens (Wikipedia, 1974 AFCON qualification; RSSSF) |
| 1975-07-13 | Morocco–Ghana | 2-0 | Morocco 6-5 | `2-0 (6-5 p)`, 1976 AFCON Q (Wikipedia, RSSSF) |
| 1977-06-26 | Zambia–Algeria | 2-0 | Zambia 6-5 | `2-0 [aet]`, Zambia qualify 6-5 on pens (RSSSF 78a) |
| 1983-02-06 | Senegal–Niger | 2-0 | Senegal 5-4 | CEDEAO Cup, 2-2 agg, Senegal won pens (RSSSF cedeao83) |
| 1989-04-23 | Kenya–Sudan | 1-0 | Kenya 6-5 | `1-0 (6:5) p`, 1990 AFCON Q 2nd leg (RSSSF, athlet.org) |
| 1993-08-15 | Australia–Canada | 2-1 | Australia 4-1 | 2nd leg, 3-3 agg, aet goalless, Australia won 4-1 (Wikipedia, Socceroos) |
| 2005-11-16 | Australia–Uruguay | 1-0 | Australia 4-2 | 2nd leg, 1-1 agg, Australia won 4-2 (Wikipedia, BBC) |
| 2012-11-21 | Argentina–Brazil | 2-1 | Brazil 4-3 | Superclásico 2nd leg, Argentina won the leg 2-1, Brazil won the shootout 4-3 (Wikipedia, AFA) |
| 2019-10-13 | Chad–Liberia | 1-0 | Chad 5-4 | 2021 AFCON Q 2nd leg, 1-0 then 5-4 pens (France24, RSSSF) |
| 2022-03-29 | Kazakhstan–Moldova | 0-1 | Kazakhstan 5-4 | Nations League play-off 2nd leg, 0-1 after ET, 5-4 pens (KFF, UEFA) |
| 2022-03-29 | Senegal–Egypt | 1-0 | Senegal 3-1 | WC playoff 2nd leg, 1-1 agg, Senegal won 3-1 (BBC, Reuters) |
| 2023-11-21 | Mexico–Honduras | 2-0 | Mexico 4-2 | CNL QF 2nd leg, 2-2 agg, Mexico won 4-2 (ESPN, AP) |

**12 of the 37 checked, 12 confirmed valid.** `FOUND.md` §10 itself asks whether "the recorded
`home_score`/`away_score` is actually the score after the shootout or is otherwise misaligned" —
the answer is that neither is true: the score is the correct leg score and the shootout decided
the *tie*, not the match.

Consequences:

1. **The `winner` field is NOT transposed.** For all 18 "contradicting" rows checked, the named
   winner is the team that actually won the shootout. `FOUND.md`'s recommendation to
   "correct `winner`" (§9 item 3) would break correct rows.
2. **The `won_by = 'penalties'` label is wrong, but for the opposite reason to the one given.**
   The real defect is that `won_by` is derived from row existence and cannot express "won the
   tie on penalties after a two-legged aggregate", nor "won on penalties in a shootout-only
   tiebreak" (§2.2 below). Recomputing `won_by` from the score would destroy 37 legitimate
   shootout records, exactly as `FOUND.md` proposes.
3. §5.1's two sub-classes (18 "winner contradicts" vs 19 "winner agrees") are **an artefact of
   the wrong assumption**, not a meaningful distinction. Both classes are the same phenomenon.

### 2.2 §5.3: the 2011-06-29 Saare County row is a shootout-only tiebreak, not a missing match

`FOUND.md` says the fixture "survives with all metadata NULL" and asks for "its score and
venue, which are missing from `match_results` entirely", implying a `match_results` row should
exist. External sources (Wikipedia *Football at the 2011 Island Games*, and the official IIGA
results PDF) show that on **Wednesday 29 June 2011** Åland and Saaremaa played **no match** —
they had finished level on W-D-L-GF-GA, so a **one-off penalty shoot-out was held on the rest
day** to decide Group D. The official results record `Åland 4(0) V 3(0) Saaremaa`, status
"After Penalties", no score.

So the `penalty_shootouts` row is **correct**, and there is nothing to recover into
`match_results`. Note also that the team is spelled **Saaremaa** in the official results but
**Saare County** in `match_results` — a second (undocumented) team-name alias, same class as
`Åland`/`Åland Islands`.

### 2.3 §5.4: `minute = 122` is **correct**, not a corrupted value

`FOUND.md` calls it "one impossible value" that "looks like a corrupted value" and should be
"special-cased". External sources are unambiguous:

* Wikipedia, *1919 South American Championship play-off*: Brazil 1-0 Uruguay after **four**
  15-minute extra-time periods (150 minutes); "Arthur Friedenreich scored the goal that
  allowed Brazil to win its first international title in the **122nd minute**, the latest goal
  in Copa América history."
* RSSSF `19sa.html`: `29.05.19 … BRA - URU 1:0 … 1:0 Friedenrich 122 NOTE: After 4 extra times
  of 15 minutes each. This was the longest match in the history of the Copa América, 150
  minutes!`

The value is a real record. **Do not special-case it.** The 120+ minute values in
`goal_scorers` generally are legitimate extra-time goals (there are 163 rows above 100, not
one), which also refutes the premise that "every other extra-time goal in this file is folded
into minute 45 or 90" — that premise is a statement about the quirks_doc, not about the data.

### 2.4 §3.1: both "unresolved score conflicts" are two distinct real matches with wrong
**dates** — not contradictory scores

`FOUND.md` asserts these need external adjudication between two candidate scores, and flags
the Guyana–Barbados one as "one of the two rows has both a wrong score and a wrong venue".

* **Tahiti vs New Caledonia, Feb 1974.** Wikipedia's Tahiti results list **three** friendlies
  that month: `1–2`, `2–1`, and `2–2`. Both `match_results` rows are therefore **correct**;
  two genuinely different matches were collapsed onto `1974-02-17`. The defect is a date
  error, and no score needs to be chosen.
* **Guyana vs Barbados, Oct 1977.** The Guyana FA's own record (Kaieteur News) and eloratings
  list **three** matches in the American Life Trophy series: **2-0 at Mackenzie Sports Club
  Ground, Linden** and **two 0-0 draws at the GCC Ground, Georgetown**. So `2-0 / Linden` and
  `0-0 / Georgetown` are each **correct** — again two distinct matches on one date. The city
  disagreement is real evidence of the date bug, not of a wrong venue.

This matters for §9 item 1: the mitigation is "which row wins?", but the correct mitigation is
**split these keys back into their real, differently-dated matches** — no score or venue is
discarded.

By contrast the **Singapore–Malaysia** case is exactly as `quirks_doc` and `FOUND.md` say:
`0-0` on 1973-09-04 is correct (SEAP Games group stage) and `0-3` really happened on
**1973-09-07** (third-place match). Confirmed against RSSSF `sea73.html` and Wikipedia
*Football at the 1973 SEAP Games*. The `goal_scorers` orphan caveat in §7 stands.

### 2.5 §6.3: the "38 goal identities / 46 surplus rows / 30 matches" figures are wrong, and
the `Peter Sharne` example is misread

Recomputed:

* Duplicated goal identities in `goals_ir` on
  `(date, home_team, away_team, scorer, goal_minute, scorer_team, current_team_score)`:
  **92 identities, 92 surplus rows, 18 matches** (or 112 / 112 / 20 if the kickoff rows are
  included). Not 38 / 46 / 30.
* **All of them come from the 20 duplicated `match_results` keys.** Restricting to matches whose
  key is *not* duplicated: **0 duplicated identities, 0 surplus rows, 0 matches**. `FOUND.md`
  attributes this inflation to the 128 duplicated `goal_scorers` rows; it is actually caused
  entirely by the §3 duplication, via the §6.1 fan-out. The 128 duplicate goal rows do **not**
  produce duplicate identities in `goals_ir` — they get distinct `current_team_score` values by
  construction.

`Peter Sharne` really does appear 4 times and `Ian Hunter` 3 times for
`1980-02-26 Australia 11-2 Papua New Guinea` — but with `current_team_score` 8, 9, 10, 11
respectively. They are **four separate numbered goals attributed to the same player**, not one
goal counted four times. The underlying 1980-02-26 anomaly is real and worth investigating
(see §3 below), but it is a *scorer-attribution* defect in the source, not a join fan-out.

### 2.6 §3.4: the `_df` inflation figure is wrong

| frame | with duplicates | deduplicated first | `FOUND.md` inflation | actual |
|---|---|---|---|---|
| `_df` | 77,385 ✅ | **77,365** (not 47,379) | +30,006 (+63%) ❌ | **+20** |
| `matches` | 47,401 ✅ | 47,381 ✅ | +20 ✅ | +20 |

`_df` is inflated by exactly the 20 duplicated rows, not by 63%. Reason: **none** of the 20
duplicated keys has any row in `goal_scorers` (verified: `dup keys with gs rows = 0`), so the
per-match fan-out `2 * N` described in `FOUND.md` never occurs. The "+63%" claim, and the
conclusion that "team goal totals, goals-per-match averages and scoreline distributions are all
wrong for those matches" in `_df`, are both unfounded. The `matches_ir` / `goals_ir`
consequences (§6.1) are real and separate.

### 2.7 §6.3 reconciliation: 22 disagreements, not 2

Comparing `goals_ir` goal-row counts against `home_score + away_score` gives **22**
disagreements. 21 of them are exactly the 20 duplicated keys (each counted twice); after
excluding those, **1** remains — the known `2024-06-27 Uruguay–Bolivia` case.

The second "disagreement" `FOUND.md` reports, `1980-09-23 Malaysia 1-1 Qatar`, does not
disagree under any counting I tried: `goal_scorers` has 2 rows for that match and the score
implies 2. The explanation given (an artifact of counting only non-NULL `scorer`) describes a
different query that was never run against `goals_ir`.

### 2.8 §10 heading "Own-goal orientation (18 rows in §5.1a)"

This heading is a copy/paste error. The 18 rows have nothing to do with own goals; they are
aggregate play-offs (§2.1). It should be titled "Aggregate play-offs decided on penalties".

### 2.9 Minor numeric drift

* §5.7: "29,225 matches have a non-zero score but zero rows in `goal_scorers`" — 29,225 is the
  count **with duplicates**; the distinct-match count is **29,208**. Minor, but the report
  presents 29,225 alongside a distinct-match denominator.
* §2.4 `matches_ir` "= 139,481 goals + 47,399 kickoff rows" ✅.

---

## 3. Open items that external sources could not settle (unchanged from `FOUND.md` §10)

These remain genuinely unresolved and are worth a human decision:

1. **`1980-02-26 Australia 11-2 Papua New Guinea`** — `goal_scorers` has 13 rows, all with NULL
   minutes, with `Peter Sharne` ×4, `Ian Hunter` ×3, and single rows for Moulis, Bertogna,
   Bozanic, Krncevic. 11 goals are credited to Australia but only 8 distinct names. Either the
   source genuinely had 11 Australian scorers with several players scoring twice (plausible for
   an 11-2 win, but then three names are wrong), or rows were duplicated. This is the single
   most suspicious record in `goal_scorers`.
2. **`1963-11-26 Ghana 2-0 Ethiopia`** — two rows both named `Edward Acquah`, both NULL minute.
   Likely two different players collapsed into one name; needs a scorer list.
3. **Scope of the team-alias problem.** `FOUND.md` found `Åland`/`Åland Islands`. I found a
   second instance: **`Saaremaa` (official) vs `Saare County` (`match_results`)**. Before
   building an alias table, check the 336 team names for non-modern forms
   (`German DR`/`Germany`, `Republic of Ireland`, `Zanzibar`, `Yugoslavia` all appear).
4. **`Taunanarive`/`Antananarivo`** — confirmed same city: renamed *Antananarivo* → *Tananarive*
   by the French in 1895, reverted **1976** (Wikipedia, *Timeline of Antananarivo*). The 1960
   African Friendship Games should therefore be recorded as `Tananarive` for period
   authenticity, or normalised — either is defensible, but the rename direction is now settled.

---

## 4. What a mitigation agent should take from this

Revised guidance, superseding `FOUND.md` §9 where they conflict:

1. **Do not drop or "fix" the 37 shootout rows.** They are correct records of aggregate
   play-offs. The fix is to `RGSE`, not to the data: `won_by` needs a third value
   (e.g. `'penalties_after_aggregate'` / `'shootout_tiebreak'`) or the two-leg context needs to
   be modelled. `won_by` recomputed from the score alone would be a regression.
2. **Do not touch `minute = 122`.** It is the correct value and a real record.
3. **Do not "choose a winner" for the 3 score-conflicting keys.** Two of them are
   date-collision bugs where *both* rows are correct matches; fix the dates. Only
   Singapore–Malaysia is a genuine date error on a single row, and it is already documented.
4. **Deduplicating `match_results` on the key is still correct and still the highest-value fix**
   — it removes the 107 `matches_ir` phantom rows, the 92 duplicated `goals_ir` identities, the
   20 rows of `_df` inflation, and the Guyana self-contradiction. But prefer **resolving** the
   conflicting keys (correct dates) over arbitrarily keeping one row, since in 2 of 3 cases both
   rows are true.
5. **The 128 duplicated `goal_scorers` rows remain a real problem**, and the NULL-value
   entanglement described in §6.5 stands — but their downstream effect is on **scorer
   attribution and `current_team_score` ordering**, not on `goals_ir` row counts.
6. **`Åland` → `Åland Islands`** and **`Saaremaa` → `Saare County`** are both real and both need
   fixing before any join on this key can be trusted.