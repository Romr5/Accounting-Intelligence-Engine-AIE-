import flet as ft
from decimal import Decimal
from datetime import datetime
import uuid
import csv
import os

# Utility imports from the application context
from aie_helpers import Transaction, COMMON_ACCOUNTS, save_ledger, DATE_RE

# --- DATA ENTRY & UPLOAD VIEWS ---

def add_transaction_view(self):
    def save_transaction(e):
        try:
            if not self.new_desc:
                self.page.snack_bar = ft.SnackBar(ft.Text("Please fill in a description."), bgcolor=ft.Colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()
                return

            if not DATE_RE.match(self.new_date):
                self.page.snack_bar = ft.SnackBar(ft.Text("Invalid date format. Use YYYY-MM-DD."), bgcolor=ft.Colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()
                return

            debit_nonzero = (self.new_debit != Decimal('0.0'))
            credit_nonzero = (self.new_credit != Decimal('0.0'))
            if not (debit_nonzero ^ credit_nonzero):
                self.page.snack_bar = ft.SnackBar(ft.Text("Please enter exactly one amount: either Debit or Credit."), bgcolor=ft.Colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()
                return

            new_t = Transaction(id=str(uuid.uuid4()), date=self.new_date, description=self.new_desc, account=self.new_account, debit=self.new_debit, credit=self.new_credit, source_file="Manual")
            self.ledger.append(new_t)

            save_ledger(self.ledger)

            self.new_date = datetime.now().strftime('%Y-%m-%d')
            self.new_desc = ""
            self.new_account = ""
            self.new_debit = Decimal('0.0')
            self.new_credit = Decimal('0.0')
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Transaction recorded successfully."), bgcolor=ft.Colors.GREEN_700)
            self.page.snack_bar.open = True
            self.current_view = 'Ledger'
            self.update_view()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Error saving: {ex}"), bgcolor=ft.Colors.RED_700)
            self.page.snack_bar.open = True
            self.page.update()

    def handle_amount_change(e, attr_name):
        cleaned_value = e.control.value.replace(' ', '')
        parsed = self.safe_parse_decimal(cleaned_value)
        setattr(self, attr_name, parsed)

        if cleaned_value == "" or parsed == Decimal('0.0'):
            e.control.value = ""
        # Retain the user's input even on invalid parse to avoid clearing on typos
        e.control.update()

    txt_date = ft.TextField(label="Date (YYYY-MM-DD)", value=self.new_date, on_change=lambda e: setattr(self, 'new_date', e.control.value), bgcolor=ft.Colors.BLUE_GREY_700, border_radius=8, color=ft.Colors.WHITE)
    txt_desc = ft.TextField(label="Description", on_change=lambda e: setattr(self, 'new_desc', e.control.value), bgcolor=ft.Colors.BLUE_GREY_700, border_radius=8, color=ft.Colors.WHITE)
    # Auto-complete options: COMMON_ACCOUNTS + unique accounts from ledger (deduplicated)
    account_options = list(set(COMMON_ACCOUNTS) | set(t.account for t in self.ledger))
    txt_account = ft.Row([
        ft.Text("Account", size=12, color=ft.Colors.WHITE70, width=80),
        ft.Container(
            ft.AutoComplete(
                suggestions=[ft.AutoCompleteSuggestion(key=acc, value=acc) for acc in account_options],
                on_select=lambda e: setattr(self, 'new_account', e.selection.value)
            ),
            bgcolor=ft.Colors.BLUE_GREY_700,
            border_radius=8,
            padding=ft.padding.all(8),
            height=48,
            expand=True
        )
    ], spacing=10, alignment=ft.MainAxisAlignment.START)

    txt_debit = ft.TextField(label="Debit Amount", value="" if self.new_debit == Decimal('0.0') else f"{self.new_debit:,.2f}", input_filter=ft.InputFilter(r"[0-9.,]"), on_change=lambda e: handle_amount_change(e, 'new_debit'), bgcolor=ft.Colors.BLUE_GREY_700, border_radius=8, color=ft.Colors.RED_400)
    txt_credit = ft.TextField(label="Credit Amount", value="" if self.new_credit == Decimal('0.0') else f"{self.new_credit:,.2f}", input_filter=ft.InputFilter(r"[0-9.,]"), on_change=lambda e: handle_amount_change(e, 'new_credit'), bgcolor=ft.Colors.BLUE_GREY_700, border_radius=8, color=ft.Colors.GREEN_400)

    return ft.Column([
        ft.Text("Record New Transaction (Manual)", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(ft.Column([ft.ResponsiveRow([ft.Container(txt_date, col={"sm": 6, "md": 3}), ft.Container(txt_account, col={"sm": 6, "md": 3}), ft.Container(txt_debit, col={"sm": 6, "md": 3}), ft.Container(txt_credit, col={"sm": 6, "md": 3})], spacing=15), ft.ResponsiveRow([ft.Container(txt_desc, col={"sm": 12, "md": 9}), ft.Container(ft.ElevatedButton(content=ft.Row([ft.Icon(ft.Icons.SAVE), ft.Text("Save Transaction")], spacing=5), on_click=save_transaction, bgcolor=ft.Colors.BLUE_ACCENT_700, color=ft.Colors.WHITE, height=48), col={"sm": 12, "md": 3}, alignment=ft.alignment.center_right)], spacing=15)], spacing=20), padding=30, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10)], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

def upload_data_view(self):
    instruction_text = ft.Text("Upload a CSV or XLSX file containing transaction data. The file must include columns: Date (YYYY-MM-DD), Description, Account, Debit, Credit. Data will be validated for double-entry rules before upload.", color=ft.Colors.WHITE70, size=14)
    upload_button = ft.ElevatedButton("Select and Upload File", icon=ft.Icons.FILE_UPLOAD_ROUNDED, on_click=lambda e: self.file_picker.pick_files(allow_multiple=False, allowed_extensions=['csv', 'xlsx']), bgcolor=ft.Colors.BLUE_ACCENT_700, color=ft.Colors.WHITE, height=48)

    status_color = ft.Colors.RED_400 if "error" in self.upload_status.lower() or "failure" in self.upload_status.lower() or "validation errors" in self.upload_status.lower() or "missing" in self.upload_status.lower() else ft.Colors.GREEN_400

    return ft.Column([ft.Text("Upload Transaction Data (File Import)", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE), ft.Container(height=20), ft.Container(ft.Column([instruction_text, upload_button, ft.Text(self.upload_status, color=status_color, weight=ft.FontWeight.BOLD)], spacing=20), padding=30, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10)], scroll=ft.ScrollMode.ADAPTIVE, expand=True)