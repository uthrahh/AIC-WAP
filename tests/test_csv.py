from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

csv_path = BASE_DIR / "app" / "seeds" / "managers.csv"

manager_df = pd.read_csv(csv_path)

print(manager_df)