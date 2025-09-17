import streamlit as st
import pandas as pd
import os
import shutil

# Function to handle CSV file upload
def upload_csv():
    uploaded_file = st.file_uploader("Upload a CSV file", type="csv")
    if uploaded_file is not None:
        file_path = os.path.join("Library", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"File {uploaded_file.name} uploaded to Library folder!")
        return uploaded_file.name.replace('.csv', '')
    return None

# Upload button and process
new_library = upload_csv()
if new_library:
    st.experimental_rerun()

# Read all CSV files in the Library folder
folder_path = "./Library"
if not os.path.exists(folder_path):
    st.error(f"Library folder not found at {folder_path}. Please ensure it exists next to app.py with the CSV files.")
else:
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    dataframes = {}

    for file in csv_files:
        file_path = os.path.join(folder_path, file)
        library_name = file.replace('.csv', '')
        try:
            dataframes[library_name] = pd.read_csv(file_path)
        except Exception as e:
            st.error(f"Error reading {file}: {str(e)}")

    # Sidebar filter for libraries (dynamically updated)
    available_libraries = list(dataframes.keys())
    if available_libraries:
        selected_library = st.sidebar.selectbox("Select Library", available_libraries)
        # Display selected library data
        df = dataframes[selected_library]
        col1, col2 = st.columns(2)
        with col1:
            st.write("First Half")
            st.dataframe(df.iloc[:len(df)//2])
        with col2:
            st.write("Second Half")
            st.dataframe(df.iloc[len(df)//2:])
    else:
        st.error("No CSV files found in the Library folder.")
