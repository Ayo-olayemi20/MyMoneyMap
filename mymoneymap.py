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

        # Try to match county in CFPB data (flexible column names)
        possible_cols = [col for col in cfpb_df.columns if 'county' in col.lower()]
        county_complaints = pd.DataFrame()
        if possible_cols:
            county_col = possible_cols[0]
            county_name = county.split(',')[0].strip()
            county_complaints = cfpb_df[
                cfpb_df[county_col].str.contains(county_name, case=False, na=False)
            ]
        else:
            # Fallback: try state-only match
            state = selected["state"].iloc[0]
            state_col = next((col for col in cfpb_df.columns if 'state' in col.lower()), None)
            if state_col:
                county_complaints = cfpb_df[
                    cfpb_df[state_col].str.contains(state, case=False, na=False)
                ]

        if not county_complaints.empty and 'complaint_count' in county_complaints.columns:
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
                margin=dict(t=60, b=60, l=60