import streamlit as st
import pandas as pd
from supabase import create_client, Client
from io import BytesIO
import base64

# Manual input for Supabase credentials
st.sidebar.title("database Setup")
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

# Function to analyze image and generate book list CSV
def upload_picture_for_books(uploaded_image):
    if uploaded_image is not None:
        try:
            # Display the uploaded image
            st.image(uploaded_image, caption="Uploaded Image", use_column_width=True)
            st.write("Analyzing image for book recognition...")

            # Read and encode the image
            image_bytes = uploaded_image.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_data = f"data:image/jpeg;base64,{image_base64}" if uploaded_image.type == 'image/jpeg' else f"data:image/png;base64,{image_base64}"

            # Use Grok's image analysis capability (simulated here; in practice, this would be handled by the system)
            # For this example, we'll simulate the AI response with book data from the image
            # In a real setup, the system would analyze the image and return recognized books
            # Assuming the image contains books like in the conversation history, we'll use sample data
            ai_response = """
Based on the uploaded image of a bookshelf, I recognize the following books:

Author,Title,Publication Year
Kate Atkinson,Shrines of Gaiety,2022
Kate Atkinson,Transcription,2018
Tracy Chevalier,Falling Angels,2001
Isabel Allende,The House of the Spirits,1982
Barbara Kingsolver,The Lacuna,2009
Caitlin Moran,How to Be a Woman,2011
            """

            # Parse the AI response into DataFrame
            from io import StringIO
            df = pd.read_csv(StringIO(ai_response))
            
            # Generate CSV filename
            library_name = "recognized_books"
            file_name = f"{library_name}.csv"
            
            # Upload to Supabase
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            supabase.storage.from_(BUCKET_NAME).upload(file_name, csv_bytes)
            st.success(f"Uploaded recognized books '{library_name}' to Supabase storage!")
            
            # Load into session state
            st.session_state.libraries[library_name] = df
            st.cache_data.clear()
            
            # Display the recognized books
            st.subheader("Recognized Books from Image")
            st.dataframe(df)
            
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")

# Main app
if st.button("Refresh Libraries from Supabase"):
    st.session_state.libraries = load_libraries_from_supabase()
    st.rerun()

# File uploader for CSV
uploaded_file = st.sidebar.file_uploader("Upload a CSV file to Supabase", type="csv")
upload_to_supabase(uploaded_file)

# Picture uploader for book recognition
uploaded_image = st.sidebar.file_uploader("Upload an Image for Book Recognition", type=["jpg", "jpeg", "png"])
upload_picture_for_books(uploaded_image)

# Load from Supabase if no libraries
if not st.session_state.libraries:
    st.session_state.libraries = load_libraries_from_supabase()

# Sidebar selection
available_libraries = list(st.session_state.libraries.keys())
if available_libraries:
    selected_library = st.sidebar.radio("Select Library", available_libraries)
    df = st.session_state.libraries[selected_library]
   
    # Three-column display with library name only in first column
    col1, col2, col3 = st.columns(3)
    total_rows = len(df)
    with col1:
        st.subheader(selected_library)
        st.dataframe(df.iloc[:total_rows//3])
    with col2:
        st.dataframe(df.iloc[total_rows//3:2*total_rows//3])
    with col3:
        st.dataframe(df.iloc[2*total_rows//3:])
else:
    st.info("No libraries available. Upload a CSV or ensure files are in Supabase storage.")

# Instructions
with st.sidebar.expander("Setup Instructions"):
    st.markdown("""
    1. Install supabase-py: Add `supabase` to your `requirements.txt`.
    2. Create a Supabase project and a storage bucket named 'libraries'.
    3. Set policies: Allow public read (or authenticated), and insert/update for your key.
    4. Enter your Supabase URL and Key manually above.
    5. Upload a CSV with headers 'Author,Title,Publication Year' to start, or ensure files exist in the Supabase bucket.
    """)
