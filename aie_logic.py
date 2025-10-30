from aie_helpers import Transaction, COMMON_ACCOUNTS, ANOMALY_THRESHOLD, ACCOUNT_TYPES, DEBIT_BALANCE_ACCOUNTS, CREDIT_BALANCE_ACCOUNTS
from datetime import datetime
from decimal import Decimal
from typing import List

# --- 2. ACCOUNTING INTELLIGENCE ENGINE (AIE) LOGIC ---

def perform_aie_analysis(transactions: List[Transaction]) -> List[Transaction]:
    """
    Performs rules-based validation and anomaly detection on transactions.
    Uses Decimal arithmetic and produces a new list of Transaction instances
    with status and errors filled in.
    """
    analyzed_transactions = []
    
    # Pre-calculate sets for fast lookup
    debit_accounts_set = set(DEBIT_BALANCE_ACCOUNTS)
    credit_accounts_set = set(CREDIT_BALANCE_ACCOUNTS)
    
    # Threshold for a 'significant' opposite-entry anomaly check
    OPPOSITE_ENTRY_THRESHOLD = Decimal('100.0')

    for t in transactions:
        status = 'Valid'
        error_messages = []

        # Rule 1: Basic presence/format checks
        # Date Validity Check (Basic check)
        try:
            if not t.date or not isinstance(t.date, str):
                raise ValueError("Empty date")
            datetime.strptime(t.date, '%Y-%m-%d')
        except Exception:
            status = 'Error'
            error_messages.append('Invalid date format (must be YYYY-MM-DD).')

        # Rule: Negative amounts are invalid
        try:
            if t.debit < Decimal('0') or t.credit < Decimal('0'):
                status = 'Error'
                error_messages.append('Negative amounts are not allowed.')
        except Exception:
            status = 'Error'
            error_messages.append('Amount parsing error.')

        # Rule: Both debit and credit present on one line (if you want single-sided lines)
        try:
            if t.debit > Decimal('0') and t.credit > Decimal('0'):
                status = 'Error'
                error_messages.append('Both debit and credit are populated on a single line; one side must be zero.')
        except Exception:
            # Skip; this will be caught by amount parsing error above if dysfunctional
            pass

        # Rule 2: Anomaly Detection (Threshold Check)
        try:
            if (t.debit > ANOMALY_THRESHOLD or t.credit > ANOMALY_THRESHOLD) and status != 'Error':
                status = 'Anomaly'
                error_messages.append(f'Large transaction detected (exceeds ${ANOMALY_THRESHOLD:,.2f}).')
        except Exception:
            pass

        # Rule 3: Removed - Unclassified accounts default to Credit-Normal in balance calculation

        # Rule 4: Account Type Anomaly Check (Unexpected Debit/Credit)
        try:
            is_debit_balance = t.account in debit_accounts_set
            is_credit_balance = t.account in credit_accounts_set
            # Check for significant Credit on a normal Debit Balance account (e.g., Asset loss)
            if is_debit_balance and t.credit > Decimal('0') and t.credit > OPPOSITE_ENTRY_THRESHOLD and status == 'Valid':
                status = 'Anomaly'
                error_messages.append('Significant credit activity in a normal debit balance account (Asset/Expense).')

            # Check for significant Debit on a normal Credit Balance account (e.g., Revenue refund)
            elif is_credit_balance and t.debit > Decimal('0') and t.debit > OPPOSITE_ENTRY_THRESHOLD and status == 'Valid':
                status = 'Anomaly'
                error_messages.append('Significant debit activity in a normal credit balance account (Liability/Equity/Revenue).')

        except Exception:
            pass

        # Create a new Transaction instance with updated status/errors
        analyzed_transactions.append(Transaction(
            id=t.id,
            date=t.date,
            description=t.description,
            account=t.account,
            debit=t.debit,
            credit=t.credit,
            status=status,
            errors=error_messages or []
        ))

    return analyzed_transactions

def calculate_balances(transactions: List[Transaction]) -> dict:
    """
    Calculates the T-account balances, ignoring entries marked as 'Error' for realism.
    Properly handles different account types using the lists defined in aie_helpers.
    Returns a mapping account -> Decimal balance and aggregate fields as Decimal.
    """
    analyzed = perform_aie_analysis(transactions)

    # Initialize balances with ALL unique accounts found in the ledger (using Decimal zeros)
    unique_accounts = set(t.account for t in analyzed)
    all_accounts = set(COMMON_ACCOUNTS)
    all_accounts.update(unique_accounts)

    balances = {acc: Decimal('0.0') for acc in all_accounts}

    # Use the helper lists
    asset_accounts = ACCOUNT_TYPES['ASSET']
    liability_accounts = ACCOUNT_TYPES['LIABILITY']
    equity_accounts = ACCOUNT_TYPES['EQUITY']
    revenue_accounts = ACCOUNT_TYPES['REVENUE']
    expense_accounts = ACCOUNT_TYPES['EXPENSE']

    # Pre-calculate sets for efficiency
    all_debit_accounts = set(DEBIT_BALANCE_ACCOUNTS)
    all_credit_accounts = set(CREDIT_BALANCE_ACCOUNTS)

    for t in analyzed:
        # Only process transactions that are not fundamentally invalid (Error status)
        if t.status == 'Error':
            continue

        # Ensure account exists
        if t.account not in balances:
            balances[t.account] = Decimal('0.0')

        # Proper accounting logic based on account type
        if t.account in all_debit_accounts:
            # Debit increases, Credit decreases (Normal Debit Balance)
            balances[t.account] += (t.debit - t.credit)
        elif t.account in all_credit_accounts:
            # Credit increases, Debit decreases (Normal Credit Balance)
            balances[t.account] += (t.credit - t.debit)
        else:
            # UNCLASSIFIED ACCOUNTS: Reflect net activity (positive=net Debit, negative=net Credit)
            balances[t.account] += (t.debit - t.credit)

    # Calculate key aggregates using the full balances dict
    total_assets = sum(balances.get(acc, Decimal('0.0')) for acc in asset_accounts)
    total_liabilities = sum(balances.get(acc, Decimal('0.0')) for acc in liability_accounts)
    total_equity = sum(balances.get(acc, Decimal('0.0')) for acc in equity_accounts)
    total_revenue = sum(balances.get(acc, Decimal('0.0')) for acc in revenue_accounts)
    total_expenses = sum(balances.get(acc, Decimal('0.0')) for acc in expense_accounts)

    # Prepare formatted_balances only for presentation (exclude zero balances)
    formatted_balances = {}
    for acc, val in balances.items():
        if val != Decimal('0.0'):
            formatted_balances[acc] = val

    # Separate aggregates for clarity
    aggregates = {
        'Total Assets': total_assets,
        'Total Liabilities': total_liabilities,
        'Total Equity': total_equity,
        'Net Income': (total_revenue - total_expenses)
    }

    return {
        'balances': formatted_balances,
        'aggregates': aggregates
    }

# --- 3. MOCK DATA INITIALIZATION ---

def generate_mock_ledger() -> list[Transaction]:
    """
    Returns an empty list for the ledger, requiring users to input data via
    'Add Entry' or 'Upload Data'.
    """
    return []