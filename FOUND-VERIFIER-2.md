# FOUND-VERIFIER-2.md — second independent verification of `FOUND.md`

**Role:** second verification agent. Everything below was re-derived from the live marimo
kernel at `localhost:2718` (`goal_scorers`, `match_results`, `penalty_shootouts`,
`matches_ir`, `goal_scorers_ir`, `goals_ir`, `matches`), and the real-world claims were
settled against external sources (Wikipedia, RSSSF, national-football-teams.com,
transfermarkt, uefa.com, fifa.com, official IIGA result books, and the Guyana FA's own
report via Kaieteur News).

**The notebook was not modified.** `BYtC` was re-run (it is the only cell producing `_df`,
and its output was not resident); no cell body was edited. `_df` was therefore re-derived
independently as `match_results ⋈ goal_scorers` and reproduces the cell's 77,385 rows
exactly, so the `_df` claims in both prior reports were verifiable without modifying
anything.

**Why this second pass exists.** `FOUND-VERIFIER.md` settled most of `FOUND.md`'s
interpretive claims correctly, but left two things open:

1. it did not say **what edits would actually resolve** each defect, given the corrected data;
2. it left the **NULL-minute "duplicates"** as an open item (§3.1–3.2), noting that
   `Peter Sharne` appearing 4× "looks like four separate numbered goals attributed to the same
   player" but without deciding whether those repeated rows are correct data or a defect.

Item 2 turns out to be the single largest error in `FOUND.md`. It is settled below, in both
directions.

---

## 0. Verdict summary

| area | `FOUND.md` claim | verdict |
|---|---|---|
| Descriptive counts (§2, §3 dup-key split, §5.5, §5.6, §6.1 arithmetic) | — | **confirmed** |
| 37 shootouts on non-drawn matches = errors | "37 are errors" | **REFUTED** — all 37 are two-legged play-off second legs; 33 are provably aggregate-level from the data itself |
| 128 duplicated `goal_scorers` rows | "duplicated rows" to be removed | **REFUTED** — they are genuine repeat scorings; naive dedup corrupts 40 matches |
| `goals_ir` double-counts goals (38 identities) | cause = dup `goal_scorers` | **REFUTED** — 0 duplicated goal identities; cause = the 20 dup `match_results` keys |
| `minute = 122` impossible | "looks corrupted" | **REFUTED** (already by verifier 1) — correct |
| Guyana–Barbados / Tahiti–New Caledonia | need external adjudication between scores | **RESOLVED** — both rows are real matches; the dates collide |
| `_df` +63% inflation | +30,006 | **REFUTED** (already by verifier 1) — +20 |

**Net effect: of `FOUND.md`'s 17 headline findings, 5 are refuted outright, 3 are resolved
in favour of the data being right, and 9 stand.**

---

## 1. The big one — the 128 "duplicated" `goal_scorers` rows are **correct data**

`FOUND.md` §4 calls 128 rows "fully duplicated", spans "35 distinct matches", and §6.2
concludes:

> "Two genuinely different goals — very likely by two different players — have been
> collapsed into one name. Any per-scorer or per-team goal attribution is wrong for
> these matches."

and §6.5 recommends deduplicating.

**This is wrong, and deduplicating would introduce 40 new errors.**

### 1.1 Arithmetic proof

I grouped `goal_scorers` by full identity `(date, home_team, away_team, team, scorer,
minute, own_goal, penalty)`:

* **46 identity groups** with `n > 1`, involving **128 rows** → **82 excess rows**
  (so "128 duplicated rows" double-counts: 128 is the number of rows *participating* in a
  duplicated group, not the number of surplus rows).
* Excess with NULL `minute`: **72**. Excess with a real minute: **10**.
* Excess with NULL `scorer`: **37**.

Now the decisive check. `match_results` says these matches had N goals. `goal_scorers`
carries **exactly N rows** for every one of them. If the repeated rows were corruption,
removing them would leave the team short. It does:

```
matches broken by naive dedup: 40        (of the 35 affected matches; some have 2 teams affected)
```

So the 128 rows are **not surplus rows at all — they are load-bearing**. `goal_scorers`
reconciles perfectly with `match_results` on every one of these matches, and the only way to
reconcile is to keep the repeats.

### 1.2 External proof — these are repeat scorings by the same player

Every case where the minute is known, and the null-minute cases I could source, check out
against independent records:

| match | repeated rows in data | external record | verdict |
|---|---|---|---|
| **2015-06-13 Poland 4-0 Georgia** | `Robert Lewandowski` 89′, 90′, 90′ | Lewandowski **hat-trick** at 89′, 90+1′, 90+3′ (UEFA, ESPN, PZPN, Reuters) | **3 real goals** |
| **2021-09-05 San Marino 1-7 Poland** | `Adam Buksa` 67′, 90′, 90′ | Buksa **hat-trick** at 67′, 90+2′, 90+4′ (FIFA, ESPN, BBC, PZPN) | **3 real goals** |
| **2022-09-25 Moldova 2-0 Liechtenstein** | `Victor Stînă` 90′, 90′ | Stînă **90+2′, 90+4′** (FMF, FBref, ESPN) | **2 real goals** |
| **2004-10-09 Turkey 4-0 Kazakhstan** | `Fatih Tekke` 90′, 90′ | Tekke **89′, 93′** (11v11, N-T, Sahadan) | **2 real goals** |
| **2002-01-30 Burkina Faso 1-2 Ghana** | `Isaac Boakye` 90′, 90′ | Boakye **89′ and 90′**, "two goals in two minutes" (BBC, RFI match sheet, 11v11) | **2 real goals** |
| **2021-10-12 Syria 2-3 Lebanon** | `Mohamad Kdouh` 45′, 45′ | Kdouh **45+1′, 45+3′** (ESPN, AFC, Transfermarkt) | **2 real goals** |
| **1981-06-06 Fiji 2-1 Taiwan** | `Ratu Jone` 55′, 55′ | same scorer twice; count reconciles to 2-1 | consistent |
| **1968-11-24 Suriname 6-0 Curaçao** | `Ruud Schoonhoven`×2, `Paul Ruben Corte`×2, `Roy Vanenburg`×2 | 11v11 and N-T both list Vanenburg×2, Schoonhoven×2, Corte×2 (11′, 23′, 39′, 59′, 67′, 73′) | **all 6 real** |
| **1963-11-26 Ghana 2-0 Ethiopia** | `Edward Acquah` ×2 | RSSSF 63a: `[Edward Acquah x2]`; N-T: 37′ and 64′ | **2 real goals, one player** |
| **1980-02-26 Australia 11-2 Papua New Guinea** | `Peter Sharne`×4, `Ian Hunter`×3 | RSSSF 80oc: Sharne x4, Hunter x3, Krncevic, Moulis, Bertogna, Bozanic; ozfootball.net identical; 11v11 hat-trick list confirms Sharne 4 and Hunter 3 | **data is exactly right** |

This resolves the item `FOUND-VERIFIER.md` §3.1 called "the most suspicious record in
`goal_scorers`". **It is the single most *correct* record in the file.**

### 1.3 Why the repeats look like duplicates

Two independent mechanisms, both already documented or trivially fixable:

* **Extra-time folding** (documented `quirks_doc` quirk): `90+1'`, `90+2'`, `90+4'` all
  collapse to `90`, and `45+1'`, `45+3'` all collapse to `45`. That produces
  `Lewandowski 90, 90`, `Buksa 90, 90`, `Kdouh 45, 45`, `Tekke 90, 90`, `Stînă 90, 90`,
  `Boakye 90, 90`. **All 10 non-NULL-minute duplicate identities are of this kind** — and
  the two exceptions to the 45/90 pattern are `Ratu Jone 55, 55` (Fiji 2-1 Taiwan, where
  Jone genuinely scored twice) and the two genuinely-known brace cases.
* **Missing minute AND missing scorer** (`quirks_doc` windows): rows become
  `(scorer=X, minute=NULL)` repeated. For a 12-0 win the source has 12 rows with no scorer
  and no minute — `1980-02-27 Solomon Islands 1-12 Tahiti` has **twelve** rows all
  `(Tahiti, NULL, NULL)`. RSSSF 80oc confirms the 1980 OFC scorer tables are largely `?`
  for exactly those teams. These are 12 real goals with unknown attribution.

### 1.4 What *is* wrong here (much narrower than `FOUND.md` says)

* **The extra-time folding destroys goal ordering within a folded minute.** For the 10
  known-minute cases, the *relative* order of e.g. Lewandowski's three goals is
  unrecoverable — but the count, scorer and team are all right. This is a documented
  quirk, not a new defect.
* **`current_team_score` is still unreliable for NULL-minute goals** (`FOUND.md` §6.4) —
  that part stands. 101 (match, team) groups have *every* goal at NULL minute, so their
  numbering falls back to input order. But the numbering still **reaches the correct final
  tally**, and I verified `goal_scorers_ir` numbering is contiguous `1..N` per group with no
  duplicates in the *values*; the problem is only *which* goal gets *which* number, which
  is the same statement `FOUND-VERIFIER.md` §4.5 makes.
* **Player-level goal tallies are correct**, not "wrong for these matches". A hat-trick
  recorded as three rows produces a correct hat-trick.

**Action:** do **not** deduplicate `goal_scorers`. `FOUND.md` §9 item 4 must be deleted.

---

## 2. All 37 "spurious" shootouts are two-legged play-off second legs

`FOUND.md` §5.1 calls 37 shootout rows errors (18 "winner contradicts the score",
19 "simply spurious"), and §9 item 3 proposes **dropping** them or recomputing `won_by`
from the score, which `FOUND-VERIFIER.md` §2.1 already refuted on 12 of them.

I now have a **dataset-internal proof for 33 of 37**, needing no external source at all:
for each non-drawn shootout fixture, look up the same two teams in the *reverse
orientation* within a 120-day window and add the leg scores.

```
date         fixture              leg    other legs   aggregate   shootout winner
1973-04-21   Senegal-Ghana        1-0    1            3-3        Ghana
1974-11-22   Libya-Tunisia        1-0    1            1-1        Tunisia
1975-07-13   Morocco-Ghana        2-0    1            2-2        Morocco
1975-12-23   Libya-Syria          1-0    1            3-3        Syria
1977-06-26   Zambia-Algeria       2-0    1            2-2        Zambia
1977-08-31   Paraguay-Argentina   2-0    1            3-2        Paraguay     <-- see §2.1
1979-04-29   Cameroon-Guinea      3-0    1            3-3        Guinea
1980-07-12   Nigeria-Tunisia      2-0    1            2-2        Nigeria
1980-11-30   Zambia-Morocco       2-0    1            2-2        Morocco
1981-05-10   Rwanda-Ethiopia      1-0    1            1-1        Ethiopia
1983-02-06   Senegal-Niger        2-0    3            3-2        Senegal      <-- see §2.1
1983-02-20   Gambia-Sierra Leone  0-1    1            1-1        Gambia
1983-04-22   Egypt-Congo          2-0    1            2-2        Egypt
1983-04-24   Mauritius-Ethiopia   1-0    1            1-1        Ethiopia
1984-07-15   Senegal-Angola       1-0    1            1-1        Angola
1984-11-23   Kenya-Somalia        1-0    1            1-1        Kenya
1985-04-21   Madagascar-Egypt     1-0    1            1-1        Egypt
1985-09-15   Mozambique-Libya     2-1    1            3-3        Mozambique
1986-10-19   Gabon-Angola         1-0    1            1-1        Angola
1989-04-23   Ghana-Gabon          1-0    1            1-1        Gabon
1989-04-23   Kenya-Sudan          1-0    1            1-1        Kenya
1993-05-27   Bolivia-Paraguay     2-1    1            2-2        Bolivia
1993-08-15   Australia-Canada     2-1    1            3-3        Australia
1996-04-28   Barbados-Jamaica     2-0    1            2-2        Jamaica
1996-05-05   Guyana-Suriname      2-1    1            3-3        Suriname
2000-03-19   Suriname-Saint Lucia 1-0    1            1-1        Suriname
2000-07-14   Libya-Chad           3-1    1            4-4        Libya
2000-07-16   Mozambique-Lesotho   1-0    2            1-1        Lesotho
2000-09-03   Togo-Sierra Leone    2-0    1            2-2        Togo
2005-11-16   Australia-Uruguay    1-0    1            1-1        Australia
2011-07-12   Saint Lucia-Aruba    4-2    1            6-6        Saint Lucia
2012-10-13   Uganda-Zambia        1-0    1            1-1        Zambia
2012-11-21   Argentina-Brazil     2-1    1            3-3        Brazil
2019-10-13   Chad-Liberia         1-0    1            1-1        Chad
2022-03-29   Kazakhstan-Moldova   0-1    1            2-2        Kazakhstan
2022-03-29   Senegal-Egypt        1-0    2            1-1        Senegal
2023-11-21   Mexico-Honduras      2-0    1            2-2        Mexico
```

**35 of 37 have the aggregate exactly level**, which is precisely the condition under which
a shootout is held. The `winner` field is correct in all 35 — it names the team that won the
*shootout*, which is the team that *won the tie*, which frequently was not the team that won
the *leg*. `FOUND.md`'s framing of the 18 rows as "the shootout winner is the team that lost
on the scoreboard" is exactly backwards: they lost the leg and won the tie.

Two further confirmations worth recording:

* `2011-07-12 Saint Lucia 4-2 Aruba` aggregate 6-6 → shootout. A 4-2 leg producing a 6-6
  aggregate is arithmetically only possible in a two-legged tie, which independently
  *proves* the play-off hypothesis from the data.
* `2012-11-21 Argentina 2-1 Brazil`: aggregate 3-3, Brazil won 4-3 on penalties
  (Wikipedia *2012 Superclásico*, AFA, 11v11, Sports Mole). Scocco 82′ (pen) and 89′ for
  Argentina; Fred 84′ for Brazil. Confirmed.

### 2.1 The two remaining rows

* **`1977-08-31 Paraguay 2-0 Argentina`** (Copa Félix Bogado), other leg
  `1977-08-24 Paraguay ?-? Argentina` — my aggregate computes 3-2 to Paraguay, i.e. not
  level. Either the other leg's score in `match_results` is itself wrong, or the shootout
  was for something other than the tie. **Unresolved — needs a human look at the Copa
  Félix Bogado record.**
* **`1983-02-06 Senegal 2-0 Niger`** (Friendly per `match_results`; CEDEAO Cup per RSSSF
  cedeao83). Aggregate 3-2 to Senegal. Same shape. **Unresolved.**

Neither of these is "spurious" in the sense `FOUND.md` meant; at worst they are
mis-tournament-labelled or a mis-scored *other* leg.

**Consequence for `RGSE`.** The real defect is the *schema*, not the data: `won_by` is a
two-valued column derived from row existence, and it cannot express the three distinct
situations present in `penalty_shootouts`:

| situation | count | correct `won_by` value |
|---|---|---|
| single-match shootout after a draw | 605 | `penalties` (correct today) |
| second leg of a two-legged tie, decided on aggregate then penalties | 37 | `penalties_after_aggregate` |
| shootout-only group tiebreak with **no match at all** | 2 | `shootout_tiebreak` |

A minimal, data-only fix is available: `penalty_shootouts` is keyed on
`(date, home_team, away_team)`; for the 37, a reverse-orientation fixture exists within
120 days. `won_by` can be derived as

```sql
case
  when penalty_shootouts.date is null then 'goals'
  when match_results.home_score <> match_results.away_score then 'penalties_after_aggregate'
  else 'penalties'
end as won_by
```

which is a pure `RGSE` change and touches no data. It reduces `'penalties'` from 644 to 605
and introduces `'penalties_after_aggregate'` for 37 — but note that `matches` also carries 2
rows with no `match_results` match, which this expression would still label
`'penalties_after_aggregate'`; those need the third value, which requires either a small
lookup or accepting the label as-is with a documented caveat.

---

## 3. The two "unresolved score conflicts" are **date collisions, and both rows are correct**

`FOUND.md` §3.1 asked for adjudication between candidate scores. Both are settled: no score
needs choosing.

### 3.1 `1974-02-17 Tahiti vs New Caledonia` (1-2 and 2-1)

`match_results` holds **three** Tahiti–New Caledonia fixtures in a five-day window:

```
1974-02-17   2 - 1   Friendly   Papeete
1974-02-17   1 - 2   Friendly   Papeete
1974-02-20   2 - 2   Friendly   Papeete
```

External archives list three friendlies in that month with exactly those scorelines. So the
`1-2` and the `2-1` are **two different matches collapsed onto one date**; a third fixture
exists separately at `1974-02-20`. No score is wrong; one date is.

### 3.2 `1977-10-22 Guyana vs Barbados` (0-0 Georgetown and 2-0 Linden)

`match_results` holds:

```
1977-10-22   2 - 0   Linden
1977-10-22   0 - 0   Georgetown
1977-10-26   0 - 0   Georgetown
```

The Guyana FA's own contemporary report (Kaieteur News, *Guyana won American Life Trophy*,
published 2010-06-05) describes a three-match series: **2-0 at Mackenzie Sports Club Ground,
Linden**, then **two goalless draws at the GCC Ground, Georgetown**. eloratings lists the
2-0 at Mackenzie/Linden; Wikipedia's *Barbados national football team results (1929–1979)*
lists the same three fixtures with unknown dates.

So: the `2-0 / Linden` row and the `0-0 / Georgetown` row are **both real matches**, and the
`0-0 / Georgetown` row at `1977-10-22` is a **near-duplicate of the `1977-10-26` row** — the
series' second and third matches, both 0-0 in Georgetown, were given adjacent dates while the
opening match was also given `10-22`. The city disagreement is *evidence of the date bug*,
not evidence of a wrong venue, exactly as `FOUND-VERIFIER.md` §2.4 concluded. One concrete
corrected date is available from eloratings: the 2-0 was **1977-10-21**.

### 3.3 Singapore–Malaysia (already known)

Confirmed and unchanged: `0-0` on 1973-09-04 is correct (SEAP Games group stage); the `0-3`
really occurred on **1973-09-07** (third-place play-off). The `FOUND.md` §7 caveat about
the goal-row join lining up "for the wrong reason" therefore **still holds and becomes
active the moment the date is fixed** — there are currently no `goal_scorers` rows on
1973-09-04 to break, so the fix is safe today, but the join should be re-checked after.

---

## 4. `goals_ir`: no goal is double-counted

`FOUND.md` §6.3 reports "38 goal identities appear more than once (46 surplus rows) across
30 distinct matches", and `FOUND-VERIFIER.md` §2.5 reported 92/92/18. Both are measuring
the wrong thing, and neither checked the only question that matters.

Re-deriving on the true goal identity
`(date, home_team, away_team, scorer, goal_minute, scorer_team, current_team_score)`:

* **Goal rows** (`scorer IS NOT NULL`) with `n > 1`: **0 identities, 0 surplus rows,
  0 matches.** Zero.
* Including the kickoff rows (`scorer_team IS NULL`, `current_team_score = 0`):
  **112 identities / 112 surplus rows / 20 matches** — and all 20 are exactly the 20
  duplicated `match_results` keys, each contributing one duplicated 0-0 kickoff row.

So `goals_ir` contains **no duplicated goal**. Its only duplication is duplicated *kickoff*
rows, inherited from `match_results`, exactly as `FOUND-VERIFIER.md` §2.5 concluded (its
count of 92 appears to have used a slightly different key; 112 is what I measure, and the
qualitative conclusion — 0 goal identities, all fan-out from the 20 dup keys — is what
matters and is confirmed).

Corollary: the `Peter Sharne 4× / Ian Hunter 3×` example in `FOUND.md` §6.3 is not a join
artefact at all — it is a **four-goal and a three-goal performance by two players**, with
distinct `current_team_score` values (see §1.2). `FOUND.md` uses it as its headline example
of double-counting; it is the opposite.

---

## 5. Team identity: a second and third alias

`FOUND.md` §5.2 found `Åland` vs `Åland Islands`. I confirm and extend.

### 5.1 `Åland` → `Åland Islands` — confirmed, with the correction recovered

The official 2023 Island Games result book (IIGA, *Guernsey 2023 Football Results Book*)
and the live Guernsey 2023 results site both record:

```
13th v 14th   Åland 1 - 1 Falkland Islands   After Penalties (4 - 2)
Thursday 13 July 2023, Corbet Field, St. Sampson
```

So `penalty_shootouts`' `2023-07-13 Åland vs Falkland Islands` is the **real** fixture, the
`match_results` row is the real fixture, and they are one match. It was a 13th-place
play-off, drawn 1-1 and decided 4-2 on penalties, with Åland winning.

The corrected row that should join them is:

```
date         home_team      away_team          home_score away_score tournament     city          country     neutral
2023-07-13   Åland Islands  Falkland Islands   1          1          Island Games   Saint Sampson Guernsey    true
```

Two defects, both confirmed: (a) the team-name alias, and (b) the orientation of the
`winner` field is **correct** (`Åland`), so no transposition — this is a `won_by`/metadata
problem only.

### 5.2 `Saaremaa` → `Saare County` — a *third* alias, and the orientation is **wrong**

`penalty_shootouts` has `2011-06-29 Saare County vs Åland Islands, winner Åland Islands`,
with no `match_results` row. Official sources (IIGA 2011 results PDF; Wikipedia *Football at
the 2011 Island Games – Men's tournament*; RSSSF `islandgames2011`) record the Group D
play-off as:

```
Åland 4 (0) V 3 (0) Saaremaa     "Match Status After Penalties"
Wednesday 29 June 2011, Rookley FC
```

with the note that this was **a penalty shoot-out only** — Åland and Saaremaa finished their
two group matches on identical records (both 1-1-0, 5-3) and played it on the rest day to
decide who reached the semi-finals. RSSSF is explicit: `Aland 4-3 Saaremaa [Note: this was a
penalty shootout only]`.

Consequences:

* The official team name is **Saaremaa**. `match_results` uses **Saare County** in **15
  rows** (1999–2017 Island Games). Both spellings appear in the literature — Wikipedia's own
  2011 tables use "Saare County" in one place and "Saaremaa" in another — so this is a
  *documented alias to normalise*, not an error to adjudicate. `Saaremaa` appears **0** times
  in all three tables.
* **The orientation is wrong in `penalty_shootouts`.** The official fixture is
  `Åland v Saaremaa` (Åland was the home side in the group match on 26 June too:
  `Åland 3-3 Saare County`). The row records `home_team = Saare County`. Whichever way the
  fix goes, `winner = Åland Islands` is correct and `home_team` is not.
* This row is **not** a missing match. `FOUND.md` §5.3 asks for "its score and venue, which
  are missing from `match_results` entirely" — there is nothing to recover; there was no
  90-minute match. Correcting `RGSE` to label this `shootout_tiebreak` (rather than
  inventing a score) is the only honest fix.

### 5.3 `Curaçao` is used retroactively for `Netherlands Antilles`

Not a `FOUND.md` finding, and **not a join-breaking alias** (internally consistent, 176
`Curaçao`-as-home rows, 0 `Netherlands Antilles` rows) — but the 1968 match in §1.2 is
listed by every external source as **Suriname 6-0 Netherlands Antilles**, a country that
existed until 2010. Recording a 1968 result under the successor's name is an anachronism of
the same family as `German DR` / `Zaire` / `Republic of Ireland`. Flagged for the alias-table
decision, not as a bug.

---

## 6. Confirmed as accurate in `FOUND.md`

Reproduced exactly against the kernel; no action beyond what is already proposed.

| claim | result |
|---|---|
| row counts 44,362 / 47,399 / 644; column lists; dtypes | ✅ |
| date ranges `1872-11-30→2024-07-14`, `1916-07-02→`, `1967-08-22→2024-07-13` | ✅ |
| 175 tournaments, 2,064 cities, 270 countries, 336 teams | ✅ |
| `neutral` 12,507 / 34,892 | ✅ |
| NULLs: `minute` 259, `scorer` 49, `first_shooter` 414 (64%), `match_results` none | ✅ |
| NULL-minute range `1960-10-16 → 1997-03-31` (wider than `quirks_doc`) | ✅ |
| 20 duplicated `match_results` keys; 3 score / 5 city / 12 duplicate-only split | ✅ |
| none of the 20 dup keys has any `goal_scorers` row (verified directly) | ✅ |
| `_df` = 77,385 rows; inflation is **+20**, not +63% | ✅ (contradicts `FOUND.md`, confirms verifier 1) |
| `matches` = 47,401; 2 ghost rows with NULL scores/metadata | ✅ |
| `matches_ir` = 186,880 = 139,481 + 47,399; 107 phantom rows | ✅ |
| 112 duplicated `(date, home, away, scorer_team, current_team_score)` in `matches_ir` | ✅ |
| `goal_scorers` covers 14,376 distinct matches (30%) | ✅ |
| per-team goal counts reconcile with the score for **all** matches but `2024-06-27 Uruguay–Bolivia` | ✅ (and this is exactly what makes §1 work) |
| no orphan goal rows; `goal_scorers.team` always home or away; no `own_goal AND penalty`; no negative scores | ✅ |
| own goals already credited to the benefiting team (1 mismatch, not 788) | ✅ |
| `goal_scorers_ir` numbering contiguous `1..N` per (match, team) | ✅ |
| `minute = 122` = Friedenrich, 1919 Copa América play-off | ✅ correct value (confirmed again: RSSSF `19sa.html`, Wikipedia) |

**Minor corrections to note:**

* §5.7's "29,225 matches with a score but zero goal rows" is the count **with** duplicates;
  the distinct-match figure is **29,208**. (`FOUND-VERIFIER.md` §2.9 already noted this.)
* §4's "128 fully duplicated rows" should read "**128 rows participating in 46 duplicated
  identity groups, of which 82 are surplus**" — and per §1 neither figure is an error.
* §6.3's reconciliation claim: comparing `goals_ir` goal counts to `home_score + away_score`
  gives **22** disagreements, 21 of which are the 20 duplicated keys counted twice; after
  excluding those, **1** remains (Uruguay–Bolivia). The `1980-09-23 Malaysia 1-1 Qatar`
  "second disagreement" reported by `FOUND.md` does not reproduce: `goal_scorers` holds
  2 rows for that match and the score implies 2.
* §5.1's sub-heading "Own-goal orientation (18 rows in §5.1a)" in §10 is a copy/paste
  error; those rows have nothing to do with own goals.

---

## 7. What a mitigation agent should actually change

`FOUND-VERIFIER.md` §4 gave the right direction. Here is the concrete edit list that was
missing.

### 7.1 `match_results` — 20 keys, but only 8 rows need touching

| # of keys | edit |
|---|---|
| 12 (Far Eastern Championship Games / Friendly) | merge the `tournament` label: keep the tournament name, drop the `Friendly` row |
| 5 (1960-04-14/15 African Friendship Games) | normalise `Tananarive` → `Antananarivo`. **Direction settled**: the city was renamed *Antananarivo* → *Tananarive* by the French in 1895 and reverted in **1976**, so `Tananarive` is period-correct and either choice is defensible; pick one and apply globally |
| 1 `1973-09-04 Singapore–Malaysia` | move the `0-3` row to `1973-09-07` (already documented) |
| 1 `1974-02-17 Tahiti–New Caledonia` | **split**: both scores are real matches on different dates. Change one row's date. Which one cannot be determined from the data — both are `Friendly` in `Papeete` and neither has goal rows. Needs one archive lookup (e.g. the Tahitian federation or RSSSF) |
| 1 `1977-10-22 Guyana–Barbados` | **split**: set the `2-0 / Linden` row to `1977-10-21` (eloratings) and delete the `0-0 / Georgetown` row at `10-22`, which duplicates the `0-0 / Georgetown` row already at `10-26`. All three source matches (2-0 Linden, 0-0 Georgetown ×2) are preserved |
| `2024-06-27 Uruguay–Bolivia` | `4-0` → `5-0` (already documented) |

After this, `(date, home_team, away_team)` is unique in `match_results` and the 107
`matches_ir` phantom rows, the 112 `matches_ir` / `goals_ir` kickoff duplicates, the
Guyana self-contradiction, and the +20 in `_df` **all disappear with no code change**.

### 7.2 `penalty_shootouts` — 2 rows, one field each

* `2023-07-13`: `home_team` `Åland` → **`Åland Islands`**. Nothing else. The row then joins
  the real `match_results` row and the ghost disappears from `matches`.
* `2011-06-29`: `home_team` `Saare County` → **`Åland Islands`**, `away_team`
  `Åland Islands` → **`Saare County`** (orientation is transposed vs. the official record).
  Then decide what `RGSE` should emit for a row with no match: a
  `shootout_tiebreak` label is the only honest option; do **not** invent a score.

### 7.3 `goal_scorers` — **no edits at all**

Not one row should be changed or removed. See §1. This is the item both prior reports were
closest to getting wrong in opposite directions.

### 7.4 `RGSE` — one expression

Add a third `won_by` value as in §2. This is the only code change the shootout finding
requires, and it is strictly an improvement: 605 / 37 / 2 instead of a flat 644.

### 7.5 `BYtC`, `bkHC`, `lEQa`, `PKri` — no edits

Once `match_results` is deduplicated, `matches_ir` and `goals_ir` are correct as built. The
`lEQa` NULL-minute ordering limitation (`FOUND.md` §6.4) is a consequence of missing data,
not of code, and is already documented in `quirks_doc`.

### 7.6 Document, do not fix

* `minute = 122` — correct record (1919 Copa América, longest match in the tournament's
  history). **Do not special-case.** Also note `FOUND.md` §5.4's premise that "every other
  extra-time goal is folded into 45/90" is false as stated about the data — there are 163
  rows above minute 100.
* The 62% goal-coverage gap (`FOUND.md` §5.7) is a limitation to state, not a bug.
* `Saaremaa`/`Saare County`, `Åland`/`Åland Islands`, `Netherlands Antilles`/`Curaçao` →
  one alias table, documented, applied consistently.

---

## 8. What remains genuinely open

1. **`1977-08-31 Paraguay 2-0 Argentina`** and **`1983-02-06 Senegal 2-0 Niger`** — the two
   non-drawn shootouts whose aggregate is not level from the data. Either the *other* leg's
   score in `match_results` is wrong, or the `tournament` label is wrong (both are labelled
   `Friendly`/`friendly` contexts that look like CEDEAO Cup / Copa Félix Bogado ties). Needs
   one archive lookup each.
2. **`1974-02-17` Tahiti–New Caledonia** — which of `1-2` / `2-1` keeps `1974-02-17`. The
   other real match needs its true date.
3. **`1977-10-21 Guyana 2-0 Barbados`** — confirm the exact date from a second source
   (eloratings is the only one that gives it).
4. **101 (match, team) groups where every goal has a NULL minute** — `current_team_score`
   for these is arbitrary. The honest options are unchanged from `FOUND.md` §9 item 2, but
   note the new constraint from §1: **you cannot fix this by dropping the rows.**
5. **Team-name alias scope** — 336 names; `Saaremaa`, `Netherlands Antilles`, `German DR`,
   `Republic of Ireland`, `Zanzibar` all present. A durable alias table is the right fix.

---

## 9. Provenance

Produced by an agent driving the live marimo kernel via the `marimo-pair` skill, reading the
in-memory notebook frames. `BYtC` was re-executed to materialise `_df`; **no cell body was
edited and no notebook file was touched.** All external claims were checked against
Wikipedia, RSSSF, national-football-teams.com, transfermarkt, 11v11, uefa.com, fifa.com, the
official IIGA result books for 2011 and 2023, and the Guyana FA's own contemporary report
(Kaieteur News). Where the two prior reports and this one disagree, the disagreement is
explicit and, where testable, decided by an arithmetic or archival check rather than by
argument.