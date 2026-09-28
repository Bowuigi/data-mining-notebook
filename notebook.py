# /// script
# dependencies = [
#     "altair==6.3.0",
#     "duckdb==1.5.5",
#     "marimo",
#     "mcp==2.2.0",
#     "polars[pyarrow]==1.44.2",
#     "pyarrow==25.0.1",
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

__generated_with = "0.25.0"
app = marimo.App(sql_output="polars")

with app.setup:
    import marimo as mo
    import polars as pl
    import altair as alt


@app.cell
def _():
    def from_csv(filename: str):
        return pl.read_csv(filename, null_values=["NA"], schema_overrides={'date': pl.Date})

    goal_scorers = from_csv("data/Goal_Scorers.csv")

    match_results = from_csv("data/Match_Results.csv")

    penalty_shootouts = from_csv("data/Penalty_Shootouts.csv")
    return (penalty_shootouts,)


@app.cell
def _(penalty_shootouts):
    penalty_shootouts
    return


@app.cell
def _():
    _df = mo.sql(
        f"""
        select
            ifnull(match_results.home_team, penalty_shootouts.home_team) as home_team,
            ifnull(match_results.away_team, penalty_shootouts.away_team) as away_team,
            columns(match_results.*) as "m_\\0",
            columns(penalty_shootouts.*) as "p_\\0"
        from
            match_results
            full outer join penalty_shootouts on match_results.date = penalty_shootouts.date
            and match_results.home_team = penalty_shootouts.home_team
            and match_results.away_team = penalty_shootouts.away_team
        """
    )
    return


if __name__ == "__main__":
    app.run()
