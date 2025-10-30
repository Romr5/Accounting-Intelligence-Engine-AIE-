import flet as ft
from decimal import Decimal, InvalidOperation
from datetime import datetime
import uuid
import re
import os
import csv
import traceback
from typing import Union

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

# Import functions/constants from helpers and logic
from aie_helpers import Transaction, COMMON_ACCOUNTS, save_ledger, load_ledger, DATE_RE
from aie_logic import perform_aie_analysis, calculate_balances

# Import view components from the new views content file
from aie_views_content import get_views_mixins

# Mixin the view-generating methods into the AIEApp class
class AIEApp(ft.Column, get_views_mixins()):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.page = page

        # --- STATE MANAGEMENT ---
        persisted = load_ledger()
        self.ledger = persisted if persisted else []
        self.current_view = 'Dashboard'
        self.diagnostic_entries = self.ledger
        self.upload_status = "Awaiting CSV file selection..."

        # State for new manual entry form
        self.new_date = datetime.now().strftime('%Y-%m-%d')
        self.new_desc = ""
        self.new_account = ""
        self.new_debit = Decimal('0.0')
        self.new_credit = Decimal('0.0')

        # State for Diagnostics Simulation Panel
        self.simulation_active = False
        self.selected_transaction = None
        self.temp_debit = Decimal('0.0')
        self.temp_credit = Decimal('0.0')
        self.correction_type = None
        self.temp_date = ""

        # --- FLET CONFIGURATION ---
        self.page.title = "Accounting Intelligence Engine (AIE)"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.vertical_alignment = ft.CrossAxisAlignment.START
        self.page.horizontal_alignment = ft.CrossAxisAlignment.START
        self.page.bgcolor = ft.Colors.BLUE_GREY_900

        self.file_picker = ft.FilePicker(on_result=self.pick_files_result)
        self.page.overlay.append(self.file_picker)

        # --- UI LAYOUT ---
        self.nav_rail = self._create_nav_rail()
        self.main_content_container = self._create_main_content_container()

        self.controls.append(ft.Row(
            [
                self.nav_rail,
                ft.VerticalDivider(width=1, color=ft.Colors.WHITE10),
                self.main_content_container
            ],
            expand=True,
        ))

    # --- Core Utility Methods (Stays here for state access) ---

    def safe_parse_decimal(self, text: Union[str, Decimal, None]) -> Decimal:
        if isinstance(text, Decimal): return text
        if text is None: return Decimal('0.0')
        txt = str(text).replace(',', '').strip()
        if not txt: return Decimal('0.0')
        try: return Decimal(txt)
        except InvalidOperation: return Decimal('0.0')

    def get_analysis_data(self, transactions=None):
        if transactions is None:
            transactions = self.diagnostic_entries if self.current_view == 'Diagnostics' else self.ledger
        analyzed = perform_aie_analysis(transactions)
        error_count = sum(1 for t in analyzed if t.status == 'Error')
        anomaly_count = sum(1 for t in analyzed if t.status == 'Anomaly')
        total_count = len(transactions)
        deduction = min(100, (error_count * 10) + (anomaly_count * 5))
        health_score = max(0, 100 - deduction)
        return analyzed, error_count, anomaly_count, total_count, health_score

    # --- UI Layout Helpers ---

    def _create_main_content_container(self):
        return ft.Container(
            padding=30,
            expand=True,
            content=ft.Column([], expand=True),
        )

    def _create_nav_rail(self):
        return ft.NavigationRail(
            selected_index={"Dashboard": 0, "Add": 1, "Upload": 2, "Ledger": 3, "Reports": 4, "COA": 5, "Diagnostics": 6, "Settings": 7}.get(self.current_view, 0),
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=120,
            min_extended_width=200,
            leading=ft.Container(
                content=ft.Column([
                    ft.Text("AIE", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_ACCENT_400),
                    ft.Text("Intelligence Engine", size=10, color=ft.Colors.WHITE54)
                ], horizontal_alignment=ft.CrossAxisAlignment.START, spacing=2),
                padding=ft.padding.only(bottom=20, top=10)
            ),
            group_alignment=-0.9,
            destinations=[
                ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_ROUNDED, selected_icon=ft.Icons.DASHBOARD_OUTLINED, label="Dashboard"),
                ft.NavigationRailDestination(icon=ft.Icons.ADD_BOX_OUTLINED, selected_icon=ft.Icons.ADD_BOX_ROUNDED, label="Add Entry"),
                ft.NavigationRailDestination(icon=ft.Icons.UPLOAD_FILE_ROUNDED, selected_icon=ft.Icons.UPLOAD_FILE_OUTLINED, label="Upload Data"),
                ft.NavigationRailDestination(icon=ft.Icons.VIEW_LIST_ROUNDED, selected_icon=ft.Icons.VIEW_LIST_OUTLINED, label="Ledger"),
                ft.NavigationRailDestination(icon=ft.Icons.ASSESSMENT_ROUNDED, selected_icon=ft.Icons.ASSESSMENT_OUTLINED, label="Reports"),
                ft.NavigationRailDestination(icon=ft.Icons.ACCOUNT_TREE_ROUNDED, selected_icon=ft.Icons.ACCOUNT_TREE_OUTLINED, label="COA"),
                ft.NavigationRailDestination(icon=ft.Icons.HEALTH_AND_SAFETY_ROUNDED, selected_icon=ft.Icons.HEALTH_AND_SAFETY_OUTLINED, label="Diagnostics"),
                ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_ROUNDED, selected_icon=ft.Icons.SETTINGS_OUTLINED, label="Settings"),
            ],
            on_change=self.change_view,
            bgcolor=ft.Colors.BLUE_GREY_900,
        )

    # --- Control Flow / Router Methods ---

    def change_view(self, e):
        view_map = {
            0: 'Dashboard',
            1: 'Add',
            2: 'Upload',
            3: 'Ledger',
            4: 'Reports',
            5: 'COA',
            6: 'Diagnostics',
            7: 'Settings'
        }
        self.current_view = view_map.get(e.control.selected_index, 'Dashboard')
        self.simulation_active = False
        self.diagnostic_entries = self.ledger
        self.update_view()

    def get_current_view_content(self, analysis_data, balances):
        if self.current_view == 'Dashboard': return self.dashboard_view(analysis_data, balances)
        if self.current_view == 'Add': return self.add_transaction_view()
        if self.current_view == 'Upload': return self.upload_data_view()
        if self.current_view == 'Ledger': return self.ledger_view(analysis_data[0])
        if self.current_view == 'Reports': return self.reports_view(balances)
        if self.current_view == 'COA': return self.coa_view(balances)
        if self.current_view == 'Diagnostics': return self.diagnostic_view(analysis_data[0], balances)
        if self.current_view == 'Settings': return self.settings_view()
        return ft.Text("View not found.")

    def update_view(self):
        transactions_to_analyze = self.diagnostic_entries if self.current_view == 'Diagnostics' else self.ledger
        analysis_data = self.get_analysis_data(transactions_to_analyze)
        balances_result = calculate_balances(transactions_to_analyze)
        balances = {**balances_result['balances'], **balances_result['aggregates']}
        new_content = self.get_current_view_content(analysis_data, balances)
        self.main_content_container.content.controls.clear()
        self.main_content_container.content.controls.append(new_content)
        self.update()

    # --- Methods moved from old aie_views.py to aie_views_content.py are now accessible via Mixin ---

    # --- File/Data Handlers (Keep here for direct state/page access) ---

    def pick_files_result(self, e: ft.FilePickerResultEvent):
        if not e.files:
            self.upload_status = "Upload cancelled."
            self.update_view()
            return

        file_entry = e.files[0]
        file_path = getattr(file_entry, "path", None)
        if not file_path:
            self.upload_status = "File path not accessible. Please select a local file."
            self.update_view()
            return

        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in ['.csv', '.xlsx']:
            self.upload_status = "Unsupported file type. Only CSV and XLSX files are supported."
            self.update_view()
            return

        new_transactions = []
        parsed_count = 0
        error_count = 0

        try:
            if file_ext == '.csv':
                with open(file_path, mode='r', encoding='utf-8') as fobj:
                    reader = csv.reader(fobj)
                    rows = list(reader)
            elif file_ext == '.xlsx':
                if not OPENPYXL_AVAILABLE:
                    self.upload_status = "XLSX support not available. Please install openpyxl: pip install openpyxl"
                    self.update_view()
                    return
                wb = openpyxl.load_workbook(file_path, data_only=True)
                ws = wb.active
                rows = [[str(cell.value) if cell.value is not None else "" for cell in row] for row in ws.iter_rows()]

            if not rows:
                self.upload_status = "File is empty."
                self.update_view()
                return

            # Read headers from first row
            headers = [h.strip().lower() for h in rows[0]]
            required_cols = ['date', 'description', 'account', 'debit', 'credit']
            missing_cols = [col for col in required_cols if col not in headers]
            if missing_cols:
                self.upload_status = f"Missing required columns: {', '.join(missing_cols)}. File must include: Date, Description, Account, Debit, Credit."
                self.update_view()
                return

            # Map column indices
            col_indices = {col: headers.index(col) for col in required_cols}

            # Process data rows
            for i, row in enumerate(rows[1:], start=2):  # Start from row 2 (1-indexed)
                if not row or all(cell.strip() == "" for cell in row):
                    continue
                
                # Default values for error logging in case of partial row reading
                current_date = "N/A"
                current_description = "N/A"
                current_account = "Unclassified"

                try:
                    date = row[col_indices['date']].strip()
                    description = row[col_indices['description']].strip()
                    account = row[col_indices['account']].strip()
                    debit_str = row[col_indices['debit']].strip()
                    credit_str = row[col_indices['credit']].strip()
                    
                    current_date = date
                    current_description = description or "No description"
                    current_account = account or "Unclassified"

                    # Parse amounts BEFORE validation checks that use them
                    debit = self.safe_parse_decimal(debit_str)
                    credit = self.safe_parse_decimal(credit_str)

                    # Pre-upload validation: Date format
                    if not DATE_RE.match(date):
                        error_count += 1
                        # Use the invalid date from the file in the error transaction, retain original amounts for diagnosis
                        new_t = Transaction(id=str(uuid.uuid4()), date=current_date, description=current_description, account=current_account, debit=debit, credit=credit, status='Error', errors=['Invalid date format (must be YYYY-MM-DD).'], source_file=os.path.basename(file_path))
                        new_transactions.append(new_t)
                        continue

                    # Pre-upload validation: Negative amounts
                    if debit < Decimal('0') or credit < Decimal('0'):
                        error_count += 1
                        new_t = Transaction(id=str(uuid.uuid4()), date=current_date, description=current_description, account=current_account, debit=debit, credit=credit, status='Error', errors=['Negative amounts are not allowed.'], source_file=os.path.basename(file_path))
                        new_transactions.append(new_t)
                        continue

                    # Pre-upload validation: Double-entry rules
                    if debit > Decimal('0') and credit > Decimal('0'):
                        error_count += 1
                        new_t = Transaction(id=str(uuid.uuid4()), date=current_date, description=current_description, account=current_account, debit=debit, credit=credit, status='Error', errors=['Both debit and credit are populated; one side must be zero.'], source_file=os.path.basename(file_path))
                        new_transactions.append(new_t)
                        continue

                    if debit == Decimal('0') and credit == Decimal('0'):
                        error_count += 1
                        new_t = Transaction(id=str(uuid.uuid4()), date=current_date, description=current_description, account=current_account, debit=debit, credit=credit, status='Error', errors=['Debit and credit fields are both empty.'], source_file=os.path.basename(file_path))
                        new_transactions.append(new_t)
                        continue

                    parsed_count += 1
                    new_transactions.append(Transaction(id=str(uuid.uuid4()), date=date, description=description, account=account, debit=debit, credit=credit, source_file=os.path.basename(file_path)))

                except IndexError:
                    error_count += 1
                    # Log data sample to help diagnose insufficient columns error
                    row_data = ", ".join(row) if row else "Empty Row"
                    date_for_log = row[col_indices['date']].strip() if len(row) > col_indices.get('date', 0) else "N/A"
                    new_t = Transaction(id=str(uuid.uuid4()), date=date_for_log, description=f"Row parsing error: Insufficient columns.", account="Unclassified", debit=Decimal('0.0'), credit=Decimal('0.0'), status='Error', errors=[f"Row {i} has insufficient columns. Data sample: {row_data[:50]}..."], source_file=os.path.basename(file_path))
                    new_transactions.append(new_t)
                except Exception as row_ex:
                    error_count += 1
                    # Log data sample to help diagnose general row error
                    row_data = ", ".join(row) if row else "Empty Row"
                    date_for_log = row[col_indices['date']].strip() if len(row) > col_indices.get('date', 0) else "N/A"
                    new_t = Transaction(id=str(uuid.uuid4()), date=date_for_log, description=f"Row parsing error: {type(row_ex).__name__}", account="Unclassified", debit=Decimal('0.0'), credit=Decimal('0.0'), status='Error', errors=[f"Row {i} error: {str(row_ex)}. Data sample: {row_data[:50]}..."], source_file=os.path.basename(file_path))
                    new_transactions.append(new_t)

            if new_transactions:
                self.ledger.extend(new_transactions)
                save_ledger(self.ledger)
                self.upload_status = f"Successfully loaded {parsed_count} entries. {error_count} entries recorded with validation errors."
                self.current_view = 'Ledger'
            else:
                self.upload_status = "File processed, but no valid transactions were found."

        except Exception as ex:
            self.upload_status = f"File processing failure: {type(ex).__name__}: {ex}"

        self.update_view()

    def download_all_csv(self, e):
        try:
            from pathlib import Path
            import subprocess

            downloads_dir = Path.home() / "Downloads"
            downloads_dir.mkdir(exist_ok=True)
            csv_path = downloads_dir / "aie_ledger_all.csv"

            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Date', 'Description', 'Account', 'Debit', 'Credit', 'Source File']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for t in self.ledger:
                    writer.writerow({
                        'Date': t.date,
                        'Description': t.description,
                        'Account': t.account,
                        'Debit': str(t.debit),
                        'Credit': str(t.credit),
                        'Source File': t.source_file
                    })

            # Open the file
            if os.name == 'nt':  # Windows
                subprocess.run(['start', str(csv_path)], shell=True)
            elif os.name == 'posix':  # macOS/Linux
                subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', str(csv_path)])

            self.page.snack_bar = ft.SnackBar(ft.Text(f"Downloaded all transactions to {csv_path}"), bgcolor=ft.Colors.GREEN_700)
            self.page.snack_bar.open = True
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"Download failed: {ex}"), bgcolor=ft.Colors.RED_700)
            self.page.snack_bar.open = True
            self.page.update()

    def show_source_selection_dialog(self, e):
        # Get unique source files
        sources = list(set(t.source_file for t in self.ledger))
        sources.sort()

        if not sources:
            self.page.snack_bar = ft.SnackBar(ft.Text("No transactions to download."), bgcolor=ft.Colors.ORANGE_700)
            self.page.snack_bar.open = True
            self.page.update()
            return

        # Create checkboxes for each source
        checkboxes = []
        selected_sources = []

        def on_checkbox_change(source):
            def handler(e):
                if e.control.value:
                    selected_sources.append(source)
                else:
                    selected_sources.remove(source)
            return handler

        for source in sources:
            cb = ft.Checkbox(label=source, value=False, on_change=on_checkbox_change(source))
            checkboxes.append(cb)

        def download_selected(e):
            if not selected_sources:
                self.page.snack_bar = ft.SnackBar(ft.Text("Please select at least one source."), bgcolor=ft.Colors.ORANGE_700)
                self.page.snack_bar.open = True
                self.page.update()
                return

            try:
                from pathlib import Path
                import subprocess

                downloads_dir = Path.home() / "Downloads"
                downloads_dir.mkdir(exist_ok=True)

                opened_files = []
                for source in selected_sources:
                    transactions = [t for t in self.ledger if t.source_file == source]
                    safe_source = "".join(c for c in source if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    csv_path = downloads_dir / f"aie_ledger_{safe_source}.csv"

                    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['Date', 'Description', 'Account', 'Debit', 'Credit', 'Source File']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        for t in transactions:
                            writer.writerow({
                                'Date': t.date,
                                'Description': t.description,
                                'Account': t.account,
                                'Debit': str(t.debit),
                                'Credit': str(t.credit),
                                'Source File': t.source_file
                            })

                    opened_files.append(csv_path)

                # Open all selected files
                for csv_path in opened_files:
                    if os.name == 'nt':  # Windows
                        subprocess.run(['start', str(csv_path)], shell=True)
                    elif os.name == 'posix':  # macOS/Linux
                        subprocess.run(['open' if os.uname().sysname == 'Darwin' else 'xdg-open', str(csv_path)])

                self.page.snack_bar = ft.SnackBar(ft.Text(f"Downloaded {len(opened_files)} CSV file(s) to Downloads folder"), bgcolor=ft.Colors.GREEN_700)
                self.page.snack_bar.open = True
                self.page.update()
                self.page.close(dlg)
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Download failed: {ex}"), bgcolor=ft.Colors.RED_700)
                self.page.snack_bar.open = True
                self.page.update()

        def cancel_download(e):
            self.page.close(dlg)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Select Sources to Download"),
            content=ft.Container(
                content=ft.Column(checkboxes, spacing=10, scroll=ft.ScrollMode.AUTO),
                height=300
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel_download),
                ft.ElevatedButton("Download Selected", on_click=download_selected, bgcolor=ft.Colors.GREEN_ACCENT_700),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)