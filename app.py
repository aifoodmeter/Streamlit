import datetime
import os
import streamlit as st
import requests
import json
import urllib3
import logging
import pandas as pd
import plotly.express as px
from dateutil import parser  # For more robust datetime parsing
import plotly.graph_objects as go
from PIL import Image
import locale
from datetime import datetime
from dotenv import load_dotenv
from api import *
from audio import *

st.set_page_config(page_icon="icon.jpg")

# Add custom CSS for centering
st.markdown("""
    <style>
        section[data-testid="stSidebar"] div.stImage {
            display: flex;
            justify-content: center;
        }
        [data-testid=stSidebar] [data-testid=stMarkdown]{
            text-align: left;
        }
        
        /* Container to keep image and text together at bottom */
        .sidebar-content {
            position: fixed;
            bottom: 20px;
            width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

# Create a container div for the bottom content
st.sidebar.markdown("""
    <div class="sidebar-content">
    </div>
    """, unsafe_allow_html=True)

# Create three columns in the sidebar for centering
left_col, mid_col, right_col = st.sidebar.columns([1, 2, 1])
    
# In your sidebar code
image = Image.open('wastemeter.jpg')
st.sidebar.image(image, width=100)
st.sidebar.markdown("### Food Meter")

print(os.getcwd())
print(os.path.exists("wastemeter.jpg"))

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Disable insecure HTTPS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

api_key = st.secrets["api_key"]

def verify_access_token():
    # Get URL parameters
    params = st.query_params
    access_token = params.get("token", [""])
    
    # Check if token matches your secret token
    valid_token = st.secrets["access_token"]
    return access_token == valid_token

def main(session):
    if st.session_state and st.session_state.logged_in:
        st.markdown(f"""
            <h1 style='color: #1A202C;'>Food Annotation System</h1>
            <h3 style='color: #4A5568;'>Welcome {st.session_state.username}: track your household food effortlessly.<br>Save money while saving the planet.</h3>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <h1 style='color: #1A202C;'>Food Annotation System</h1>
            <h3 style='color: #4A5568;'>Track your household food effortlessly.<br>Save money while saving the planet.</h3>
        """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.current_page = "main"
        st.session_state.number_of_ops = 0

    # Login Page
    if not st.session_state.logged_in:
        username = st.text_input("Enter email")
        
        if st.button("Login"):
            user = get_user_by_username(session, username)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user['id']
                st.session_state.username = user['name']
                st.session_state.number_of_ops = user['numberOfOps']
                st.rerun()
            else:
                st.error("User not found")

    # Main Application Pages
    else:
        # Sidebar navigation using selectbox instead of radio
        st.sidebar.title("Navigation")
        page = st.sidebar.selectbox(
            "Go to",
            ["Food", "Search Food", "Price History"]
        )
        
        if page == "Food":

            if st.button('Reset Selection'):
                st.session_state.number_of_ops += 1
                st.write("Num:", st.session_state.number_of_ops)
        
            # Initialize session state for transcribed text
            if 'transcribed_text' not in st.session_state:
                st.session_state.transcribed_text = ""
            # Initialize session state for selected option
            if "reset_counter" not in st.session_state:
                st.session_state.reset_counter = 0

            # Create new annotation section
            st.header("Add New Food Items (A.I. way)", divider=True)
            locale.setlocale(locale.LC_TIME, 'C')  # or 'en_US.UTF-8'
            formatted_date = datetime.now().strftime("%d %B %Y")
            # Add labels as buttons
            selected_option = st.selectbox(
                "Select an example:",
                [
                    "Add 2 kg of peaches at 5 USD per kilo",
                    "Add one box of biscuits I paid 5 USD",
                    "Add 3 kg of bananas at 2 USD per kilo",
                    "Add 5 apples at 1 USD each",
                ],
                index=None,  # No default selection
                key=f"select_{st.session_state.reset_counter}"  # Key changes when reset is clicked
            )

            # Create a container for the input field and button
            input_container = st.container()
            
            # Create two columns with custom widths
            col1, col2 = input_container.columns([6, 1])
            
            # Text input in the first (wider) column
            with col1:
                quick_description = st.text_input(
                    "Enter text or use voice input:",
                    value=selected_option if selected_option else st.session_state.transcribed_text,
                    label_visibility="collapsed"
                )
            
            # Microphone button in the second (narrower) column
            with col2:
                if st.button("🎤", use_container_width=True):
                    try:
                        # Record audio
                        recording, sample_rate = record_audio()
                        
                        # Save audio to temporary file
                        audio_file_path = save_audio(recording, sample_rate)
                        
                        # Transcribe audio
                        st.session_state.reset_counter += 1
                        st.session_state.transcribed_text = transcribe_audio(audio_file_path, api_key)
                        quick_description = st.session_state.transcribed_text
                        increment_user_ops(session);
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")

            # Create a form for search parameters
            with st.form("quick_new_annotations"):
                st.write("Add descriptions like the examples above")
                
                # Flexible search fields
                #quick_description = st.text_input("Description", value=selected_option)

                # Submit button
                submit_button = st.form_submit_button("Quick Add Food Item")
            
                # Process new when button is clicked
                if submit_button:
                    annotation_data = {
                        "name": st.session_state.username,
                        "description": quick_description,
                        "itemName": None,
                        "price": None,
                        "quantity": None
                    }
                    if create_waste_annotation(session, st.session_state.user_id, annotation_data):
                        st.success("Foof added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add food")

            st.header("Add New Food Items (old way)", divider=True)
            with st.form("new_annotation"):
                name = st.text_input("Name")
                description = st.text_area("Description")
                item_name = st.text_input("Item Name")
                price = st.number_input("Price", min_value=0.0, value=None)
                quantity = st.number_input("Quantity", min_value=0, value=None)
                
                submit_button = st.form_submit_button("Add Food Item")
                
                if submit_button:
                    if price is None or price <= 0:
                        price = None
                    if quantity is None or quantity <= 0:
                        quantity = None
                    annotation_data = {
                        "name": name,
                        "description": description,
                        "itemName": item_name if item_name else None,
                        "price": price,
                        "quantity": quantity
                    }

                    # Placeholder for the progress message
                    progress_message = st.empty()
                    progress_message.write("Processing request...")

                    if create_waste_annotation(session, st.session_state.user_id, annotation_data):
                        st.success("Foof added successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to add food")

            # Display existing annotations
            st.header("Your Food Items", divider=True)
            annotations = get_waste_annotations(session, st.session_state.user_id)
            
            if not annotations:
                st.info("No food items found")
            else:
                for annotation in annotations:
                    with st.expander(f"Food Items: {annotation.get('name', 'N/A')}"):
                        st.write(f"Description: {annotation.get('description', 'N/A')}")
                        if annotation.get('itemName'):
                            st.write(f"Item Name: {annotation['itemName']}")
                        if annotation.get('price'):
                            st.write(f"Price: {annotation['price']}")
                        if annotation.get('quantity'):
                            st.write(f"Quantity: {annotation['quantity']}")
                        if annotation.get('timestamp'):
                            st.write(f"Timestamp: {annotation['timestamp']}")
                        
                        if st.button("Delete", key=f"delete_{annotation['id']}"):
                            if delete_waste_annotation(
                                session, 
                                st.session_state.user_id,
                                annotation['id']
                            ):
                                st.success("Item deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to delete item")

        elif page == "Price History":
            st.header("Price History Analysis", divider=True)
            
            # Get annotations and prepare data
            annotations = get_waste_annotations(session, st.session_state.user_id)
            df = get_price_history_data( annotations)
            
            if df is not None and not df.empty:
                # Create tabs for different views
                tab1, tab2 = st.tabs(["Item Price History", "Cumulative Analysis"])
                
                with tab1:
                    st.header("Price History by Item")
                    # Create item selector
                    items = sorted(df['itemName'].unique())
                    selected_item = st.selectbox("Select Item", items)
                    
                    # Filter data for selected item
                    item_data = df[df['itemName'] == selected_item].sort_values('timestamp')
                    
                    # Create the price history plot
                    fig_price = px.line(
                        item_data,
                        x='timestamp',
                        y='price',
                        title=f'Price History for {selected_item}',
                        hover_data=['annotation_name']
                    )
                    
                    # Customize the plot
                    fig_price.update_layout(
                        xaxis_title="Date",
                        yaxis_title="Price",
                        hovermode='x unified'
                    )
                    
                    # Display the plot
                    st.plotly_chart(fig_price)
                    
                    # Display data table
                    st.header("Price History Data")
                    st.dataframe(
                        item_data[['timestamp', 'price', 'quantity', 'total_spent', 'annotation_name']]
                        .rename(columns={
                            'timestamp': 'Time',
                            'price': 'Price',
                            'quantity': 'Quantity',
                            'total_spent': 'Total',
                            'annotation_name': 'Description'
                        })                        
                        .sort_values('Time', ascending=False)
                    )
                
                with tab2:
                    st.header("Cumulative Spending Analysis")
                    
                    # Overall cumulative sum chart
                    fig_cumsum = go.Figure()
                    
                    # Add overall cumulative sum line
                    fig_cumsum.add_trace(go.Scatter(
                        x=df['timestamp'],
                        y=df['overall_cumulative_sum'],
                        mode='lines',
                        name='Total Cumulative Spending',
                        line=dict(width=3, color='black')
                    ))
                    
                    # Add individual item cumulative sums
                    for item in items:
                        item_data = df[df['itemName'] == item]
                        fig_cumsum.add_trace(go.Scatter(
                            x=item_data['timestamp'],
                            y=item_data['cumulative_sum'],
                            mode='lines+markers',
                            name=f'{item} Cumulative',
                            marker=dict(size=8)
                        ))
                    
                    fig_cumsum.update_layout(
                        title='Cumulative Spending Over Time',
                        xaxis_title='Date',
                        yaxis_title='Cumulative Spending',
                        hovermode='x unified',
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_cumsum)
                    
                    # Summary statistics
                    st.header("Spending Summary")
                    total_spent = df['total_spent'].sum()
                    
                    # Create summary by item
                    summary_by_item = df.groupby('itemName').agg({
                        'total_spent': 'sum',
                        'quantity': 'sum'
                    }).round(2)
                    
                    summary_by_item.columns = ['Total Spent', 'Total Quantity']
                    summary_by_item['Percentage of Total'] = (
                        summary_by_item['Total Spent'] / total_spent * 100
                    ).round(2)
                    
                    st.write(f"Total spending: ${total_spent:,.2f}")
                    st.dataframe(summary_by_item)
                    
            else:
                st.info("No price history data available. Add annotations with prices to see the charts.")
        
        elif page == "Search Food":
                st.header("Search Food Items (A.I. way)", divider=True)

                # Add labels as buttons
                formatted_date = datetime.now().strftime("%d %B %Y")
                selected_option = st.selectbox(
                    "Search for food examples:",
                    [
                        "Select the food with name apple",
                        "Select the food with name apple with a minimum quantity of 1 kilo at any time",
                        f"Get the total price of food apple in the last 15 days; today is {formatted_date}",
                        f"Get the total price of food apple in the last month; today is {formatted_date} and price is USD",
                    ],
                    index=None  # No default selection
                )

                # Create a form for search parameters
                with st.form("quick_search_annotations"):
                    st.write("Search descriptions like the examples above")
                    
                    # Flexible search fields
                    quick_search_query = st.text_input("Query", value=selected_option)

                    # Submit button
                    search_button = st.form_submit_button("Quick Search Food Items")
                
                    # Process search when button is clicked
                    if search_button:
                        # Prepare search parameters dynamically
                        search_params = {}
                        if quick_search_query:
                            search_params['query'] = quick_search_query

                        # Perform search
                        search_results = search_waste_annotations(session, st.session_state.user_id, search_params)
                        
                        # Display results
                        if search_results:
                            st.header("Search Results")
                            if search_results.get("reply") is not None:
                                st.write(f"Answer: {search_results['reply']}")
                            # Create a DataFrame for easy display
                            if search_results.get("wasteAnnotations") is not None:
                                annotations_result = search_results['wasteAnnotations']
                                if annotations_result:
                                    results_df = pd.DataFrame(annotations_result)
                                    st.dataframe(results_df)
                                    
                                    # Optional: Additional visualizations or summary
                                    st.write(f"Total Food Items Found: {len(annotations_result)}")
                                    
                                    # Optional breakdown by item
                                    if 'itemName' in results_df.columns:
                                        item_counts = results_df['itemName'].value_counts()
                                        st.subheader("Food Distribution by Item")
                                        st.bar_chart(item_counts)
                        else:
                            st.info("No food items found matching question.")



                # Create a form for search parameters
                with st.form("search_annotations"):
                    st.header("Search Food Items (old way)", divider=True)
                    
                    # Flexible search fields
                    item_name = st.text_input("Item Name (optional)")
                    
                    # Date range inputs
                    start_date = st.date_input("Start Date (optional)", value=None)
                    end_date = st.date_input("End Date (optional)", value=None)
                    
                    # Price range inputs
                    min_price = st.number_input("Minimum Price (optional)", min_value=0.0, value=None)
                    max_price = st.number_input("Maximum Price (optional)", min_value=0.0, value=None)
                    
                    # Quantity range inputs
                    min_quantity = st.number_input("Minimum Quantity (optional)", min_value=0.0, value=None)
                    max_quantity = st.number_input("Maximum Quantity (optional)", min_value=0.0, value=None)
                    
                    # Submit button
                    search_button = st.form_submit_button("Search Food Items")
                
                # Process search when button is clicked
                if search_button:
                    # Prepare search parameters dynamically
                    search_params = {}
                    
                    if item_name:
                        search_params['itemName'] = item_name
                    
                    if start_date:
                        search_params['startDate'] = start_date.strftime('%Y-%m-%d')
                    
                    if end_date:
                        search_params['endDate'] = end_date.strftime('%Y-%m-%d')
                    
                    if min_price is not None:
                        search_params['minPrice'] = min_price
                    
                    if max_price is not None:
                        search_params['maxPrice'] = max_price
                    
                    if min_quantity is not None:
                        search_params['minQuantity'] = min_quantity
                    
                    if max_quantity is not None:
                        search_params['maxQuantity'] = max_quantity
                    
                    # Perform search
                    search_results = search_waste_annotations(session, st.session_state.user_id, search_params)
                    
                    # Display results
                    if search_results:
                        st.header("Search Results")
                        if not search_results:
                            st.info("No food items found matching your search criteria.")
                        else:
                            # Create a DataFrame for easy display
                            if search_results.get("wasteAnnotations") is not None:
                                annotations_result = search_results['wasteAnnotations']
                                results_df = pd.DataFrame(annotations_result)
                                st.dataframe(results_df)
                                
                                # Optional: Additional visualizations or summary
                                st.write(f"Total Food Items Found: {len(annotations_result)}")
                                
                                # Optional breakdown by item
                                if 'itemName' in results_df.columns:
                                    item_counts = results_df['itemName'].value_counts()
                                    st.subheader("Food Distribution by Item")
                                    st.bar_chart(item_counts)
                    else:
                        st.error("Failed to perform search. Please try again.")

if verify_access_token():
    # Create a session that skips certificate verification
    session = create_session()
    logging.disable(logging.DEBUG)

    if __name__ == "__main__":
        main(session)
else:
    if __name__ == "__main__":
        st.error("Unauthorized access. Please use a valid access link.")

# [Rest of the code remains the same]

