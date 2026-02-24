from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal
import pandas as pd
import pickle
from fastapi.responses import JSONResponse

app = FastAPI(title="Insurance Premium Category Predictor")


tier_1_cities = ["Kathmandu","Pokhara","lalitpur","Bharatpur"]
tier_2_cities = [
    "Butwal","Tulsipur","Janakpur","Biratnagar","Dharan","Hetauda","Bhairahawa","Dhangadhi","Itahari","Gorkha","Nepalgunj"]

# ---- Load model ----
try:
    with open("model.pkl", "rb") as f:
        model = pickle.load(f)
except Exception as e:
    raise RuntimeError(f"Failed to load model.pkl: {e}")


class UserInput(BaseModel):
    age: int = Field(gt=0, lt=120)
    weight: float = Field(gt=0)
    height: float = Field(gt=0)   # meters
    income: float = Field(gt=0)
    smoker: bool
    city: str
    occupation: Literal[
        "Student",
        "Part-time Worker",
        "Intern",
        "Office Assistant",
        "Teacher Assistant",
        "Engineer",
        "Software Developer",
        "Designer",
        "Sales Executive",
    ]

    @property
    def bmi(self) -> float:
        return round(self.weight / (self.height ** 2), 2)

    @property
    def lifestyle_risk(self) -> str:
        # MUST match training casing: Low/Medium/High
        if self.smoker and self.bmi > 30:
            return "High"
        elif self.smoker or self.bmi > 27:
            return "Medium"
        else:
            return "Low"

    @property
    def age_group(self) -> str:
        if self.age < 25:
            return "young"
        elif self.age < 45:
            return "adult"
        elif self.age < 60:
            return "middle_aged"
        else:
            return "senior"

    @property
    def city_tier(self) -> int:
        if self.city in TIER_1_CITIES:
            return 1
        elif self.city in TIER_2_CITIES:
            return 2
        else:
            return 3


@app.get("/")
def home():
    return {"message": "API is running"}


@app.post("/predict")
def predict(data: UserInput):
    input_df = pd.DataFrame([{
        "bmi": data.bmi,
        "age_group": data.age_group,
        "lifestyle_risk": data.lifestyle_risk,
        "city_tier": data.city_tier,
        "income": data.income,
        "occupation": data.occupation,
    }])

    try:
        pred = model.predict(input_df)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"predicted_category": pred})