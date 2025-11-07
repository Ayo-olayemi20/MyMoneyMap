# mymoneymap.py
import streamlit as st
import pandas as pd
import plotly.express as px

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

# --- Load Data from Google Drive ---
@st.cache_data
def load_census_data():
    url = "https://drive.google.com/uc?export=download&id=1eNb1pGNkGPskx3lxSLjJO-1QcwacMqqN"
    df = pd.read_csv(url)
    st.success(f"Loaded Census data: {len(df):,} rows")
    return df

@st.cache_data
def load_cfpb_data():
    url = "https://drive.google.com/uc?export=download&id=1AMkPdNY-am-mnyGCku_AHL8P9r3F9_Ba"
    df = pd.read_csv(url)
    st.success(f"Loaded CFPB complaints: {len(df):,} rows")
    return df

# Load data
try:
    df = load_census_data()
    cfpb_df = load_cfpb_data()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

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
    return mapping.get(str(name).strip(), str(name).strip())

if not cfpb_df.empty:
    cfpb_df["Product"] = cfpb_df["Product"].apply(shorten_category_name)

# Extract state from county
df["state"] = df["county"].str.extract(r",\s*([A-Za-z\s]+)$")
if df["state"].isna().all():
    st.warning("State names not found in county column. Expected format: 'Autauga County, Alabama'")

# Sidebar filters
st.sidebar.header("Filters")
income_range = st.sidebar.slider(
    "Median Income Range",
    min_value=0,
    max_value=int(df["median_income"].max() + 1000),
    value=(0, int(df["median_income"].max()))
)
county = st.sidebar.selectbox("County", options=["All"] + sorted(df["county"].unique()))

# Filter for scatter
filtered_df = df[
    (df["median_income"] >= income_range[0]) &
    (df["median_income"] <= income_range[1])
]

# Scatter Plot
st.subheader("Income vs. Complaints Correlation")
fig = px.scatter(
    filtered_df,
    x="median_income",
    y="total_complaints",
    title="Median Income vs. Consumer Complaints (r=0.88)",
    labels={"median_income": "Median Income ($)", "total_complaints": "Number of Complaints"},
    hover_data=["county"]
)
st.plotly_chart(fig, use_container_width=True)

# Localized Complaint Drill-Down
st.subheader("Localized Complaint Drill-Down")
if county != "All":
    selected = df[df["county"] == county]
    if not selected.empty:
        complaints = selected["total_complaints"].iloc[0]
        st.write(f"**{county}**: Total Complaints: {complaints:,}")

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
            fig_pie = px.pie(
                county_complaints,
                values="complaint_count",
                names="Product",
                title=f"Complaint Categories in {county}",
                color="Product",
                color_discrete_map=color_map
            )
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
            tips = {
                "debt collection": "Contact a local credit counselor to negotiate debt repayment plans.",
                "mortgage": "Explore mortgage relief programs or refinancing options.",
                "credit card": "Review credit card statements for errors and consider lower-interest options.",
                "checking": "Compare bank fees and switch to a low-cost or no-fee account.",
                "credit report": "Check your credit report for errors at AnnualCreditReport.com."
            }
            tip = next((v for k, v in tips.items() if k in top_category.lower()), 
                       f"Seek financial education resources for managing {top_category.lower()} issues.")
            st.markdown(f"- **Tip**: {tip}")

            st.download_button(
                label=f"Download Complaints for {county}",
                data=county_complaints.to_csv(index=False),
                file_name=f"{county.replace(' ', '_')}_complaints.csv",
                mime="text/csv"
            )
        else:
            st.write(f"No complaint data for {county}. Limited CFPB coverage in this area.")
    else:
        st.write("County not found in data.")
else:
    st.write("Select a county to see complaint details.")

# Find Your Financial Peers
st.subheader("Find Your Financial Peers")
if county != "All" and not df[df["county"] == county].empty:
    selected = df[df["county"] == county].iloc[0]
    income_min = selected["median_income"] * 0.95
    income_max = selected["median_income"] * 1.05
    peers = df[
        (df["median_income"].between(income_min, income_max)) &
        (df["state"] != selected["state"])
    ].sort_values("median_income").head(5)

    if not peers.empty:
        st.write(f"Counties with similar income (±5% of ${selected['median_income']:,.0f}):")
        st.dataframe(peers[["county", "median_income", "total_complaints"]])
        st.download_button("Download Peers", peers.to_csv(index=False), "peers.csv", "text/csv")
    else:
        st.write("No peer counties found.")
else:
    st.write("Select a county to find peers.")

# Vulnerability Ranking
st.subheader("Vulnerability Ranking Score")
if county != "All" and not df[df["county"] == county].empty:
    df["distress_score"] = (df["total_complaints"] / df["total_complaints"].max() * 0.5 +
                            (1 - df["median_income"] / df["median_income"].max()) * 0.5)
    state = df[df["county"] == county]["state"].iloc[0]
    state_df = df[df["state"] == state].copy()
    state_df["rank"] = state_df["distress_score"].rank(ascending=False)
    row = state_df[state_df["county"] == county].iloc[0]
    st.write(f"**{county}**: Distress Score: {row['distress_score']:.2f} (Rank {int(row['rank'])} in {state})")
    st.dataframe(state_df[["county", "median_income", "total_complaints", "distress_score", "rank"]].head(10))
else:
    st.write("Select a county to see ranking.")

# Savings Goal Tracker
st.subheader("Savings Goal Tracker")
goal = st.number_input("Savings Goal ($)", min_value=0.0, value=5000.0, step=100.0)
saved = st.number_input("Amount Saved ($)", min_value=0.0, value=1000.0, step=100.0)
progress = min(saved / goal, 1.0) if goal > 0 else 0.0
st.progress(progress)
st.write(f"Progress: {progress * 100:.1f}%")
if saved >= goal and goal > 0:
    st.success("Congratulations! You've reached your goal!")

# Budget & Spending
st.subheader("Budget Overview")
income = st.number_input("Monthly Income ($)", min_value=0.0, value=2000.0)
expenses = st.number_input("Monthly Expenses ($)", min_value=0.0, value=1500.0)
st.write(f"Net Savings: ${income - expenses:.2f}")

st.subheader("Spending Breakdown")
categories = ["Housing", "Food", "Transport", "Other"]
values = [st.number_input(f"{cat} ($)", min_value=0.0, value=100.0, key=f"spend_{cat}") for cat in categories]
fig_pie = px.pie(values=values, names=categories, title="Spending by Category")
st.plotly_chart(fig_pie, use_container_width=True)