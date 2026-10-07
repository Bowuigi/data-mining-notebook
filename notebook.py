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

with app.setup(hide_code=True):
    import marimo as mo
    import polars as pl
    import altair as alt

    def _from_csv(filename: str):
        return pl.read_csv(filename, null_values=["NA"], schema_overrides={'date': pl.Date})

    goal_scorers = _from_csv("data/Goal_Scorers.csv")
    match_results = _from_csv("data/Match_Results.csv")
    penalty_shootouts = _from_csv("data/Penalty_Shootouts.csv")


@app.cell(hide_code=True)
def _():
    mo.md(r"""
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
    - `matches_ir`: Cada fila es un resultado del partido conforme va pasando.
      <br>Suma las siguientes columnas a `match_results`:
      - `goal_scorer_team`: El que metió gol en ese momento. Si es `NULL`, es el inicio del partido (fila incluída para no borrar partidos 0-0 y para poder obtener con facilidad sólo los partidos si hacen falta). Si no, es un gol.
      - `current_team_score`: Marcador de ese equipo hasta e incluyendo ese gol. Si es 0 (y por tanto `goal_scorer_team` es `NULL`), es el inicio del partido. Si no, es un gol.

        Se renombran las siguientes columnas de `match_results`:
      - `home_score` → `final_home_score`
      - `away_score` → `final_away_score`
    """)
    return


@app.cell
def matches_ir():
    def _scored_goals(side: str):
        # One row per goal actually scored by `side`
        return (
            match_results.lazy()
            .with_columns(
                goal_number=pl.int_ranges(1, pl.col(f"{side}_score") + 1)
            )
            .explode("goal_number", empty_as_null=False)
            .filter(pl.col("goal_number").is_not_null())
            .select(
                "date",
                "home_team",
                "away_team",
                pl.col(f"{side}_team").alias("goal_scorer_team"),
                pl.col("goal_number").alias("current_team_score"),
                pl.col("home_score").alias("final_home_score"),
                pl.col("away_score").alias("final_away_score"),
                "tournament",
                "city",
                "country",
                "neutral",
            )
        )


    def _goalless_rows():
        # One zero-th row per match, so 0-N and N-0 matches are kept without duplicates
        return match_results.lazy().select(
            "date",
            "home_team",
            "away_team",
            pl.lit(None, dtype=pl.String).alias("goal_scorer_team"),
            pl.lit(0, dtype=pl.Int64).alias("current_team_score"),
            pl.col("home_score").alias("final_home_score"),
            pl.col("away_score").alias("final_away_score"),
            "tournament",
            "city",
            "country",
            "neutral",
        )


    matches_ir = (
        pl.concat(
            [
                _scored_goals("home"),
                _scored_goals("away"),
                _goalless_rows(),
            ],
            how="diagonal_relaxed",
        )
        .sort("date", "current_team_score")
        .collect()
    )
    matches_ir
    return


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    # Otros experimentos (no se usan todavía)
    """)
    return


@app.cell
def _():
    _df = mo.sql(
        f"""
        select
            goal_scorers.date,
            goal_scorers.home_team,
            goal_scorers.away_team,
            match_results.home_score,
            match_results.away_score,
            team as goal_scorer_team,
            scorer as goal_scorer,
            minute as goal_minute,
            own_goal as goal_was_own_goal,
            penalty as goal_was_penalty,
            country as played_in_country,
            tournament as played_in_tournament,
            city as played_in_city,
            neutral as neutral_field
        from
            match_results
            full outer join goal_scorers on match_results.date = goal_scorers.date
            and match_results.home_team = goal_scorers.home_team
            and match_results.away_team = goal_scorers.away_team
        """
    )
    return


@app.cell(hide_code=True)
def _():
    matches = mo.sql(
        f"""
        select
            ifnull (match_results.date, penalty_shootouts.date) as date,
            ifnull (
                match_results.home_team,
                penalty_shootouts.home_team
            ) as home_team,
            match_results.home_score,
            ifnull (
                match_results.away_team,
                penalty_shootouts.away_team
            ) as away_team,
            match_results.away_score,
            case
                when match_results.home_score > match_results.away_score then match_results.home_team
                when match_results.home_score < match_results.away_score then match_results.away_team
                else penalty_shootouts.winner
            end as winner,
            case
                when penalty_shootouts.date is null then 'goals'
                else 'penalties'
            end as won_by,
            penalty_shootouts.first_shooter as penalty_first_shooter,
            tournament,city,country,neutral
        from
            match_results
            full outer join penalty_shootouts on match_results.date = penalty_shootouts.date
            and match_results.home_team = penalty_shootouts.home_team
            and match_results.away_team = penalty_shootouts.away_team
        order by date asc
        """
    )
    return


if __name__ == "__main__":
    app.run()
