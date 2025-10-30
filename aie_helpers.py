from dataclasses import dataclass
from typing import List
import uuid
from datetime import datetime
import json
import os
from decimal import Decimal, getcontext
import re
from typing import Union

# Set a sensible precision for financial calculations
getcontext().prec = 12

# --- 1. CORE DATA STRUCTURES ---

@dataclass
class Transaction:
    """Represents a single double-entry accounting transaction line."""
    id: str
    date: str
    description: str
    account: str
    debit: Decimal
    credit: Decimal
    status: str = "Valid"
    errors: List[str] = None
    source_file: str = "Manual"  # Track the source file for separation on download

    def __post_init__(self):
        # Ensure errors is a list, even if initialized as None
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> dict:
        """Serialize Transaction to JSON-serializable dict."""
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "account": self.account,
            "debit": str(self.debit),
            "credit": str(self.credit),
            "status": self.status,
            "errors": list(self.errors or []),
            "source_file": self.source_file,
        }

    @staticmethod
    def from_dict(d: dict) -> "Transaction":
        """Deserialize Transaction from dict produced by to_dict()."""
        debit = Decimal(d.get("debit", "0.0"))
        credit = Decimal(d.get("credit", "0.0"))
        return Transaction(
            id=d.get("id", str(uuid.uuid4())),
            date=d.get("date", ""),
            description=d.get("description", ""),
            account=d.get("account", "Unclassified"),
            debit=debit,
            credit=credit,
            status=d.get("status", "Valid"),
            errors=d.get("errors", []) or [], # Simplified slightly
            source_file=d.get("source_file", "Manual")
        )

# --- 2. CONSTANTS ---

COMMON_ACCOUNTS = ['Cash', 'Accounts Payable', 'Revenue', 'Salaries', 'Capital', 'Office Supplies', 'Rent Expense']
ANOMALY_THRESHOLD = Decimal('50000.0')  # Threshold for large transaction anomaly detection
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

# Define account types for proper balance calculation (used in aie_logic)
ACCOUNT_TYPES = {
    'ASSET': ['Cash', 'Office Supplies'],
    'LIABILITY': ['Accounts Payable'],
    'EQUITY': ['Capital'],
    'REVENUE': ['Revenue'],
    'EXPENSE': ['Salaries', 'Rent Expense']
}
DEBIT_BALANCE_ACCOUNTS = ACCOUNT_TYPES['ASSET'] + ACCOUNT_TYPES['EXPENSE']
CREDIT_BALANCE_ACCOUNTS = ACCOUNT_TYPES['LIABILITY'] + ACCOUNT_TYPES['EQUITY'] + ACCOUNT_TYPES['REVENUE']

# --- 3. Simple file persistence utilities ---

def save_ledger(ledger: List[Transaction], path: str = "ledger.json") -> None:
    """Save ledger (list of Transaction) to a JSON file (atomic write)."""
    try:
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump([t.to_dict() for t in ledger], f, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        # Log the exception for debugging persistence issues
        import traceback
        traceback.print_exc()
        # Best-effort: avoid raising to keep UI responsive; caller may surface errors.
        pass

def load_ledger(path: str = "ledger.json") -> List[Transaction]:
    """Load ledger from JSON file, returning list of Transaction. Returns empty list if not found or invalid."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        txs = []
        for item in data:
            try:
                txs.append(Transaction.from_dict(item))
            except Exception:
                # skip malformed record
                continue
        return txs
    except Exception:
        return []