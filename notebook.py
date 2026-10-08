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

    ### Load data

    def _from_csv(filename: str):
        return pl.read_csv(
            filename, null_values=["NA"], schema_overrides={"date": pl.Date}
        )

    goal_scorers = _from_csv("data/Goal_Scorers.csv")
    match_results = _from_csv("data/Match_Results.csv")
    penalty_shootouts = _from_csv("data/Penalty_Shootouts.csv")

    ### Correcciones sobre el source data

    # Clave natural de un partido. Tras las correcciones de esta celda es única, y
    # `match_id` pasa a ser la única clave de unión del notebook.
    K = ["date", "home_team", "away_team"]

    # Se normaliza hacia la grafía oficial, que es la que usan las fuentes externas
    # (Elo, FIFA) y por lo tanto la que deja los joins enganchados.
    TEAM_ALIASES = {"Åland Islands": "Åland", "Saare County": "Saaremaa"}
    CITY_ALIASES = {"Tananarive": "Antananarivo"}

    # Países con un sucesor único y sin ambigüedad.
    COUNTRY_ALIASES = {
        "Netherlands Antilles": "Curaçao",
        "Zaïre": "DR Congo",
        "German DR": "Germany",
        "Republic of Ireland": "Ireland",
        "Burma": "Myanmar",
        "Rhodesia": "Zimbabwe",
        "Ceylon": "Sri Lanka",
        "Tanganyika": "Tanzania",
        "Upper Volta": "Burkina Faso",
        "Dahomey": "Benin",
        "Gold Coast": "Ghana",
    }
    # Los países con varios sucesores (`Soviet Union`, `Yugoslavia`, `Czechoslovakia`,
    # `Serbia and Montenegro`, `Zanzibar`) no entran arriba a propósito:
    # `normalized_country` conserva su nombre histórico y lo que se corrige es
    # `region`, siempre bajo un nombre actual.
    COUNTRY_REGIONS = {
        "Africa": (
            "Algeria",
            "Angola",
            "Benin",
            "Belgian Congo",
            "Botswana",
            "Burkina Faso",
            "Burundi",
            "Cameroon",
            "Cape Verde",
            "Central African Republic",
            "Chad",
            "Comoros",
            "Congo",
            "DR Congo",
            "Djibouti",
            "Egypt",
            "Equatorial Guinea",
            "Eritrea",
            "Eswatini",
            "Ethiopia",
            "French Somaliland",
            "Gabon",
            "Gambia",
            "Ghana",
            "Guinea",
            "Guinea-Bissau",
            "Ivory Coast",
            "Kenya",
            "Lesotho",
            "Liberia",
            "Libya",
            "Madagascar",
            "Malawi",
            "Mali",
            "Mali Federation",
            "Mauritania",
            "Mauritius",
            "Mayotte",
            "Morocco",
            "Mozambique",
            "Namibia",
            "Niger",
            "Nigeria",
            "Northern Rhodesia",
            "Nyasaland",
            "Portuguese Guinea",
            "Réunion",
            "Rwanda",
            "Senegal",
            "Seychelles",
            "Sierra Leone",
            "Somalia",
            "South Africa",
            "South Sudan",
            "Southern Rhodesia",
            "Sudan",
            "Swaziland",
            "São Tomé and Príncipe",
            "Tanzania",
            "Togo",
            "Tunisia",
            "Uganda",
            "United Arab Republic",
            "Zambia",
            "Zanzibar",
            "Zimbabwe",
        ),
        "Asia": (
            "Afghanistan",
            "Armenia",
            "Azerbaijan",
            "Bahrain",
            "Bangladesh",
            "Bhutan",
            "Brunei",
            "Cambodia",
            "China PR",
            "Cyprus",
            "East Timor",
            "Georgia",
            "Hong Kong",
            "India",
            "Indonesia",
            "Iran",
            "Iraq",
            "Israel",
            "Japan",
            "Jordan",
            "Kazakhstan",
            "Kuwait",
            "Kyrgyzstan",
            "Laos",
            "Lebanon",
            "Macau",
            "Malaya",
            "Malaysia",
            "Maldives",
            "Manchuria",
            "Mongolia",
            "Myanmar",
            "Nepal",
            "North Korea",
            "Northern Cyprus",
            "Oman",
            "Pakistan",
            "Palestine",
            "Philippines",
            "Qatar",
            "Saudi Arabia",
            "Singapore",
            "South Korea",
            "Sri Lanka",
            "Syria",
            "Taiwan",
            "Tajikistan",
            "Thailand",
            "Turkey",
            "Turkmenistan",
            "United Arab Emirates",
            "Uzbekistan",
            "Vietnam",
            "Vietnam DR",
            "Vietnam Republic",
            "Yemen",
            "Yemen AR",
            "Yemen DPR",
        ),
        "Caribbean": (
            "Anguilla",
            "Antigua and Barbuda",
            "Aruba",
            "Bahamas",
            "Barbados",
            "Bermuda",
            "Bonaire",
            "British Virgin Islands",
            "Cayman Islands",
            "Cuba",
            "Curaçao",
            "Dominica",
            "Dominican Republic",
            "Grenada",
            "Guadeloupe",
            "Haiti",
            "Jamaica",
            "Martinique",
            "Montserrat",
            "Puerto Rico",
            "Saint Barthélemy",
            "Saint Kitts and Nevis",
            "Saint Lucia",
            "Saint Martin",
            "Saint Vincent and the Grenadines",
            "Sint Maarten",
            "Trinidad and Tobago",
            "Turks and Caicos Islands",
            "United States Virgin Islands",
        ),
        "Europe": (
            "Alderney",
            "Albania",
            "Andorra",
            "Austria",
            "Belarus",
            "Belgium",
            "Bohemia",
            "Bohemia and Moravia",
            "Bosnia and Herzegovina",
            "Bulgaria",
            "Croatia",
            "Czech Republic",
            "Czechoslovakia",
            "Denmark",
            "England",
            "Estonia",
            "Faroe Islands",
            "Finland",
            "France",
            "German DR",
            "Germany",
            "Gibraltar",
            "Greece",
            "Guernsey",
            "Hungary",
            "Iceland",
            "Ireland",
            "Irish Free State",
            "Isle of Man",
            "Italy",
            "Jersey",
            "Kosovo",
            "Latvia",
            "Liechtenstein",
            "Lithuania",
            "Luxembourg",
            "Malta",
            "Moldova",
            "Monaco",
            "Montenegro",
            "Netherlands",
            "North Macedonia",
            "Northern Ireland",
            "Norway",
            "Poland",
            "Portugal",
            "Romania",
            "Russia",
            "Saarland",
            "San Marino",
            "Scotland",
            "Serbia",
            "Serbia and Montenegro",
            "Slovakia",
            "Slovenia",
            "Soviet Union",
            "Spain",
            "Sweden",
            "Switzerland",
            "Ukraine",
            "Wales",
            "Yugoslavia",
            "Éire",
        ),
        "North America": (
            "Belize",
            "Canada",
            "Costa Rica",
            "El Salvador",
            "Greenland",
            "Guatemala",
            "Honduras",
            "Mexico",
            "Nicaragua",
            "Panama",
            "United States",
        ),
        "Oceania": (
            "Australia",
            "Cook Islands",
            "Fiji",
            "French Polynesia",
            "Guam",
            "Micronesia",
            "New Caledonia",
            "New Hebrides",
            "New Zealand",
            "Northern Mariana Islands",
            "Palau",
            "Papua New Guinea",
            "Samoa",
            "Solomon Islands",
            "Tahiti",
            "Tonga",
            "Vanuatu",
            "Western Samoa",
        ),
        "South America": (
            "Argentina",
            "Bolivia",
            "Brazil",
            "British Guyana",
            "Chile",
            "Colombia",
            "Ecuador",
            "French Guiana",
            "Guyana",
            "Netherlands Guyana",
            "Paraguay",
            "Peru",
            "Suriname",
            "Uruguay",
            "Venezuela",
        ),
    }
    REGION = {
        c: r for r, countries in COUNTRY_REGIONS.items() for c in countries
    }

    goal_scorers = goal_scorers.with_columns(
        [
            pl.col(c).replace(TEAM_ALIASES)
            for c in ("home_team", "away_team", "team")
        ]
    )

    # Nombres de jugador: se les sacan los diacríticos sin tocar las mayúsculas
    # (`Sívori` -> `Sivori`). Es la única unificación que hace falta, y por eso NO
    # hay mapa de alias: sobre 14.335 goleadores distintos, `normalize("NFKD")`
    # resuelve por sí solo las 7 únicas colisiones, y todas son genuinamente la misma
    # persona. Cualquier unificación más agresiva sería falsa: `Sándor Müller` y
    # `Gerd Müller` son dos jugadores distintos, igual que el `Ronaldo` a secas
    # (39 goles) y `Cristiano Ronaldo` (108).
    goal_scorers = goal_scorers.with_columns(
        pl.col("scorer")
        .str.normalize("NFKD")
        .str.replace_all(r"[^\x20-\x7E]", "")
        .alias("scorer")
    )

    match_results = match_results.with_columns(
        [pl.col(c).replace(TEAM_ALIASES) for c in ("home_team", "away_team")]
    )
    penalty_shootouts = penalty_shootouts.with_columns(
        [
            pl.col(c).replace(TEAM_ALIASES)
            for c in ("home_team", "away_team", "winner")
        ]
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

    match_results = match_results.with_columns(
        pl.col("city").replace(CITY_ALIASES)
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

    match_results = match_results.with_columns(
        pl.col("country").replace(COUNTRY_ALIASES).alias("normalized_country")
    ).with_columns(
        pl.col("normalized_country").replace(REGION).alias("region")
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
    - `matches_keyed`: Una fila por partido.
      <br>Suma las siguientes columnas a `match_results`:
      - `match_id`: Clave entera y única del partido. Es la clave de unión de todo el notebook; `(date, home_team, away_team)` queda sólo como payload.
      - `normalized_country`: País actual cuando hay un sucesor único y no ambiguo; si no, el nombre histórico tal cual.
      - `region`: Geografía actual, siempre bajo un nombre actual (`USSR` → `Europe`, `Zanzibar` → `Africa`).
    - `goal_events`: Una fila por gol de `goal_scorers`.
      <br>Suma las siguientes columnas:
      - `match_id`: Partido del gol.
      - `goal_no`: Enésimo gol de ese equipo en ese partido, según el orden del source data.
      - `has_incomplete_minute_data`: `True` si a algún gol de ese partido le falta `minute`.

        Se renombran las siguientes columnas de `goal_scorers`:
      - `team` → `scorer_team`
      - `minute` → `goal_minute`
      - `own_goal` → `goal_was_own_goal`
      - `penalty` → `goal_was_penalty`
    - `shootout_events`: Una fila por partido de `penalty_shootouts`, unida a su `match_id`.
      <br>Suma las siguientes columnas:
      - `match_id`: Partido del shootout. `NULL` en el único desempate sin partido de 90 minutos.

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
      - `shootout_winner`, `penalty_first_shooter`, `won_by`: Del partido, por `match_id`.

        Se renombran las siguientes columnas de `matches`:
      - `home_score` → `final_home_score`
      - `away_score` → `final_away_score`
      - `neutral` → `neutral_field`
    """)
    return


@app.cell
def matches_keyed():
    # Una fila por partido, con una clave entera y única. A partir de acá todas las
    # uniones son por `match_id`, y como la clave es única ninguna unión puede
    # multiplicar filas.
    matches_keyed = match_results.sort(*K).with_row_index("match_id")

    assert matches_keyed.select(K).is_duplicated().sum() == 0
    assert matches_keyed["match_id"].n_unique() == matches_keyed.height

    matches_keyed
    return (matches_keyed,)


@app.cell
def goal_events(matches_keyed):
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
        .join(matches_keyed.lazy().select("match_id", *K), on=K, how="left")
        .select(
            "match_id",
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

    assert goal_events.filter(pl.col("match_id").is_null()).height == 0
    assert (
        goal_events.select("match_id", "scorer_team", "goal_no")
        .is_duplicated()
        .sum()
        == 0
    )

    goal_events
    return (goal_events,)


@app.cell
def shootout_events(matches_keyed):
    # Una fila por shootout, unida a su partido. 643 de 644 caen en un `match_id`; la
    # restante es `2011-06-29 Åland v Saaremaa`, un desempate sin partido de 90
    # minutos, y queda con `match_id = NULL` a propósito.
    shootout_events = (
        penalty_shootouts.lazy()
        .join(matches_keyed.lazy().select("match_id", *K), on=K, how="left")
        .rename(
            {
                "winner": "shootout_winner",
                "first_shooter": "penalty_first_shooter",
            }
        )
        .select("match_id", *K, "shootout_winner", "penalty_first_shooter")
        .collect()
    )

    assert shootout_events.height == penalty_shootouts.height
    assert shootout_events.filter(pl.col("match_id").is_null()).height == 1

    shootout_events
    return (shootout_events,)


@app.cell
def matches(goal_events, matches_keyed, shootout_events):
    # Una fila por partido. El marcador se reconcilia acá, una sola vez: si el partido
    # tiene goles registrados, el marcador pasa a ser lo que dicen las filas de gol.
    # Los goles sólo suman información, así que un partido con pocos goleadores nunca
    # puede empeorar su marcador.
    #
    # `2024-06-27 Uruguay-Bolivia` es el único partido donde el source data discrepa
    # (4-0 registrado, 5 goles) y queda reparado acá, sin fix a mano.
    _goals_counted = (
        goal_events.lazy()
        .join(
            matches_keyed.lazy().select("match_id", "home_team", "away_team"),
            on="match_id",
        )
        .group_by("match_id", "home_team", "away_team")
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
        "match_id",
        "date",
        "home_team",
        "away_team",
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
        matches_keyed.select(*_MATCH_COLUMNS)
        .join(_goals_counted, on="match_id", how="left")
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
            shootout_events.select(
                "match_id", "shootout_winner", "penalty_first_shooter"
            ),
            on="match_id",
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
    # torneo, ni filas de goles.
    _tiebreaks = shootout_events.filter(pl.col("match_id").is_null()).select(
        pl.lit(None, dtype=pl.UInt32).alias("match_id"),
        "date",
        "home_team",
        "away_team",
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
                "match_id",
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
            "match_id",
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
                "match_id",
                "date",
                "home_team",
                "away_team",
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
            on="match_id",
            how="left",
        )
        .sort("match_id", "scorer_team", "goal_no", nulls_last=True)
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
    - `city`: `Tananarive` → `Antananarivo` (10 filas).
    - Equipos: `Åland Islands` → `Åland`, `Saare County` → `Saaremaa`. `2011-06-29` estaba invertido (`Åland v Saaremaa`).
    - `goal_scorers`: 128 filas totalmente duplicadas. **No son un error**: hat-tricks de Lewandowski y Buksa, `Peter Sharne` 4 veces. No deduplicar.
    - `goal_scorers`: 7 pares de goleadores diferían sólo en diacríticos (`Sívori`/`Sivori`, `Kéïta`/`Keita`, `Barthélemy`/`Barthelemy`, `Nguyễn Hồng Sơn`/`Nguyen Hong Son`, `Désir`/`Desir`, `Éder`/`Eder`, `Rivas`). Se pliegan con NFKD. **No hay mapa de alias**: sobre 14.335 goleadores ésos son los únicos 7 casos, y unificar más sería falso (`Gerd Müller` y `Sándor Müller` son dos jugadores distintos).
    - `goal_scorers`: 259 goles sin `minute`, entre `1960-10-16` y `1997-03-31` (no 1963-1980).
    - `goal_scorers`: 49 goles sin `scorer`, entre `1980-02-24` y `1980-09-23`.
    - `goal_scorers`: `minute = 122` (Friedenreich, `1919-05-29` Brasil-Uruguay). **No es un error**.
    - `goal_scorers`: 163 goles de tiempo extra con su minuto real. No están doblados a 45/90.
    - `penalty_shootouts`: 37 con marcador no empatado. Son segundos partidos de ida y vuelta decididos por el global (33/37 con el partido de vuelta a ≤120 días y global empatado). **No borrarlos**, no recalcular `winner`.
    - `penalty_shootouts`: `first_shooter` NULL en 414 de 644 (64%).
    - `penalty_shootouts`: `2011-06-29 Åland v Saaremaa` es un desempate sin partido de 90 minutos. No tiene `match_id` ni filas en `goals_ir`, y tampoco se le inventa un marcador.
    """)
    return


@app.cell
def invariants(goal_events, goals_ir, matches, matches_keyed, shootout_events):
    # Chequeos permanentes. Cada uno corresponde a un hallazgo que alguien tuvo que
    # descubrir a mano; dejarlos escritos es la forma más barata de que la próxima
    # pasada no vuelva a tropezar con lo mismo.

    # --- clave y grano ---
    assert matches_keyed["match_id"].n_unique() == matches_keyed.height
    assert matches_keyed.select(K).is_duplicated().sum() == 0
    assert goal_events.filter(pl.col("match_id").is_null()).height == 0
    assert (
        goal_events.select("match_id", "scorer_team", "goal_no")
        .is_duplicated()
        .sum()
        == 0
    )
    assert (
        goals_ir.filter(pl.col("goal_no").is_not_null())
        .select("match_id", "scorer_team", "goal_no")
        .is_duplicated()
        .sum()
        == 0
    )

    # --- shootouts ---
    # 643 de 644 caen en un partido. El que queda es el desempate sin partido de
    # 90 minutos, que existe a propósito y no tiene `goals_ir`.
    assert shootout_events.height == 644
    assert (
        shootout_events.filter(pl.col("match_id").is_not_null()).height == 643
    )
    assert (
        shootout_events.group_by("match_id")
        .agg(pl.len().alias("n"))
        .filter(pl.col("n") > 1)
        .height
        == 0
    )
    assert (
        shootout_events["match_id"].drop_nulls().n_unique() == 643
    )  # n_unique() cuenta el NULL
    assert (
        goals_ir.filter(pl.col("shootout_winner").is_not_null())[
            "match_id"
        ].n_unique()
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
        .group_by("match_id", "home_team", "away_team")
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
    assert matches_keyed["normalized_country"].null_count() == 0
    assert matches_keyed["region"].null_count() == 0
    assert (
        matches_keyed.filter(pl.col("normalized_country") == "Soviet Union")[
            "region"
        ]
        .eq("Europe")
        .all()
    )
    assert (
        matches_keyed.filter(pl.col("normalized_country") == "Zanzibar")[
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
    assert matches_keyed.height == 47381
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
