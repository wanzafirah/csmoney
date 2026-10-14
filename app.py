import os
import csv
from datetime import date, timedelta
import pandas as pd
import streamlit as st
import altair as alt


DATA_FILE = "transactions.csv"
INCOME_CATEGORIES = ["Salary", "Freelance", "Investment", "Gift", "Refund", "Other Income"]
EXPENSE_CATEGORIES = ["Food & Dining", "Groceries", "Transport", "Housing", "Utilities", "Entertainment", "Healthcare", "Shopping", "Education", "Travel", "Other Expense"]


def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["id", "date", "type", "category", "amount", "description"])
    df = pd.read_csv(DATA_FILE)
    if df.empty:
        return pd.DataFrame(columns=["id", "date", "type", "category", "amount", "description"])
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    df["id"] = df["id"].astype(int)
    return df


def save_data(df):
    df.sort_values("id", ascending=False).to_csv(DATA_FILE, index=False, quoting=csv.QUOTE_NONNUMERIC)


def next_id(df):
    if df.empty:
        return 1
    return int(df["id"].max()) + 1


def format_currency(value):
    return f"${value:,.2f}"


st.set_page_config(page_title="Money Tracker", page_icon="💰", layout="wide")

st.title("💰 Money Tracker")
st.caption("Track your income and expenses with ease")

df = load_data()

if "editing_id" not in st.session_state:
    st.session_state.editing_id = None


def reset_form():
    st.session_state.editing_id = None


menu = st.sidebar.radio("Navigation", ["Dashboard", "Add Transaction", "Transactions", "Reports"], on_change=reset_form)

if not df.empty:
    total_income = df[df["type"] == "Income"]["amount"].sum()
    total_expense = df[df["type"] == "Expense"]["amount"].sum()
    balance = total_income - total_expense
else:
    total_income = total_expense = balance = 0.0

st.sidebar.markdown("---")
st.sidebar.metric("Current Balance", format_currency(balance))
col_inc, col_exp = st.sidebar.columns(2)
col_inc.metric("Income", format_currency(total_income))
col_exp.metric("Expenses", format_currency(total_expense))

if menu == "Dashboard":
    st.header("📊 Overview")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Income", format_currency(total_income), delta="inflows")
    c2.metric("Total Expenses", format_currency(total_expense), delta="outflows")
    c3.metric("Net Balance", format_currency(balance))

    if df.empty:
        st.info("No transactions yet. Head to **Add Transaction** to get started.")
    else:
        st.markdown("### Monthly Cash Flow")
        monthly = df.copy()
        monthly["month"] = pd.to_datetime(monthly["date"]).dt.to_period("M").dt.to_timestamp()
        pivot = monthly.pivot_table(index="month", columns="type", values="amount", aggfunc="sum", fill_value=0)
        for col in ["Income", "Expense"]:
            if col not in pivot.columns:
                pivot[col] = 0.0
        pivot = pivot.reset_index()
        chart = alt.Chart(pivot.melt("month", var_name="type", value_name="amount")).mark_bar().encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y("amount:Q", title="Amount ($)"),
            color=alt.Color("type:N", scale=alt.Scale(domain=["Income", "Expense"], range=["#2ecc71", "#e74c3c"])),
            tooltip=["month", "type", "amount"],
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)

        st.markdown("### Spending by Category")
        expenses = df[df["type"] == "Expense"]
        if expenses.empty:
            st.write("No expenses recorded yet.")
        else:
            by_cat = expenses.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
            cat_chart = alt.Chart(by_cat).mark_arc(innerRadius=60).encode(
                theta=alt.Theta("amount:Q"),
                color=alt.Color("category:N", legend=alt.Legend(title="Category")),
                tooltip=["category", "amount"],
            ).properties(height=380)
            st.altair_chart(cat_chart, use_container_width=True)

        st.markdown("### Recent Transactions")
        recent = df.sort_values("date", ascending=False).head(8)
        st.dataframe(recent[["date", "type", "category", "amount", "description"]], use_container_width=True, hide_index=True)

elif menu == "Add Transaction":
    st.header("➕ Add / Edit Transaction")
    edit_id = st.session_state.editing_id
    editing = edit_id is not None

    if editing:
        row = df[df["id"] == edit_id]
        if row.empty:
            st.session_state.editing_id = None
            editing = False
            def_date = date.today()
            def_type = "Expense"
            def_category = EXPENSE_CATEGORIES[0]
            def_amount = 0.0
            def_desc = ""
        else:
            r = row.iloc[0]
            def_date = r["date"]
            def_type = r["type"]
            def_category = r["category"]
            def_amount = float(r["amount"])
            def_desc = r["description"]
    else:
        def_date = date.today()
        def_type = "Expense"
        def_category = EXPENSE_CATEGORIES[0]
        def_amount = 0.0
        def_desc = ""

    with st.form("transaction_form", clear_on_submit=not editing):
        col1, col2 = st.columns(2)
        with col1:
            t_type = st.selectbox("Type", ["Expense", "Income"], index=0 if def_type == "Expense" else 1)
            t_date = st.date_input("Date", value=def_date, max_value=date.today())
        with col2:
            categories = INCOME_CATEGORIES if t_type == "Income" else EXPENSE_CATEGORIES
            if def_category not in categories:
                def_category = categories[0]
            t_category = st.selectbox("Category", categories, index=categories.index(def_category))
            t_amount = st.number_input("Amount ($)", min_value=0.0, value=float(def_amount), step=0.01, format="%.2f")

        t_description = st.text_input("Description (optional)", value=def_desc)

        submitted = st.form_submit_button("Save Transaction", type="primary")
        if submitted:
            if t_amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                if editing:
                    df.loc[df["id"] == edit_id, ["date", "type", "category", "amount", "description"]] = [
                        t_date, t_type, t_category, t_amount, t_description
                    ]
                    st.success("Transaction updated!")
                else:
                    new_row = {
                        "id": next_id(df),
                        "date": t_date,
                        "type": t_type,
                        "category": t_category,
                        "amount": t_amount,
                        "description": t_description,
                    }
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    st.success("Transaction added!")
                save_data(df)
                st.session_state.editing_id = None
                st.rerun()

    if editing:
        st.button("Cancel Editing", on_click=reset_form)

elif menu == "Transactions":
    st.header("📋 All Transactions")
    if df.empty:
        st.info("No transactions to display.")
    else:
        with st.expander("Filters", expanded=True):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                type_filter = st.selectbox("Type", ["All", "Income", "Expense"])
            with fc2:
                cats = sorted(df["category"].unique())
                cat_filter = st.selectbox("Category", ["All"] + cats)
            with fc3:
                min_date = df["date"].min()
                max_date = df["date"].max()
                date_range = st.date_input("Date Range", value=[min_date, max_date], min_value=min_date, max_value=max_date)

        filtered = df.copy()
        if type_filter != "All":
            filtered = filtered[filtered["type"] == type_filter]
        if cat_filter != "All":
            filtered = filtered[filtered["category"] == cat_filter]
        if len(date_range) == 2:
            start, end = date_range
            filtered = filtered[(filtered["date"] >= start) & (filtered["date"] <= end)]

        filtered = filtered.sort_values("date", ascending=False).reset_index(drop=True)
        st.write(f"Showing **{len(filtered)}** transaction(s)")
        display = filtered[["date", "type", "category", "amount", "description"]].copy()
        display["amount"] = display.apply(lambda r: ("+" if r["type"] == "Income" else "-") + format_currency(r["amount"]).lstrip("$"), axis=1)
        st.dataframe(display, use_container_width=True, hide_index=True)

        if not filtered.empty:
            st.markdown("### Actions")
            sel_id = st.selectbox("Select a transaction to edit or delete", options=filtered["id"].tolist(),
                                  format_func=lambda i: f"#{i} — {filtered.loc[filtered['id']==i, 'date'].iloc[0]} {filtered.loc[filtered['id']==i, 'type'].iloc[0]} {filtered.loc[filtered['id']==i, 'category'].iloc[0]} {format_currency(filtered.loc[filtered['id']==i, 'amount'].iloc[0])}")
            a1, a2 = st.columns(2)
            with a1:
                if st.button("✏️ Edit", use_container_width=True):
                    st.session_state.editing_id = sel_id
                    st.switch_page("app.py")
            with a2:
                if st.button("🗑️ Delete", use_container_width=True):
                    df = df[df["id"] != sel_id]
                    save_data(df)
                    st.success("Transaction deleted.")
                    st.rerun()

elif menu == "Reports":
    st.header("📈 Reports")
    if df.empty:
        st.info("Add some transactions to see reports.")
    else:
        report_range = st.selectbox("Period", ["Last 7 Days", "Last 30 Days", "This Month", "Last Month", "All Time"])
        today = pd.to_datetime(date.today())
        if report_range == "Last 7 Days":
            start = (today - timedelta(days=7)).date()
        elif report_range == "Last 30 Days":
            start = (today - timedelta(days=30)).date()
        elif report_range == "This Month":
            start = today.replace(day=1).date()
        elif report_range == "Last Month":
            first = today.replace(day=1)
            last_month_end = (first - timedelta(days=1)).date()
            start = (first - timedelta(days=1)).replace(day=1).date()
        else:
            start = df["date"].min()

        period_df = df[df["date"] >= start].copy()
        p_income = period_df[period_df["type"] == "Income"]["amount"].sum()
        p_expense = period_df[period_df["type"] == "Expense"]["amount"].sum()
        p_balance = p_income - p_expense

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Period Income", format_currency(p_income))
        rc2.metric("Period Expenses", format_currency(p_expense))
        rc3.metric("Period Net", format_currency(p_balance), delta=f"{((p_balance/p_income)*100):.0f}% of income" if p_income else "0%")

        if not period_df.empty:
            st.markdown("#### Daily Cash Flow")
            daily = period_df.copy()
            daily["date"] = pd.to_datetime(daily["date"]).dt.date
            dp = daily.pivot_table(index="date", columns="type", values="amount", aggfunc="sum", fill_value=0).reset_index()
            for col in ["Income", "Expense"]:
                if col not in dp.columns:
                    dp[col] = 0.0
            melted = dp.melt("date", var_name="type", value_name="amount")
            line = alt.Chart(melted).mark_line(point=True).encode(
                x=alt.X("date:O", title="Date"),
                y=alt.Y("amount:Q", title="Amount ($)"),
                color=alt.Color("type:N", scale=alt.Scale(domain=["Income", "Expense"], range=["#2ecc71", "#e74c3c"])),
                tooltip=["date", "type", "amount"],
            ).properties(height=320)
            st.altair_chart(line, use_container_width=True)

            st.markdown("#### Expense Breakdown")
            exp = period_df[period_df["type"] == "Expense"]
            if exp.empty:
                st.write("No expenses in this period.")
            else:
                exp_cat = exp.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
                bars = alt.Chart(exp_cat).mark_bar(color="#e74c3c").encode(
                    x=alt.X("amount:Q", title="Amount ($)"),
                    y=alt.Y("category:N", sort="-x", title=None),
                    tooltip=["category", "amount"],
                ).properties(height=320)
                st.altair_chart(bars, use_container_width=True)

            st.markdown("#### Income Breakdown")
            inc = period_df[period_df["type"] == "Income"]
            if inc.empty:
                st.write("No income in this period.")
            else:
                inc_cat = inc.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
                ibars = alt.Chart(inc_cat).mark_bar(color="#2ecc71").encode(
                    x=alt.X("amount:Q", title="Amount ($)"),
                    y=alt.Y("category:N", sort="-x", title=None),
                    tooltip=["category", "amount"],
                ).properties(height=320)
                st.altair_chart(ibars, use_container_width=True)
