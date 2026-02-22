from fastapi import FastAPI, Path, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Optional
import json
from fastapi.responses import JSONResponse

app = FastAPI()

DATA_FILE = "patients.json"


class Patient(BaseModel):
    id: Annotated[str, Field(description="ID of the patient", examples=["P001"])]
    name: Annotated[str, Field(max_length=50, description="Patient name", examples=["Sanam Thapa"])]
    age: Annotated[int, Field(gt=0, lt=120, description="Patient age", examples=[22])]
    gender: Annotated[Literal["Male", "Female", "Other"], Field(description="Patient gender", examples=["Female"])]
    height: Annotated[float, Field(gt=0, description="Patient height in meters", examples=[1.65])]
    weight: Annotated[float, Field(gt=0, description="Patient weight in kg", examples=[60.0])]

    @property
    def bmi(self) -> float:
        
        return round(self.weight / (self.height ** 2), 2)

    @property
    def verdict(self) -> str:
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal"
        elif self.bmi < 30:
            return "Overweight"
        return "Obese"

class PatientUpdate(BaseModel):
    name: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt =0)]
    gender: Annotated[Optional[Literal["Male", "Female", "Other"]], Field(default=None)]
    height: Annotated[Optional[float], Field(gt=0,default = None)]
    weight: Annotated[Optional[float], Field(gt=0, default=None)]


def load_data() -> dict:
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        # If file exists but is empty/corrupt
        return {}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def patient_out(patient_id: str, patient_payload: dict) -> dict:
    """
    Convert stored JSON dict -> Patient model -> dict output including bmi/verdict.
    """
    p = Patient(id=patient_id, **patient_payload)
    out = p.model_dump()
    out["bmi"] = p.bmi
    out["verdict"] = p.verdict
    return out

@app.get("/")
def root():
    return {"message": "FastAPI Patient API is running"}


@app.get("/patients")
def view_all_patients():
    data = load_data()
    # return list with id included (better for frontend)
    return [patient_out(pid, payload) for pid, payload in data.items()]


@app.get("/patients/{patient_id}")
def view_patient(
    patient_id: str = Path(..., description="The ID of the patient to retrieve", examples=["P001"])
):
    data = load_data()

    if patient_id in data:
        return patient_out(patient_id, data[patient_id])

    raise HTTPException(status_code=404, detail="Patient not found")


@app.get("/sort")
def sort_patients(
    sort_by: str = Query(
        ...,
        description="The field to sort by (height, weight or bmi)",
        examples=["bmi"],
    ),
    order: str = Query(
        "asc",
        description="The sort order (asc or desc)",
        examples=["desc"],
    ),
):
    valid_fields = ["height", "weight", "bmi"]
    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f"Invalid sort field. Must be one of {valid_fields}")

    if order not in ["asc", "desc"]:
        raise HTTPException(status_code=400, detail="Invalid sort order. Must be 'asc' or 'desc'")

    data = load_data()
    patients = [Patient(id=pid, **payload) for pid, payload in data.items()]

    # sort using attribute (bmi works even though it's computed)
    sorted_patients = sorted(
        patients,
        key=lambda p: getattr(p, sort_by),
        reverse=(order == "desc"),
    )

    # return output including bmi/verdict
    return [
        {**p.model_dump(), "bmi": p.bmi, "verdict": p.verdict}
        for p in sorted_patients
    ]


@app.post("/create")
def create_patient(patient: Patient):
    data = load_data()

    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient with this ID already exists")

    # store WITHOUT id because id is used as key in JSON
    payload = patient.model_dump(exclude={"id"})  #convert to dict and exclude id
    data[patient.id] = payload
    save_data(data)

    return JSONResponse(
        content={"message": "Patient created successfully", "patient": patient_out(patient.id, payload)},
        status_code=201,
    )


@app.put("/edit/{patient_id}")
def edit_patient(
    patient_id: str = Path(..., description="The ID of the patient to update", examples=["P001"]),
    patient_update: PatientUpdate = ...,
):
    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get existing data and update with new values (only if provided)
    existing_data = data[patient_id]
    update_data = patient_update.model_dump(exclude_unset=True)  # only include fields that were provided
    existing_data.update(update_data)

    # Validate updated data by creating a Patient instance (will raise error if invalid)
    try:
        updated_patient = Patient(id=patient_id, **existing_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save updated data
    data[patient_id] = existing_data
    save_data(data)

    return {"message": "Patient updated successfully", "patient": patient_out(patient_id, existing_data)}



@app.delete("/delete/{patient_id}")
def delete_patient(
    patient_id: str = Path(..., description="The ID of the patient to delete", examples=["P001"])
):
    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    del data[patient_id]
    save_data(data)

    return {"message": "Patient deleted successfully"}