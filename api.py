import os
import streamlit as st
import requests
import urllib3
import logging
import pandas as pd
from dateutil import parser  # For more robust datetime parsing
from dotenv import load_dotenv

load_dotenv()
Ocp_Apim_Subscription_Key = os.getenv('Ocp-Apim-Subscription-Key')
BASE_URL = os.getenv('base_url')

# Configure headers
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Ocp-Apim-Subscription-Key': Ocp_Apim_Subscription_Key
}

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Disable insecure HTTPS warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure the base URL for your API
#BASE_URL = "https://localhost:7169/api"
#BASE_URL = "https://localhost:51088/api"
#BASE_URL = "https://foodmeterapiapi.azure-api.net/api"

def create_session():

    # Create a session that skips certificate verification
    session = requests.Session()
    session.verify = False
    session.headers.update(HEADERS)
    logging.disable(logging.DEBUG)
    return session

def get_user_by_username(session, username):
    """Get user details by username"""
    try:
        logging.debug(f"Requesting: GET {BASE_URL}/users")
        response = session.get(f"{BASE_URL}/users")
        
        logging.debug(f"Response status: {response.status_code}")
        logging.debug(f"Response body: {response.text}")
        
        if response.status_code == 200:
            users = response.json()
            # Match by name instead of username since that's what the API returns
            for user in users:
                if user.get('name') == username:  # Changed from 'username' to 'name'
                    return user
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
    return None

def get_waste_annotations(session, user_id):
    """Fetch waste annotations for a user"""
    try:
        logging.debug(f"Requesting: GET {BASE_URL}/users/{user_id}/wasteannotations")
        response = session.get(f"{BASE_URL}/users/{user_id}/wasteannotations")
        
        logging.debug(f"Response status: {response.status_code}")
        logging.debug(f"Response body: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
    return []

def create_waste_annotation(session, user_id, annotation_data):
    """Create a new food annotation"""
    try:
        logging.debug(f"Requesting: POST {BASE_URL}/users/{user_id}/wasteannotations")
        logging.debug(f"Request body: {annotation_data}")
        
        with st.spinner("Processing request... This may take a while."):   
            response = session.post(
                f"{BASE_URL}/users/{user_id}/wasteannotations",
                json=annotation_data
            )
        
        logging.debug(f"Response status: {response.status_code}")
        logging.debug(f"Response body: {response.text}")
        
        return response.status_code == 200 or response.status_code == 201  
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False

def delete_waste_annotation(session, user_id, annotation_id):
    """Delete a waste annotation"""
    try:
        logging.debug(f"Requesting: DELETE {BASE_URL}/users/{user_id}/wasteannotations/{annotation_id}")
        response = session.delete(
            f"{BASE_URL}/users/{user_id}/wasteannotations/{annotation_id}"
        )
        
        logging.debug(f"Response status: {response.status_code}")
        logging.debug(f"Response body: {response.text}")
        
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return False

# =================================================================================================
# New code for price history analysis
# =================================================================================================

def parse_timestamp(timestamp_str):
    """Parse timestamp string to datetime object using dateutil parser"""
    try:
        return parser.parse(timestamp_str)
    except (ValueError, TypeError):
        return None

def get_price_history_data(annotations):
    """Process annotations into a format suitable for plotting"""
    # Convert annotations to DataFrame
    data = []
    for ann in annotations:
        if ann.get('itemName') and ann.get('price') and ann.get('timestamp'):
            data.append({
                'itemName': ann['itemName'],
                'price': float(ann['price']),
                'timestamp': parse_timestamp(ann['timestamp']),
                'annotation_name': ann['name']
            })
    
    df = pd.DataFrame(data)
    return df if not df.empty else None

def get_price_history_data(annotations):
    """Process annotations into a format suitable for plotting"""
    # Convert annotations to DataFrame
    data = []
    for ann in annotations:
        if ann.get('itemName') and ann.get('price') and ann.get('timestamp'):
            data.append({
                'itemName': ann['itemName'],
                'price': float(ann['price']),
                'timestamp': parse_timestamp(ann['timestamp']),
                'annotation_name': ann['name'],
                'quantity': float(ann.get('quantity', 1))  # Default to 1 if quantity not provided
            })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('timestamp')
        # Calculate total spent (price * quantity)
        df['total_spent'] = df['price'] * df['quantity']
        # Calculate cumulative sum for each item
        df['cumulative_sum'] = df.groupby('itemName')['total_spent'].cumsum()
        # Calculate overall cumulative sum
        df['overall_cumulative_sum'] = df['total_spent'].cumsum()
    
    return df if not df.empty else None

# =================================================================================================
# Waste Annotation Search Endpoint Integration
# =================================================================================================

def search_waste_annotations(session, user_id, search_params):
    """Search waste annotations for a user"""
    try:
        logging.debug(f"Requesting: POST {BASE_URL}/users/{user_id}/wasteannotations/search")
        logging.debug(f"Request body: {search_params}")
        
        with st.spinner("Searching annotations... This may take a while."):   
            response = session.post(
                f"{BASE_URL}/users/{user_id}/wasteannotations/search",
                json=search_params
            )
        
        logging.debug(f"Response status: {response.status_code}")
        logging.debug(f"Response body: {response.text}")
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Search Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Connection error: {str(e)}")
        return None
      
def increment_user_ops(session, user_id: int) -> bool:
    """
    Increment the NumberOfOps for a specific user
    
    Args:
        user_id (int): The ID of the user to update
        
    Returns:
        bool: True if successful, False if user not found
        
    Raises:
        requests.exceptions.RequestException: If the API call fails
    """
    url = f"{BASE_URL}/api/users/{user_id}/increment-ops"
    
    try:
        response = session.patch(url)
        
        if response.status_code == 204:
            return True
        elif response.status_code == 404:
            return False
        
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        # You might want to log the error here
        raise