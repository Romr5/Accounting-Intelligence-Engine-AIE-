import flet as ft
from decimal import Decimal
from typing import List
import traceback

# Utility imports from the application context
# NOTE: These are imported globally as they are needed by the views (via the mixin class)
# We assume necessary imports from aie_helpers and aie_logic are handled by the main app structure
from aie_helpers import Transaction
from aie_logic import perform_aie_analysis, calculate_balances

# --- UTILITY WIDGETS (Moved from original aie_views_content.py) ---

def create_stat_card(self, title, value, icon, color):
    """Creates a standardized stat card for the dashboard."""
    return ft.Card(
        content=ft.Container(
            bgcolor=ft.Colors.BLUE_GREY_800,
            padding=15,
            content=ft.Column([
                ft.Row([ft.Icon(icon, color=color, size=30), ft.Text(title, size=14, color=ft.Colors.WHITE70)], alignment=ft.MainAxisAlignment.START, spacing=10),
                ft.Text(f"{value}", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
            ], spacing=8),
        ),
        elevation=5,
    )

def create_balance_card(self, title, value):
    """Creates a standardized balance card for reports and diagnostics."""
    is_positive = value >= Decimal('0.0')
    value_text = f"${value:,.2f}"
    color = ft.Colors.GREEN_ACCENT_400 if is_positive else ft.Colors.RED_400
    icon = ft.Icons.TRENDING_UP if is_positive else ft.Icons.TRENDING_DOWN

    return ft.Card(
        content=ft.Container(
            bgcolor=ft.Colors.BLUE_GREY_800,
            padding=12,
            content=ft.Column([
                ft.Text(title, size=12, color=ft.Colors.WHITE70),
                ft.Row([ft.Text(value_text, size=18, weight=ft.FontWeight.W_600, color=color), ft.Icon(icon, color=color, size=20)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=5),
        ),
        elevation=3
    )

# --- CORE VIEWS ---

def dashboard_view(self, analysis_data, balances):
    analyzed, error_count, anomaly_count, total_count, health_score = analysis_data

    health_color = ft.Colors.GREEN_ACCENT_700
    if health_score < 75: health_color = ft.Colors.YELLOW_ACCENT_700
    if health_score < 50: health_color = ft.Colors.RED_ACCENT_700

    health_ring = ft.Container(
        content=ft.Column([
            ft.Text("Financial Health Score", size=16, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
            ft.ProgressRing(value=health_score / 100, width=150, height=150, stroke_width=10, color=health_color, bgcolor=ft.Colors.WHITE10),
            ft.Text(f"{health_score}%", size=28, weight=ft.FontWeight.BOLD, color=health_color),
            ft.Text("Validated by AIE Rules", size=12, color=ft.Colors.WHITE54),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
        alignment=ft.alignment.center,
        padding=30
    )

    stat_cards = ft.Row(
        [self.create_stat_card("Errors Found", error_count, ft.Icons.DANGEROUS, ft.Colors.RED_400),
         self.create_stat_card("Anomalies", anomaly_count, ft.Icons.WARNING_AMBER_ROUNDED, ft.Colors.YELLOW_400),
         self.create_stat_card("Total Entries", total_count, ft.Icons.RECEIPT, ft.Colors.BLUE_400)],
        wrap=True, spacing=20, alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    
    # Filter balances to only include key aggregates and top 4 non-aggregate accounts for a cleaner dashboard view
    key_aggregates = {k: v for k, v in balances.items() if k in ['Total Assets', 'Total Liabilities', 'Total Equity', 'Net Income']}
    non_aggregates = {k: v for k, v in balances.items() if k not in key_aggregates and k not in ['Total Assets', 'Total Liabilities', 'Total Equity', 'Net Income']}
    sorted_non_aggregates = dict(sorted(non_aggregates.items(), key=lambda item: abs(item[1]), reverse=True)[:4])
    final_balances = {**key_aggregates, **sorted_non_aggregates}


    balance_cards = ft.Column(
        [ft.Text("Key Financial Positions", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
         ft.ResponsiveRow([ft.Container(self.create_balance_card(key, value), col={"sm": 6, "md": 4, "lg": 3}) for key, value in final_balances.items()], spacing=15)],
        spacing=15
    )

    # Transaction Balancing Check (excluding 'Error' transactions)
    valid_transactions = [t for t in analyzed if t.status != 'Error']
    total_debits = sum(t.debit for t in valid_transactions)
    total_credits = sum(t.credit for t in valid_transactions)
    difference = total_debits - total_credits
    balancing_check = ft.Container(
        ft.Text(f"Balancing Check (excluding errors): Total Debits = ${total_debits:,.2f}, Total Credits = ${total_credits:,.2f}, Difference = ${difference:,.2f}", size=14, color=ft.Colors.GREEN_400 if abs(difference) < Decimal('0.01') else ft.Colors.RED_400),
        padding=20, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10
    )

    return ft.Column(
        [ft.Text("AIE Dashboard Overview", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
         ft.Container(height=20),
         ft.ResponsiveRow([ft.Container(health_ring, col={"lg": 4}, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10, padding=0), ft.Container(stat_cards, col={"lg": 8}, padding=0)], spacing=20),
         ft.Container(balance_cards, padding=20, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10),
         ft.Container(height=20),
         balancing_check],
        scroll=ft.ScrollMode.ADAPTIVE, expand=True,
    )

def ledger_view(self, analyzed_transactions: List[Transaction]):
    def get_status_control(status, errors):
        color = ft.Colors.GREEN_600
        text = "Valid"
        if status == 'Error':
            color = ft.Colors.RED_600
            text = "Error"
        elif status == 'Anomaly':
            color = ft.Colors.YELLOW_600
            text = "Anomaly"
        return ft.Container(ft.Text(text, size=10, weight=ft.FontWeight.BOLD), padding=ft.padding.only(left=8, right=8, top=4, bottom=4), border_radius=5, bgcolor=color)

    data_rows = [ft.DataRow(cells=[
                ft.DataCell(ft.Text(t.date, size=12)),
                ft.DataCell(ft.Text(t.description, size=12)),
                ft.DataCell(ft.Text(t.account, size=12, color=ft.Colors.CYAN_ACCENT_100)),
                ft.DataCell(ft.Text(f"${t.debit:,.2f}", size=12, color=ft.Colors.RED_400)),
                ft.DataCell(ft.Text(f"${t.credit:,.2f}", size=12, color=ft.Colors.GREEN_400)),
                ft.DataCell(get_status_control(t.status, t.errors)),
                ft.DataCell(ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_color=ft.Colors.RED_400, tooltip="Delete Entry", on_click=self.delete_transaction, data=t.id)),
            ], color={"hovered": ft.Colors.BLUE_GREY_700}) for t in analyzed_transactions]

    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Date", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Description", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Account", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Debit", weight=ft.FontWeight.W_600), numeric=True),
            ft.DataColumn(ft.Text("Credit", weight=ft.FontWeight.W_600), numeric=True),
            ft.DataColumn(ft.Text("AIE Status", weight=ft.FontWeight.W_600)),
            ft.DataColumn(ft.Text("Actions", weight=ft.FontWeight.W_600)),
        ],
        rows=data_rows,
        bgcolor=ft.Colors.BLUE_GREY_800,
        border_radius=10,
        sort_column_index=0,
        sort_ascending=False,
        heading_row_color=ft.Colors.BLUE_GREY_700,
        heading_row_height=40,
    )

    download_buttons = ft.Row([
        ft.ElevatedButton(
            content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD), ft.Text("Download All as CSV")], spacing=5),
            on_click=self.download_all_csv,
            bgcolor=ft.Colors.BLUE_ACCENT_700,
            color=ft.Colors.WHITE,
            height=48
        ),
        ft.ElevatedButton(
            content=ft.Row([ft.Icon(ft.Icons.DOWNLOAD_FOR_OFFLINE), ft.Text("Download by Source")], spacing=5),
            on_click=self.show_source_selection_dialog,
            bgcolor=ft.Colors.GREEN_ACCENT_700,
            color=ft.Colors.WHITE,
            height=48
        )
    ], spacing=10)

    clear_all_button = ft.ElevatedButton(
        content=ft.Row([ft.Icon(ft.Icons.CLEAR_ALL), ft.Text("Clear All Transactions")], spacing=5),
        on_click=self.clear_all_transactions,
        bgcolor=ft.Colors.RED_ACCENT_700,
        color=ft.Colors.WHITE,
        height=48
    )

    return ft.Column([
        ft.Text("AIE Ledger & Validation", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(height=10),
        ft.Container(ft.Row([download_buttons, ft.Container(expand=True), clear_all_button], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), alignment=ft.alignment.center_right),
        ft.Container(height=10),
        ft.Container(data_table, expand=True, padding=20, border_radius=10, bgcolor=ft.Colors.BLUE_GREY_800)
    ], scroll=ft.ScrollMode.ADAPTIVE, expand=True)

def diagnostic_view(self, analyzed_transactions: List[Transaction], simulation_results):
    errors_and_anomalies = [t for t in analyzed_transactions if t.status != 'Valid']

    def make_click_handler(tid: str):
        def handler(e):
            self.selected_transaction = next((t for t in analyzed_transactions if t.id == tid), None)
            if not self.selected_transaction:
                self.page.snack_bar = ft.SnackBar(ft.Text("Selected transaction not found."), bgcolor=ft.Colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()
                return

            first_error_text = self.selected_transaction.errors[0] if self.selected_transaction.errors else "No details available."

            if "date" in first_error_text.lower() or "invalid date format" in first_error_text.lower():
                self.open_date_correction_panel(tid, analyzed_transactions)
            else:
                self.open_amount_correction_panel(tid, analyzed_transactions)
        return handler

    issue_list = ft.Container(
        content=ft.Column(
            [ft.Text("Detected Issues", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
             ft.Container(height=1, bgcolor=ft.Colors.WHITE10)] +
            ([ft.ListTile(
                title=ft.Text(f"{t.description} ({t.account})", size=14, weight=ft.FontWeight.W_500),
                subtitle=ft.Text(t.errors[0] if t.errors else "No details", size=12, color=ft.Colors.WHITE54),
                trailing=ft.IconButton(ft.Icons.ARROW_FORWARD, on_click=make_click_handler(t.id), tooltip="Open simulation", icon_color=ft.Colors.WHITE),
                on_click=make_click_handler(t.id),
                data=t.id,
                bgcolor=ft.Colors.RED_900 if t.status == 'Error' else ft.Colors.YELLOW_900,
                shape=ft.RoundedRectangleBorder(radius=ft.border_radius.all(8)),
            ) for t in errors_and_anomalies]) if errors_and_anomalies else [ft.Container(content=ft.Text("No critical issues detected. Financials are clean.", color=ft.Colors.GREEN_400, italic=True), padding=ft.padding.all(10))],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=20,
        bgcolor=ft.Colors.BLUE_GREY_800,
        border_radius=10,
        height=400,
    )

    simulation_cards = ft.Column([
        ft.Text("Simulated Balance Impact", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
        ft.Text("Select an issue to apply hypothetical corrections and see the new balances.", size=12, color=ft.Colors.WHITE54),
        ft.ResponsiveRow([ft.Container(self.create_balance_card(key, value), col={"sm": 6, "md": 4, "lg": 3}) for key, value in simulation_results.items()], spacing=15)
    ], spacing=15)

    if self.simulation_active and self.selected_transaction:
        panel_fields = []
        if self.correction_type == 'date':
            txt_date = ft.TextField(label="New Date (YYYY-MM-DD)", value=self.temp_date, on_change=lambda e: setattr(self, 'temp_date', e.control.value), bgcolor=ft.Colors.BLUE_GREY_700, border_radius=8, color=ft.Colors.WHITE)
            panel_fields.append(ft.Container(txt_date, expand=True))
        else:
            txt_debit = ft.TextField(label="New Debit Value", value="" if self.temp_debit == Decimal('0.0') else f"{self.temp_debit:,.2f}", on_change=lambda e: self.handle_temp_amount_change(e, 'temp_debit'), bgcolor=ft.Colors.BLUE_GREY_700, border_radius=8, color=ft.Colors.WHITE)
            txt_credit = ft.TextField(label="New Credit Value", value="" if self.temp_credit == Decimal('0.0') else f"{self.temp_credit:,.2f}", on_change=lambda e: self.handle_temp_amount_change(e, 'temp_credit'), bgcolor=ft.Colors.BLUE_GREY_700, border_radius=8, color=ft.Colors.WHITE)
            panel_fields.append(ft.Row([ft.Container(txt_debit, expand=True), ft.Container(txt_credit, expand=True)], spacing=10))

        balances_sim = calculate_balances(self.diagnostic_entries)
        sim_balances = {**balances_sim['balances'], **balances_sim['aggregates']}

        inpage_panel = ft.Container(
            ft.Column([
                ft.Text("Simulation Panel (in-page)", size=18, weight=ft.FontWeight.W_600, color=ft.Colors.WHITE),
                ft.Text(f"Entry: {self.selected_transaction.description} ({self.selected_transaction.account})", size=14, color=ft.Colors.WHITE70),
                ft.Text(f"Issue: {self.selected_transaction.errors[0] if self.selected_transaction.errors else 'No details'}", size=12, color=ft.Colors.YELLOW_300),
            ] + panel_fields + [
                ft.Row([
                    ft.ElevatedButton("Apply Simulation", on_click=self.apply_simulation_panel, bgcolor=ft.Colors.YELLOW_ACCENT_700),
                    ft.ElevatedButton("Commit Correction", on_click=self.commit_simulation_panel, bgcolor=ft.Colors.GREEN_ACCENT_700),
                    ft.TextButton("Close", on_click=lambda e: self.close_simulation_panel()),
                ], alignment=ft.MainAxisAlignment.END, spacing=12),
                ft.Container(height=20),
                ft.Text("Simulated Balances (after applying)", size=14, color=ft.Colors.WHITE70),
                ft.ResponsiveRow([ft.Container(self.create_balance_card(key, value), col={"sm": 6, "md": 4, "lg": 3}) for key, value in sim_balances.items()], spacing=12)
            ], spacing=12),
            padding=20, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10,
        )

        right_column = ft.Container(inpage_panel, col={"lg": 8}, padding=0)
    else:
        # Added col={"lg": 8} and expand=True here for proper layout when panel is closed
        right_column = ft.Container(simulation_cards, col={"lg": 8}, padding=20, bgcolor=ft.Colors.BLUE_GREY_800, border_radius=10, expand=True)

    return ft.Column([
        ft.Text("AIE Diagnostic & Simulation Engine", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
        ft.Container(height=20),
        ft.ResponsiveRow([ft.Container(issue_list, col={"lg": 4}, padding=0), right_column], spacing=20)
    ], scroll=ft.ScrollMode.ADAPTIVE, expand=True)