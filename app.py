import streamlit as st
import pandas as pd
import os

# Sidebar filter for libraries
selected_library = st.sidebar.selectbox("Select Library", ["library 1", "library 2"])

# Read all CSV files in the Library folder (relative path)
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

    # Display selected library data
    if selected_library in dataframes:
        df = dataframes[selected_library]
        col1, col2 = st.columns(2)
        with col1:
            st.write("First Half")
            st.dataframe(df.iloc[:len(df)//2])
        with col2:
            st.write("Second Half")
            st.dataframe(df.iloc[len(df)//2:])
    elif selected_library:
        st.error(f"No data found for {selected_library}. Please check the CSV file.")
