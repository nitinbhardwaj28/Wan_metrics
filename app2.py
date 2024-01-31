import streamlit as st
import pandas as pd
import numpy as np

def convert_to_kbps(x):
    if isinstance(x, str):
        value, unit = x.split()
        value = float(value)
        if unit == 'Mbps':
            return value * 1000
    return x

def process_files(peak_traff_path, prov_cap_path, errors_path, availability_path):
    # Read input files
    peak_traff = pd.read_csv(peak_traff_path)
    peak_traff.rename(columns={"Unnamed: 1": "Device"}, inplace=True)

    Prov_cap = pd.read_excel(prov_cap_path)

    Errors = pd.read_csv(errors_path)
    Errors.rename(columns={"NODE": "Device", "INTERFACE": "Interface"}, inplace=True)

    Availability = pd.read_csv(availability_path)
    Availability.rename(columns={"Node": "Device"}, inplace=True)

    # Perform the left join
    left_joined_df = Prov_cap.merge(peak_traff, on=['Device', 'Interface'], how='left')
    left_joined_df.drop(["Date", "Unnamed: 2", "Unnamed: 4", "School / Site", "Average receive bps", "Average transmit bps"], axis=1, inplace=True)

    # Perform the left join
    sec_joined_df = left_joined_df.merge(Errors, on=['Device', 'Interface'], how='left')
    sec_joined_df.drop(["Unnamed: 0", "Unnamed: 2", "Timestamp", "Percent Discards (Transmitted + Received)"], axis=1, inplace=True)

    # Perform the left join
    final_joined_df = sec_joined_df.merge(Availability, on=['Device', 'Interface'], how='left')
    final_joined_df.drop(["Vendor", "Interface Type", "Timestamp", "Interface ID", "Node ID"], axis=1, inplace=True)

    # Convert columns to kbps
    final_joined_df['Peak receive kbps'] = final_joined_df['Peak receive bps'].apply(convert_to_kbps)
    final_joined_df['Peak transmit kbps'] = final_joined_df['Peak transmit bps'].apply(convert_to_kbps)

    # Calculate percentages
    final_joined_df['Percent_Errors'] = final_joined_df['Percent Errors (Transmitted + Received)'].str.rstrip('%').astype('float') / 100.0
    final_joined_df['Availability'] = final_joined_df['Average Availability'].str.rstrip('%').astype('float') / 100.0

    # Comparisons and handling Null values
    conditions = [
        (final_joined_df['Percent_Errors'].isnull()),
        (final_joined_df['Percent_Errors'] > 0)
    ]
    choices = ['Undefined', 'No']
    final_joined_df['Is the school network error rate less than 1%?'] = np.select(conditions, choices, default='Yes')

    conditions1 = [
        (final_joined_df['Availability'].isnull()),
        (final_joined_df['Availability'] < 1)
    ]
    final_joined_df ['Is the network uptime over 99.5%?'] = np.select(conditions1, choices, default='Yes')

    conditions2 = [
        (final_joined_df['Peak receive kbps'].isnull()),
        (final_joined_df['Provisioned Downloads (Kbps)'] * 0.7 > final_joined_df['Peak receive kbps'])
    ]
    choices1 = ['Undefined', 'Good']
    final_joined_df['Is received traffic (download) volume 70% or less of the school download capacity?'] = np.select(conditions2, choices1, default='Bad')

    conditions2 = [
        (final_joined_df['Peak transmit kbps'].isnull()),
        (final_joined_df['Provisioned Upload(Kbps)'] * 0.7 > final_joined_df['Peak transmit kbps'])
    ]
    choices2 = ['Undefined', 'Good']
    final_joined_df['Is transmit traffic volume (upload) 70% or less of the school upload capacity?'] = np.select(conditions2, choices2, default='Bad')
    final_joined_df.drop(["Provisioned Downloads (Kbps)","Provisioned Upload(Kbps)","Peak receive bps",	"Peak transmit bps","Percent Errors (Transmitted + Received)",	"Average Availability",	"Peak receive kbps","Peak transmit kbps","Percent_Errors","Availability"], axis=1, inplace=True)
    return final_joined_df

#Setting up the page view for Streamlit app
def main():
    st.title("Network WAN metrics App")

    # File Upload widgets
    peak_traff_path = st.file_uploader("Upload Peak Traffic CSV", type=["csv"])
    prov_cap_path = st.file_uploader("Upload Provisioned Capacity Excel", type=["xlsx"])
    errors_path = st.file_uploader("Upload Errors CSV", type=["csv"])
    availability_path = st.file_uploader("Upload Availability CSV", type=["csv"])

    if st.button("Process Files"):
        if peak_traff_path and prov_cap_path and errors_path and availability_path:
            processed_data = process_files(peak_traff_path, prov_cap_path, errors_path, availability_path)

            # Export the DataFrame to an Excel file
            excel_output_path = 'processed_data.xlsx'
            processed_data.to_excel(excel_output_path, index=False)

            st.success(f"Files processed successfully! Exported to {excel_output_path}")
            #st.download_button("Download Processed Data", excel_output_path)
            st.markdown(f"Download Processed Data: [processed_data.xlsx](data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{processed_data.to_excel(index=False, engine='openpyxl').to_excel(None, index=False, engine='openpyxl').to_bytes(encoding='utf-8', index=False).hex()})", unsafe_allow_html=True)
        else:
            st.warning("Please upload all four files.")

if __name__ == "__main__":
    main()