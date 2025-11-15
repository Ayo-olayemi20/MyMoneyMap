# mymoneymap.py
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import requests
import tempfile
import os

# Set page configuration
st.set_page_config(page_title="MyMoneyMap", layout="wide")

# Title and description
st.title("MyMoneyMap: Financial Empowerment Dashboard")
st.markdown("Visualizing financial health for underserved communities.")
st.markdown("""
### How to Use
- Select a county to view complaint categories in a pie chart.
- Hover over the chart for complaint counts and percentages.
- Download complaint data as a CSV file.
- Tips provide actionable financial advice based on the top complaint category.
""")

# --- DATABASE LOADED FROM GOOGLE DRIVE ---
DB_FILE_ID = "1Zq5UdX3yjKXUUBvvBp25x60xQW7P8ShZ"  # YOUR .db FILE

@st.cache_data
def load_data():
    try:
        url = f"https://drive.google.com/uc?export=download&id={DB_FILE_ID}"
        response = requests.get(url)
        response.raise_for_status()

        # Save to temporary file (required for sqlite3 in Streamlit Cloud)
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db.write(response.content)
        temp_db.close()

        db_path = temp_db.name

        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM financial_data", conn)
        cfpb_df = pd.read_sql_query("SELECT * FROM complaint_categories", conn)
        conn.close()

        # Clean up temp file
        os.unlink(db_path)

        st.success(f"Loaded {len(df):,} counties and {len(cfpb_df):,} complaint records")
        return df, cfpb_df
    except Exception as e:
        st.error(f"Error loading database: {e}")
        return pd.DataFrame(), pd.DataFrame()

df, cfpb_df = load_data()

# Shorten complaint category names
def shorten_category_name(name):
    mapping = {
        "Bank account or service": "Bank Account",
        "Checking or savings account": "Checking/Savings",
        "Credit card": "Credit Card",
        "Credit card or prepaid card": "Card/Prepaid",
        "Credit reporting": "Credit Report",
        "Debt collection": "Debt Collection",
        "Mortgage": "Mortgage"
    }
    return mapping.get(name, name)

if not cfpb_df.empty:
    cfpb_df["Product"] = cfpb_df["Product"].apply(shorten_category_name)

# Check if data loaded successfully
if not df.empty:
    # Extract state
    df["state"] = df["county"].str.extract(r",\s*([A-Za-z\s]+)$")

    # Sidebar
    st.sidebar.header("Filters")
    income_range = st.sidebar.slider("Median Income Range", min_value=0, max_value=int(df["median_income"].max() + 1000), value=(0, int(df["median_income"].max())))
    county = st.sidebar.selectbox("County", options=["All"] + list(df["county"].unique()))

    # Filter for scatter
    filtered_df = df[(df["median_income"] >= income_range[0]) & (df["median_income"] <= income_range[1])]

    # Scatter plot
    st.subheader("Income vs. Complaints Correlation")
    fig = px.scatter(filtered_df, x="median_income", y="total_complaints", 
                     title="Median Income vs. Consumer Complaints (r=0.88)",
                     labels={"median_income": "Median Income ($)", "total_complaints": "Number of Complaints"},
                     hover_data=["county"])
    st.plotly_chart(fig, use_container_width=True)

    # Localized Complaint Drill-Down
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
                    textfont_size=14,
                    pull=[0.1 if i == county_complaints["complaint_count"].idxmax() else 0 for i in range(len(county_complaints))],
                    hovertemplate="%{label}: %{value} complaints (%{percent})"
                )
                fig_pie.update_layout(
                    showlegend=True,
                    margin=dict(t=60, b=60, l=60, r=250),
                    legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.4),
                    width=450
                )
                st.plotly_chart(fig_pie, use_container_width=True)
                top_category = county_complaints.loc[county_complaints["complaint_count"].idxmax(), "Product"]
                st.write(f"**Top Complaint Category**: {top_category}")
                
                # Tips
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

    # Find Your Financial Peers
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

    # Vulnerability Ranking Score
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

else:
    st.warning("No data loaded. Please check the database file.")

# Savings goal tracker
st.subheader("Savings Goal Tracker")
goal = st.number_input("Savings Goal ($)", min_value=0.0, value=5000.0, step=100.0)
saved = st.number_input("Amount Saved ($)", min_value=0.0, value=1000.0, step=100.0)
progress = min(saved / goal, 1.0) if goal > 0 else 0.0
st.progress(progress)
st.write(f"Progress: {progress * 100:.1f}%")
if saved >= goal and goal > 0:
    st.success("Congratulations! You've reached your savings goal!")

# Budget tracker
st.subheader("Budget Overview")
income = st.number_input("Monthly Income ($)", min_value=0.0, value=2000.0)
expenses = st.number_input("Monthly Expenses ($)", min_value=0.0, value=1500.0)
st.write(f"Net Savings: ${income - expenses:.2f}")

# Spending breakdown
st.subheader("Spending Breakdown")
categories = ["Housing", "Food", "Transport", "Other"]
values = [st.number_input(f"{cat} ($)", min_value=0.0, value=100.0) for cat in categories]
fig_pie = px.pie(values=values, names=categories, title="Spending by Category")
st.plotly_chart(fig_pie, use_container_width=True)