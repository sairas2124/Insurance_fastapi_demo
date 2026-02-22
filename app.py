from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Annotated, Literal
import pickle
import pandas as pd


try:
    with open("model.pkl", "rb") as f:
        model = pickle.load(f)
except FileNotFoundError:
    raise RuntimeError("model.pkl not found. Put model.pkl in the same folder as this file.")
except Exception as e:
    raise RuntimeError(f"Failed to load model.pkl: {e}")


app = FastAPI(title="Insurance Premium Category Predictor")



TIER_1_CITIES = ["Kathmandu", "Pokhara"]
TIER_2_CITIES = ["Butwal", "Lalitpur", "Biratnagar"]


class UserInput(BaseModel):
    age: Annotated[int, Field(gt=0, lt=120, description="Age", examples=[22])]
    weight: Annotated[float, Field(gt=0, description="Weight in kg", examples=[60.0])]
    height: Annotated[float, Field(gt=0, description="Height in meters", examples=[1.65])]
    income: Annotated[float, Field(gt=0, description="Annual income", examples=[50000.0])]

   
    smoker: Annotated[bool, Field(description="Smoker status", examples=["Yes", "No"])]

    city: Annotated[str, Field(description="City of residence", examples=["Kathmandu"])]

    occupation: Annotated[
        Literal[
            "Student",
            "Part-time Worker",
            "Intern",
            "Office Assistant",
            "Teacher Assistant",
            "Engineer",
            "Software Developer",
            "Designer",
            "Sales Executive",
        ],
        Field(description="Occupation status"),
    ]

    

    @property
    def bmi(self) -> float:
        return round(self.weight / (self.height ** 2), 2)

    @property
    def lifestyle_risk(self) -> str:
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


def predict_risk(user_input: UserInput):
   
    input_df = pd.DataFrame([{
        "age": user_input.age,
        "weight": user_input.weight,
        "height": user_input.height,
        "income": user_input.income, 
        "bmi": user_input.bmi,
        "age_group": user_input.age_group,
        "lifestyle_risk": user_input.lifestyle_risk,
        "city_tier": user_input.city_tier,
        "occupation": user_input.occupation,
    }])

    try:
        prediction = model.predict(input_df)[0]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model prediction failed. Check training feature columns match API columns. Error: {e}"
        )

    return JSONResponse(status_code=200, content={"predicted_category": prediction})