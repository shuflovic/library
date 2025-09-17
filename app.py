import streamlit as st
import pandas as pd
from supabase import create_client, Client
from io import BytesIO

# Manual input for Supabase credentials
st.title("Universal Library Manager - Manual Setup")
supabase_url = st.text_input("Enter Supabase URL", "https://yourproject.supabase.co")
supabase_key = st.text_input("Enter Supabase Key", "", type="password")

if not supabase_url or not supabase_key:
    st.error("Please enter both Supabase URL and Key to proceed.")
    st.stop()

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

BUCKET_NAME = "libraries"  # Change this to your Supabase storage bucket name

# Initialize session state
if 'libraries' not in st.session_state:
    st.session_state.libraries = {}

# Function to load libraries from Supabase storage
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_libraries_from_supabase():
    libraries = {}
    try:
        response = supabase.storage.from_(BUCKET_NAME).list()
        files = response.data if response.data else []
        
        for file_info in files:
            file_name = file_info['name']
            if file_name.endswith('.csv'):
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
            
            existing_files = supabase.storage.from_(BUCKET_NAME).list()
            existing_names = [f['name'].replace('.csv', '') for f in existing_files.data if f['name'].endswith('.csv')]
            if library_name in existing_names:
                st.warning(f"Library '{library_name}' already exists. Overwriting...")
            
            supabase.storage.from_(BUCKET_NAME).upload(file_name, uploaded_file.read())
            st.success(f"Uploaded '{library_name}' to Supabase storage!")
            st.session_state.libraries[library_name] = pd.read_csv(BytesIO(uploaded_file.read()))  # Load into session state
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error uploading to Supabase: {str(e)}")
    return None

# Main app
if st.button("Refresh Libraries from Supabase"):
    st.session_state.libraries = load_libraries_from_supabase()
    st.rerun()

# File uploader
uploaded_file = st.file_uploader("Upload a CSV file to Supabase", type="csv")
upload_to_supabase(uploaded_file)

# Load from Supabase if no libraries
if not st.session_state.libraries:
    st.session_state.libraries = load_libraries_from_supabase()

# Sidebar selection
available_libraries = list(st.session_state.libraries.keys())
if available_libraries:
    selected_library = st.sidebar.selectbox("Select Library", available_libraries)
    df = st.session_state.libraries[selected_library]
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("First Half")
        st.dataframe(df.iloc[:len(df)//2])
    with col2:
        st.subheader("Second Half")
        st.dataframe(df.iloc[len(df)//2:])
else:
    st.info("No libraries available. Upload a CSV or ensure files are in Supabase storage.")

# Instructions
with st.expander("Setup Instructions"):
    st.markdown("""
    1. Install supabase-py: Add `supabase` to your `requirements.txt`.
    2. Create a Supabase project and a storage bucket named 'libraries'.
    3. Set policies: Allow public read (or authenticated), and insert/update for your key.
    4. Enter your Supabase URL and Key manually above.
    5. Upload a CSV to start, or ensure files exist in the Supabase bucket.
    """)
