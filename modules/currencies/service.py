from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from modules.common.base_service import BaseService
from models.accounts import Currency, ExchangeRate, CurrencyType

class CurrencyService(BaseService[Currency]):
    def __init__(self, db: Session):
        super().__init__(Currency, db)

    def create_currency(
        self,
        code: str,
        name: str,
        symbol: str,
        type: CurrencyType,
        decimals: int | None = None
    ) -> Currency:
        """Create a new currency"""
        if decimals is None:
            decimals = 8 if type == CurrencyType.crypto else 2
            
        # Create the currency directly using the model
        currency = Currency(
            code=code.upper(),
            name=name,
            symbol=symbol,
            type=type,
            decimals=decimals,
            is_active=True
        )
        self.db.add(currency)
        self.db.commit()
        self.db.refresh(currency)
        return currency

    def get_by_code(self, code: str) -> Optional[Currency]:
        """Get a currency by its code"""
        return self.db.query(Currency).filter(Currency.code == code.upper()).first()

    def list_currencies(self, type: Optional[CurrencyType] = None) -> List[Currency]:
        """List all active currencies, optionally filtered by type"""
        query = self.db.query(Currency).filter(Currency.is_active == True)
        if type:
            query = query.filter(Currency.type == type)
        return query.all()

    def set_exchange_rate(
        self,
        from_currency_code: str,
        to_currency_code: str,
        rate: Decimal,
        timestamp: Optional[datetime] = None
    ) -> ExchangeRate:
        """Set the exchange rate between two currencies"""
        from_currency = self.get_by_code(from_currency_code)
        to_currency = self.get_by_code(to_currency_code)
        
        if not from_currency or not to_currency:
            raise ValueError("One or both currencies not found")
            
        exchange_rate = ExchangeRate(
            from_currency_id=from_currency.id,
            to_currency_id=to_currency.id,
            rate=rate,
            timestamp=timestamp or datetime.utcnow()
        )
        
        self.db.add(exchange_rate)
        self.db.commit()
        self.db.refresh(exchange_rate)
        
        return exchange_rate

    def get_exchange_rate(
        self,
        from_currency_code: str,
        to_currency_code: str,
        at_time: Optional[datetime] = None
    ) -> Optional[Decimal]:
        """Get the latest exchange rate between two currencies"""
        from_currency = self.get_by_code(from_currency_code)
        to_currency = self.get_by_code(to_currency_code)
        
        if not from_currency or not to_currency:
            raise ValueError("One or both currencies not found")
            
        # If same currency, rate is 1
        if from_currency.id == to_currency.id:
            return Decimal("1")
            
        query = self.db.query(ExchangeRate).filter(
            and_(
                ExchangeRate.from_currency_id == from_currency.id,
                ExchangeRate.to_currency_id == to_currency.id
            )
        )
        
        if at_time:
            # Get rate closest to but not after specified time
            rate = query.filter(ExchangeRate.timestamp <= at_time)\
                       .order_by(ExchangeRate.timestamp.desc())\
                       .first()
        else:
            # Get latest rate
            rate = query.order_by(ExchangeRate.timestamp.desc()).first()
            
        return rate.rate if rate else None

    def convert_amount(
        self,
        amount: Decimal,
        from_currency_code: str,
        to_currency_code: str,
        at_time: Optional[datetime] = None
    ) -> Optional[Decimal]:
        """Convert an amount from one currency to another"""
        rate = self.get_exchange_rate(from_currency_code, to_currency_code, at_time)
        if rate is None:
            return None
        return amount * rate