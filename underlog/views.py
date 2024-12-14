import os
import pandas as pd
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
from django.http import HttpResponse
from django.core.mail import send_mail
import smtplib
import ssl
from django.template.loader import render_to_string
import requests
from datetime import datetime


import ssl
from django.core.mail.backends.smtp import EmailBackend

from email.mime.text import MIMEText
import logging
matplotlib.use('Agg')
csv_path = os.path.join(settings.BASE_DIR, 'underlog/static/logs/processed_logs10.csv')
csv_path_met = os.path.join(settings.BASE_DIR, 'underlog/static/logs/correlated_data.xlsx')


def logs(request):
   



    logs_df = pd.read_csv(csv_path)
    logs_df['number'] = range(1, len(logs_df) + 1)
    logs_df['server_name'] = logs_df['source'].apply(lambda x: "Icinga Server" if "hq-osm-t03" in str(x)  
        else ("Windows Server" if "HQ-ISM-T01" in str(x)  
          else ("Graylog Server" if "hq9-glg-t01" in str(x) 
                      else "") 
           ))

    
    search_source = request.GET.get('source', None)
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce').dt.tz_localize(None)



    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
    if search_source:
        # Filter the logs dataframe based on the selected source
        logs_df = logs_df[logs_df['source'].str.contains(search_source, case=False, na=False)]  


    if start_date:
        logs_df = logs_df[logs_df['timestamp'] >= start_date]
    if end_date:
        logs_df =  logs_df[logs_df['timestamp'] <= end_date]
    



    logs_list = logs_df.to_dict(orient="records")
    cnt = len(logs_list)
    paginator = Paginator(logs_list, 30)  
    page_number = request.GET.get('page') 
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'cnt':cnt,
        'search_source' :search_source,
        'start_date': start_date.strftime("%Y-%m-%d") if start_date else "",
        'end_date': end_date.strftime("%Y-%m-%d") if end_date else "",
        
    }
    return render(request, 'temp/logtable.html',  context)
    
def show(request):
    
    # Read the CSV file
    logs_df = pd.read_csv(csv_path)
    
    # Count the occurrences of each source and get the top 10 sources
    source_counts = logs_df['source'].value_counts()
    top_sources = source_counts.head(10)
    
    # Optionally, save the plot to static files for later use in the template
    plt.figure(figsize=(10, 6))
    sns.barplot(x=top_sources.values, y=top_sources.index, palette='viridis')
    plt.title("Top 10 Sources")
    plt.xlabel("Number of Logs")
    plt.ylabel("Source")
    plt.savefig(os.path.join(settings.BASE_DIR, 'underlog/static/images/img.png'))  # Save the plot
    plt.close()
  
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')

    if logs_df['timestamp'].isnull().any():
        print("Invalid timestamps found. Dropping these rows.")
        logs_df = logs_df.dropna(subset=['timestamp'])

    logs_df = logs_df.set_index('timestamp')
    error_logs = logs_df[logs_df['message'].str.contains('error', case=False, na=False)]
    error_frequency = error_logs.resample('H').size()
    error_frequency_sorted = error_frequency.sort_values(ascending=False)


    plt.figure(figsize=(10, 5))
    error_frequency.plot(kind='line', color='red', title="Error Frequency Over Time")
    plt.xlabel("Time")
    plt.ylabel("Number of Errors")
    plt.grid(True)
    error_frequency_plot_path = os.path.join(settings.BASE_DIR, 'underlog/static/images/error_frequency.png')
    plt.savefig(error_frequency_plot_path)
    plt.close()



    ################################################


    def categorize_error(message):
        """Function to categorize error messages based on keywords."""
        if 'timeout' in message.lower() or 'connection' in message.lower():
            return 'NetworkError'
        elif 'auth' in message.lower() or 'Authentication failed' in message.lower():
            return 'AuthenticationError'
        elif 'database' in message.lower() or 'db' in message.lower():
            return 'DatabaseError'
        elif 'config' in message.lower() or 'missing' in message.lower() or 'invalid' in message.lower() or 'not found' in message.lower() or 'error loading config' in message.lower() or 'misconfigured' in message.lower():
            return 'ConfigurationError'
        '''elif '400 bad request' in message.lower():
            return 'ClientSideIssue'
        else:
            return 'GeneralError'''
        
    logs_df['error_category'] = logs_df['message'].apply(categorize_error)
    database_error_count = len(logs_df[logs_df['error_category'] == 'DatabaseError'])
    network_error_count = len(logs_df[logs_df['error_category'] == 'NetworkError'])
    Auth_count = len(logs_df[logs_df['error_category'] == 'AuthenticationError'])
    general_count = len(logs_df[logs_df['error_category'] == 'GeneralError'])
    config_count = len(logs_df[logs_df['error_category'] == 'ConfigurationError'])
    client_count = len(logs_df[logs_df['error_category'] == 'ClientSideIssue'])

    def categorize_errors(logs_df):
        """Apply the categorization function to each log entry."""
        # Filter out logs containing 'error' keyword
        error_logs = logs_df[logs_df['message'].str.contains('error', case=False, na=False)]
        
        # Apply categorization to each error message
        error_logs['error_type'] = error_logs['message'].apply(categorize_error)
        
        # Count occurrences of each error type
        error_counts = error_logs['error_type'].value_counts()
        
        return error_counts, error_logs

    # Call the categorize function to get the error counts and categorized logs
    error_counts, error_logs = categorize_errors(logs_df)

    # Step 3: Plot the error types frequency
    plt.figure(figsize=(10, 6))
    sns.barplot(x=error_counts.index, y=error_counts.values, palette='viridis')
    plt.title("Error Types Frequency")
    plt.xlabel("Error Type")
    plt.ylabel("Frequency")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the plot image to the static directory
    plot_image_path = os.path.join(settings.BASE_DIR, 'underlog/static/images/error_types_plot.png')
    plt.savefig(plot_image_path)
    #################################

    logs_df['error_type'] = logs_df['message'].apply(categorize_error)
    error_counts = logs_df['error_type'].value_counts()
    plt.figure(figsize=(12, 6))  # Set the figure size
    explode = [0.1 if count < 5 else 0 for count in error_counts]  # Adjust based on counts

    error_counts.plot(
        kind='pie',
        autopct=lambda p: f'{p:.1f}%\n({int(p * sum(error_counts) / 100)})',  # Percent + counts
        startangle=90,
        explode=explode,
        textprops={'fontsize': 12},  # Larger font for better readability
        wedgeprops={'edgecolor': 'black'}   # Apply a color scheme
    )
    plt.title("Distribution of Error Types")
    plt.ylabel("")  # Remove the y-label for a cleaner appearance
    plt.legend(title="Error Types", loc="upper right", bbox_to_anchor=(1.3, 0.9), fontsize=10, title_fontsize=12)
    plt.tight_layout()
    # Save the pie chart as an image
    error_types_plot_path = os.path.join(settings.BASE_DIR, 'underlog/static/images/error_types.png')
    plt.savefig(error_types_plot_path)
    plt.close()

    ###################################
    ###################################

    top_error_messages = logs_df['message'].value_counts().head(10)

    ###################################
    # Step 4: Pass the data and plot to the template


    #################Serverity of logs CRITICAL, INFO, ERROR, WARN ##############################
    logs_df['severity'] = logs_df['message'].str.extract(r'\b(ERROR|INFO|WARN|CRITICAL)\b', expand=False)

# Count the severity levels
    severity_counts = logs_df['severity'].value_counts()

    # Plot the distribution of severity levels
    plt.figure(figsize=(14, 6))
    sns.barplot(x=severity_counts.index, y=severity_counts.values, palette='muted')
    plt.title("Distribution of Severity Levels")
    plt.xlabel("Severity Level")
    plt.ylabel("Frequency")
    severity_plot_path = os.path.join(settings.BASE_DIR, 'underlog/static/images/severity_distribution.png')
    plt.savefig(severity_plot_path)
    plt.close()
 ###############################################



    context = {
        'error_counts': error_counts,  # Error type frequency counts
        'plot_image': 'images/error_types_plot.png',
        'error_types_plot': 'images/error_types.png',  # Path to the saved plot
        'error_logs': error_logs,  # Logs with categorized error types
        'database_error_count': database_error_count,
        'network_error_count' : network_error_count,
        'Auth_count' : Auth_count,
        'general_count' :general_count,
        'config_count' :config_count,
        'top_error_messages': top_error_messages,
        'client_count': client_count,
        'ip_error_plot' : 'images/ip_error_plot.png',
#moved from trend

        'top_sources_plot': 'images/img.png',
        'error_frequency_plot': 'images/error_frequency.png',
        'error_frequency': error_frequency_sorted, #Error Frequency Data display
        'severity_image': 'images/severity_distribution.png',
        'source_image': 'images/error_sources.png',
       
    }
    
    return render(request, 'temp/show.html', context)

def errorcategory(request):

    logs_df = pd.read_csv(csv_path)

    # Step 2: Categorize errors
    def categorize_error(message):
        """Function to categorize error messages based on keywords."""
        if 'timeout' in message.lower() or 'connection' in message.lower():
            return 'NetworkError'
        elif 'auth' in message.lower() or 'unauthorized' in message.lower() or 'permission denied' in message.lower():
            return 'AuthenticationError'
        elif 'database' in message.lower() or 'db' in message.lower():
            return 'DatabaseError'
        elif 'config' in message.lower() or 'missing' in message.lower() or 'invalid' in message.lower() or 'not found' in message.lower() or 'error loading config' in message.lower() or 'misconfigured' in message.lower():
            return 'ConfigurationError'
        elif '400 bad request' in message.lower():
            return '404badrequest'
      
        else:
            return 'GeneralError'''
        
    logs_df['error_category'] = logs_df['message'].apply(categorize_error)
    database_error_count = len(logs_df[logs_df['error_category'] == 'DatabaseError'])
    network_error_count = len(logs_df[logs_df['error_category'] == 'NetworkError'])
    Auth_count = len(logs_df[logs_df['error_category'] == 'AuthenticationError'])
    general_count = len(logs_df[logs_df['error_category'] == 'GeneralError'])
    config_count = len(logs_df[logs_df['error_category'] == 'ConfigurationError'])
    client_count = len(logs_df[logs_df['error_category'] == '404badrequest'])

    total = database_error_count + network_error_count + Auth_count + general_count + config_count + client_count

    


    def categorize_errors(logs_df):
        """Apply the categorization function to each log entry."""
        # Filter out logs containing 'error' keyword
        error_logs = logs_df[logs_df['message'].str.contains('error', case=False, na=False)]
        
        # Apply categorization to each error message
        error_logs['error_type'] = error_logs['message'].apply(categorize_error)
        
        # Count occurrences of each error type
        error_counts = error_logs['error_type'].value_counts()
        
        return error_counts, error_logs

    # Call the categorize function to get the error counts and categorized logs
    error_counts, error_logs = categorize_errors(logs_df)

    logs_df['error_type'] = logs_df['message'].apply(categorize_error)
    error_counts = logs_df['error_type'].value_counts()
    plt.figure(figsize=(6, 6))  # Set the figure size
    explode = [0.1 if count < 5 else 0 for count in error_counts]  # Adjust based on counts


    top_error_messages = logs_df['message'].value_counts().head(10)


    context = {
        'error_counts': error_counts,      
        'database_error_count': database_error_count,
        'network_error_count' : network_error_count,
        'Auth_count' : Auth_count,
        'general_count' :general_count,
        'config_count' :config_count,
        'top_error_messages': top_error_messages,
        'client_count': client_count,
 
        'total': total
 
    }
    

    # Return the response with data to the template
    return render(request, 'temp/errorcategory.html', context)

def network(request):

    logs_df = pd.read_csv(csv_path)
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')
    
    if logs_df['timestamp'].isnull().any():
       
        logs_df = logs_df.dropna(subset=['timestamp'])

    network_error_logs = logs_df[logs_df['message'].str.contains('timeout|connection', case=False, na=False)]
    cnt = len(network_error_logs)
    context = {
        'network_error_logs': network_error_logs,
        'cnt' : cnt
    }
    
    return render(request, 'temp/network.html', context)

def database(request):

    logs_df = pd.read_csv(csv_path)
    
    # Ensure timestamp is properly formatted
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')
    if logs_df['timestamp'].isnull().any():
        print("Invalid timestamps found. Dropping these rows.")
        logs_df = logs_df.dropna(subset=['timestamp'])

    # Filter database errors
    database_error_logs = logs_df[logs_df['message'].str.contains('database|db', case=False, na=False)]
    
    
    cnt = len(database_error_logs)

    #################specific database error############################
    def categorize_database_error(message):
  
        message = message.lower()
        
        if 'timeout' in message or 'connection' in message:
            return 'DatabaseConnectionError'
        elif 'syntax' in message or 'query' in message or 'invalid' in message:
            return 'DatabaseQueryError'
        elif 'deadlock' in message:
            return 'DatabaseDeadlockError'
        elif 'foreign key' in message or 'constraint' in message:
            return 'DatabaseConstraintError'
        elif 'transaction' in message:
            return 'DatabaseTransactionError'
        
        else:
            return 'GeneralDatabaseError'
    logs_df['database_error_category'] = logs_df['message'].apply(categorize_database_error)


    context = {'database_error_logs': database_error_logs,
               'cnt':cnt
               
               
               }
    return render(request, 'temp/database.html', context)

def general(request):

    logs_df = pd.read_csv(csv_path)
    
    # Ensure timestamp is properly formatted
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')

    if logs_df['timestamp'].isnull().any():
        logs_df = logs_df.dropna(subset=['timestamp'])

    def categorize_error(message):
        """Function to categorize error messages based on keywords."""
        if 'timeout' in message.lower() or 'connection' in message.lower():
            return 'NetworkError'
        elif 'auth' in message.lower() or 'unauthorized' in message.lower():
            return 'AuthenticationError'
        elif 'database' in message.lower() or 'db' in message.lower():
            return 'DatabaseError'
        elif '400 bad request' in message.lower():
            return 'ClientSideIssue'
        elif 'config' in message.lower() or 'missing' in message.lower() or 'invalid' in message.lower() or 'not found' in message.lower() or 'error loading config' in message.lower() or 'misconfigured' in message.lower():
            return 'ConfigurationError'
        else:
            return 'GeneralError'''
       
    

    # Filter general errors (errors that are not network, authentication, or database-related)
    general_error_logs = logs_df[logs_df['message'].apply(lambda msg: categorize_error(msg) == 'GeneralError')]
    general_error_logs['formatted_timestamp'] = general_error_logs['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

    
    cnt = len(general_error_logs)

    context = {'general_error_logs': general_error_logs,
               'cnt' : cnt
               
               
               }
    return render(request, 'temp/general.html', context)

def auth(request):

    logs_df = pd.read_csv(csv_path)
    
    # Ensure timestamp is properly formatted
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')
    if logs_df['timestamp'].isnull().any():
        print("Invalid timestamps found. Dropping these rows.")
        logs_df = logs_df.dropna(subset=['timestamp'])

    auth_error_logs = logs_df[logs_df['message'].str.contains('auth|unauthorized', case=False, na=False)]
    cnt = len(auth_error_logs)    

    # Render database error template
    context = {'auth_error_logs': auth_error_logs,
               'cnt':cnt,
       
               
               }
    return render(request, 'temp/auth.html', context)


def configuration(request):



    logs_df = pd.read_csv(csv_path)
    
    # Ensure timestamp is properly formatted
    logs_df['timestamp'] = pd.to_datetime(logs_df['timestamp'], errors='coerce')
    if logs_df['timestamp'].isnull().any():
        print("Invalid timestamps found. Dropping these rows.")
        logs_df = logs_df.dropna(subset=['timestamp'])

    conf_error_logs = logs_df[logs_df['message'].str.contains('config|missing|invalid|notfound|error loading config|misconfigured', case=False, na=False)]
    cnt = len(conf_error_logs)

    #rare error logs
   
    

    # Render database error template
    context = {'conf_error_logs': conf_error_logs,
               'cnt':cnt,
       
               
               }
    return render(request, 'temp/configuration.html', context)
    pass


def send_telegram_message(bot_token, chat_id, message):

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, data=params)
    return response.json()

def send_email_view(request):

    if request.method == 'POST':
    
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        recipient = request.POST.get('recipient')
        recipient_list = [recipient] if recipient else []

        if recipient_list:
            try:
                send_mail(subject, message, settings.EMAIL_HOST_USER, recipient_list)
                return HttpResponse("Email sent to " + recipient)
            except Exception as e:
                return HttpResponse(f"Error sending email: {e}")
        else:
            return HttpResponse("No recipient provided.")


    return render(request, 'temp/email.html')


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')


        if username == 'admin' and password == 'admin':
            return redirect('logs')
        else:
            return redirect('login')
    return render(request, 'temp/login.html')


def source_cat(request):
    logs_df = pd.read_csv(csv_path)

    source_counts = logs_df['source'].value_counts()
    top_sources = source_counts.head(10)

    context = {

        'top_sources': top_sources
    }

    return render(request, 'temp/source_cat.html', context)
