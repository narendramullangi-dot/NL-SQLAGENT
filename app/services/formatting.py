import pandas as pd

def result_dataframe(results: dict) -> pd.DataFrame:
    return pd.DataFrame(results.get("data", []), columns=results.get("columns", []))
