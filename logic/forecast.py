from datetime import date
from typing import List
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY
from models.scheduled_transactions import RecurrenceType, ScheduledTransaction
from schemas.forecast_transactions import ForecastTransaction


FREQUENCY_MAP = {
    RecurrenceType.DAILY: DAILY,
    RecurrenceType.WEEKLY: WEEKLY,
    RecurrenceType.MONTHLY: MONTHLY,
}


def expand_scheduled_transactions(
    scheduled: List[ScheduledTransaction],
    start_date: date,
    end_date: date
) -> List[ForecastTransaction]:
    forecast = []

    for item in scheduled:
        freq = FREQUENCY_MAP.get(item.recurrence)
        if not freq:
            continue  # Skip if unknown recurrence type

        rule_start = max(item.start_date, start_date)
        rule_end = min(item.end_date or end_date, end_date)
        
        for dt in rrule(freq, dtstart=rule_start, until=rule_end):
            forecast.append(ForecastTransaction(
                date=dt.date(),
                name=item.description,
                amount=item.amount,
                source_account_id=item.from_account_id,
                destination_account_id=item.to_account_id,
            ))

    return forecast
