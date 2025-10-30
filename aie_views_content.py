import flet as ft
from decimal import Decimal
from datetime import datetime
import uuid
from typing import List, Type
import traceback
import csv
import os

# Import functions/constants for use within the methods
from aie_helpers import Transaction, save_ledger, DATE_RE
from aie_logic import calculate_balances

# Import views from new files
from aie_views_core import create_stat_card, create_balance_card, dashboard_view, ledger_view, diagnostic_view
from aie_views_data_entry import add_transaction_view, upload_data_view
from aie_views_reports import reports_view, coa_view, settings_view


# --- MIXIN UTILITY ---
def get_views_mixins() -> Type:
    """
    Creates a mixin class containing all view-generating and UI action methods
    from the separate view files and this file's utility handlers.
    """
    # Collect all functions defined in this module that are not internal helpers/imports
    # This now only includes the Simulation/Action handlers and the imported view methods
    mixin_methods = {
        name: obj for name, obj in globals().items()
        if callable(obj) and not name.startswith('_') and name not in ['get_views_mixins', 'datetime', 'Decimal', 'uuid', 'List', 'Type', 'traceback', 'csv', 'os', 'ft', 'Transaction', 'save_ledger', 'DATE_RE', 'calculate_balances']
    }
    
    # Create an anonymous class with these methods
    return type("AIEViewsMixin", (object,), mixin_methods)


# --- VIEW CONTENT METHODS (These are utility methods/handlers remaining in this file) ---
# NOTE: All these methods will have access to 'self' (the AIEApp instance).

# Include the imported methods directly so they are found by get_views_mixins
# (The functions imported above are now methods of the Mixin)
create_stat_card = create_stat_card
create_balance_card = create_balance_card
dashboard_view = dashboard_view
ledger_view = ledger_view
diagnostic_view = diagnostic_view
add_transaction_view = add_transaction_view
upload_data_view = upload_data_view
reports_view = reports_view
coa_view = coa_view
settings_view = settings_view


# --- DIAGNOSTICS & SIMULATION HANDLERS (Remain here as they directly affect app state) ---

def open_amount_correction_panel(self, t_id: str, analyzed_transactions: List[Transaction]):
    self.selected_transaction = next((t for t in analyzed_transactions if t.id == t_id), None)
    if not self.selected_transaction:
        self.page.snack_bar = ft.SnackBar(ft.Text("Selected transaction not found."), bgcolor=ft.Colors.RED_700)
        self.page.snack_bar.open = True
        self.page.update()
        return
    self.temp_debit = self.selected_transaction.debit
    self.temp_credit = self.selected_transaction.credit
    self.correction_type = 'amount'
    self.simulation_active = True
    self.diagnostic_entries = self.ledger
    self.update_view()

def open_date_correction_panel(self, t_id: str, analyzed_transactions: List[Transaction]):
    self.selected_transaction = next((t for t in analyzed_transactions if t.id == t_id), None)
    if not self.selected_transaction:
        self.page.snack_bar = ft.SnackBar(ft.Text("Selected transaction not found."), bgcolor=ft.Colors.RED_700)
        self.page.snack_bar.open = True
        self.page.update()
        return
    self.correction_type = 'date'
    self.temp_date = self.selected_transaction.date
    self.simulation_active = True
    self.diagnostic_entries = self.ledger
    self.update_view()

def close_simulation_panel(self):
    self.simulation_active = False
    self.selected_transaction = None
    self.temp_debit = Decimal('0.0')
    self.temp_credit = Decimal('0.0')
    self.diagnostic_entries = self.ledger
    self.update_view()

def handle_temp_amount_change(self, e, attr_name):
    cleaned_value = e.control.value.replace(' ', '')
    parsed = self.safe_parse_decimal(cleaned_value)
    setattr(self, attr_name, parsed)

    if cleaned_value == "" or parsed == Decimal('0.0'):
        e.control.value = ""
    # Retain the user's input even on invalid parse to avoid clearing on typos
    e.control.update()

def apply_simulation_panel(self, e=None):
    if not self.selected_transaction:
        return
    temp_ledger = [t for t in self.ledger]
    for i, t in enumerate(temp_ledger):
        if t.id == self.selected_transaction.id:
            # We must update the source_file here too, just in case
            source = t.source_file if hasattr(t, 'source_file') else "Manual"
            if self.correction_type == 'date':
                temp_ledger[i] = Transaction(id=t.id, date=self.temp_date, description=t.description, account=t.account, debit=t.debit, credit=t.credit, source_file=source)
            else:
                temp_ledger[i] = Transaction(id=t.id, date=t.date, description=t.description, account=t.account, debit=self.temp_debit, credit=self.temp_credit, source_file=source)
            break
    self.diagnostic_entries = temp_ledger
    self.update_view()

def commit_simulation_panel(self, e=None):
    if not self.selected_transaction:
        return
    for i, t in enumerate(self.ledger):
        if t.id == self.selected_transaction.id:
            source = t.source_file if hasattr(t, 'source_file') else "Manual"
            if self.correction_type == 'date':
                if not DATE_RE.match(self.temp_date):
                    self.page.snack_bar = ft.SnackBar(ft.Text("Invalid date format. Use YYYY-MM-DD."), bgcolor=ft.Colors.RED_700)
                    self.page.snack_bar.open = True
                    self.page.update()
                    return
                self.ledger[i] = Transaction(id=t.id, date=self.temp_date, description=t.description, account=t.account, debit=t.debit, credit=t.credit, source_file=source)
            else:
                debit_nonzero = (self.temp_debit != Decimal('0.0'))
                credit_nonzero = (self.temp_credit != Decimal('0.0'))
                if not (debit_nonzero ^ credit_nonzero):
                    self.page.snack_bar = ft.SnackBar(ft.Text("Please enter exactly one amount: either Debit or Credit."), bgcolor=ft.Colors.RED_700)
                    self.page.snack_bar.open = True
                    self.page.update()
                    return
                self.ledger[i] = Transaction(id=t.id, date=t.date, description=t.description, account=t.account, debit=self.temp_debit, credit=self.temp_credit, source_file=source)
            break
    save_ledger(self.ledger)
    self.close_simulation_panel()

def delete_transaction(self, e):
    try:
        transaction_id = e.control.data
        self.ledger = [t for t in self.ledger if t.id != transaction_id]
        save_ledger(self.ledger)
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Transaction (ID: {transaction_id[:8]}) deleted."), bgcolor=ft.Colors.RED_700)
        self.page.snack_bar.open = True
        self.update_view()
    except Exception as ex:
        self.page.snack_bar = ft.SnackBar(ft.Text(f"Error deleting: {ex}"), bgcolor=ft.Colors.RED_700)
        self.page.snack_bar.open = True
        self.page.update()

def clear_all_transactions(self, e):
    def confirm_clear(e):
        self.ledger = []
        self.upload_status = "Awaiting CSV file selection..."
        save_ledger(self.ledger)
        self.page.snack_bar = ft.SnackBar(ft.Text("All transactions cleared."), bgcolor=ft.Colors.GREEN_700)
        self.page.snack_bar.open = True
        self.update_view()
        self.page.close(dlg)

    def cancel_clear(e):
        self.page.close(dlg)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirm Clear All"),
        content=ft.Text("Are you sure you want to clear all transactions? This action cannot be undone."),
        actions=[
            ft.TextButton("Cancel", on_click=cancel_clear),
            ft.ElevatedButton("Clear All", on_click=confirm_clear, bgcolor=ft.Colors.RED_700),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    self.page.open(dlg)