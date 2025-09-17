import streamlit as st
import pandas as pd
from supabase import create_client, Client
from io import BytesIO

# Function to load libraries from Supabase storage
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_libraries_from_supabase():
    libraries = {}
    try:
        response = supabase.storage.from_(BUCKET_NAME).list()
        files = response if isinstance(response, list) else (response.data if hasattr(response, 'data') else [])
        
        for file_info in files:
            file_name = file_info.get('name')
            if file_name and file_name.endswith('.csv'):
                library_name = file_name.replace('.csv', '')
                file_data = supabase.storage.from_(BUCKET_NAME).download(file_name)
                df = pd.read_csv(BytesIO(file_data))
                libraries[library_name] = df
                st.info(f"Loaded {library_name} from Supabase")
    except Exception as e:
        st.error(f"Error loading from Supabase: {str(e)}")
    return libraries

# Function to upload CSV to Supabase storage
def upload_to_supabase(uploaded_file):
    if uploaded_file is not None:
        try:
            file_name = uploaded_file.name
            library_name = file_name.replace('.csv', '')
            
            # Check existing files with robust response handling
            response = supabase.storage.from_(BUCKET_NAME).list()
            existing_files = response if isinstance(response, list) else (response.data if hasattr(response, 'data') else [])
            existing_names = [f.get('name', '').replace('.csv', '') for f in existing_files if f.get('name', '').endswith('.csv')]
            if library_name in existing_names:
                st.warning(f"Library '{library_name}' already exists. Overwriting...")
            
            # Upload the file
            file_content = uploaded_file.read()
            supabase.storage.from_(BUCKET_NAME).upload(file_name, file_content)
            st.success(f"Uploaded '{library_name}' to Supabase storage!")
            
            # Read into DataFrame with a fresh buffer
            file_buffer = BytesIO(file_content)
            df = pd.read_csv(file_buffer)
            if df.empty:
                st.error(f"Uploaded file '{file_name}' is empty or has no valid data.")
                return None
            st.session_state.libraries[library_name] = df
            st.cache_data.clear()
            st.rerun()
        except pd.errors.EmptyDataError:
            st.error(f"No columns to parse from file '{file_name}'. Ensure it has headers like 'Author,Title,Publication Year'.")
        except Exception as e:
            st.error(f"Error uploading to Supabase: {str(e)}")
    return None

# Main app
if st.button("Refresh Libraries from Supabase"):
    st.session_state.libraries = load_libraries_from_supabase()
    st.rerun()

# File uploader
uploaded_file = st.sidebar.file_uploader("Upload a CSV file to Supabase", type="csv")
upload_to_supabase(uploaded_file)

# Load from Supabase if no libraries
if not st.session_state.libraries:
    st.session_state.libraries = load_libraries_from_supabase()

# Sidebar selection
available_libraries = list(st.session_state.libraries.keys())
if available_libraries:
    selected_library = st.sidebar.radio("Select Library", available_libraries)
    df = st.session_state.libraries[selected_library]
    
    # Three-column display with library name as subheader
    col1, col2, col3 = st.columns(3)
    total_rows = len(df)
    with col1:
        st.subheader(selected_library)
        st.dataframe(df.iloc[:total_rows//3])
    with col2:
        st.subheader(selected_library)
        st.dataframe(df.iloc[total_rows//3:2*total_rows//3])
    with col3:
        st.subheader(selected_library)
        st.dataframe(df.iloc[2*total_rows//3:])
else:
    st.info("No libraries available. Upload a CSV or ensure files are in Supabase storage.")

# Manual input for Supabase credentials
st.sidebar.title("Universal Library Manager - Manual Setup")
supabase_url = st.sidebar.text_input("Enter Supabase URL", "https://rigsljqkzlnemypqjlbk.supabase.co")
supabase_key = st.sidebar.text_input("Enter Supabase Key", "", type="password")



if not supabase_url or not supabase_key:
    st.error("Please enter both Supabase URL and Key to proceed.")
    st.stop()

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

BUCKET_NAME = "libraries"  # Change this to your Supabase storage bucket name

# Initialize session state
if 'libraries' not in st.session_state:
    st.session_state.libraries = {}

# Instructions
with st.expander("Setup Instructions"):
    st.markdown("""
    1. Install supabase-py: Add `supabase` to your `requirements.txt`.
    2. Create a Supabase project and a storage bucket named 'libraries'.
    3. Set policies: Allow public read (or authenticated), and insert/update for your key.
    4. Enter your Supabase URL and Key manually above.
    5. Upload a CSV with headers 'Author,Title,Publication Year' to start, or ensure files exist in the Supabase bucket.
    """)
