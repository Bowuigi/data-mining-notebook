# /// script
# dependencies = [
#     "altair==6.3.0",
#     "duckdb==1.5.5",
#     "marimo",
#     "mcp==2.2.0",
#     "polars[pyarrow]==1.44.2",
#     "python-lsp-ruff==2.3.4",
#     "ruff==0.16.9",
#     "sqlglot==30.19.0",
#     "unidecode==1.4.0",
#     "vegafusion",
#     "vl-convert-python",
#     "websockets==17.1",
# ]
# requires-python = ">=3.13"
# ///

import marimo

__generated_with = "0.25.1"
app = marimo.App(app_title="DM Fútbol", sql_output="polars")

with app.setup:
    ### Import libraries as required

    import marimo as mo
    import polars as pl
    import altair as alt

    import unidecode

    from corrections import (CITY_ALIASES, COUNTRY_ALIASES, REGION, TEAM_ALIASES)

    ### Load data

    def _from_csv(filename: str):
        return pl.read_csv(
            filename, null_values=["NA"], schema_overrides={"date": pl.Date}
        )

    goal_scorers = _from_csv("data/Goal_Scorers.csv")
    match_results = _from_csv("data/Match_Results.csv")
    penalty_shootouts = _from_csv("data/Penalty_Shootouts.csv")

    ### Correcciones sobre los datos base

    # Clave natural de un partido y única clave de unión del notebook. Las
    # correcciones de esta celda son las que la hacen única: son ellas las que
    # desarman las 20 claves repetidas de `match_results`. No hay clave sintética
    # aparte, así que la unicidad de `K` es un invariante que hay que mantener, no
    # una propiedad que se pueda recuperar después.
    K = ["date", "home_team", "away_team"]

    goal_scorers = goal_scorers.with_columns(
        [
            pl.col(c).replace(TEAM_ALIASES)
            for c in ("home_team", "away_team", "team")
        ]
    )

    # Se convierten los nombres de jugador a ASCII.
    #
    # NFKD por sí solo no alcanza: 214 goleadores usan letras que no se descomponen
    # (ø, ł, đ, ß, æ, þ, ð, ı, ə). La versión anterior las borraba con
    # `str.replace_all(r"[^\x20-\x7E]", "")`, que mutilaba el nombre
    # (`Søren Larsen` -> `Sren Larsen`, `Ødegaard` -> `degaard`).
    # `unidecode` translitera esas letras y quita los diacríticos, y ya devuelve
    # ASCII puro, así que no hace falta NFKD ni `unicodedata` aquí.
    goal_scorers = goal_scorers.with_columns(
        pl.col("scorer")
        .map_elements(unidecode.unidecode, return_dtype=pl.String)
        .alias("scorer")
    )

    # Aplicar aliases
    match_results = match_results.with_columns(
        [pl.col(c).replace(TEAM_ALIASES) for c in ("home_team", "away_team")]
    )
    penalty_shootouts = penalty_shootouts.with_columns(
        [
            pl.col(c).replace(TEAM_ALIASES)
            for c in ("home_team", "away_team", "winner")
        ]
    )
    match_results = match_results.with_columns(
        pl.col("city").replace(CITY_ALIASES)
    )
    match_results = match_results.with_columns(
        pl.col("country").replace(COUNTRY_ALIASES).alias("normalized_country")
    ).with_columns(
        pl.col("normalized_country").replace(REGION).alias("region")
    )


    # 2011-06-29 está invertido: el desempate lo ganó Åland como local.
    _is_tiebreak = (pl.col("date") == pl.date(2011, 6, 29)) & (
        pl.col("home_team") == "Saaremaa"
    )
    penalty_shootouts = penalty_shootouts.with_columns(
        pl.when(_is_tiebreak)
        .then(pl.col("away_team"))
        .otherwise(pl.col("home_team"))
        .alias("home_team"),
        pl.when(_is_tiebreak)
        .then(pl.col("home_team"))
        .otherwise(pl.col("away_team"))
        .alias("away_team"),
    )

    # 17 claves duplicadas por un segundo registro `Friendly` de un partido de torneo
    # (Far Eastern Championship Games 1923-1934, African Friendship Games 1960).
    # Se conserva el registro del torneo.
    _duplicated_by_tournament = (
        match_results.filter(pl.col("tournament") != "Friendly")
        .select(K)
        .unique()
        .with_columns(pl.lit(True).alias("_has_tournament_row"))
    )
    match_results = (
        match_results.join(_duplicated_by_tournament, on=K, how="left")
        .filter(
            ~(
                (pl.col("tournament") == "Friendly")
                & pl.col("_has_tournament_row").fill_null(False)
            )
        )
        .drop("_has_tournament_row")
    )

    # The three remaining duplicate keys are two real matches recorded under one date.
    match_results = match_results.with_columns(
        pl.when(
            (pl.col("date") == pl.date(1973, 9, 4))
            & (pl.col("home_team") == "Singapore")
            & (pl.col("home_score") == 0)
            & (pl.col("away_score") == 3)
        )
        .then(pl.date(1973, 9, 7))
        .otherwise(pl.col("date"))
        .alias("date")
    )
    match_results = match_results.with_columns(
        pl.when(
            (pl.col("date") == pl.date(1974, 2, 17))
            & (pl.col("home_team") == "Tahiti")
            & (pl.col("home_score") == 1)
            & (pl.col("away_score") == 2)
        )
        .then(
            pl.date(1974, 2, 18)
        )  # provisional: the two legs are not separable here
        .otherwise(pl.col("date"))
        .alias("date")
    )
    match_results = match_results.with_columns(
        pl.when(
            (pl.col("date") == pl.date(1977, 10, 22))
            & (pl.col("home_team") == "Guyana")
            & (pl.col("city") == "Linden")
        )
        .then(pl.date(1977, 10, 21))
        .otherwise(pl.col("date"))
        .alias("date")
    )
    # The 0-0 / Georgetown row on 10-22 is the same fixture already recorded on 10-26.
    match_results = match_results.filter(
        ~(
            (pl.col("date") == pl.date(1977, 10, 22))
            & (pl.col("home_team") == "Guyana")
            & (pl.col("city") == "Georgetown")
        )
    )


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Nota: Se utilizó IA **sólo** para agilizar la escritura de código y la verificación de datos. En particular, el proceso KDD se llevó a cabo bajo dirección humana y "a pasitos", revisando todo 2 veces por las dudas. Aplicación: OpenCode; Modelo: Space Bunny Free (uno de los "incógnito", eventualmente revelarán cuál es y quién lo hizo).

    # Fase 1: Objetivos de negocio

    - Objetivo descriptivo:
    - Objetivo predictivo:
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Fase 2: Selección y creación del target dataset
    """)
    return


@app.cell(hide_code=True)
def ir_doc():
    mo.md(r"""
    **Tablas intermedias:**
    - `match_results` (corregida): Una fila por partido, con `(date, home_team, away_team)`
      como clave única de unión de todo el notebook. Es el punto de partida de todo lo
      demás, así que no es una tabla intermedia: las columnas que le suman las
      correcciones de la celda de base son
      - `normalized_country`: País actual cuando hay un sucesor único y no ambiguo; si no, el nombre histórico tal cual.
      - `region`: Geografía actual, siempre bajo un nombre actual (`USSR` → `Europe`, `Zanzibar` → `Africa`).
    - `goal_events`: Una fila por gol de `goal_scorers`.
      <br>Suma las siguientes columnas:
      - `goal_no`: Enésimo gol de ese equipo en ese partido, según el orden del source data.
      - `has_incomplete_minute_data`: `True` si a algún gol de ese partido le falta `minute`.

        Se renombran las siguientes columnas de `goal_scorers`:
      - `team` → `scorer_team`
      - `minute` → `goal_minute`
      - `own_goal` → `goal_was_own_goal`
      - `penalty` → `goal_was_penalty`
    - `shootout_events`: Una fila por partido de `penalty_shootouts`.
      <br>Es `penalty_shootouts` renombrado. 643 de sus 644 filas caen en un partido de
      `match_results`; la restante es `2011-06-29 Åland v Saaremaa`, un desempate sin
      partido de 90 minutos, y no se une con ninguna.

        Se renombran las siguientes columnas de `penalty_shootouts`:
      - `winner` → `shootout_winner`
      - `first_shooter` → `penalty_first_shooter`
    - `matches`: Una fila por partido, con el marcador reconciliado contra los goles.
      <br>Suma las siguientes columnas:
      - `has_goal_detail`: `True` si el partido tiene goles en `goal_scorers` (14.376 de 47.381).
      - `shootout_winner`, `penalty_first_shooter`: Del shootout, si lo hubo.
      - `winner`: Local o visitante según el marcador; si empataron, el ganador del shootout.
      - `won_by`: `goals` / `penalties` / `penalties_after_aggregate` / `shootout_tiebreak`.
    - `goals_ir`: Una fila por momento del partido: los goles reales de `goal_events`, y para los partidos sin goleadores, filas derivadas del marcador.
      <br>Suma las siguientes columnas a los goles:
      - `goal_no`, `has_incomplete_minute_data`: De `goal_events`.
      - `current_team_score`: Marcador de ese equipo hasta e incluyendo ese gol. Si `scorer_team` es `NULL`, es el inicio de un partido 0-0 sin goleadores.
      - `has_goal_detail`: `False` si la fila se derivó del marcador y no de `goal_scorers`.
      - `shootout_winner`, `penalty_first_shooter`, `won_by`: Del partido, por la clave `(date, home_team, away_team)`.

        Se renombran las siguientes columnas de `matches`:
      - `home_score` → `final_home_score`
      - `away_score` → `final_away_score`
      - `neutral` → `neutral_field`
    """)
    return


@app.cell
def goal_events():
    # Una fila por gol real. El orden dentro de un partido es el del source data, y
    # `goal_no` es la posición de secuencia autoritativa: nada aguas abajo la recalcula.
    # Las filas repetidas de `goal_scorers` son hat-tricks y goles repetidos de un
    # mismo jugador, no duplicados, así que no se deduplica nada.
    goal_events = (
        goal_scorers.lazy()
        .sort("date", "minute", nulls_last=True)
        .with_columns(
            goal_no=pl.int_range(1, pl.len() + 1).over(*K, "team"),
            has_incomplete_minute_data=pl.col("minute").is_null().over(*K),
        )
        .rename(
            {
                "team": "scorer_team",
                "minute": "goal_minute",
                "own_goal": "goal_was_own_goal",
                "penalty": "goal_was_penalty",
            }
        )
        .select(
            *K,
            "scorer_team",
            "goal_no",
            "scorer",
            "goal_minute",
            "goal_was_own_goal",
            "goal_was_penalty",
            "has_incomplete_minute_data",
        )
        .collect()
    )

    # Todo gol tiene que pertenecer a un partido de `match_results`. Sin clave
    # sintética esto ya no se ve como un NULL: hay que buscarlo explícitamente.
    assert goal_events.join(match_results.select(K), on=K, how="anti").height == 0
    assert (
        goal_events.select(*K, "scorer_team", "goal_no").is_duplicated().sum() == 0
    )

    goal_events
    return (goal_events,)


@app.cell
def shootout_events():
    # Una fila por shootout. 643 de 644 caen en un partido de `match_results`; la
    # restante es `2011-06-29 Åland v Saaremaa`, un desempate sin partido de 90
    # minutos, y se la deja sin unir a propósito.
    shootout_events = penalty_shootouts.rename(
        {
            "winner": "shootout_winner",
            "first_shooter": "penalty_first_shooter",
        }
    ).select(*K, "shootout_winner", "penalty_first_shooter")

    assert shootout_events.height == penalty_shootouts.height
    assert shootout_events.join(match_results.select(K), on=K, how="anti").height == 1

    shootout_events
    return (shootout_events,)


@app.cell
def matches(goal_events, shootout_events):
    # Una fila por partido. El marcador se reconcilia acá, una sola vez: si el partido
    # tiene goles registrados, el marcador pasa a ser lo que dicen las filas de gol.
    # Los goles sólo suman información, así que un partido con pocos goleadores nunca
    # puede empeorar su marcador.
    #
    # `2024-06-27 Uruguay-Bolivia` es el único partido donde el source data discrepa
    # (4-0 registrado, 5 goles) y queda reparado acá, sin fix a mano.
    _goals_counted = (
        goal_events.lazy()
        .group_by(*K)
        .agg(
            pl.col("scorer_team")
            .filter(pl.col("scorer_team") == pl.col("home_team"))
            .len()
            .cast(pl.Int64)
            .alias("_goals_from_rows"),
            pl.col("scorer_team")
            .filter(pl.col("scorer_team") == pl.col("away_team"))
            .len()
            .cast(pl.Int64)
            .alias("_goals_from_rows_away"),
        )
        .collect()
    )

    _MATCH_COLUMNS = [
        *K,
        "home_score",
        "away_score",
        "tournament",
        "city",
        "country",
        "normalized_country",
        "region",
        "neutral",
    ]

    matches = (
        match_results.select(*_MATCH_COLUMNS)
        .join(_goals_counted, on=K, how="left")
        .with_columns(
            pl.col("_goals_from_rows").is_not_null().alias("has_goal_detail")
        )
        .with_columns(
            pl.when(pl.col("has_goal_detail"))
            .then(pl.col("_goals_from_rows"))
            .otherwise(pl.col("home_score"))
            .alias("home_score"),
            pl.when(pl.col("has_goal_detail"))
            .then(pl.col("_goals_from_rows_away"))
            .otherwise(pl.col("away_score"))
            .alias("away_score"),
        )
        .join(
            shootout_events.select(*K, "shootout_winner", "penalty_first_shooter"),
            on=K,
            how="left",
        )
        .with_columns(
            pl.when(pl.col("shootout_winner").is_null())
            .then(pl.lit("goals"))
            .when(pl.col("home_score") != pl.col("away_score"))
            .then(pl.lit("penalties_after_aggregate"))
            .otherwise(pl.lit("penalties"))
            .alias("won_by"),
            # Cuando hubo shootout, el partido lo decidió el shootout. En los
            # playoffs de ida y vuelta el ganador de la partida registrada no es
            # necesariamente el que avanzó: en 18 de los 37 perdieron la ida.
            pl.when(pl.col("shootout_winner").is_not_null())
            .then(pl.col("shootout_winner"))
            .when(pl.col("home_score") > pl.col("away_score"))
            .then(pl.col("home_team"))
            .when(pl.col("home_score") < pl.col("away_score"))
            .then(pl.col("away_team"))
            .otherwise(pl.lit(None, dtype=pl.String))
            .alias("winner"),
        )
        .select(
            *_MATCH_COLUMNS,
            "has_goal_detail",
            "shootout_winner",
            "penalty_first_shooter",
            "winner",
            "won_by",
        )
    )

    # El desempate sin partido de 90 minutos vive sólo acá: no tiene marcador, ni
    # torneo, ni filas de goles. Es la única fila de `shootout_events` cuya clave no
    # aparece en `match_results`, así que se localiza con un anti-join.
    _tiebreaks = shootout_events.join(match_results.select(K), on=K, how="anti").select(
        *K,
        pl.lit(None, dtype=pl.Int64).alias("home_score"),
        pl.lit(None, dtype=pl.Int64).alias("away_score"),
        pl.lit(None, dtype=pl.String).alias("tournament"),
        pl.lit(None, dtype=pl.String).alias("city"),
        pl.lit(None, dtype=pl.String).alias("country"),
        pl.lit(None, dtype=pl.String).alias("normalized_country"),
        pl.lit(None, dtype=pl.String).alias("region"),
        pl.lit(False).alias("neutral"),
        pl.lit(False).alias("has_goal_detail"),
        "shootout_winner",
        "penalty_first_shooter",
        pl.col("shootout_winner").alias("winner"),
        pl.lit("shootout_tiebreak").alias("won_by"),
    )

    matches = pl.concat([matches, _tiebreaks], how="vertical").sort(
        "date", "home_team", "away_team"
    )

    matches
    return (matches,)


@app.cell
def goals_ir(goal_events, matches):
    # Una fila por momento del partido. Los partidos con goleadores usan los goles
    # reales de `goal_events`; los que no tienen, se derivan del marcador para que
    # sobrevivan los N-0 y los 0-0. Un 0-0 sin goleadores conserva una fila de
    # arranque, con `scorer_team = NULL`.
    def _rows_from_score(side: str):
        return (
            matches.filter(~pl.col("has_goal_detail"))
            .lazy()
            .select(
                *K,
                pl.col(f"{side}_team").alias("scorer_team"),
                pl.col(f"{side}_score")
                .cast(pl.UInt32)
                .alias("current_team_score"),
            )
            .with_columns(
                pl.int_ranges(1, pl.col("current_team_score") + 1).alias(
                    "goal_no"
                )
            )
            .explode("goal_no", empty_as_null=True)
            .filter(pl.col("goal_no").is_not_null())
            .with_columns(
                pl.col("goal_no").cast(pl.UInt32),
                pl.col("current_team_score").cast(pl.UInt32),
                pl.lit(None, dtype=pl.String).alias("scorer"),
                pl.lit(None, dtype=pl.Int64).alias("goal_minute"),
                pl.lit(False).alias("goal_was_own_goal"),
                pl.lit(False).alias("goal_was_penalty"),
                pl.lit(False).alias("has_incomplete_minute_data"),
                pl.lit(False).alias("has_goal_detail"),
            )
        )

    _kickoffs = (
        matches.filter(
            (~pl.col("has_goal_detail"))
            & (pl.col("home_score") == 0)
            & (pl.col("away_score") == 0)
        )
        .lazy()
        .select(
            *K,
            pl.lit(None, dtype=pl.String).alias("scorer_team"),
            pl.lit(None, dtype=pl.UInt32).alias("goal_no"),
            pl.lit(0, dtype=pl.UInt32).alias("current_team_score"),
            pl.lit(None, dtype=pl.String).alias("scorer"),
            pl.lit(None, dtype=pl.Int64).alias("goal_minute"),
            pl.lit(False).alias("goal_was_own_goal"),
            pl.lit(False).alias("goal_was_penalty"),
            pl.lit(False).alias("has_incomplete_minute_data"),
            pl.lit(False).alias("has_goal_detail"),
        )
    )

    goals_ir = (
        pl.concat(
            [
                goal_events.lazy().with_columns(
                    pl.lit(True).alias("has_goal_detail")
                ),
                _rows_from_score("home"),
                _rows_from_score("away"),
                _kickoffs,
            ],
            how="diagonal_relaxed",
        )
        .join(
            matches.lazy().select(
                *K,
                pl.col("home_score").cast(pl.Int64).alias("final_home_score"),
                pl.col("away_score").cast(pl.Int64).alias("final_away_score"),
                "tournament",
                "city",
                "country",
                "normalized_country",
                "region",
                pl.col("neutral").alias("neutral_field"),
                "shootout_winner",
                "penalty_first_shooter",
                "won_by",
            ),
            on=K,
            how="left",
        )
        .sort(*K, "scorer_team", "goal_no", nulls_last=True)
        .collect()
    )

    goals_ir
    return (goals_ir,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Otros experimentos (no se usan todavía)
    """)
    return


@app.cell(hide_code=True)
def quirks_doc():
    mo.md(r"""
    Cosas raras del **source data**:
    - `match_results`: 20 claves `(date, home_team, away_team)` repetidas. 17 eran un segundo registro `Friendly` de un partido de torneo (Far Eastern Championship Games 1923-1934, African Friendship Games 1960); se conserva el del torneo. Las otras 3 eran dos partidos distintos con la misma fecha: Singapur-Malasia 0-3 → `1973-09-07`; Guyana-Barbados 2-0 (Linden) → `1977-10-21` y el 0-0 (Georgetown) de `10-22` repetía el de `10-26`; Tahiti-Nueva Caledonia 2-1 y 1-2 compartían `1974-02-17`, con el 1-2 movido a `1974-02-18` **sin confirmar contra una segunda fuente**.
    - `match_results`: Uruguay-Bolivia `2024-06-27` figura 4-0 y `goal_scorers` registra 5 goles. El source queda 4-0; `matches` y `goals_ir` lo reconcilian a 5-0.
    - `match_results`: `country` con nombres obsoletos. Hay `normalized_country` (sucesor único) y `region` (geografía actual). Los de varios sucesores (`Soviet Union`, `Yugoslavia`, `Czechoslovakia`, `Serbia and Montenegro`, `Zanzibar`) conservan el nombre histórico.
    - `city`: 4 aliases, no un pliegue a ASCII. `Tananarive` → `Antananarivo` (10 filas) y 3 pares que sólo difieren en diacríticos (`Bogota`/`Bogotá`, `Gijon`/`Gijón`, `Valparaiso`/`Valparaíso`, 2+1+1 filas). **No hay más**: NFKD sobre las 2.064 ciudades da 5 colisiones y 2 son ciudades distintas -- `San Jose` (United States, 11 filas) vs `San José` (Costa Rica, 272) y `Pula` (Croatia, 4) vs `Púla` (Cyprus, 1). Pliegar `city` las fusionaría.
    - Equipos: `Åland Islands` → `Åland`, `Saare County` → `Saaremaa`. `2011-06-29` estaba invertido (`Åland v Saaremaa`).
    - `goal_scorers`: 128 filas totalmente duplicadas. **No son un error**: hat-tricks de Lewandowski y Buksa, `Peter Sharne` 4 veces. No deduplicar.
    - `goal_scorers`: 8 pares de goleadores diferían sólo en diacríticos (`Sívori`/`Sivori`, `Kéïta`/`Keita`, `Barthélemy`/`Barthelemy`, `Nguyễn Hồng Sơn`/`Nguyen Hong Son`, `Désir`/`Desir`, `Éder`/`Eder`, `Rivas`, `Þórðarson`/`Thordarson`). Se pliegan transliterando con `unidecode`. **No hay mapa de alias**: sobre 14.335 goleadores ésos son los únicos 8 casos, y unificar más sería falso (`Gerd Müller` y `Sándor Müller` son dos jugadores distintos).
    - `goal_scorers`: el nombre original con diacríticos se pierde. `scorer` queda en ASCII; sobre 14.335 goleadores, 214 cambia al transliterar y 0 quedan con caracteres no-ASCII.
    - `goal_scorers`: 259 goles sin `minute`, entre `1960-10-16` y `1997-03-31` (no 1963-1980).
    - `goal_scorers`: 49 goles sin `scorer`, entre `1980-02-24` y `1980-09-23`.
    - `goal_scorers`: `minute = 122` (Friedenreich, `1919-05-29` Brasil-Uruguay). **No es un error**.
    - `goal_scorers`: 163 goles de tiempo extra con su minuto real. No están doblados a 45/90.
    - `penalty_shootouts`: 37 con marcador no empatado. Son segundos partidos de ida y vuelta decididos por el global (33/37 con el partido de vuelta a ≤120 días y global empatado). **No borrarlos**, no recalcular `winner`.
    - `penalty_shootouts`: `first_shooter` NULL en 414 de 644 (64%).
    - `penalty_shootouts`: `2011-06-29 Åland v Saaremaa` es un desempate sin partido de 90 minutos. No aparece en `match_results`, no tiene filas en `goals_ir`, y tampoco se le inventa un marcador.
    """)
    return


@app.cell
def invariants(goal_events, goals_ir, matches, shootout_events):
    # Chequeos permanentes. Cada uno corresponde a un hallazgo que alguien tuvo que
    # descubrir a mano; dejarlos escritos es la forma más barata de que la próxima
    # pasada no vuelva a tropezar con lo mismo.

    # --- clave y grano ---
    assert match_results.select(K).is_duplicated().sum() == 0
    assert goal_events.join(match_results.select(K), on=K, how="anti").height == 0
    assert goal_events.select(*K, "scorer_team", "goal_no").is_duplicated().sum() == 0
    assert (
        goals_ir.filter(pl.col("goal_no").is_not_null())
        .select(*K, "scorer_team", "goal_no")
        .is_duplicated()
        .sum()
        == 0
    )

    # --- shootouts ---
    # 643 de 644 caen en un partido. El que queda es el desempate sin partido de
    # 90 minutos, que existe a propósito y no tiene `goals_ir`.
    assert shootout_events.height == 644
    assert shootout_events.join(match_results.select(K), on=K, how="semi").height == 643
    assert (
        shootout_events.group_by(*K)
        .agg(pl.len().alias("n"))
        .filter(pl.col("n") > 1)
        .height
        == 0
    )
    assert (
        shootout_events.select(*K).join(match_results.select(K), on=K, how="semi")[
            K
        ]
        .n_unique()
        == 643
    )
    assert (
        goals_ir.filter(pl.col("shootout_winner").is_not_null())
        .select(*K)
        .n_unique()
        == 643
    )
    assert goals_ir.filter(pl.col("won_by") == "shootout_tiebreak").height == 0

    # --- la reconciliación de marcador ---
    _uruguay_bolivia = goals_ir.filter(
        (pl.col("date") == pl.date(2024, 6, 27))
        & (pl.col("home_team") == "Uruguay")
    )
    assert (
        _uruguay_bolivia.filter(pl.col("scorer_team") == "Uruguay").height == 5
    )
    assert (
        _uruguay_bolivia.filter(pl.col("scorer_team") == "Uruguay")[
            "final_home_score"
        ]
        .eq(5)
        .all()
    )
    # Y en ningún otro sitio: ningún otro partido puede discrepar de sus goles.
    assert (
        goals_ir.filter(pl.col("has_goal_detail"))
        .group_by(*K)
        .agg(
            pl.col("scorer_team")
            .filter(pl.col("scorer_team") == pl.col("home_team"))
            .len()
            .alias("h"),
            pl.col("scorer_team")
            .filter(pl.col("scorer_team") == pl.col("away_team"))
            .len()
            .alias("a"),
            pl.col("final_home_score").first(),
            pl.col("final_away_score").first(),
        )
        .filter(
            (pl.col("h") != pl.col("final_home_score"))
            | (pl.col("a") != pl.col("final_away_score"))
        )
        .height
        == 0
    )

    # --- geografía ---
    assert match_results["normalized_country"].null_count() == 0
    assert match_results["region"].null_count() == 0

    # `city` se unifica por alias, no por pliegue: las dos colisiones que NFKD
    # produciría son ciudades distintas y no deben fusionarse.
    _cities = match_results.with_columns(
        pl.col("city").replace(CITY_ALIASES).alias("c")
    )["c"].unique()
    # los alias se aplicaron: los valores de entrada ya no están
    assert not _cities.is_in(CITY_ALIASES.keys()).any()
    # y las ciudades homónimas de países distintos siguen separadas
    assert {"San Jose", "San José", "Pula", "Púla"} <= set(_cities.to_list())
    # las 3 parejas homónimas de país distinto conservan su fila original
    assert (
        match_results.filter(pl.col("city").is_in(["San Jose", "Pula"])).height
        == 11 + 4
    ), "San Jose (US) y Pula (Croacia) deben conservar sus filas"
    assert (
        match_results.filter(
            pl.col("city").is_in(["Bogotá", "Gijón", "Valparaíso"])
        ).height
        == 88 + 14 + 12  # 86+2, 13+1, 11+1: el alias absorbe la grafía sin tilde
    ), "los aliases de ciudad no se aplicaron"

    # `scorer` queda en ASCII y transliterado, no mutilado.
    assert (
        goal_scorers["scorer"].drop_nulls().str.contains(r"[^\x20-\x7E]").sum() == 0
    )
    assert goal_scorers.filter(pl.col("scorer") == "Teitur Thordarson").height == 2
    assert goal_scorers.filter(pl.col("scorer") == "Omar Sivori").height == 8
    assert (
        match_results.filter(pl.col("normalized_country") == "Soviet Union")[
            "region"
        ]
        .eq("Europe")
        .all()
    )
    assert (
        match_results.filter(pl.col("normalized_country") == "Zanzibar")[
            "region"
        ]
        .eq("Africa")
        .all()
    )

    # --- etiquetas de shootout ---
    assert (matches["won_by"] == "goals").sum() == 46738
    assert (matches["won_by"] == "penalties").sum() == 606
    assert (matches["won_by"] == "penalties_after_aggregate").sum() == 37
    assert (matches["won_by"] == "shootout_tiebreak").sum() == 1

    # --- cobertura ---
    # El 70% de los partidos no tiene goleadores: nunca unir por dentro para sacar
    # datos a nivel de partido, porque no se ve que falte nada.
    assert matches["has_goal_detail"].sum() == 14376
    assert match_results.height == 47381
    assert goal_events.height == goal_scorers.height

    # --- invariantes que NO hay que "arreglar" ---
    assert (
        goals_ir.filter(pl.col("goal_minute") == 122).height == 1
    )  # Friedenreich, 1919
    assert (
        goal_scorers.is_duplicated().sum() == 128
    )  # hat-tricks, no duplicados
    assert (
        matches.filter(pl.col("won_by") == "penalties_after_aggregate").height
        == 37
    )
    # El ganador de esos 37 es el del shootout, no el de la partida registrada: en 18
    # de ellos el ganador de la ida perdió el shootout.
    assert (
        matches.filter(
            (pl.col("won_by") == "penalties_after_aggregate")
            & (pl.col("winner") != pl.col("shootout_winner"))
        ).height
        == 0
    )
    assert (
        matches.filter(pl.col("shootout_winner").is_not_null())
        .filter(pl.col("winner") != pl.col("shootout_winner"))
        .height
        == 0
    )

    "All assertions OK"
    return


if __name__ == "__main__":
    app.run()
