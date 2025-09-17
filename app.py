import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client
from io import BytesIO

# Supabase configuration - Use Streamlit secrets or environment variables
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY"))  # Use anon key for reads, service key for writes

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase credentials not found. Please set SUPABASE_URL and SUPABASE_KEY in secrets.toml or environment variables.")
    st.stop()

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BUCKET_NAME = "libraries"  # Change this to your Supabase storage bucket name

# Initialize session state
if 'libraries' not in st.session_state:
    st.session_state.libraries = {}

# Function to load libraries from Supabase storage
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_libraries_from_supabase():
    libraries = {}
    try:
        # List files in the bucket
        response = supabase.storage.from_(BUCKET_NAME).list()
        files = response.data if response.data else []
        
        for file_info in files:
            file_name = file_info['name']
            if file_name.endswith('.csv'):
                library_name = file_name.replace('.csv', '')
                # Download file
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
            # Upload to Supabase storage
            file_name = uploaded_file.name
            library_name = file_name.replace('.csv', '')
            
            # Check if file already exists
            existing_files = supabase.storage.from_(BUCKET_NAME).list()
            existing_names = [f['name'].replace('.csv', '') for f in existing_files.data if f['name'].endswith('.csv')]
            if library_name in existing_names:
                st.warning(f"Library '{library_name}' already exists. Overwriting...")
            
            # Upload
            supabase.storage.from_(BUCKET_NAME).upload(file_name, uploaded_file.read())
            st.success(f"Uploaded '{library_name}' to Supabase storage!")
            
            # Clear cache and rerun to reload
            st.cache_data.clear()
            st.rerun()
            return library_name
        except Exception as e:
            st.error(f"Error uploading to Supabase: {str(e)}")
    return None

# Load static libraries from local folder (fallback for local dev)
def load_static_libraries():
    folder_path = "./Library"
    if os.path.exists(folder_path):
        csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        for file in csv_files:
            file_path = os.path.join(folder_path, file)
            library_name = file.replace('.csv', '')
            if library_name not in st.session_state.libraries:
                try:
                    df = pd.read_csv(file_path)
                    st.session_state.libraries[library_name] = df
                    st.info(f"Loaded static {library_name}")
                except Exception as e:
                    st.error(f"Error reading static {file}: {str(e)}")

# Main app
st.title("Universal Library Manager")

# Load data
if st.button("Refresh Libraries from Supabase"):
    st.session_state.libraries = load_libraries_from_supabase()
    st.rerun()

# Load static if available (for local/Replit)
load_static_libraries()

# File uploader
uploaded_file = st.file_uploader("Upload a CSV file to Supabase", type="csv")
new_library = upload_to_supabase(uploaded_file)

# Load from Supabase if no static or on demand
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
    4. In Streamlit Cloud: Add SUPABASE_URL and SUPABASE_KEY to app secrets.
    5. In Replit/Local: Set as environment variables.
    6. For static files: Keep Library folder for local dev, but uploads go to Supabase.
    """)
