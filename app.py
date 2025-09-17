import streamlit as st
import pandas as pd
import os

# Sidebar filter for libraries
selected_library = st.sidebar.selectbox("Select Library", ["library 1", "library 2"])

# Read all CSV files in the Library folder
folder_path = "./Library"
csv_files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
dataframes = {}

for file in csv_files:
    file_path = os.path.join(folder_path, file)
    library_name = file.replace('.csv', '')
    dataframes[library_name] = pd.read_csv(file_path)

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
