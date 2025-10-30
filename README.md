Accounting Intelligence Engine (AIE)
A desktop accounting application built with Python and Flet. AIE provides a local-first, user-friendly interface for managing financial transactions, performing automated validation, and generating key financial reports.

> Note: Replace the image URL above with a screenshot of your running application.

- Key Features
This application is organized into several key modules accessible via the side navigation bar:

- Dashboard: Get an at-a-glance overview of your financial health.

Financial Health Score: A percentage score based on the number of errors and anomalies in your data.

Key Metrics: View total errors, anomalies, and transaction counts.

Key Balances: See your most important balances, such as Total Assets, Total Liabilities, and Net Income.

Balancing Check: Confirms that your debits equal your credits (for all valid entries).

- Data Entry:

Add Manual Entry: A form for manually entering single journal entries (Date, Description, Account, Debit/Credit).

Upload Data: Import transactions from CSV or XLSX files. The uploader validates data on import and requires columns: Date, Description, Account, Debit, and Credit.

- General Ledger:

View all transactions in a sortable, filterable table.

AIE Status: Each transaction is automatically labeled as Valid, Anomaly, or Error.

Data Management: Delete individual entries or clear all transactions with confirmation.

Export: Download your entire ledger as a CSV or download separate CSVs based on the original source file (e.g., "Manual", "upload1.csv").

- Financial Reports:

Balance Sheet: Automatically generated report showing Assets, Liabilities, and Equity. Includes a check to ensure Assets = Liabilities + Equity.

Income Statement: Automatically generated report showing Revenue, Expenses, and Net Income.

- Chart of Accounts (COA):

Displays a clean table of all accounts, their classified type (Asset, Liability, Revenue, etc.), and their current balance.

- AIE Diagnostics & Simulation:

Issue List: Lists all transactions flagged with Error or Anomaly.

Simulation Engine: This is the "intelligence" part. Select a flagged transaction to:

Open a simulation panel.

Propose a correction (e.g., fix a date, change an amount).

Instantly see the simulated impact of your change on all account balances before you commit it.

Commit the correction to permanently fix the data.

- Settings:

Theme Toggle: Switch between Light and Dark mode.

Data Management: Securely clear all application data or export your settings and data to a JSON backup file.

- Technology Stack
Framework: Flet (for the Python-based desktop UI)

Language: Python 3

Libraries: openpyxl (for .xlsx file support)

- How It Works
Local-First Persistence: All your financial data is stored locally in a ledger.json file created in the application's directory. This means you have full control over your data.

Modular UI: The application interface is broken into separate "view" files (e.g., aie_views_core.py, aie_views_reports.py) which are dynamically loaded by the main aie_app.py.

Rules-Based Validation: The "brain" of the app is in aie_logic.py. It runs a series of rules on every transaction to check for:

Invalid date formats

Negative amounts

Entries with both a debit and a credit

Large transaction anomalies

Account type anomalies (e.g., a large debit to a Revenue account)

State Management: The main AIEApp class in aie_app.py manages the application's state, including the current view and the transaction ledger.

- Installation & Setup
To run this application on your local machine, follow these steps.

Clone the repository:

Bash

git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
Create a virtual environment (recommended):

Bash

python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
Install the required dependencies: Create a file named requirements.txt in the project directory and paste the following content:

flet
openpyxl
Then, install the dependencies:

Bash

pip install -r requirements.txt
 How to Run
With your virtual environment activated and dependencies installed, simply run the main_app.py file:

Bash

python main_app.py
The Flet application window will open, and you can begin using the Accounting Intelligence Engine.

 File Structure
.
├── main_app.py             # Entry point: Runs the Flet app
├── aie_app.py              # Core: Main AIEApp class, state management, navigation
├── aie_helpers.py          # Core: Transaction data class, file save/load (ledger.json)
├── aie_logic.py            # Core: All accounting rules, validation, and balance calculations
├── aie_views_content.py    # UI: Mixin factory, Diagnostic/Ledger action handlers
├── aie_views_core.py       # UI: Dashboard, Ledger, and Diagnostic view definitions
├── aie_views_data_entry.py # UI: "Add Entry" and "Upload Data" view definitions
└── aie_views_reports.py    # UI: "Reports", "COA", and "Settings" view definitions
