# /// script
# dependencies = [
#     "altair==6.3.0",
#     "duckdb==1.5.5",
#     "marimo",
#     "mcp==2.2.0",
#     "numpy==2.5.3",
#     "polars[pyarrow]==1.44.2",
#     "python-lsp-ruff==2.3.4",
#     "ruff==0.16.9",
#     "scikit-learn==1.9.1",
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

with app.setup(hide_code=True):
    ### Import libraries as required
    import marimo as mo
    import polars as pl
    import altair as alt
    import unidecode
    from corrections import CITY_ALIASES, COUNTRY_ALIASES, REGION, TEAM_ALIASES


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Nota: Se utilizó IA **sólo** para agilizar la escritura de código y la verificación de datos. En particular, el proceso KDD se llevó a cabo bajo dirección humana y "a pasitos", revisando todo 2 veces por las dudas. Aplicación: OpenCode; Modelo: Space Bunny (uno de los "incógnito", eventualmente revelarán cuál es y quién lo hizo).

    # Fase 1: Objetivos de negocio

    - Objetivo descriptivo: Un medio de comunicación quiere hacer una nota periodística que investigue si diversas características destacadas (según opinión popular) y eventos de partidos de fútbol están relacionados con el nivel de estrés causado al hincha promedio por cada partido. Como primer acercamiento, se busca reducir el número de partidos a analizar maximizando la representatividad, para luego hacer encuestas sobre el estrés percibido.
    - Objetivo predictivo: Un club deportivo quiere completar datos históricos de partidos internacionales (no cubiertos en estos _datasets_ actuales) para enviárselos a la RSSSF y necesita un proceso de verificación de consistencia para comparar diversas fuentes. Cada una de estas fuentes contiene un registro detallado de penales acertados (durante y post-juego) y el resultado final del partido (de tablas de clasificación y puntajes particulares), pero el resto está incompleto.

    # Prerequisitos para la fase 2 pero técnicamente de la fase 3

    Algunas cosas son exclusivamente de la fase 3, pero igual se documenta todo junto

    Se encontraron cosas raras en los datos:

    - En `match_results`:
      - Hay 20 claves primarias compuestas (fecha, equipo local, equipo visitante) repetidas. 17 eran un segundo registro de un partido de torneo como si hubiesen sido amistosos (Far Eastern Championship Games 1923-1934, African Friendship Games 1960); se conserva el del torneo. Las otras 3 eran dos partidos distintos con la misma fecha: Singapur-Malasia 0-3 el 07/09/1973; Guyana-Barbados 2-0 el 21/10/1977 y el 0-0 del 22/10 repetía el del 26/10; Tahiti-Nueva Caledonia 2-1 y 1-2 compartían 17/02/1974, con el 1-2 movido a 18/02/1974 solo para desambiguar.
      - Uruguay-Bolivia el 27/06/2024 figura 4-0 y `goal_scorers` registra 5 goles (que es correcto). Se reconcilia automáticamente al unir las tablas.
      - `country` tiene nombres obsoletos.  Se agregan `normalized_country` (sucesor único) y `region` (región geográfica actual). Los paises con varios sucesores (URSS, Yugoslavia, Checoslovaquia, Serbia y Montenegro, Zanzibar) conservan el nombre histórico.
      - `city` tenía ciudades que estaban repetidas pero escritas distinto. Se usaron aliases para corregirlas.
      - Algunos equipos tenían nombres obsoletos. Se utilizaron aliases para su corrección.
    - En `goal_scorers`:
      - Varios pares de goleadores diferían sólo en caracteres no-ASCII. Se unifican mediante transliteración.
      - Hay 259 goles sin `minute`, entre el 16/10/1960 y el 31/03/1997.
      - Hay 49 goles sin `scorer`, entre el 24/02/1980 y el 23/09/1980.
    - En `penalty_shootouts`:
      - Hay 37 rondas de penales con marcador no empatado. Es normal (aunque inesperado) por las reglas del fútbol de ese momento.
      - `first_shooter` es nulo en más de la mitad de los partidos.
      - Saare County / Saaremaa vs Åland Islands / Åland el 29/06/2011 es un desempate sin partido (ni fila en `match_results`). Aparte de este caso especial, la fuente está mal (ganó Åland, que figura de visitante). Se descarta la fila.
    """)
    return


@app.cell(hide_code=True)
def _():
    def _from_csv(filename):
        return pl.read_csv(
            filename, null_values=["NA"], schema_overrides={"date": pl.Date}
        )

    base_goal_scorers = _from_csv("data/Goal_Scorers.csv")
    base_match_results = _from_csv("data/Match_Results.csv")
    base_penalty_shootouts = _from_csv("data/Penalty_Shootouts.csv")

    # Clave primaria compuesta que identifica un partido
    K = ["date", "home_team", "away_team"]
    return K, base_goal_scorers, base_match_results, base_penalty_shootouts


@app.cell(hide_code=True)
def _(K, base_goal_scorers, base_match_results, base_penalty_shootouts):
    # Cleaning
    goal_scorers = base_goal_scorers
    match_results = base_match_results
    penalty_shootouts = base_penalty_shootouts

    goal_scorers = goal_scorers.with_columns(
        [
            pl.col(c).replace(TEAM_ALIASES)
            for c in ("home_team", "away_team", "team")
        ]
    )

    goal_scorers = goal_scorers.with_columns(
        # Transliterate
        pl.col("scorer")
        .map_elements(unidecode.unidecode, return_dtype=pl.String)
        .alias("scorer")
    )

    # Apply aliases
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

    # Delete `2011-06-29 Saaremaa v Åland`
    penalty_shootouts = penalty_shootouts.filter(
        ~(
            (pl.col("date") == pl.date(2011, 6, 29))
            & (pl.col("home_team") == "Saaremaa")
        )
    )

    # Duplicate friendly-tournament matches. Friendly duplicates removed
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
    return goal_scorers, match_results, penalty_shootouts


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
    - `goal_scorers_ir`: Una fila por gol de `goal_scorers`.
      <br>Suma las siguientes columnas:
      - `benefitting_team_score`: Número de gol del equipo que se benefició en ese partido, según el orden de los datos de base.
      - `has_incomplete_minute_data`: `True` si a algún gol de ese partido le falta `minute`.

        Se renombran las siguientes columnas de `goal_scorers`:
      - `team` → `benefitting_team`
      - `minute` → `goal_minute`
      - `own_goal` → `goal_was_opponent_own_goal`
      - `penalty` → `goal_was_penalty`
    - `match_data`: Cada fila son los datos de cada partido. Recorte de `match_results`, unido con `penalty_shootouts`.
      <br>Se modifican las siguientes columnas de `penalty_shootouts`:
      - `winner`: Si no hay desempate por penales, se calcula quién es el ganador mediante el puntaje y se pone ese equipo. En caso de empates, vale `NULL`.

        Se renombran las siguientes columnas de `match_results`:
      - `home_score` → `final_home_score`
      - `away_score` → `final_away_score`
      - `neutral` → `neutral_field`

    - `match_expected_goals`: Cada fila es un resultado del partido conforme va pasando, extraído de `match_results`.
      <br>Suma las siguientes columnas a `match_results`:
      - `benefitting_team`: El equipo que se benefició del gol en ese momento (no hay que invertirlo para `own_goal`). Si es `NULL`, es el inicio del partido (fila incluída para no borrar partidos 0-0 y para poder obtener con facilidad sólo los partidos si hacen falta). Si no, es un gol.
      - `benefitting_team_score`: Marcador de ese equipo hasta e incluyendo ese gol. Si es 0 (y por tanto `benefitting_team` es `NULL`), es el inicio del partido. Si no, es un gol.
    """)
    return


@app.cell(hide_code=True)
def _(K, match_results, penalty_shootouts):
    # One row per match: who played, where, when and the final score.
    match_data = match_results.join(
        penalty_shootouts, on=K, how="full", coalesce=True
    ).select(
        *K,
        pl.col("home_score").alias("final_home_score"),
        pl.col("away_score").alias("final_away_score"),
        "tournament",
        "city",
        "country",
        "normalized_country",
        "region",
        pl.coalesce(
            pl.col("winner"),
            pl.when(pl.col("home_score") > pl.col("away_score"))
            .then(pl.col("home_team"))
            .when(pl.col("home_score") < pl.col("away_score"))
            .then(pl.col("away_team")),
        ),
        "first_shooter",
        pl.col("neutral").alias("neutral_field"),
    )
    match_data
    return (match_data,)


@app.cell(hide_code=True)
def _(match_data):
    _match_data = match_data.lazy()
    MATCH_INFO = [
        "date",
        "home_team",
        "away_team",
        "final_home_score",
        "final_away_score",
        "tournament",
        "city",
        "country",
        "normalized_country",
        "region",
        "neutral_field",
    ]

    def _scored_goals(side: str):
        return (
            _match_data.with_columns(
                benefitting_team_score=pl.int_ranges(
                    1, pl.col(f"final_{side}_score") + 1
                ),
            )
            .explode("benefitting_team_score", empty_as_null=False)
            .filter(pl.col("benefitting_team_score").is_not_null())
            .select(
                pl.col(f"{side}_team").alias("benefitting_team"),
                "benefitting_team_score",
                *MATCH_INFO,
            )
        )

    # One zero-th row per match, so 0-N and N-0 matches are kept without duplicates
    _goalless_rows = _match_data.select(
        pl.lit(None, dtype=pl.String).alias("benefitting_team"),
        pl.lit(0, dtype=pl.Int64).alias("benefitting_team_score"),
        *MATCH_INFO,
    )

    # One row per goal, in goal order. Expected goals = how many goals that team
    # had scored up to and including this one; 0 on the match-start row.
    match_expected_goals = (
        pl.concat(
            [_scored_goals("home"), _scored_goals("away"), _goalless_rows],
            how="diagonal_relaxed",
        )
        .sort("date", "benefitting_team", "benefitting_team_score")
        .select(
            "date",
            "home_team",
            "away_team",
            "benefitting_team",
            "benefitting_team_score",
        )
        .collect()
    )

    match_expected_goals
    return (match_expected_goals,)


@app.cell(hide_code=True)
def goal_scorers_ir(K, goal_scorers):
    goal_scorers_ir = (
        goal_scorers.lazy()
        .sort("date", "minute", nulls_last=True)
        .with_columns(
            benefitting_team_score=pl.int_range(1, pl.len() + 1).over(
                *K, "team"
            ),
            has_incomplete_minute_data=pl.col("minute").is_null().any().over(*K),
        )
        .rename(
            {
                "team": "benefitting_team",
                "minute": "goal_minute",
                "own_goal": "goal_was_opponent_own_goal",
                "penalty": "goal_was_penalty",
            }
        )
        .select(
            *K,
            "benefitting_team",
            "benefitting_team_score",
            "scorer",
            "goal_minute",
            "goal_was_opponent_own_goal",
            "goal_was_penalty",
            "has_incomplete_minute_data",
        )
        .collect()
    )

    goal_scorers_ir
    return (goal_scorers_ir,)


@app.cell(hide_code=True)
def _(K, goal_scorers_ir, match_expected_goals):
    goals = (
        goal_scorers_ir.join(
            match_expected_goals,
            on=[*K, "benefitting_team", "benefitting_team_score"],
            how="full",
            coalesce=True,
        )
        .filter(~pl.col("benefitting_team_score").eq(0))
        .with_columns(
            has_incomplete_minute_data=pl.coalesce(
                pl.col("has_incomplete_minute_data"), pl.lit(True)
            ),
        )
    )

    goals
    return (goals,)


@app.cell
def _(K, goals, match_data):
    goals_agg = (
        goals.group_by(*K, "benefitting_team")
        .agg(
            pl.col("benefitting_team_score").count().alias("goal_count"),
            # Currently defaulting for own_goals and penalties. Attempt other methods to mitigate NULL values
            pl.col("goal_was_opponent_own_goal").fill_null(False).cast(pl.Int8).sum().alias("known_opponent_own_goals"),
            pl.col("goal_was_penalty").fill_null(False).cast(pl.Int8).sum().alias("known_penalties"),
            pl.col("scorer").mode().first().alias("highest_goal_scorer"),
        )
        .join(
            match_data.select(*K, "final_home_score", "final_away_score"), on=K
        )
        .with_columns(
            match_benefitting_team_score=pl.when(
                benefitting_team=pl.col("home_team")
            )
            .then(pl.col("final_home_score"))
            .when(benefitting_team=pl.col("away_team"))
            .then(pl.col("final_away_score"))
        )
        .select(
            *K,
            "benefitting_team",
            pl.max_horizontal(
                pl.col("goal_count"), pl.col("match_benefitting_team_score")
            ).alias("goals"),
            "highest_goal_scorer",
            "known_opponent_own_goals",
            "known_penalties",
        )
        .sort("date", "home_team", "away_team", "benefitting_team")
    )

    goals_agg
    return (goals_agg,)


@app.cell
def _(K, goals_agg, match_data):
    def _agg_for(side: str):
        return (
            goals_agg.filter(benefitting_team=pl.col(f"{side}_team"))
            .rename(
                {
                    "goals": f"{side}_score",
                    "highest_goal_scorer": f"{side}_highest_goal_scorer",
                    "known_opponent_own_goals": f"{side}_known_opponent_own_goals",
                    "known_penalties": f"{side}_known_penalties",
                }
            )
            .drop("benefitting_team")
        )

    matches = (
        _agg_for("home")
        .join(_agg_for("away"), on=K, how="full", coalesce=True)
        .join(
            match_data,
            on=K,
            how="full",
            coalesce=True,
        )
        .with_columns(
            home_score=pl.coalesce(pl.col("home_score"), pl.lit(0)),
            away_score=pl.coalesce(pl.col("away_score"), pl.lit(0)),
            # Defaulting to deal with nulls here
            home_known_opponent_own_goals=pl.coalesce(
                pl.col("home_known_opponent_own_goals"), pl.lit(0)
            ),
            away_known_opponent_own_goals=pl.coalesce(
                pl.col("away_known_opponent_own_goals"), pl.lit(0)
            ),
            home_known_penalties=pl.coalesce(
                pl.col("home_known_penalties"), pl.lit(0)
            ),
            away_known_penalties=pl.coalesce(
                pl.col("away_known_penalties"), pl.lit(0)
            ),
        )
    )
    matches
    return (matches,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Fase 5: Selección de la tarea de minería de datos

    Formalización técnica:

    - Para el objetivo descriptivo: La tarea es de **clustering**, segmentación de partidos por características de juego, época, torneo, localía, goles y penales.
    - Para el objetivo predictivo: La tarea es de **clasificación supervisada**, predicción de resultado final (Victoria/Empate/Derrota) usando árboles de decisión y Naive Bayes.

    # Fase 6: Selección del algoritmo y proceso analítico

    - Para el objetivo descriptivo (clustering):
      - K-Means: Algoritmo rápido, escalable, ideal para segmentación global. Requiere elegir $k$ y asume clusters esféricos.
      - Agglomerative: Jerárquico, no requiere fijar $k$ de antemano, captura estructuras anidadas. Con Ward funciona bien con clusters compactos.
    - Para el objetivo predictivo (clasificación):
      - Árbol de Decisión: Interpretable, maneja variables numéricas y categóricas, captura no linealidades y permite extraer reglas. Se limita su tamaño para evitar overfitting.
      - Naive Bayes: Base probabilística, rápido y simple.
    """)
    return


@app.cell
def _(matches):
    # ---------- Fase 4: Feature engineering ----------
    df = matches.with_columns(
        # Label (A): 90/120-minute result from home team's view.
        home_result=pl.when(pl.col("final_home_score") > pl.col("final_away_score"))
        .then(pl.lit("Victoria"))
        .when(pl.col("final_home_score") < pl.col("final_away_score"))
        .then(pl.lit("Derrota"))
        .otherwise(pl.lit("Empate")),
        # Temporal derivation (Fase 4).
        year=pl.col("date").dt.year(),
        month=pl.col("date").dt.month(),
        # "Eras" — the assignment explicitly asks for this.
        era=pl.when(pl.col("date") < pl.date(1945, 1, 1))
        .then(pl.lit("Pre-guerra"))
        .when(pl.col("date") < pl.date(1990, 1, 1))
        .then(pl.lit("Post-guerra"))
        .when(pl.col("date") < pl.date(2018, 1, 1))
        .then(pl.lit("Moderna"))
        .otherwise(pl.lit("VAR")),
        # Pre-result signals derived from first_shooter.
        had_shootout=pl.col("first_shooter").is_not_null().cast(pl.Boolean),
        shootout_first_shooter_is_home=(
            pl.col("first_shooter") == pl.col("home_team")
        ).cast(pl.Int8),
        # Numeric normalizations of existing features.
        total_known_penalties=(
            pl.col("home_known_penalties") + pl.col("away_known_penalties")
        ),
        penalty_balance=(
            pl.col("home_known_penalties") - pl.col("away_known_penalties")
        ),
        own_goal_balance=(
            pl.col("home_known_opponent_own_goals")
            - pl.col("away_known_opponent_own_goals")
        ),
    )

    # Leaky-only features (clustering only, not for the classifier).
    df = df.with_columns(
        total_goals=pl.col("home_score") + pl.col("away_score"),
        goal_diff=pl.col("home_score") - pl.col("away_score"),
    )
    df
    return (df,)

if __name__ == "__main__":
    app.run()
