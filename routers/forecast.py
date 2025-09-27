from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from modules.scenarios.service import ScenarioService
from schemas.forecast_transactions import ForecastPoint, ForecastTransaction
from datetime import date, datetime

router = APIRouter(prefix="/forecast", tags=["Forecast"])

@router.get("/scenarios/{scenario_id}", response_model=List[ForecastTransaction])
def get_scenario_forecast(
    scenario_id: int,
    end_date: date,
    db: Session = Depends(get_db)
):
    service = ScenarioService(db)
    try:
        return service.calculate_forecast(scenario_id, end_date)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/balances", response_model=List[ForecastPoint])
def get_forecast_balances(
    start_date: date,
    end_date: date,
    scenario_id: int = None,
    db: Session = Depends(get_db)
):
    service = ScenarioService(db)
    try:
        return service.calculate_balance_forecast(
            start_date=start_date,
            end_date=end_date,
            scenario_id=scenario_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
