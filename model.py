import pandas as pd
from sklearn.linear_model import LinearRegression
from joblib import dump

data = pd.read_csv("database.csv")

data = data.rename(columns={
    "Work Hours Per Day": "work_hours",
    "Study Hours Per Day": "study_hours",
    "Sleep Duration": "sleep_hours",
    "Physical Exercise": "exercise",
    "Stress Level": "stress"
})

inputs = data[["work_hours", "study_hours", "sleep_hours", "exercise"]]
output = data["stress"]

model = LinearRegression()
model.fit(inputs, output)

dump(model, "stress_model.pkl")

print("Model has been trained!")
