from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.accounts import Account
from models.scheduled_transactions import ScheduledTransaction
from schemas.forecast_transactions import ForecastPoint, ForecastTransaction
from logic.forecast import expand_scheduled_transactions
from datetime import date
from dateutil.rrule import rrule, DAILY

router = APIRouter(prefix="/forecast", tags=["Forecast"])

@router.get("/", response_model=list[ForecastTransaction])
def get_forecast(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    scheduled = db.query(ScheduledTransaction).all()
    return expand_scheduled_transactions(scheduled, start_date, end_date)

@router.get("/balances", response_model=list[ForecastPoint])
def get_forecast_balances(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    forecast = get_forecast(start_date, end_date, db)

    balances = defaultdict(lambda: defaultdict(float))  # {account_id: {date: balance}}

    # Initial account balances
    accounts = db.query(Account).all()
    account_names = {a.id: a.name for a in accounts}
    running_balances = {a.id: a.balance for a in accounts}
    account_dict = {a.id: a for a in accounts}
    movement_out = {a.id: defaultdict(float) for a in accounts}  # {account_id: {date: movement}}
    movement_in = {a.id: defaultdict(float) for a in accounts}  # {account_id: {date: movement}}
    dates = [d for d in rrule(DAILY, dtstart=start_date, until=end_date)]

    for day in dates:
        for tx in filter(lambda t: t.date == day.date(), forecast):
            running_balances[tx.source_account_id] -= tx.amount
            running_balances[tx.destination_account_id] += tx.amount
            movement_out[tx.source_account_id][day] = movement_out[tx.source_account_id].get(day, 0) + tx.amount
            movement_in[tx.destination_account_id][day] = movement_in[tx.destination_account_id].get(day, 0) + tx.amount
        for acc_id, bal in running_balances.items():
            balances[acc_id][day] = bal

    results = []
    for acc_id, daily_balances in balances.items():
        for dt, bal in daily_balances.items():
            results.append(ForecastPoint(
                account_id=acc_id,
                account_name=account_names.get(acc_id, "Unknown"),
                date=dt,
                balance=bal,
                is_external=account_dict[acc_id].is_external,
                amount_in=movement_in[acc_id][dt],
                amount_out=movement_out[acc_id][dt],
            ))

    return results
