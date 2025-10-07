"""Service for matching transactions between accounts"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Sequence, Tuple, Literal
from dataclasses import dataclass

from models.transactions import Transaction

TransferType = Literal["account_transfer", "pot_transfer"]

@dataclass
class TransferMatch:
    """Represents a potential match between two transactions that form a transfer"""
    source_transaction: Transaction
    dest_transaction: Transaction
    days_apart: int
    transfer_type: TransferType

class TransactionMatcher:
    """Service for matching transactions between accounts"""
    
    # Keywords that indicate pot transfers in different banks
    POT_TRANSFER_KEYWORDS = [
        "pot transfer",
        "savings space",
        "vault transfer",
        "space transfer"
    ]
    
    def _is_pot_transfer(self, tx: Transaction) -> bool:
        """Check if a transaction is a pot transfer based on description or type"""
        # Check explicit type field first if available
        tx_type = getattr(tx, 'type', None)
        if tx_type and str(tx_type).lower() in ["pot transfer", "vault transfer"]:
            return True
            
        # Check description for pot transfer keywords
        description = str(getattr(tx, 'description', '')).lower()
        return any(keyword in description for keyword in self.POT_TRANSFER_KEYWORDS)
    
    def find_transfer_matches(
        self,
        transactions: Sequence[Transaction],
        max_days_apart: int = 3
    ) -> list[TransferMatch]:
        """Find potential matches between transactions that could represent transfers
        
        Args:
            transactions: List of transactions to analyze
            max_days_apart: Maximum number of days between matching transactions
            
        Returns:
            List of potential matches ordered by date proximity, separating
            pot transfers from account transfers
        """
        matches: list[TransferMatch] = []
        
        # Group transactions by date to reduce comparison space
        date_groups: dict[str, list[Transaction]] = {}  # Use date string as key
        for tx in transactions:
            date_str = tx.date.strftime('%Y-%m-%d')  # Convert to string for dict key
            date_groups.setdefault(date_str, []).append(tx)
            
        # Look for matches within the date range
        for date_str, group in date_groups.items():
            base_date = datetime.strptime(date_str, '%Y-%m-%d')
            # Get transactions from surrounding days
            date_range = [
                (base_date + timedelta(days=d)).strftime('%Y-%m-%d')
                for d in range(-max_days_apart, max_days_apart + 1)
            ]
            compare_txs = []
            for d in date_range:
                compare_txs.extend(date_groups.get(d, []))
                
            # Compare transactions
            for tx1 in group:
                for tx2 in compare_txs:
                    # Skip same transaction or same account
                    if (getattr(tx1, 'id', None) == getattr(tx2, 'id', None) or 
                        getattr(tx1, 'account_id', None) == getattr(tx2, 'account_id', None)):
                        continue
                        
                    # Check if amounts match (one positive, one negative)
                    if getattr(tx1, 'amount', 0) != -getattr(tx2, 'amount', 0):
                        continue
                        
                    # Calculate days between transactions
                    days_apart = abs((tx1.date - tx2.date).days)
                    
                    # Determine transfer type based on transaction descriptions/types
                    is_pot = self._is_pot_transfer(tx1) or self._is_pot_transfer(tx2)
                    transfer_type: TransferType = "pot_transfer" if is_pot else "account_transfer"
                    
                    # Order by source (negative amount) and destination (positive)
                    tx_amount = getattr(tx1, 'amount', 0)
                    if tx_amount < 0:
                        match = TransferMatch(tx1, tx2, days_apart, transfer_type)
                    else:
                        match = TransferMatch(tx2, tx1, days_apart, transfer_type)
                    matches.append(match)
                        
        # Sort by date proximity and group by transfer type
        matches.sort(key=lambda m: (m.transfer_type == "account_transfer", m.days_apart))
        return matches