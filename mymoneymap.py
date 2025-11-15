# mymoneymap.py
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import requests
import tempfile
import os
from streamlit import session_state

# -------------------------------------------------
# Page config
# -------------------------------------------------
st.set_page_config(page_title="MyMoneyMap", layout="wide")

# -------------------------------------------------
# Title & Intro
# -------------------------------------------------
st.title("MyMoneyMap: Financial Empowerment Dashboard")
st.markdown("Visualizing financial health for underserved communities.")
st.markdown("""
### How to Use
- Select a county to view complaint categories in a pie chart.
- Hover over the chart for complaint counts and percentages.
- Download complaint data as a CSV file.
- Tips provide actionable financial advice based on the top complaint category.
""")

# -------------------------------------------------
# Load SQLite DB from Google Drive
# -------------------------------------------------
DB_FILE_ID = "1Zq5UdX3yjKXUUBvvBp25x60xQW7P8ShZ"

@st.cache_data
def load_data():
    try:
        url = f"https://drive.google.com/uc?export=download&id={DB_FILE_ID}"
        response = requests.get(url)
        response.raise_for_status()

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.write(response.content)
        temp_db.close()

        conn = sqlite3.connect(temp_db.name)
        df = pd.read_sql_query("SELECT * FROM financial_data", conn)
        cfpb_df = pd.read_sql_query("SELECT * FROM complaint_categories", conn)
        conn.close()

        os.unlink(temp_db.name)

        st.success(f"Loaded {len(df):,} counties and {len(cfpb_df):,} complaint records")
        return df, cfpb_df
    except Exception as e:
        st.error(f"Error loading database: {e}")
        return pd.DataFrame(), pd.DataFrame()

df, cfpb_df = load_data()

# -------------------------------------------------
# Shorten product names
# -------------------------------------------------
def shorten_category_name(name):
    mapping = {
        "Bank account or service": "Bank Account",
        "Checking or savings account": "Checking/Savings",
        "Credit card": "Credit Card",
        "Credit card or prepaid card": "Credit/Prepaid",
        "Credit reporting": "Credit Report",
        "Debt collection": "Debt Collection",
        "Mortgage": "Mortgage"
    }
    return mapping.get(name, name)

if not cfpb_df.empty:
    cfpb_df["Product"] = cfpb_df["Product"].apply(shorten_category_name)

# -------------------------------------------------
# Main App
# -------------------------------------------------
if not df.empty:
    df["state"] = df["county"].str.extract(r",\s*([A-Za-z\s]+)$")

    st.sidebar.header("Filters")
    income_range = st.sidebar.slider("Median Income Range", min_value=0, max_value=int(df["median_income"].max() + 1000), value=(0, int(df["median_income"].max())))
    county = st.sidebar.selectbox("County", options=["All"] + list(df["county"].unique()))

    filtered_df = df[(df["median_income"] >= income_range[0]) & (df["median_income"] <= income_range[1])]

    st.subheader("Income vs. Complaints Correlation")
    fig = px.scatter(filtered_df, x="median_income", y="total_complaints", 
                     title="Median Income vs. Consumer Complaints (r=0.88)",
                     labels={"median_income": "Median Income ($)", "total_complaints": "Number of Complaints"},
                     hover_data=["county"])
    st.plotly_chart(fig, use_container_width=True)

    # --- Drill-Down (Mobile-Friendly with Fallback) ---
    st.subheader("Localized Complaint Drill-Down")
    if county != "All":
        selected_county = df[df["county"] == county]
        if not selected_county.empty:
            complaints = selected_county["total_complaints"].iloc[0]
            st.write(f"**{county}**: Total Complaints: {complaints}")
            
            county_complaints = cfpb_df[cfpb_df["county"] == county]
            if not county_complaints.empty:
                color_map = {
                    "Bank Account": "#1f77b4",
                    "Checking/Savings": "#ff7f0e",
                    "Credit Card": "#2ca02c",
                    "Card/Prepaid": "#d62728",
                    "Credit Report": "#9467bd",
                    "Debt Collection": "#8c564b",
                    "Mortgage": "#e377c2"
                }
                fig_pie = px.pie(county_complaints, values="complaint_count", names="Product", 
                                 title=f"Complaint Categories in {county}",
                                 color="Product", color_discrete_map=color_map)
                fig_pie.update_traces(
                    textinfo='percent+label',
                    textfont_size=10,  # Further reduced for mobile
                    pull=[0.1 if i == county_complaints["complaint_count"].idxmax() else 0 for i in range(len(county_complaints))],
                    hovertemplate="%{label}: %{value} complaints (%{percent})"
                )
                # Mobile detection and layout adjustment
                user_agent = st.get_option("browser.userAgent")
                is_mobile = user_agent and any(mobile in user_agent.lower() for mobile in ['mobile', 'android', 'iphone'])
                if is_mobile:
                    fig_pie.update_layout(
                        showlegend=False,  # Hide legend on mobile to save space
                        margin=dict(t=20, b=20, l=20, r=20),  # Minimal margins
                        height=300,  # Fixed height for mobile
                    )
                else:
                    fig_pie.update_layout(
                        showlegend=True,
                        margin=dict(t=40, b=40, l=40, r=40),
                        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.2),
                    )
                st.plotly_chart(fig_pie, use_container_width=True)
                top_category = county_complaints.loc[county_complaints["complaint_count"].idxmax(), "Product"]
                st.write(f"**Top Complaint Category**: {top_category}")
                
                if "debt collection" in top_category.lower():
                    st.markdown("- **Tip**: Contact a local credit counselor to negotiate debt repayment plans.")
                elif "mortgage" in top_category.lower():
                    st.markdown("- **Tip**: Explore mortgage relief programs or refinancing options.")
                elif "credit card" in top_category.lower():
                    st.markdown("- **Tip**: Review credit card statements for errors and consider lower-interest options.")
                elif "checking" in top_category.lower():
                    st.markdown("- **Tip**: Compare bank fees and switch to a low-cost or no-fee account.")
                elif "credit report" in top_category.lower():
                    st.markdown("- **Tip**: Check your credit report for errors at AnnualCreditReport.com.")
                else:
                    st.markdown(f"- **Tip**: Seek financial education resources for managing {top_category.lower()} issues.")
                
                st.download_button(
                    label=f"Download Complaints for {county}",
                    data=county_complaints.to_csv(index=False),
                    file_name=f"{county}_complaints.csv",
                    mime="text/csv"
                )
            else:
                st.markdown(f"No complaint category data available for {county}.")
        else:
            st.write(f"Select a county to see complaint details.")
    else:
        st.write("Select a county to see complaint details.")

    st.subheader("Find Your Financial Peers")
    if county != "All":
        selected_county = df[df["county"] == county]
        if not selected_county.empty:
            selected_income = selected_county["median_income"].iloc[0]
            income_min = selected_income * 0.95
            income_max = selected_income * 1.05
            selected_state = selected_county["state"].iloc[0]
            peers_df = df[(df["median_income"] >= income_min) & 
                          (df["median_income"] <= income_max) & 
                          (df["state"] != selected_state)].sort_values("median_income")
            if not peers_df.empty:
                st.write(f"Counties with similar median income (±5% of ${selected_income:,.2f}):")
                st.dataframe(peers_df[["county", "median_income", "total_complaints"]].head(5))
                st.download_button("Download Peer Counties", peers_df.to_csv(index=False), "peers.csv", "text/csv")
            else:
                st.write("No counties found with similar median income in other states.")
        else:
            st.write(f"No data for {county} in financial_data.")
    else:
        st.write("Select a county to find financial peers.")

    st.subheader("Vulnerability Ranking Score")
    if county != "All":
        selected_county = df[df["county"] == county]
        if not selected_county.empty:
            df["distress_score"] = (df["total_complaints"] / df["total_complaints"].max() * 0.5 + 
                                    (1 - df["median_income"] / df["median_income"].max()) * 0.5)
            state = selected_county["state"].iloc[0]
            state_df = df[df["state"] == state].sort_values("distress_score", ascending=False)
            state_df["rank"] = state_df["distress_score"].rank(ascending=False)
            selected_rank = state_df[state_df["county"] == county]["rank"].iloc[0]
            selected_score = state_df[state_df["county"] == county]["distress_score"].iloc[0]
            st.write(f"**{county}** Financial Distress Score: {selected_score:.2f} (Rank {int(selected_rank)} in {state})")
            st.write("Higher score = greater distress.")
            st.dataframe(state_df[["county", "median_income", "total_complaints", "distress_score", "rank"]].head(10))
        else:
            st.write(f"No data for {county} in financial_data.")
    else:
        st.write("Select a county to see vulnerability ranking.")

    st.subheader("Savings Goal Tracker")
    goal = st.number_input("Savings Goal ($)", min_value=0.0, value=5000.0, step=100.0)
    saved = st.number_input("Amount Saved ($)", min_value=0.0, value=1000.0, step=100.0)
    progress = min(saved / goal, 1.0) if goal > 0 else 0.0
    st.progress(progress)
    st.write(f"Progress: {progress * 100:.1f}%")
    if saved >= goal and goal > 0:
        st.success("Congratulations! You've reached your savings goal!")

    st.subheader("Budget Overview")
    income = st.number_input("Monthly Income ($)", min_value=0.0, value=2000.0)
    expenses = st.number_input("Monthly Expenses ($)", min_value=0.0, value=1500.0)
    st.write(f"Net Savings: ${income - expenses:.2f}")

    st.subheader("Spending Breakdown")
    categories = ["Housing", "Food", "Transport", "Other"]
    values = [st.number_input(f"{cat} ($)", min_value=0.0, value=100.0) for cat in categories]
    fig_pie = px.pie(values=values, names=categories, title="Spending by Category")
    st.plotly_chart(fig_pie, use_container_width=True)

# -------------------------------------------------
# FEEDBACK FORM
# -------------------------------------------------
st.markdown("---")
st.subheader("Share Your Feedback")
st.markdown("Help improve MyMoneyMap for **immigrants, students, and families**.")

with st.form("feedback_form"):
    name = st.text_input("Your Name (optional)")
    email = st.text_input("Email (optional, for follow-up)")
    role = st.selectbox("Who are you?", [
        "Immigrant", "Student", "Low-Income Family", 
        "Financial Educator", "Researcher", "Other"
    ])
    helpful = st.radio("Was this dashboard helpful?", ["Yes", "No", "Somewhat"])
    comment = st.text_area("Your thoughts (optional)")
    submitted = st.form_submit_button("Submit Feedback")

    if submitted:
        feedback_data = {
            "Name": name,
            "Email": email,
            "Role": role,
            "Helpful": helpful,
            "Comment": comment,
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
        }
        try:
            if "feedback" not in session_state:
                session_state.feedback = []
            session_state.feedback.append(feedback_data)
            st.success("Thank you! Your feedback has been recorded.")
        except:
            st.error("Could not save feedback. Try again.")

# Show submitted feedback (for demo/NIW proof)
if "feedback" in session_state and session_state.feedback:
    with st.expander("View All Feedback (Admin Only)"):
        feedback_df = pd.DataFrame(session_state.feedback)
        st.dataframe(feedback_df)
        st.download_button(
            "Download All Feedback (CSV)",
            feedback_df.to_csv(index=False),
            "mymoneymap_feedback.csv",
            "text/csv"
        )

# Footer
st.markdown("---")
st.caption("Built by @ayo-olayemi20 | Empowering financial equity through data | Nov 15, 2025")
