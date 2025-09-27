from modules.common.base_service import BaseService
from .models import Scenario, ScenarioTransaction
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from decimal import Decimal

class ScenarioService(BaseService[Scenario]):
    def __init__(self, db: Session):
        super().__init__(Scenario, db)

    def create_scenario(self, name: str, description: str = None) -> Scenario:
        return self.create({
            "name": name,
            "description": description
        })

    def add_transaction(self, scenario_id: int, amount: Decimal, 
                       description: str, date: datetime) -> ScenarioTransaction:
        scenario = self.get(scenario_id)
        if not scenario:
            raise ValueError("Scenario not found")

        transaction = ScenarioTransaction(
            scenario_id=scenario_id,
            amount=float(amount),
            description=description,
            date=date
        )
        self.db.add(transaction)
        self.db.commit()
        return transaction

    def calculate_forecast(self, scenario_id: int, end_date: datetime) -> List[dict]:
        scenario = self.get(scenario_id)
        if not scenario:
            raise ValueError("Scenario not found")

        transactions = (self.db.query(ScenarioTransaction)
                       .filter(ScenarioTransaction.scenario_id == scenario_id)
                       .filter(ScenarioTransaction.date <= end_date)
                       .order_by(ScenarioTransaction.date)
                       .all())

        balance = Decimal('0.00')
        forecast = []
        
        for transaction in transactions:
            balance += Decimal(str(transaction.amount))
            forecast.append({
                'date': transaction.date,
                'amount': transaction.amount,
                'balance': float(balance),
                'description': transaction.description
            })
        
        return forecast