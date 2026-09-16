import streamlit as st
import requests
import pandas as pd

from datetime import date, timedelta

FINE_PER_DAY = 5 
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Library Management System", layout="wide")
st.title("Library Management System")
st.subheader("Learn, Organize, Track!!", divider="blue")

# ---------------------------
# Sidebar navigation
# ---------------------------
st.sidebar.title("📚 Library System")
page = st.sidebar.radio(
    "Navigate", ["🏠 Home", "➕ Add Book", "📖 View Books", "📤 Issue Book", "📥 Return Book","💰 Fine Section"]
)

# ---------------------------
# Home Page
# ---------------------------
if page == "🏠 Home":
    st.title("📚 Welcome to the World of Knowledge")
    st.write("Use the sidebar to navigate through the system.")
    
    st.image("https://www.fortquappelle.com/public/images/library-clipart-19.jpg")

# ---------------------------
# Add Book
# ---------------------------
elif page == "➕ Add Book":
    st.title("➕ Add New Book")
    
    title = st.text_input("Title")
    author = st.text_input("Author")
    quantity = st.number_input("Quantity", min_value=1, step=1)

    if st.button("Add Book"):
        payload = {
            "title": title,
            "author": author,
            "quantity": quantity
        }
        response = requests.post(f"{API_URL}/books/", json=payload)

        if response.status_code == 200:
            st.success("Book added successfully!")
        else:
            st.error(f"Failed to add book: {response.text}")

# ---------------------------
# View Books
# ---------------------------
elif page == "📖 View Books":
    st.title("📖 All Books(available now)")

    response = requests.get(f"{API_URL}/books/")
    if response.status_code == 200:
        books = pd.DataFrame(response.json())
        if not books.empty:
            st.dataframe(books, use_container_width=True)
        else:
            st.info("No books available.")
    else:
        st.error("Failed to fetch books from backend.")

# ---------------------------
# Issue Book
# ---------------------------
elif page == "📤 Issue Book":
    st.title("📤 Issue Book")
    st.subheader("Issued books must be returned within due date. Failing to do so, fine will be charged as ₹ 5 on per day basis.")

    response = requests.get(f"{API_URL}/books/")
    if response.status_code == 200:
        books = pd.DataFrame(response.json())
        available_books = books[books["available"] > 0]
        if not available_books.empty:
            book_id = st.selectbox("Select Book ID", available_books["id"])
            user = st.text_input("User Name")

            issue_date = date.today()
            return_date = issue_date + timedelta(days=14)
            st.write(f"Issue Date: {issue_date}")
            st.write(f"Return Date (due): {return_date}")

            if st.button("Issue"):
                params = {"book_id": int(book_id), "user": user}
                r = requests.post(f"{API_URL}/issue/", params=params)
                if r.status_code == 200:
                    st.success(f"Book issued successfully!\nIssue Date: {issue_date}\nReturn Date: {return_date}")
                else:
                    st.error(f"Failed to issue book: {r.text}")
        else:
            st.warning("No books available for issuing.")
    else:
        st.error("Failed to fetch books from backend.")

    # Display currently issued books
    st.subheader("📋 Currently Issued Books")
    tx_response = requests.get(f"{API_URL}/transactions/")
    if tx_response.status_code == 200:
        transactions = pd.DataFrame(tx_response.json())
        if transactions.empty:
            st.info("No books have been issued yet.")
            st.stop()

        issued_tx = transactions[transactions["action"] == "ISSUE"]
        returned_tx = transactions[transactions["action"] == "RETURN"]

        active_issues = issued_tx.merge(
            returned_tx,
            on=["book_id", "user"],
            how="left",
            indicator=True
        )

        active_issues = active_issues[active_issues["_merge"] == "left_only"]

        if active_issues.empty:
            st.info("No books are currently issued.")
        else:
            active_issues = active_issues.merge(books, left_on='book_id', right_on='id', how='left')
            active_issues['due_date'] = pd.to_datetime(active_issues['date_x']) + pd.Timedelta(days=14)

            df_display = active_issues[['book_id', 'user', 'title', 'date_x', 'due_date']]
            df_display = df_display.rename(columns={
                'book_id': 'Book ID',
                'user': 'User Name',
                'title': 'Book Title',
                'date_x': 'Issue Date',
                'due_date': 'Return Date (Due)'
            })

            st.dataframe(df_display, use_container_width=True)

    else:
        st.error("Failed to fetch transactions from backend.")

# ---------------------------
# Return Book
# ---------------------------
elif page == "📥 Return Book":
    st.title("📥 Return Book")

    response = requests.get(f"{API_URL}/books/")
    tx_response = requests.get(f"{API_URL}/transactions/")

    if response.status_code == 200 and tx_response.status_code == 200:
        books = pd.DataFrame(response.json())
        transactions = pd.DataFrame(tx_response.json())

        if not books.empty:

            book_id = st.selectbox("Select Book ID", books["id"])

            issued_users = transactions[
                (transactions['book_id'] == book_id) &
                (transactions['action'] == 'ISSUE')
            ]['user'].unique()

            returned_users = transactions[
                (transactions['book_id'] == book_id) &
                (transactions['action'] == 'RETURN')
            ]['user'].unique()

            active_users = [u for u in issued_users if u not in returned_users]

            if active_users:
                user = st.selectbox("Select User", active_users)
            else:
                st.info("No users have this book issued currently.")
                st.stop()

            # Fetch earliest issue date
            date_response = requests.get(f"{API_URL}/return_dates/", params={"book_id": book_id, "user": user})
            if date_response.status_code == 200:
                data = date_response.json()
                earliest_issue_date = data.get("earliest_issue_date")
                if earliest_issue_date:
                    min_date = pd.to_datetime(earliest_issue_date).date()
                else:
                    min_date = date.today()
            else:
                st.warning("Failed to fetch earliest issue date.")
                min_date = date.today()

            return_date = st.date_input("Select Actual Return Date", value=date.today(), min_value=min_date)

            if st.button("Return"):
                params = {
                    "book_id": int(book_id),
                    "user": user,
                    "return_date": return_date.isoformat()
                }

                r = requests.post(f"{API_URL}/return/", params=params)

                if r.status_code == 200:
                    st.success(f"Book returned successfully on {return_date}!")
                else:
                    st.error(f"Failed to return book: {r.text}")

        else:
            st.warning("No books available.")
    else:
        st.error("Failed to fetch data from backend.")

# ---------------------------
# Fine Section
# ---------------------------
elif page == "💰 Fine Section":
    st.title("💰 Fine Section - Overdue Books")

    tx_response = requests.get(f"{API_URL}/transactions/")
    books_response = requests.get(f"{API_URL}/books/")

    if tx_response.status_code == 200 and books_response.status_code == 200:
        transactions = pd.DataFrame(tx_response.json())
        books = pd.DataFrame(books_response.json())

        issued_books = transactions[transactions['action'] == 'ISSUE']

        fine_records = []
        today = date.today()
        FINE_PER_DAY = 5

        for _, tx in issued_books.iterrows():
            book_id = tx['book_id']
            user = tx['user']
            issue_date = date.fromisoformat(tx['date'])
            due_date = issue_date + timedelta(days=14)

            return_tx = transactions[
                (transactions['book_id'] == book_id) &
                (transactions['user'] == user) &
                (transactions['action'] == 'RETURN')
            ]

            if not return_tx.empty:
                actual_return_date = date.fromisoformat(return_tx.iloc[-1]['date'])
                days_late = (actual_return_date - due_date).days
            else:
                actual_return_date = None
                days_late = (today - due_date).days

            if days_late > 0:
                fine_amount = FINE_PER_DAY * days_late
            else:
                fine_amount = 0
                days_late = 0

            if fine_amount > 0:
                book_title = books[books['id'] == book_id]['title'].values[0]
                fine_records.append({
                    "Book ID": book_id,
                    "Title": book_title,
                    "User": user,
                    "Issue Date": issue_date,
                    "Due Date": due_date,
                    "Actual Return Date": actual_return_date if actual_return_date else "Not Returned",
                    "Days Late": days_late,
                    "Fine (₹)": fine_amount
                })

        if fine_records:
            df_fines = pd.DataFrame(fine_records)
            st.dataframe(df_fines, use_container_width=True)
        else:
            st.info("No fines at the moment. All books are returned on time.")
    else:
        st.error("Failed to fetch data from backend.")

# ---------------------------
# Footer
# ---------------------------
st.sidebar.markdown("---")
st.sidebar.write("Developed with ❤️ using Streamlit")
