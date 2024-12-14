import requests
import pandas as pd
import io

# Graylog Server Configuration
graylog_url = "http://10.10.101.116:9000/api/search/universal/relative"
username = "admin"  # Replace with your Graylog username
password = "admin@123"  # Replace with your Graylog password

# Query Parameters for the API
params = {
    "query": "error AND source:hq-glg-t01", 
    "range": 86400,  # Search from the last 24 hours (86400 seconds)
    "limit": 3000,  # Limit the result to 3000 logs
    "fields": "timestamp,source,message"  
}

# Sending the request to Graylog API
response = requests.get(graylog_url, params=params, auth=(username, password))
csv_data = response.text

# Load the response CSV data into a DataFrame
logs_df = pd.read_csv(io.StringIO(csv_data))

# Filter Metricbeat-related data
metricbeat_df = logs_df[logs_df['message'].str.contains('metricset', case=False, na=False)]

# Convert timestamp columns to datetime (ensure both DataFrames use datetime format for merging)
logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'])
metricbeat_df['timestamp'] = pd.to_datetime(metricbeat_df['timestamp'])

# Remove timezone information (make datetime naive) using .loc[] to avoid SettingWithCopyWarning
metricbeat_df.loc[:, 'timestamp'] = metricbeat_df['timestamp'].dt.tz_localize(None)
logs_df.loc[:, 'timestamp'] = logs_df['timestamp'].dt.tz_localize(None)

# Merge the logs and Metricbeat data on the timestamp (you can use a time window if needed)
merged_df = pd.merge_asof(logs_df.sort_values('timestamp'), 
                           metricbeat_df.sort_values('timestamp'), 
                           on='timestamp', 
                           direction='nearest', 
                           tolerance=pd.Timedelta('5min'))  # Adjust time tolerance as needed

# Now you can analyze the merged data
# For example, finding logs and metrics within the same time window:
print(merged_df.describe())

# Optionally, save the merged data to a file
#merged_df.to_excel("correlated_data.xlsx", index=False)

print("Correlated data has been saved to 'correlated_data.xlsx'.")
