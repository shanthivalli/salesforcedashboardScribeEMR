
import streamlit as st
import pandas as pd
import plotly.express as px
from simple_salesforce import Salesforce, SalesforceLogin
from simple_salesforce.exceptions import SalesforceAuthenticationFailed

# Streamlit app configuration
st.set_page_config(page_title="Salesforce Lead Dashboard", layout="wide")

# Apply custom CSS for smaller table font and aligned legend
st.markdown(
    """
    <style>
    .dataframe {
        font-size: 12px !important;
    }
    .plotly-legend {
        font-size: 10px !important;
    }
    .table-header {
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize session state variables
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'sf' not in st.session_state:
    st.session_state.sf = None
if 'lead_data' not in st.session_state:
    st.session_state.lead_data = None

# Allowed LeadSource values
allowed_lead_sources = [
    "Indeed",
    "Google Leads - Website",
    "Website",
    "Customer Referral",
    "Self Generated"
]

# Function to remap LeadSource values
def remap_lead_source(lead_sources):
    return lead_sources.apply(lambda x: x if x in allowed_lead_sources else "Other")

# Function to handle login
def handle_login(username, password, security_token, domain):
    try:
        # Authenticate with Salesforce
        session_id, instance = SalesforceLogin(
            username=username,
            password=password,
            security_token=security_token,
            domain=domain
        )
        # Establish connection and update session state
        st.session_state.sf = Salesforce(instance=instance, session_id=session_id)
        st.session_state.logged_in = True
        st.success("Logged in to Salesforce successfully!")
    except SalesforceAuthenticationFailed:
        st.error("Authentication failed. Please check your credentials.")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Login page
if not st.session_state.logged_in:
    st.title("Salesforce Lead Analysis")
    st.subheader("Login to Salesforce")
    username = st.text_input("Salesforce Username")
    password = st.text_input("Salesforce Password", type="password")
    security_token = st.text_input("Salesforce Security Token", type="password")
    domain = st.selectbox("Salesforce Domain", ["login", "test"])

    if st.button("Login"):
        if username and password and security_token:
            handle_login(username, password, security_token, domain)
        else:
            st.warning("Please provide all required credentials.")

# Dashboard page
if st.session_state.logged_in:
    st.title("Sales Dashboard")

    # Fetch lead data only if not already fetched
    if st.session_state.lead_data is None:
        try:
            # Define the SOQL query to fetch all lead records
            soql_query = """
            SELECT Id, Status, CreatedDate, OwnerId, LeadSource, Owner.Name,junk__c, Name,
            Email,MobilePhone,Product__c,Company FROM Lead
            """
            
            # Execute the query
            lead_records = st.session_state.sf.query_all(soql_query)
            
            # Check if records are returned
            if lead_records['totalSize'] > 0:
                # Convert records to a pandas DataFrame
                df_leads = pd.json_normalize(lead_records['records'])
                
                # Drop the 'attributes' column if it exists
                if 'attributes' in df_leads.columns:
                    df_leads.drop(columns='attributes', inplace=True)
                
                # Parse 'CreatedDate' to datetime
                df_leads['CreatedDate'] = pd.to_datetime(df_leads['CreatedDate'])
                
                # Rename columns for clarity
                df_leads.rename(columns={'Owner.Name': 'OwnerName'}, inplace=True)
                
                # Remap LeadSource values
                df_leads['LeadSource'] = remap_lead_source(df_leads['LeadSource'])
                
                # Store the data in session state
                st.session_state.lead_data = df_leads
            else:
                st.warning("No lead records found.")
        except Exception as e:
            st.error(f"An error occurred while fetching lead data: {e}")

    # Extract data for the dashboard
    if st.session_state.lead_data is not None:
        df_leads = st.session_state.lead_data
        
        # Arrange filters horizontally
        filter_col1, filter_col2, filter_col3,filter_col4 = st.columns(4)
        
        with filter_col1:
            # Year selection dropdown
            years = df_leads['CreatedDate'].dt.year.unique()
            years.sort()
            years = ['All'] + list(years.astype(str))  # Convert to string for display
            selected_year = st.selectbox("Select Year", years)
        
        with filter_col2:
            # Owner Name selection dropdown
            owner_names = df_leads['OwnerName'].dropna().unique()
            owner_names.sort()
            owner_names = ['All'] + list(owner_names)
            selected_owner = st.selectbox("Select Owner", owner_names)
        
        with filter_col3:
            # Lead Source selection dropdown
            lead_sources = df_leads['LeadSource'].dropna().unique()
            custom_order = [
                "Google Leads - Website",
                "Website",
                "Customer Referral",
                "Self Generated",
                "Indeed",
                "Other"
            ]
            lead_sources=sorted(lead_sources, key=lambda x: custom_order.index(x))
            lead_sources = ['All'] + list(lead_sources)
            selected_lead_source = st.selectbox("Select Lead Source", lead_sources)

        with filter_col4:
            # Lead Source selection dropdown
            lead_status = df_leads['Status'].dropna().unique()
            lead_status.sort()
            lead_status = ["All"] + list(lead_status)

            selected_lead_status = st.multiselect(
                "Select Lead Status",  # Label
                options=lead_status,   # Available lead statuses with "All"
                default=["All"]        # Default: "All" selected
            )
            # Handle deselection: If no option is selected, explicitly set to "All"
            if not selected_lead_status or "All" in selected_lead_status:
                selected_lead_status = ["All"]
                filtered_lead_status = lead_status[1:]  # All statuses (exclude "All")
            else:
                filtered_lead_status = selected_lead_status

            
        df_filtered = df_leads[df_leads['Status'].isin(filtered_lead_status)]
        df_filtered = df_leads.copy()
        
        if selected_year != 'All':
            df_filtered = df_filtered[df_filtered['CreatedDate'].dt.year == int(selected_year)]
        
        if selected_owner != 'All':
            df_filtered = df_filtered[df_filtered['OwnerName'] == selected_owner]
        
        if selected_lead_source != 'All':
            df_filtered = df_filtered[df_filtered['LeadSource'] == selected_lead_source]

        if selected_lead_status != 'All':
            df_filtered = df_filtered[df_filtered['Status'].isin(filtered_lead_status)]
        

        # Display charts if data is available
        if not df_filtered.empty:
            st.write(f"**Total Leads:** {df_filtered.shape[0]}")

            # Containers for fixed layout
            col1, col2 = st.columns(2, gap="large")

            # First column for Lead Status
            with col1:
                st.subheader("Lead Status Analysis")
                status_col1, status_col2 = st.columns([2, 1])  # Pie chart takes 2/3 width, table takes 1/3
                
                with status_col1:
                    # Pie chart for Lead Status
                    status_counts = df_filtered['Status'].value_counts().reset_index()
                    status_counts.columns = ['Status', 'Count']
                    fig_status = px.pie(
                        status_counts,
                        names='Status',
                        values='Count',
                        #title='Lead Status Distribution',
                        height=450
                    )
                    fig_status.update_layout(legend=dict(orientation="h", y=-0.3))
                    st.plotly_chart(fig_status, use_container_width=True)

                with status_col2:
                    #st.markdown("<div class='table-header'>Lead Status Counts</div>", unsafe_allow_html=True)
                    st.table(status_counts)

            # Second column for Lead Source
            with col2:
                st.subheader("Lead Source Analysis")
                source_col1, source_col2 = st.columns([2, 1])  # Pie chart takes 2/3 width, table takes 1/3
                
                with source_col1:
                    # Pie chart for Lead Source
                    lead_source_counts = df_filtered['LeadSource'].value_counts().reset_index()
                    lead_source_counts.columns = ['LeadSource', 'Count']
                    fig_source = px.pie(
                        lead_source_counts,
                        names='LeadSource',
                        values='Count',
                        #title='Lead Source Distribution',
                        height=450
                    )
                    fig_source.update_layout(legend=dict(orientation="h", y=-0.3))
                    st.plotly_chart(fig_source, use_container_width=True)

                with source_col2:
                    #st.markdown("<div class='table-header'>Lead Source Counts</div>", unsafe_allow_html=True)
                    st.table(lead_source_counts)
        else:
            st.info("No lead records found for the selected filters.")


# Second Dashboard: Monthly Distribution Stacked Bar Chart
st.markdown("---")  # Divider between dashboards
st.title("Monthly Lead Distribution by Status")

# Apply the same filters for the stacked bar chart
if st.session_state.lead_data is not None:
    if not df_filtered.empty:
        # Create a new DataFrame for monthly aggregation
        df_filtered['Month'] = df_filtered['CreatedDate'].dt.month_name()  # Extract month name
        df_filtered['Month_Number'] = df_filtered['CreatedDate'].dt.month  # Extract month number
        df_monthly = (
            df_filtered.groupby(['Month', 'Status'])
            .size()
            .reset_index(name='Count')
        )

        # Calculate total leads per month
        df_month_totals = df_monthly.groupby('Month')['Count'].sum().reset_index(name='Total')
        df_monthly = df_monthly.merge(df_month_totals, on='Month')

        # Sort the month names in the correct order (Jan-Dec)
        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        df_monthly['Month'] = pd.Categorical(df_monthly['Month'], categories=month_order, ordered=True)
        df_monthly = df_monthly.sort_values(['Month'])

        # Create a stacked bar chart using Plotly
        fig_stacked = px.bar(
            df_monthly,
            y='Month',  # Y-axis: Months
            x='Count',  # X-axis: Count of leads
            color='Status',  # Stacked by Lead Status
            orientation='h',  # Horizontal bar chart
            #title='Monthly Distribution of Leads by Status',
            labels={'Count': 'Number of Leads', 'Month': 'Month', 'Status': 'Lead Status'},
        )

        # Add total count annotations at the end of each bar
        for i, row in df_month_totals.iterrows():
            fig_stacked.add_annotation(
                x=row['Total'],  # Total count
                y=row['Month'],  # Corresponding month
                text=row['Total'],  # Text to display
                showarrow=False,  # No arrow
                font=dict(size=12),  # Font size for annotation
                xanchor="left",  # Position text to the left of the bar
                yanchor="middle"
            )

        # Update the layout to increase chart size and adjust bar gap
        fig_stacked.update_layout(
            height=700,  # Increased chart height for better visibility
            barmode='stack',  # Stacked bars
            bargap=0.3,  # Increase gap between bars
            bargroupgap=0.2  # Space between groups
        )

        # Display the chart
        st.plotly_chart(fig_stacked, use_container_width=True)
    else:
        st.info("No data available for the selected filters to generate the stacked bar chart.")

# At the bottom of the dashboard, display all filtered records
st.markdown("---")
st.title("Filtered Records")

# Check if filtered data is available
if st.session_state.lead_data is not None:
    if not df_filtered.empty:
        # Add a new column for Lead Name
        if 'FirstName' in df_filtered.columns and 'LastName' in df_filtered.columns:
            df_filtered['Lead Name'] = df_filtered['FirstName'].fillna('') + ' ' + df_filtered['LastName'].fillna('')
        
        # Define the columns to display
        display_columns = ['Id','Name','Product__c','OwnerName', 'Status', 'LeadSource', 'CreatedDate']
        
        # Add Salesforce link to Id column
        salesforce_base_url = st.session_state.sf.base_url.split("/services")[0]  # Extract base URL
        df_filtered['Id'] = df_filtered['Id'].apply(lambda x: f"[{x}]({salesforce_base_url}/lightning/r/Lead/{x}/view)")

        # Add pagination
        rows_per_page = 10
        total_rows = df_filtered.shape[0]
        total_pages = (total_rows // rows_per_page) + (1 if total_rows % rows_per_page != 0 else 0)
        
        # Slice the DataFrame for the current page
        page_number = st.number_input(
            "Page Number", min_value=1, max_value=total_pages, value=1, step=1
        )
        start_idx = (page_number - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        
        df_paginated = df_filtered.iloc[start_idx:end_idx][display_columns]
        
        # Display the paginated table without the index column
        st.write(f"**Displaying page {page_number} of {total_pages}**")
        st.markdown(
            df_paginated.to_markdown(index=False, tablefmt="pipe"), 
            unsafe_allow_html=True
        )
    else:
        st.info("No records found for the selected filters.")
