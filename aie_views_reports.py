import flet as ft
from decimal import Decimal
import json
import os
import subprocess

# Utility imports from the application context
from aie_helpers import ACCOUNT_TYPES, save_ledger

# --- REPORTS & SETTINGS VIEWS ---

def reports_view(self, balances):
    # Balance Sheet
    # Only list individual accounts, not the aggregate total itself
    individual_assets = {k: v for k, v in balances.items() if k in ACCOUNT_TYPES.get('ASSET', [])}
    individual_liabilities = {k: v for k, v in balances.items() if k in ACCOUNT_TYPES.get('LIABILITY', [])}
    individual_equity = {k: v for k, v in balances.items() if k in ACCOUNT_TYPES.get('EQUITY', [])}

    total_debits = sum(t.debit for t in self.ledger)
    total_credits = sum(t.credit for t in self.ledger)
    difference = total_debits - total_credits

    total_l_plus_e = balances.get('Total Liabilities', 0) + balances.get('Total Equity', 0) + balances.get('Net Income', 0)
    balance_check_color = ft.Colors.GREEN_400 if abs(balances.get('Total Assets', 0) - total_l_plus_e) < Decimal('0.01') else ft.Colors.RED_400
    balancing_color = ft.Colors.GREEN_400 if abs(difference) < Decimal('0.01') else ft.Colors.RED_400

    balance_sheet = ft.Column([
        ft.Text("Balance Sheet", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(height=10),
        ft.Row([
            ft.Container(
                ft.Column([
                    ft.Text("Assets", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.GREEN_ACCENT_400),
                    *[ft.Text(f"{k}: ${v:,.2f}", size=14, color=ft.Colors.WHITE70) for k, v in individual_assets.items()],
                ], spacing=5),
                expand=True
            ),
            ft.Container(
                ft.Column([
                    ft.Text("Liabilities", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.RED_ACCENT_400),
                    *[ft.Text(f"{k}: ${v:,.2f}", size=14, color=ft.Colors.WHITE70) for k, v in individual_liabilities.items()],
                ], spacing=5),
                expand=True
            ),
            ft.Container(
                ft.Column([
                    ft.Text("Equity", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.BLUE_ACCENT_400),
                    *[ft.Text(f"{k}: ${v:,.2f}", size=14, color=ft.Colors.WHITE70) for k, v in individual_equity.items()],
                ], spacing=5),
                expand=True
            ),
        ], spacing=20),
        ft.Container(height=20),
        ft.Text(f"Balance Check: Assets = Liabilities + Equity (plus Net Income): ${balances.get('Total Assets', 0):,.2f} = ${total_l_plus_e:,.2f}", size=14, color=balance_check_color),
        ft.Container(height=10),
        ft.Text(f"Transaction Balancing Check (all transactions): Total Debits = ${total_debits:,.2f}, Total Credits = ${total_credits:,.2f}, Difference = ${difference:,.2f}", size=14, color=balancing_color),
    ], spacing=10)

    # Income Statement
    revenue = {k: v for k, v in balances.items() if k in ACCOUNT_TYPES.get('REVENUE', [])}
    expenses = {k: v for k, v in balances.items() if k in ACCOUNT_TYPES.get('EXPENSE', []) or k.startswith('Net Income')}

    income_statement = ft.Column([
        ft.Text("Income Statement", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(height=10),
        ft.Column([
            ft.Text("Revenue", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.GREEN_ACCENT_400),
            *[ft.Text(f"{k}: ${v:,.2f}", size=14, color=ft.Colors.WHITE70) for k, v in revenue.items()],
            ft.Container(height=10),
            ft.Text("Expenses", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.RED_ACCENT_400),
            *[ft.Text(f"{k}: ${v:,.2f}", size=14, color=ft.Colors.WHITE70) for k, v in expenses.items() if not k.startswith('Net Income')],
            ft.Container(height=10),
            ft.Text(f"Net Income: ${balances.get('Net Income', 0):,.2f}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT_400),
        ], spacing=5),
    ], spacing=10)

    # T-Account Visualization (simplified, click account in Ledger for full view)
    all_classified_accounts = set(sum(ACCOUNT_TYPES.values(), []))
    t_accounts = ft.Column([
        ft.Text("T-Account Overview (Click account in Ledger for details)", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
        ft.Container(height=10),
        ft.ResponsiveRow([ft.Container(self.create_balance_card(key, value), col={"sm": 6, "md": 4, "lg": 3}) for key, value in balances.items() if key not in all_classified_accounts and key not in ['Total Assets', 'Total Liabilities', 'Total Equity', 'Net Income']], spacing=15),
    ], spacing=10)

    return ft.Column([
        ft.Text("AIE Financial Reports", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(height=20),
        ft.Container(balance_sheet, padding=20, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10),
        ft.Container(height=20),
        ft.Container(income_statement, padding=20, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10),
        ft.Container(height=20),
        ft.Container(t_accounts, padding=20, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10),
    ], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

def coa_view(self, balances):
    coa_data = []
    for category, accounts in ACCOUNT_TYPES.items():
        for account in accounts:
            balance = balances.get(account, Decimal('0.0'))
            if balance != Decimal('0.0'):
                coa_data.append({"Account": account, "Type": category, "Balance": balance})

    all_classified_accounts = set(sum(ACCOUNT_TYPES.values(), []))
    custom_accounts = {k: v for k, v in balances.items()
                       if k not in all_classified_accounts and not k.startswith('Total')}

    for account, balance in custom_accounts.items():
        if balance != Decimal('0.0'):
            coa_data.append({"Account": account, "Type": "Custom/Unclassified", "Balance": balance})

    data_rows = [ft.DataRow(cells=[
        ft.DataCell(ft.Text(row["Account"], size=12)),
        ft.DataCell(ft.Text(row["Type"], size=12)),
        ft.DataCell(ft.Text(f"${row['Balance']:,.2f}", size=12)),
    ]) for row in coa_data]

    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Account", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Type", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Balance", weight=ft.FontWeight.W_600), numeric=True),
        ],
        rows=data_rows,
        bgcolor=ft.Colors.BLUE_GREY_800,
        border_radius=10,
        heading_row_color=ft.Colors.BLUE_GREY_700,
        heading_row_height=40,
    )

    return ft.Column([
        ft.Text("Chart of Accounts (COA)", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(height=10),
        ft.Container(data_table, expand=True, padding=20, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800)
    ], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

def settings_view(self):
    def toggle_theme(e):
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = ft.Colors.WHITE
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = ft.Colors.BLUE_GREY_900
        self.page.update()

    def clear_data(e):
        def confirm_clear(e):
            self.ledger = []
            self.upload_status = "Awaiting CSV file selection..."
            save_ledger(self.ledger)
            self.page.snack_bar = ft.SnackBar(ft.Text("All data cleared."), bgcolor=ft.Colors.GREEN_700)
            self.page.snack_bar.open = True
            self.update_view()
            self.page.close(dlg)

        def cancel_clear(e):
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Clear All Data"),
            content=ft.Text("Are you sure you want to clear all transactions and data? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_clear),
                ft.ElevatedButton("Clear All", on_click=confirm_clear, bgcolor=ft.Colors.RED_700),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    def export_data(e):
        try:
            from pathlib import Path
            
            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(exist_ok=True)
            export_path = downloads_dir / "aie_settings_backup.json"
            import json
            data = {
                "ledger": [t.__dict__ for t in self.ledger],
                "theme_mode": self.page.theme_mode.value,
            }
            # Manually convert Decimal objects in the ledger to strings for JSON
            json_serializable_data = data.copy()
            json_serializable_data["ledger"] = []
            for t_dict in data["ledger"]:
                t_dict['debit'] = str(t_dict['debit'])
                t_dict['credit'] = str(t_dict['credit'])
                json_serializable_data["ledger"].append(t_dict)


            with open(export_path, 'w') as f:
                json.dump(json_serializable_data, f, indent=4)

            self.page.snack_bar = ft.SnackBar(ft.Text(f"Settings exported to {export_path}"), bgcolor=ft.Colors.GREEN_700)
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Export failed: {ex}"), bgcolor=ft.Colors.RED_700)
            self.page.snack_bar.open = True
            self.page.update()

    theme_toggle = ft.Switch(label="Light Mode", value=self.page.theme_mode == ft.ThemeMode.LIGHT, on_change=toggle_theme)

    return ft.Column([
        ft.Text("Settings", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(height=20),
        ft.Container(
            ft.Column([
                ft.Text("Appearance", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                theme_toggle,
                ft.Container(height=20),
                ft.Text("Data Management", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                ft.ElevatedButton("Clear All Data", on_click=clear_data, bgcolor=ft.Colors.RED_ACCENT_700, color=ft.Colors.WHITE),
                ft.ElevatedButton("Export Settings & Data", on_click=export_data, bgcolor=ft.Colors.BLUE_ACCENT_700, color=ft.Colors.WHITE),
            ], spacing=15),
            padding=30, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10
        )
    ], scroll=ft.ScrollMode.ADAPTIVE, expand=True)