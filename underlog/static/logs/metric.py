import requests
import csv
from datetime import datetime
import io
# Set Graylog API credentials and URL
graylog_url = "http://10.10.101.116:9000/api/search/universal/relative"
username = "admin"  # Replace with your Graylog username
password = "admin@123"  # Replace with your Graylog password
# Define the search query for Metricbeat logs (you may need to adjust this based on your setup)
params = {
    "query": "metricbeat_service_type : system, metricbeat_metricset_name: cpu, metricbeat_host_cpu_usage: 0.0507",  # Adjust this to match your Metricbeat logs
    "range": 8600,  # Adjust time range as needed
    "limit": 2,
    "fields": "timestamp, message, *"  # Example fields
}


# Headers for authentication (using API token for simplicity)


# Send request to Graylog API
response = requests.get(graylog_url, params=params, auth=(username, password))

print(response.text)








''' 
if response.status_code == 200:
    data = response.json()
    messages = data.get("messages", [])
    
    # Prepare the data to save in CSV
    with open('metricbeat_data.csv', 'w', newline='') as csvfile:
        fieldnames = ["timestamp", "host", "metricset_name", "cpu_idle", "memory_used_pct"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        
        for message in messages:
            timestamp = message.get("timestamp")
            host = message.get("host.name")
            metricset_name = message.get("metricset.name")
            cpu_idle = message.get("system.cpu.idle")
            memory_used_pct = message.get("system.memory.actual.used.pct")
            
            # Write data row to CSV
            writer.writerow({
                "timestamp": timestamp,
                "host": host,
                "metricset_name": metricset_name,
                "cpu_idle": cpu_idle,
                "memory_used_pct": memory_used_pct
            })

    print("Metricbeat data saved to metricbeat_data.csv")
else:
    print(f"Failed to query Graylog API: {response.status_code}")
'''