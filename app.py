import streamlit as st
import pandas as pd
from supabase import create_client, Client
from io import BytesIO
import requests

# --- Sidebar Setup ---
st.sidebar.title("Database Setup")
supabase_url = st.sidebar.text_input("Enter Supabase URL", "https://rigsljqkzlnemypqjlbk.supabase.co")
supabase_key = st.sidebar.text_input("Enter Supabase Key", "", type="password")
OCR_API_KEY = st.sidebar.text_input("Enter OCR API Key", "", type="password")

if not supabase_url or not supabase_key:
    st.error("Please enter both Supabase URL and Key to proceed.")
    st.stop()

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)
BUCKET_NAME = "libraries"  # Change this to your Supabase storage bucket name

# Initialize session state
if 'libraries' not in st.session_state:
    st.session_state.libraries = {}
if 'approved' not in st.session_state:
    st.session_state.approved = False
if "csv_uploader_key" not in st.session_state:
    st.session_state.csv_uploader_key = 0
if "image_uploader_key" not in st.session_state:
    st.session_state.image_uploader_key = 0

# --- Functions ---

@st.cache_data(ttl=300)
def load_libraries_from_supabase():
    """Load all CSV libraries from Supabase storage."""
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


def upload_to_supabase(uploaded_file):
    """Upload a CSV file to Supabase storage."""
    if uploaded_file is not None:
        try:
            file_name = uploaded_file.name
            library_name = file_name.replace('.csv', '')

            # Check existing files
            response = supabase.storage.from_(BUCKET_NAME).list()
            existing_files = response if isinstance(response, list) else (response.data if hasattr(response, 'data') else [])
            existing_names = [f.get('name', '').replace('.csv', '') for f in existing_files if f.get('name', '').endswith('.csv')]
            if library_name in existing_names:
                st.warning(f"Library '{library_name}' already exists. Overwriting...")

            # Upload the file
            file_content = uploaded_file.read()
            supabase.storage.from_(BUCKET_NAME).upload(file_name, file_content)
            st.success(f"Uploaded '{library_name}' to Supabase storage!")

            # Read into DataFrame
            file_buffer = BytesIO(file_content)
            df = pd.read_csv(file_buffer)
            if df.empty:
                st.error(f"Uploaded file '{file_name}' is empty or has no valid data.")
                return None
            st.session_state.libraries[library_name] = df
            st.cache_data.clear()

            # Reset uploader
            st.session_state.csv_uploader_key += 1
            st.rerun()
        except pd.errors.EmptyDataError:
            st.error(f"No columns to parse from file '{file_name}'. Ensure it has headers like 'Author,Title,Publication Year'.")
        except Exception as e:
            st.error(f"Error uploading to Supabase: {str(e)}")
    return None


def extract_text_from_image(image_file, api_key, filename="uploaded.jpg"):
    """Send image to OCR API and return extracted text."""
    url = "https://api.ocr.space/parse/image"
    payload = {
        "apikey": api_key,
        "language": "eng",
        "isTable": True,
    }
    # Pass tuple: (filename, file_object, mime_type)
    files = {
        "file": (filename, image_file, "image/jpeg")
    }
    response = requests.post(url, data=payload, files=files)
    result = response.json()
    if result.get("IsErroredOnProcessing"):
        raise Exception(result.get("ErrorMessage", "Unknown OCR error"))
    return result["ParsedResults"][0]["ParsedText"]



def upload_picture_for_books():
    """Upload an image, run OCR, and create a CSV library."""
    if 'uploaded_image' in st.session_state and st.session_state.uploaded_image is not None and not st.session_state.approved:
        try:
            st.image(st.session_state.uploaded_image, caption="Uploaded Image", use_column_width=True)

            if not OCR_API_KEY:
                st.warning("Please provide OCR API Key to analyze images.")
                return

            st.write("Analyzing image with OCR API...")
            image_bytes = st.session_state.uploaded_image.getvalue()
extracted_text = extract_text_from_image(
    BytesIO(image_bytes),
    OCR_API_KEY,
    filename=st.session_state.uploaded_image.name  # 👈 pass original filename
)

            

            st.text_area("Raw OCR Output", extracted_text, height=200)

            # --- Basic parsing example ---
            # Right now, just make one dummy entry from OCR text.
            # You can replace this with regex/LLM parsing for real structure.
            recognized_books = [{"Author": "Unknown", "Title": extracted_text[:50], "Publication Year": ""}]

            # Convert to DataFrame
            df = pd.DataFrame(recognized_books)

            # Use image filename as library name
            library_name = st.session_state.uploaded_image.name.rsplit('.', 1)[0]
            file_name = f"{library_name}.csv"

            # Upload to Supabase
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            supabase.storage.from_(BUCKET_NAME).upload(file_name, csv_bytes)
            st.success(f"Uploaded recognized books '{library_name}' to Supabase storage!")

            # Load into session state
            st.session_state.libraries[library_name] = df
            st.cache_data.clear()
            st.session_state.selected_library = library_name

            # Display recognized books
            st.subheader("Recognized Books from Image")
            st.dataframe(df)

        except Exception as e:
            st.error(f"Error processing image: {str(e)}")


# --- Main App ---

if st.button("Refresh Libraries from Supabase"):
    st.session_state.libraries = load_libraries_from_supabase()
    st.rerun()

# File uploader for CSV
uploaded_file = st.sidebar.file_uploader(
    "Upload a CSV file to Supabase",
    type="csv",
    key=f"csv_uploader_{st.session_state.csv_uploader_key}"
)
upload_to_supabase(uploaded_file)

# Picture uploader for book recognition
uploaded_image = st.sidebar.file_uploader(
    "Upload an Image for Book Recognition",
    type=["jpg", "jpeg", "png"],
    key=f"image_uploader_{st.session_state.image_uploader_key}"
)
if uploaded_image and 'uploaded_image' not in st.session_state:
    st.session_state.uploaded_image = uploaded_image
    st.session_state.approved = False
upload_picture_for_books()

# Approved button to clear image
if (
    'selected_library' in st.session_state
    and not st.session_state.approved
    and st.button("Approved")
):
    if 'uploaded_image' in st.session_state:
        del st.session_state['uploaded_image']
    st.session_state.approved = True
    st.write("Image cleared")

    # Force new uploader key
    st.session_state.image_uploader_key += 1
    st.rerun()

# Load from Supabase if no libraries
if not st.session_state.libraries:
    st.session_state.libraries = load_libraries_from_supabase()

# Sidebar selection with radio buttons
available_libraries = list(st.session_state.libraries.keys())
if available_libraries:
    selected_library = st.sidebar.radio(
        "Select Library",
        available_libraries,
        index=available_libraries.index(
            st.session_state.get('selected_library', available_libraries[0]) if available_libraries else 0
        )
    )
    df = st.session_state.libraries[selected_library]

    # Three-column display
    col1, col2, col3 = st.columns(3)
    total_rows = len(df)
    with col1:
        st.subheader(selected_library + "  (1/3)")
        st.dataframe(df.iloc[:total_rows//3])
    with col2:
        st.subheader("(2/3)")
        st.dataframe(df.iloc[total_rows//3:2*total_rows//3])
    with col3:
        st.subheader("(3/3)")
        st.dataframe(df.iloc[2*total_rows//3:])
else:
    st.info("No libraries available. Upload a CSV or ensure files are in Supabase storage.")

# Instructions
with st.sidebar.expander("Setup Instructions"):
    st.markdown("""
    1. Install dependencies: `supabase`, `requests`, `streamlit`, `pandas`.
    2. Create a Supabase project and a storage bucket named 'libraries'.
    3. Set storage policies: allow read/write for your key.
    4. Enter your Supabase URL, Key, and OCR API Key in the sidebar.
    5. Upload a CSV with headers 'Author,Title,Publication Year', or upload an image for OCR book recognition.
    """)
