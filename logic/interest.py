from models.accounts import Account, AccountType


def accrue_interest(account: Account, days: int):
    if not account.interest_rate or not account.interest_compounding:
        return 0

    rate = float(account.interest_rate)
    if account.interest_compounding == "daily":
        daily_rate = rate / 365
    elif account.interest_compounding == "monthly":
        daily_rate = rate / 12 / 30
    else:
        return 0

    interest = account.balance * ((1 + daily_rate) ** days - 1)
    return interest

def accrue_overdraft_interest(account: Account, days: int):
    if account.type != AccountType.checking:
        return 0

    if account.balance >= 0 or not account.overdraft_interest_rate:
        return 0

    daily_rate = float(account.overdraft_interest_rate) / 365
    overdraft_amount = abs(min(account.balance, account.overdraft_limit or 0))
    interest = overdraft_amount * ((1 + daily_rate) ** days - 1)
    return interest
