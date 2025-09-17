import streamlit as st
import pandas as pd
import os

# Initialize session state for libraries
if 'libraries' not in st.session_state:
    st.session_state.libraries = {}

# Function to load static CSV files from Library folder (for GitHub repo files)
def load_static_libraries():
    folder_path = "./Library"
    if os.path.exists(folder_path):
        csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        for file in csv_files:
            file_path = os.path.join(folder_path, file)
            library_name = file.replace('.csv', '')
            try:
                df = pd.read_csv(file_path)
                if library_name not in st.session_state.libraries:
                    st.session_state.libraries[library_name] = df
            except Exception as e:
                st.error(f"Error reading static file {file}: {str(e)}")
    else:
        st.warning("Library folder not found. Only uploaded files will be available.")

# Load static libraries on first run
load_static_libraries()

# File uploader for new CSV
uploaded_file = st.sidebar.file_uploader("Upload a CSV file", type="csv")
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        library_name = uploaded_file.name.replace('.csv', '')
        # Handle duplicate names by adding a suffix
        if library_name in st.session_state.libraries:
            counter = 1
            while f"{library_name}_{counter}" in st.session_state.libraries:
                counter += 1
            library_name = f"{library_name}_{counter}"
        st.session_state.libraries[library_name] = df
        st.success(f"Library '{library_name}' added successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Error processing uploaded file: {str(e)}")

# Sidebar: Select library
available_libraries = list(st.session_state.libraries.keys())
if available_libraries:
    selected_library = st.sidebar.selectbox("Select Library", available_libraries)
    df = st.session_state.libraries[selected_library]
    
    # Split display
    col1, col2 = st.columns(2)
    with col1:
        st.write("First Half")
        st.dataframe(df.iloc[:len(df)//2])
    with col2:
        st.write("Second Half")
        st.dataframe(df.iloc[len(df)//2:])
else:
    st.info("No libraries available. Upload a CSV file or ensure the Library folder exists in your repo.")
