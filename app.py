
"""Money Tracker - a simple CLI personal finance manager.

Features:
- Add income / expense transactions with category, description, date
- View all transactions with running balance
- Edit or delete transactions
- Filter by type, category, or date range
- Summary report by category
- Auto-saves data to a JSON file next to the script
"""

import json
import os
import sys
from datetime import datetime, date

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "money_tracker_data.json")

INCOME_CATEGORIES = ["Salary", "Freelance", "Gift", "Investment", "Other Income"]
EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Housing",
    "Utilities",
    "Entertainment",
    "Shopping",
    "Health",
    "Education",
    "Other Expense",
]


# --------------------------- Data layer ---------------------------

def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print(f"Warning: could not read data file '{DATA_FILE}'. Starting fresh.")
        return []


def save_data(transactions):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(transactions, f, indent=2, ensure_ascii=False)
        return True
    except OSError as e:
        print(f"Error: could not save data ({e}).")
        return False


# --------------------------- Helpers ---------------------------

def next_id(transactions):
    if not transactions:
        return 1
    return max(t["id"] for t in transactions) + 1


def fmt_amount(amount):
    sign = "-" if amount < 0 else ""
    return f"{sign}${abs(amount):,.2f}"


def parse_date(text):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


def prompt(text, allow_empty=False, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{text}{suffix}: ").strip()
        if value:
            return value
        if allow_empty:
            return default
        if default is not None:
            return default
        print("This field is required. Please try again.")


def prompt_float(text):
    while True:
        raw = prompt(text)
        try:
            value = float(raw)
            if value <= 0:
                print("Amount must be greater than zero.")
                continue
            return value
        except ValueError:
            print("Please enter a valid number.")


def choose_from_list(options, text="Choose an option"):
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        raw = prompt(f"{text} (1-{len(options)})")
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print(f"Please enter a number between 1 and {len(options)}.")


# --------------------------- Business logic ---------------------------

def add_transaction(transactions):
    print("\n--- Add Transaction ---")
    tx_type = choose_from_list(["Income", "Expense"], "Type")
    amount = prompt_float("Amount")
    if tx_type == "Expense":
        amount = -amount

    categories = INCOME_CATEGORIES if tx_type == "Income" else EXPENSE_CATEGORIES
    category = choose_from_list(categories, "Category")
    description = prompt("Description", allow_empty=True, default="")

    while True:
        raw_date = prompt("Date (YYYY-MM-DD)", allow_empty=True, default=date.today().isoformat())
        d = parse_date(raw_date)
        if d is None:
            print("Invalid date format. Use YYYY-MM-DD.")
            continue
        break

    tx = {
        "id": next_id(transactions),
        "type": tx_type,
        "amount": round(amount, 2),
        "category": category,
        "description": description,
        "date": d.isoformat(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    transactions.append(tx)
    save_data(transactions)
    print(f"\nTransaction added: {tx_type} {fmt_amount(amount)} on {d.isoformat()}.")


def list_transactions(transactions, header="--- Transactions ---"):
    if not transactions:
        print("\nNo transactions to show.")
        return
    sorted_tx = sorted(transactions, key=lambda t: t["date"])
    print(f"\n{header}")
    print(f"{'ID':<5}{'Date':<12}{'Type':<10}{'Category':<18}{'Amount':>12}  Description")
    print("-" * 80)
    running = 0.0
    for tx in sorted_tx:
        running += tx["amount"]
        print(
            f"{tx['id']:<5}{tx['date']:<12}{tx['type']:<10}{tx['category']:<18}"
            f"{fmt_amount(tx['amount']):>12}  {tx['description']}"
        )
    print("-" * 80)
    print(f"{'Balance':>48}{fmt_amount(running):>12}")


def delete_transaction(transactions):
    if not transactions:
        print("\nNo transactions to delete.")
        return
    list_transactions(transactions)
    raw = prompt("Enter the ID of the transaction to delete (or 0 to cancel)")
    try:
        tid = int(raw)
    except ValueError:
        print("Invalid ID.")
        return
    if tid == 0:
        return
    target = next((t for t in transactions if t["id"] == tid), None)
    if target is None:
        print("Transaction not found.")
        return
    confirm = prompt(f"Delete {fmt_amount(target['amount'])} '{target['description']}'? (y/n)").lower()
    if confirm.startswith("y"):
        transactions.remove(target)
        save_data(transactions)
        print("Transaction deleted.")
    else:
        print("Cancelled.")


def edit_transaction(transactions):
    if not transactions:
        print("\nNo transactions to edit.")
        return
    list_transactions(transactions)
    raw = prompt("Enter the ID of the transaction to edit (or 0 to cancel)")
    try:
        tid = int(raw)
    except ValueError:
        print("Invalid ID.")
        return
    if tid == 0:
        return
    target = next((t for t in transactions if t["id"] == tid), None)
    if target is None:
        print("Transaction not found.")
        return

    print(f"\nEditing transaction #{tid}. Press Enter to keep current value.")
    print(f"  Current type: {target['type']}")
    new_type = choose_from_list(
        ["Keep current", "Income", "Expense"], "Type"
    )
    if new_type == "Keep current":
        new_type = target["type"]

    new_amount = prompt_float(
        f"Amount (current {abs(target['amount']):.2f})"
    )
    if new_type == "Expense":
        new_amount = -abs(new_amount)
    else:
        new_amount = abs(new_amount)

    categories = INCOME_CATEGORIES if new_type == "Income" else EXPENSE_CATEGORIES
    print(f"  Current category: {target['category']}")
    cat_choice = choose_from_list(
        ["Keep current"] + categories, "Category"
    )
    new_category = target["category"] if cat_choice == "Keep current" else cat_choice

    new_desc = prompt(
        f"Description (current: '{target['description']}')",
        allow_empty=True,
        default=target["description"],
    )

    while True:
        new_date = prompt(
            f"Date (current: {target['date']})",
            allow_empty=True,
            default=target["date"],
        )
        if parse_date(new_date):
            break
        print("Invalid date format. Use YYYY-MM-DD.")

    target.update(
        {
            "type": new_type,
            "amount": round(new_amount, 2),
            "category": new_category,
            "description": new_desc,
            "date": new_date,
        }
    )
    save_data(transactions)
    print("Transaction updated.")


def filter_transactions(transactions):
    if not transactions:
        print("\nNo transactions to filter.")
        return
    print("\n--- Filter Transactions ---")
    print("  1. By type (Income / Expense)")
    print("  2. By category")
    print("  3. By date range")
    print("  4. By description keyword")
    choice = prompt("Choose a filter (1-4)")

    filtered = transactions
    if choice == "1":
        tx_type = choose_from_list(["Income", "Expense"], "Type")
        filtered = [t for t in transactions if t["type"] == tx_type]
        list_transactions(filtered, f"--- {tx_type} Transactions ---")
    elif choice == "2":
        all_cats = INCOME_CATEGORIES + EXPENSE_CATEGORIES
        category = choose_from_list(all_cats, "Category")
        filtered = [t for t in transactions if t["category"] == category]
        list_transactions(filtered, f"--- {category} ---")
    elif choice == "3":
        start = parse_date(prompt("Start date (YYYY-MM-DD)"))
        end = parse_date(prompt("End date (YYYY-MM-DD)"))
        if start is None or end is None:
            print("Invalid date.")
            return
        filtered = [
            t for t in transactions
            if start <= datetime.strptime(t["date"], "%Y-%m-%d").date() <= end
        ]
        list_transactions(filtered, f"--- Transactions from {start} to {end} ---")
    elif choice == "4":
        keyword = prompt("Keyword").lower()
        filtered = [t for t in transactions if keyword in t["description"].lower()]
        list_transactions(filtered, f"--- Matching '{keyword}' ---")
    else:
        print("Invalid choice.")


def show_summary(transactions):
    if not transactions:
        print("\nNo transactions yet.")
        return
    income = sum(t["amount"] for t in transactions if t["amount"] > 0)
    expense = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0)
    balance = income - expense

    print("\n--- Summary ---")
    print(f"Total Income : {fmt_amount(income)}")
    print(f"Total Expense: {fmt_amount(expense)}")
    print(f"Net Balance  : {fmt_amount(balance)}")
    if income > 0:
        savings_rate = (balance / income) * 100
        print(f"Savings Rate : {savings_rate:.1f}%")

    print("\nExpenses by category:")
    exp_cats = {}
    for t in transactions:
        if t["amount"] < 0:
            exp_cats[t["category"]] = exp_cats.get(t["category"], 0.0) + abs(t["amount"])
    if not exp_cats:
        print("  (no expenses recorded)")
    else:
        max_total = max(exp_cats.values())
        for cat, total in sorted(exp_cats.items(), key=lambda x: x[1], reverse=True):
            bar = "#" * int((total / max_total) * 30) if max_total else ""
            print(f"  {cat:<18} {fmt_amount(total):>12}  {bar}")

    print("\nIncome by category:")
    inc_cats = {}
    for t in transactions:
        if t["amount"] > 0:
            inc_cats[t["category"]] = inc_cats.get(t["category"], 0.0) + t["amount"]
    if not inc_cats:
        print("  (no income recorded)")
    else:
        max_total = max(inc_cats.values())
        for cat, total in sorted(inc_cats.items(), key=lambda x: x[1], reverse=True):
            bar = "#" * int((total / max_total) * 30) if max_total else ""
            print(f"  {cat:<18} {fmt_amount(total):>12}  {bar}")


def export_csv(transactions):
    if not transactions:
        print("\nNo transactions to export.")
        return
    csv_file = os.path.join(os.path.dirname(DATA_FILE), "transactions_export.csv")
    lines = ["id,date,type,category,amount,description"]
    for t in sorted(transactions, key=lambda x: x["date"]):
        desc = t["description"].replace('"', '""')
        lines.append(
            f'{t["id"]},{t["date"]},{t["type"]},{t["category"]},{t["amount"]:.2f},"{desc}"'
        )
    try:
        with open(csv_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Exported {len(transactions)} transactions to {csv_file}")
    except OSError as e:
        print(f"Error exporting: {e}")


# --------------------------- Menu ---------------------------

def print_menu():
    print("\n========== MONEY TRACKER ==========")
    print("  1. Add transaction")
    print("  2. View all transactions")
    print("  3. Edit transaction")
    print("  4. Delete transaction")
    print("  5. Filter transactions")
    print("  6. Summary report")
    print("  7. Export to CSV")
    print("  0. Exit")
    print("===================================")


def main():
    transactions = load_data()
    print(f"Loaded {len(transactions)} transaction(s) from {DATA_FILE}")

    actions = {
        "1": lambda: add_transaction(transactions),
        "2": lambda: list_transactions(transactions),
        "3": lambda: edit_transaction(transactions),
        "4": lambda: delete_transaction(transactions),
        "5": lambda: filter_transactions(transactions),
        "6": lambda: show_summary(transactions),
        "7": lambda: export_csv(transactions),
    }

    while True:
        print_menu()
        choice = prompt("Choose an option").strip()
        if choice == "0":
            print("Goodbye!")
            break
        action = actions.get(choice)
        if action is None:
            print("Invalid choice. Please pick a number from the menu.")
            continue
        try:
            action()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
