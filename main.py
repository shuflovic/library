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

supabase: Client = create_client(supabase_url, supabase_key)
BUCKET_NAME = "libraries"

# --- State ---
if "files" not in st.session_state:
    st.session_state.files = {}
if "approved" not in st.session_state:
    st.session_state.approved = False
if "csv_uploader_key" not in st.session_state:
    st.session_state.csv_uploader_key = 0
if "image_uploader_key" not in st.session_state:
    st.session_state.image_uploader_key = 0

# --- Utils ---
@st.cache_data(ttl=300)
def load_files_from_supabase():
    """Load CSV and TXT files from Supabase."""
    files_dict = {}
    try:
        response = supabase.storage.from_(BUCKET_NAME).list()
        files = response if isinstance(response, list) else getattr(response, "data", [])
        for file_info in files:
            file_name = file_info.get("name")
            if not file_name:
                continue
            file_data = supabase.storage.from_(BUCKET_NAME).download(file_name)

            if file_name.endswith(".csv"):
                df = pd.read_csv(BytesIO(file_data))
                files_dict[file_name] = df
            elif file_name.endswith(".txt"):
                text_content = file_data.decode("utf-8", errors="ignore")
                files_dict[file_name] = text_content
    except Exception as e:
        st.error(f"Error loading from Supabase: {e}")
    return files_dict


def upload_csv(uploaded_file):
    """Upload CSV and store as DataFrame."""
    try:
        file_content = uploaded_file.read()
        supabase.storage.from_(BUCKET_NAME).upload(uploaded_file.name, file_content)
        st.success(f"Uploaded '{uploaded_file.name}' to Supabase!")

        df = pd.read_csv(BytesIO(file_content))
        st.session_state.files[uploaded_file.name] = df
        st.cache_data.clear()
        st.session_state.csv_uploader_key += 1
        st.rerun()
    except Exception as e:
        st.error(f"Error uploading CSV: {e}")


def extract_text_from_image(image_file, api_key, filename="uploaded.jpg"):
    """Send image to OCR API and return text."""
    url = "https://api.ocr.space/parse/image"
    payload = {"apikey": api_key, "language": "eng"}
    files = {"file": (filename, image_file, "image/jpeg")}
    r = requests.post(url, data=payload, files=files)
    result = r.json()
    if result.get("IsErroredOnProcessing"):
        raise Exception(result.get("ErrorMessage", "Unknown OCR error"))
    return result["ParsedResults"][0]["ParsedText"]


def process_uploaded_image():
    """Run OCR on image, save TXT to Supabase, and show text."""
    if "uploaded_image" in st.session_state and st.session_state.uploaded_image:
        try:
            st.image(st.session_state.uploaded_image, caption="Uploaded Image", use_column_width=True)

            if not OCR_API_KEY:
                st.warning("Provide OCR API Key first.")
                return

            # Show Approved button before running OCR
            if not st.session_state.approved:
                if st.button("Approved"):
                    st.session_state.approved = True
                    # continue execution after approval
                else:
                    return  # stop until user clicks Approved

            # --- OCR runs only after approval ---
            st.write("Analyzing image with OCR...")
            text = extract_text_from_image(
                BytesIO(st.session_state.uploaded_image.getvalue()),
                OCR_API_KEY,
                filename=st.session_state.uploaded_image.name,
            )


# Save to Supabase as TXT
            txt_name = st.session_state.uploaded_image.name.rsplit(".", 1)[0] + ".txt"
            supabase.storage.from_(BUCKET_NAME).upload(txt_name, text.encode("utf-8"))
            st.success(f"Uploaded OCR result as '{txt_name}' to Supabase.")

# Refresh files and select new TXT
            st.cache_data.clear()
            st.session_state.files = load_files_from_supabase()
            st.session_state.selected_file = txt_name

# Clear image after processing
            del st.session_state["uploaded_image"]
            st.session_state.image_uploader_key += 1

            st.subheader("OCR Extracted Text")
            st.text_area("Text Result", text, height=300)


        except Exception as e:
            st.error(f"Error during OCR: {e}")


# --- Main UI ---
if st.button("Refresh Files from Supabase"):
    st.session_state.files = load_files_from_supabase()
    st.rerun()

uploaded_csv = st.sidebar.file_uploader(
    "Upload CSV File",
    type="csv",
    key=f"csv_uploader_{st.session_state.csv_uploader_key}",
)
if uploaded_csv:
    upload_csv(uploaded_csv)

uploaded_image = st.sidebar.file_uploader(
    "Upload Image for OCR",
    type=["jpg", "jpeg", "png"],
    key=f"image_uploader_{st.session_state.image_uploader_key}",
)
if uploaded_image and "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = uploaded_image
    st.session_state.approved = False
process_uploaded_image()

if not st.session_state.files:
    st.session_state.files = load_files_from_supabase()

# --- File Viewer ---
# Include only TXT and CSV files
available_files = list(st.session_state.files.keys())

# Determine default selected index safely
default_file = st.session_state.get("selected_file")
if default_file in available_files:
    default_index = available_files.index(default_file)
else:
    default_index = 0
    st.session_state.selected_file = available_files[0] if available_files else None

# Build radio menu
selected = st.sidebar.radio(
    "Select File",
    available_files,
    index=default_index,
)
st.session_state.selected_file = selected

    data = st.session_state.files[selected]

    if isinstance(data, pd.DataFrame):  # CSV
        st.subheader(f"CSV Preview: {selected}")
        st.dataframe(data)
    else:  # TXT
        st.subheader(f"Text File: {selected}")
        st.text_area("Content", data, height=400)
else:
    st.info("No files found in Supabase storage.")

# --- Help ---
with st.sidebar.expander("Setup Instructions"):
    st.markdown("""
    1. Install: `pip install supabase requests streamlit pandas`.
    2. Create Supabase project + storage bucket 'libraries'.
    3. Add storage policy for read/write.
    4. Enter Supabase URL, Key, and OCR API Key in sidebar.
    5. Upload a CSV (will show as table).
    6. Upload an image (runs OCR after approval, saves result as TXT).
    """)
