import requests
import pandas as pd
import io
# Graylog Server Configuration
graylog_url = "http://10.10.101.116:9000/api/search/universal/relative"
username = "admin"  # Replace with your Graylog username
password = "admin@123"  # Replace with your Graylog password

# Query Parameters for the API
params = {
    "query": "error", 
    "range": 3600,  # Search from the last 24 hours (86400 seconds)
    "limit": 3000,  # Limit the result to 1000 logs
    "fields": "timestamp,source, message"  
}
response = requests.get(graylog_url, params=params, auth=(username, password))
csv_data = response.text
logs_df = pd.read_csv(io.StringIO(csv_data))
logs_df.to_csv("processed_logs11112.csv", index=False, quoting=1)
 
print('success')