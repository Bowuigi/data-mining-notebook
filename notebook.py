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
    import numpy as np
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans, Birch
    from sklearn.metrics import silhouette_score
    from sklearn.decomposition import PCA

    from corrections import CITY_ALIASES, COUNTRY_ALIASES, REGION, TEAM_ALIASES

    # Para poder graficar conjuntos grandes de datos
    alt.data_transformers.enable("vegafusion")


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Nota: Se utilizó IA **sólo** para agilizar la escritura de código y la verificación de datos. En particular, el proceso KDD se llevó a cabo bajo dirección humana y "a pasitos", revisando todo 2 veces por las dudas. Aplicación: OpenCode; Modelo: Space Bunny (uno de los "incógnito", eventualmente revelarán cuál es y quién lo hizo).

    # Fase 1: Objetivos de negocio

    - Objetivo descriptivo: Un medio de comunicación quiere hacer una nota periodística que investigue si diversas características destacadas (según opinión popular) y eventos de partidos de fútbol están relacionados con el nivel de estrés causado al hincha promedio por cada partido. Como primer acercamiento, se busca reducir el número de partidos a analizar maximizando la representatividad, para luego hacer encuestas sobre el estrés percibido.
    - Objetivo predictivo: Un club deportivo quiere completar datos históricos de partidos internacionales (no cubiertos en estos _datasets_ actuales) para enviárselos a la RSSSF y necesita un proceso de verificación de consistencia para comparar diversas fuentes. Cada una de estas fuentes contiene un registro detallado de penales acertados (durante y post-juego) y el resultado final del partido (de tablas de clasificación y puntajes particulares), pero el resto está incompleto.

    # Fases 2 (creación del _target dataset_) y 3 (preprocesamiento y limpieza de los datos)

    Es posible separar esto en 3 partes: La limpieza antes de crear el _target dataset_, la creación del mismo (`matches`) y la limpieza posterior, pero preferimos limpiarlo por pasos para que quede más sencillo de entender al leerse de forma secuencial.

    Se encontraron errores y faltantes en los datos:

    - En `match_results`:
      - Hay 20 claves primarias compuestas (fecha, equipo local, equipo visitante) repetidas. 17 eran un segundo registro de un partido de torneo como si hubiesen sido amistosos (Far Eastern Championship Games 1923-1934, African Friendship Games 1960); se conserva el del torneo en cada caso. Las otras 3 eran dos partidos distintos con la misma fecha: Singapur-Malasia 0-3 el 07/09/1973; Guyana-Barbados 2-0 el 21/10/1977 y el 0-0 del 22/10 repetía el del 26/10; Tahiti-Nueva Caledonia 2-1 y 1-2 compartían 17/02/1974, con el 1-2 movido a 18/02/1974 solo para desambiguar.
      - Uruguay-Bolivia el 27/06/2024 figura 4-0 y `goal_scorers` registra 5 goles (que es correcto). Se reconcilia automáticamente al unir las tablas.
      - `country` tiene nombres obsoletos.  Se agregan `normalized_country` (sucesor único) y `region` (región geográfica actual). Los paises con varios sucesores (URSS, Yugoslavia, Checoslovaquia, Serbia y Montenegro, Zanzibar) conservan el nombre histórico.
      - `city` tenía ciudades que estaban repetidas pero escritas distinto. Se usaron aliases para corregirlas.
      - Algunos equipos tenían nombres obsoletos. Se utilizaron aliases para su corrección.
    - En `goal_scorers`:
      - Varios pares de goleadores diferían sólo en caracteres no-ASCII. Se unifican mediante transliteración.
      - Hay 259 goles sin `minute`, entre el 16/10/1960 y el 31/03/1997. Se registra su inexistencia y se preserva, porque puede servir para informarle a los modelos que esos datos están incompletos.
      - Hay 49 goles sin `scorer`, entre el 24/02/1980 y el 23/09/1980. Quedan como están.
    - En `penalty_shootouts`:
      - Hay 37 rondas de penales con marcador no empatado. Es normal (aunque inesperado) por las reglas del fútbol de ese momento. Se queda como está.
      - `first_shooter` es nulo en más de la mitad de los partidos. Se utilizan los que están para ayudar a determinar si hubo tanda de penales.
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

    # `first_shooter` is null in more than half the matches that had a shootout,
    # so derive the shootout flag from the presence of a row instead.
    penalty_shootouts = penalty_shootouts.with_columns(
        pl.lit(True).alias("was_shootout")
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
def ir_doc():
    mo.md(r"""
    Con la limpieza por tabla en estado razonable, la siguiente tarea es empezar a unir todo. La idea es usar los datos de todas las tablas, aunque los objetivos refieran a partidos directamente. Al juntar todo, las fuentes se combinan para "tapar" faltantes en campos individuales. De igual manera, sigue habiendo muchos valores nulos. La mejor estrategia en este caso, no para preservar la varianza sino para entender los datos _en su contexto de negocio_ (las fuentes no son siempre confiables para ninguno de los dos objetivos), es no esconder la falta de datos, sino que hacerla otra cosa que los modelos puedan usar.

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
    - `goal_scorers_ir`: Separa goles de `goal_scorers` por equipo beneficiado, corrigiendo el uso de own_goal
    - `goals`: Une todos los datos relevantes de cada gol en cada momento
    - `matches`: Une los datos de todas las tablas en un registro coherente sobre cada partido, aportando información derivada de cada tabla. Esta tabla eventualmente se transforma en la que utilizan los modelos.
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
        pl.col("was_shootout").fill_null(False).alias("had_shootout"),
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
            has_incomplete_minute_data=pl.col("minute")
            .is_null()
            .any()
            .over(*K),
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
            pl.col("goal_was_opponent_own_goal")
            .fill_null(False)
            .cast(pl.Int8)
            .sum()
            .alias("known_opponent_own_goals"),
            pl.col("goal_was_penalty")
            .fill_null(False)
            .cast(pl.Int8)
            .sum()
            .alias("known_penalties"),
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

    u_matches = (
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
    u_matches
    return (u_matches,)


@app.cell
def _(u_matches):
    _home = alt.Chart(u_matches).mark_boxplot().encode(x="home_score")
    _away = alt.Chart(u_matches).mark_boxplot().encode(x="away_score")

    matches = u_matches.filter(
        (pl.col("home_score") < 7).and_(pl.col("away_score") < pl.lit(7))
    )
    _home | _away
    return (matches,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    Se observa un gran número de outliers, que pueden confundir a los modelos más adelante. Se eliminan estos outliers de _matches_ para no contaminar al resto. Además de outliers, hay un gráfico más que puede ayudar a visibilizar en qué se centra este _dataset_:
    """)
    return


@app.cell(hide_code=True)
def _(matches):
    _chart = (
        alt.Chart(matches)
        .mark_line()
        .encode(
            x=alt.X("date:T", title="Fecha"),
            y=alt.Y("count():Q", title="Número de registros"),
            tooltip=[
                alt.Tooltip("date:T", title="date", timeUnit="yearmonthdate"),
                alt.Tooltip(
                    "count():Q", title="Número de registros", format=",.0f"
                ),
            ],
        )
    )
    _chart
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Fase 4: Transformación y reducción de datos
    """)
    return


@app.cell
def _(matches):
    df = matches.with_columns(
        # Resultado del partido mismo con el local como centro.
        home_result=pl.when(
            pl.col("final_home_score") > pl.col("final_away_score")
        )
        .then(pl.lit("Victoria"))
        .when(pl.col("final_home_score") < pl.col("final_away_score"))
        .then(pl.lit("Derrota"))
        .otherwise(pl.lit("Empate")),
        # Varias de las derivaciones temporales pedidas.
        year=pl.col("date").dt.year(),
        month=pl.col("date").dt.month(),
        era=pl.when(pl.col("date") < pl.date(1945, 1, 1))
        .then(pl.lit("Pre-guerra"))
        .when(pl.col("date") < pl.date(1990, 1, 1))
        .then(pl.lit("Post-guerra"))
        .when(pl.col("date") < pl.date(2018, 1, 1))
        .then(pl.lit("Moderna"))
        .otherwise(pl.lit("VAR")),
        # Señales que sirven a modo de casi-resultado (útil si el modelo las usa).
        # `had_shootout` ya viene de `match_data` (derivado de la presencia de
        # fila en `penalty_shootouts`, no de `first_shooter`, que es nulo en
        # más de la mitad de los partidos con desempate).
        shootout_first_shooter_is_home=pl.when(pl.col("had_shootout"))
        .then((pl.col("first_shooter") == pl.col("home_team")).cast(pl.Int8))
        .otherwise(pl.lit(0, dtype=pl.Int8)),
        # Normalización numérica de funcionalidad ya existente (agrupaciones estructurales)
        # Cabe destacar que estos campos se hacen presentes al clasificador porque el segundo objetivo no es predicción pre-partido sino una estimación/predicción a modo de verificación de fuentes
        total_known_penalties=(
            pl.col("home_known_penalties") + pl.col("away_known_penalties")
        ),
        own_goal_balance=(
            pl.col("home_known_opponent_own_goals")
            - pl.col("away_known_opponent_own_goals")
        ),
    )

    # Columnas que sirven para clustering pero no pueden usarse para clasificación (porque sería prácticamente regalar el resultado)
    df = df.with_columns(
        total_goals=pl.col("home_score") + pl.col("away_score"),
        goal_diff=pl.col("home_score") - pl.col("away_score"),
    )
    df
    return (df,)


@app.cell
def _(df):
    df_id = df.with_row_index("match_id")

    _long = pl.concat(
        [
            df_id.select(
                "match_id",
                "date",
                pl.col("home_team").alias("team"),
                pl.when(pl.col("home_result") == "Victoria")
                .then(1)
                .otherwise(0)
                .alias("win"),
                pl.when(pl.col("home_result") == "Empate")
                .then(1)
                .otherwise(0)
                .alias("draw"),
                pl.col("home_score").alias("gf"),
                pl.col("away_score").alias("ga"),
            ),
            df_id.select(
                "match_id",
                "date",
                pl.col("away_team").alias("team"),
                pl.when(pl.col("home_result") == "Derrota")
                .then(1)
                .otherwise(0)
                .alias("win"),
                pl.when(pl.col("home_result") == "Empate")
                .then(1)
                .otherwise(0)
                .alias("draw"),
                pl.col("away_score").alias("gf"),
                pl.col("home_score").alias("ga"),
            ),
        ]
    )

    _long = (
        _long.sort("team", "date", "match_id")
        .with_columns(
            prior_matches=(pl.int_range(1, pl.len() + 1).over("team") - 1),
            prior_wins=(pl.col("win").cum_sum().over("team") - pl.col("win")),
            prior_draws=(
                pl.col("draw").cum_sum().over("team") - pl.col("draw")
            ),
            prior_gf=(pl.col("gf").cum_sum().over("team") - pl.col("gf")),
            prior_ga=(pl.col("ga").cum_sum().over("team") - pl.col("ga")),
        )
        .with_columns(
            prior_win_rate=pl.when(pl.col("prior_matches") > 0)
            .then(pl.col("prior_wins") / pl.col("prior_matches"))
            .otherwise(0.5),
            prior_avg_gf=pl.when(pl.col("prior_matches") > 0)
            .then(pl.col("prior_gf") / pl.col("prior_matches"))
            .otherwise(1.0),
            prior_avg_ga=pl.when(pl.col("prior_matches") > 0)
            .then(pl.col("prior_ga") / pl.col("prior_matches"))
            .otherwise(1.0),
        )
    )

    def _side_form(team_col: str, prefix: str):
        return (
            _long.join(df_id.select("match_id", team_col), on="match_id")
            .filter(pl.col("team") == pl.col(team_col))
            .select(
                "match_id",
                pl.col("prior_win_rate").alias(f"{prefix}_form_win_rate"),
                pl.col("prior_avg_gf").alias(f"{prefix}_form_avg_gf"),
                pl.col("prior_avg_ga").alias(f"{prefix}_form_avg_ga"),
                pl.col("prior_matches").alias(f"{prefix}_form_matches"),
            )
        )

    df_feat = (
        df_id.join(_side_form("home_team", "home"), on="match_id")
        .join(_side_form("away_team", "away"), on="match_id")
        .with_columns(
            form_win_diff=pl.col("home_form_win_rate")
            - pl.col("away_form_win_rate"),
            form_gf_diff=pl.col("home_form_avg_gf")
            - pl.col("away_form_avg_gf"),
            form_ga_diff=pl.col("home_form_avg_ga")
            - pl.col("away_form_avg_ga"),
        )
        .drop("match_id")
    )
    df_feat
    return (df_feat,)


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Fase 5: Selección de la tarea de minería de datos

    Formalización técnica:

    - Para el objetivo descriptivo: La tarea es de **clustering**, segmentación de partidos por características de juego, época, torneo, localía, goles y penales.
    - Para el objetivo predictivo: La tarea es de **clasificación supervisada**, predicción de resultado final (Victoria/Empate/Derrota) mediante la variable objetivo `home_result` usando árboles de decisión y Naive Bayes.

    # Fase 6: Selección del algoritmo y proceso analítico

    - Para el objetivo descriptivo (clustering):
      - k-Means: Algoritmo rápido, escalable, ideal para segmentación global. Requiere elegir $k$ y asume clusters esféricos.
      - BIRCH: Hecho específicamente para conjuntos grandes de datos. Requiere elegir $k$.
    - Para el objetivo predictivo (clasificación):
      - Árbol de Decisión: Interpretable, maneja variables numéricas y categóricas, captura no linealidades y permite extraer reglas. Se limita su tamaño para evitar overfitting.
      - Naive Bayes: Base probabilística, rápido y simple.
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Fase 7: Minería de datos
    """)
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Clustering
    """)
    return


@app.cell
def _(df):
    CLUST_NUM = [
        # "year",
        "month",
        "home_score",
        "away_score",
        # "total_goals",
        # "goal_diff",
        "total_known_penalties",
        "own_goal_balance",
        "neutral_field",
    ]
    CLUST_CAT = ["tournament", "region", "era", "had_shootout"]

    X_clust = (
        df.select(
            [pl.col(c).cast(pl.Float64) for c in CLUST_NUM]
            + [pl.col(c).cast(pl.String) for c in CLUST_CAT]
        )
        .to_dummies(columns=CLUST_CAT, drop_first=False)
        .fill_null(0)
        .to_numpy()
        .astype(float)
    )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_clust)
    return (X_scaled,)


@app.cell
def _(X_scaled):
    # K-Means: buscar k por silhouette (submuestreado para evitar O(n²))
    rng = np.random.default_rng(0)
    idx_sil = rng.choice(len(X_scaled), size=5000, replace=False)
    sil = {}
    for k in range(3, 9):
        _km = KMeans(n_clusters=k, random_state=0, n_init=10)
        labels = _km.fit_predict(X_scaled)
        sil[k] = silhouette_score(X_scaled[idx_sil], labels[idx_sil])
    return (sil,)


@app.cell
def _(X_scaled, sil):
    best_k = max(sil, key=sil.get)
    km = KMeans(n_clusters=best_k, random_state=0, n_init=10)
    labels_km = km.fit_predict(X_scaled)
    return best_k, labels_km


@app.cell
def _(X_scaled, best_k):
    birch = Birch(n_clusters=best_k, threshold=0.2, branching_factor=50)
    labels_birch = birch.fit_predict(X_scaled)
    return (labels_birch,)


@app.cell
def _(df, labels_birch, labels_km):
    df_clusters = df.with_columns(
        cluster_kmeans=pl.Series(labels_km),
        cluster_birch=pl.Series(labels_birch),
    )

    profile_kmeans = (
        df_clusters.group_by("cluster_kmeans")
        .agg(
            pl.len().alias("n"),
            pl.col("home_score").mean().alias("avg_home_score"),
            pl.col("away_score").mean().alias("avg_away_score"),
            pl.col("total_goals").mean().alias("avg_total_goals"),
            pl.col("goal_diff").mean().alias("avg_goal_diff"),
            pl.col("year").mean().alias("avg_year"),
            pl.col("total_known_penalties").mean().alias("avg_penalties"),
            pl.col("had_shootout").mean().alias("pct_shootout"),
        )
        .sort("cluster_kmeans")
    )

    profile_birch = (
        df_clusters.group_by("cluster_birch")
        .agg(
            pl.len().alias("n"),
            pl.col("home_score").mean().alias("avg_home_score"),
            pl.col("away_score").mean().alias("avg_away_score"),
            pl.col("total_goals").mean().alias("avg_total_goals"),
            pl.col("goal_diff").mean().alias("avg_goal_diff"),
            pl.col("year").mean().alias("avg_year"),
            pl.col("total_known_penalties").mean().alias("avg_penalties"),
            pl.col("had_shootout").mean().alias("pct_shootout"),
        )
        .sort("cluster_birch")
    )

    mo.vstack([profile_kmeans, profile_birch])
    return


@app.cell
def _(X_scaled, labels_birch, labels_km, sil):
    pca = PCA(n_components=2, random_state=0)
    coords = pca.fit_transform(X_scaled)
    viz = pl.DataFrame(
        {
            "pc1": coords[:, 0],
            "pc2": coords[:, 1],
            "kmeans": labels_km,
            "birch": labels_birch,
        }
    )

    sil_df = pl.DataFrame(
        {"k": list(sil.keys()), "silhouette": list(sil.values())}
    )
    return sil_df, viz


@app.cell
def _(sil_df):
    sil_df
    return


@app.cell
def _(viz):
    chart = (
        alt.Chart(viz)
        .mark_circle(size=30, opacity=0.5)
        .encode(
            x="pc1:Q",
            y="pc2:Q",
            color=alt.Color("kmeans:N", title="Cluster K-Means"),
            tooltip=["pc1:Q", "pc2:Q", "kmeans:N", "birch:N"],
        )
        .properties(width=400, height=300, title="Clusters K-Means (PCA)")
    ) | (
        alt.Chart(viz)
        .mark_circle(size=30, opacity=0.5)
        .encode(
            x="pc1:Q",
            y="pc2:Q",
            color=alt.Color("birch:N", title="Cluster BIRCH"),
            tooltip=["pc1:Q", "pc2:Q", "kmeans:N", "birch:N"],
        )
        .properties(width=400, height=300, title="Clusters BIRCH (PCA)")
    )
    chart
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Clasificación
    """)
    return


@app.cell
def _(df_feat):
    CLS_NUM = [
        "year",
        "month",
        "home_known_penalties",
        "away_known_penalties",
        "home_known_opponent_own_goals",
        "away_known_opponent_own_goals",
        "had_shootout",
        "shootout_first_shooter_is_home",
        "neutral_field",
        "total_known_penalties",
        "own_goal_balance",
        "home_form_win_rate",
        "away_form_win_rate",
        "form_win_diff",
        "home_form_avg_gf",
        "away_form_avg_gf",
        "form_gf_diff",
        "home_form_avg_ga",
        "away_form_avg_ga",
        "form_ga_diff",
        "home_form_matches",
        "away_form_matches",
    ]
    CLS_CAT = ["region", "era", "home_team", "away_team"]

    _X = (
        df_feat.select(
            [pl.col(c).cast(pl.Float64) for c in CLS_NUM]
            + [pl.col(c).cast(pl.String) for c in CLS_CAT]
        )
        .to_dummies(columns=CLS_CAT, drop_first=False)
        .fill_null(0)
    )

    cls_X = _X.to_numpy().astype(float)
    cls_feature_names = _X.columns
    cls_y = df_feat["home_result"].to_numpy()
    return cls_X, cls_y


@app.cell
def _(cls_X, cls_y, df_feat):
    LABELS = ["Victoria", "Empate", "Derrota"]
    years = df_feat["year"].to_numpy()
    cutoff = int(np.quantile(years, 0.5))

    def _():
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.naive_bayes import GaussianNB
        from sklearn.metrics import classification_report, confusion_matrix

        tr = years <= cutoff
        te = years > cutoff

        X_tr, X_te = cls_X[tr], cls_X[te]
        y_tr, y_te = cls_y[tr], cls_y[te]

        results, fitted = {}, {}

        for name, model in {
            "DecisionTree": DecisionTreeClassifier(
                max_depth=10,
                min_samples_leaf=50,
                class_weight="balanced",
                random_state=0,
            ),
            "GaussianNB": GaussianNB(),
        }.items():
            model.fit(X_tr, y_tr)
            pred = model.predict(X_te)
            results[name] = {
                "report": classification_report(
                    y_te,
                    pred,
                    labels=LABELS,
                    output_dict=True,
                    zero_division=0,
                ),
                "cm": confusion_matrix(y_te, pred, labels=LABELS),
            }
            fitted[name] = model

        summary = pl.DataFrame(
            [
                {
                    "model": n,
                    "accuracy": r["report"]["accuracy"],
                    "macro_f1": r["report"]["macro avg"]["f1-score"],
                    "victoria_f1": r["report"]["Victoria"]["f1-score"],
                    "empate_f1": r["report"]["Empate"]["f1-score"],
                    "derrota_f1": r["report"]["Derrota"]["f1-score"],
                }
                for n, r in results.items()
            ]
        )
        return results, summary

    results, summary = _()
    summary
    return LABELS, cutoff, results


@app.cell
def _(LABELS, cutoff, results):
    rows = []
    for name, r in results.items():
        cm = r["cm"]
        for i, real in enumerate(LABELS):
            for j, pred in enumerate(LABELS):
                rows.append(
                    {
                        "model": name,
                        "real": real,
                        "pred": pred,
                        "count": int(cm[i, j]),
                    }
                )
    cm_df = pl.DataFrame(rows)

    base = alt.Chart(cm_df).encode(
        x=alt.X("pred:N", title="Predicho", sort=LABELS),
        y=alt.Y("real:N", title="Real", sort=LABELS),
    )
    heat = base.mark_rect().encode(
        color=alt.Color("count:Q", scale=alt.Scale(scheme="blues"), title="n")
    )
    text = base.mark_text(baseline="middle", fontSize=13).encode(
        text="count:Q",
        color=alt.condition(
            alt.datum.count > cm_df["count"].max() / 2,
            alt.value("white"),
            alt.value("black"),
        ),
    )
    (heat + text).properties(
        width=220, height=220, title=f"Corte temporal: año > {cutoff}"
    ).facet(column=alt.Column("model:N", title=None)).resolve_scale(
        color="independent"
    )
    return


@app.cell
def _(results):
    def _():
        rows = []
        for name, r in results.items():
            rep = r["report"]
            for label in ["Victoria", "Empate", "Derrota"]:
                rows.append(
                    {
                        "model": name,
                        "class": label,
                        "precision": rep[label]["precision"],
                        "recall": rep[label]["recall"],
                        "f1": rep[label]["f1-score"],
                        "support": int(rep[label]["support"]),
                    }
                )
            rows.append(
                {
                    "model": name,
                    "class": "macro avg",
                    "precision": rep["macro avg"]["precision"],
                    "recall": rep["macro avg"]["recall"],
                    "f1": rep["macro avg"]["f1-score"],
                    "support": int(rep["macro avg"]["support"]),
                }
            )

        metrics_df = pl.DataFrame(rows).sort(["model", "class"])
        return metrics_df


    _()
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Conclusión

    Ambos modelos de clustering tuvieron problemas para encontrar grupos naturales en los datos.
    - El coeficiente de Silhouette es muy bajo, lo que significa que los grupos encontrados están muy pegados
    - Aumentar la cantidad de clusters no ayuda.
    - Quitar variables con distribuciones desbalanceadas (el año, por ejemplo) tiene impacto positivo en el modelo k-Means pero no el suficiente.
    - Birch está hecho para conjuntos de datos mucho más grandes que el que pensábamos, y por eso se apuró a encontrar grupos grandes, a pesar de que redujéramos el parámetro que controlaba (indirectamente) el tamaño de los grupos. Tener un sólo grupo para prácticamente todo no es muy útil que digamos.

    Los clasificadores superan apenas el azar (40/47% vs 33% teórico):
    - El árbol de decisión logra mejor precisión y detecta mejor las victorias (por ser más optimista), pero le erra bastante en los empates (también por ser más optimista).
    - El tipo de Naive Bayes usado (GaussianNB) decidió tomar el camino "seguro" y decir que la mayoría de partidos son empates, cosa que es rara porque los datos no reflejan eso tan directamente. La falta de datos adicionales relevantes en un partido de fútbol (ej. la condición física de los jugadores) podría ayudar a explicar el bajo desempeño (además de nuestra poca experiencia en el área). Se concluye que la clasificación no es viable con las _features_ actuales para una predicción confiable, aunque sirve como línea de base exploratoria por acercarse al 33% teórico sin necesariamente elegir al azar.

    Los patrones descubiertos son novedosos, pero no aportan suficiente información relevante como para "hacer la diferencia" para cualquiera de los dos objetivos. Los modelos no son inútiles tampoco, en muchos casos tienen la razón.

    **¿Significa esto que estamos despedidos de ambas empresas?** No, porque la limpieza de datos se pudo ejecutar de mejor forma que la última etapa, y ser _junior_ trae ventajas. ¿Se puede mejorar? Es probable, si, pero no lo hablamos con otras personas del curso para saber si lo hicieron mejor o algo así.
    """)
    return


if __name__ == "__main__":
    app.run()
