import pandas as pd
from difflib import get_close_matches

clean = pd.read_csv("harmoniQ/harmoniq/db/CSVs/coordonnes_MRC_clean.csv")
not_clean = pd.read_csv(
    "/home/seb/Documents/skool/HarmoniQ/harmoniQ/harmoniq/db/CSVs/population_mrc.csv"
)


def find_most_similar(name, possibilities):
    matches = get_close_matches(name, possibilities, n=5, cutoff=0.8)
    return matches[0] if matches else None


clean_names = clean["CDNAME"].tolist()
not_clean["most_similar"] = not_clean["MRC"].apply(
    lambda x: find_most_similar(x, clean_names)
)
not_clean["MRC"] = not_clean["most_similar"]
not_clean["CUID"] = not_clean["most_similar"].apply(
    lambda x: clean.loc[clean["CDNAME"] == x, "CDUID"].values[0] if x else None
)

not_clean = not_clean.drop(columns=["most_similar"])
not_clean.to_csv("harmoniQ/harmoniq/db/CSVs/population_mrc_clean.csv", index=False)

duplicates = not_clean[not_clean.duplicated(subset=["MRC"], keep=False)]
if not duplicates.empty:
    print("Duplicate MRC names found:")
    print(duplicates)
else:
    print("No duplicate MRC names found.")
