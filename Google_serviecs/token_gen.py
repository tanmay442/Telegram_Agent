import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def generate_google_token_simple(credentials_file='Google_serviecs/credentials.json', token_file='Google_serviecs/token.json'):
 
    
    # Scopes for full access to Tasks, Calendar, and Gmail
    SCOPES = [
        'https://www.googleapis.com/auth/tasks',       # Full Tasks access
        'https://www.googleapis.com/auth/calendar',    # Full Calendar access
        'https://mail.google.com/'                     # Full Gmail access
    ]
    
    creds = None

    # 1. Load existing token if available
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # 2. Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        print("Existing token expired, attempting to refresh...")
        creds.refresh(Request())
        print("Token refreshed successfully.")

    # 3. Perform full authorization if no valid/refreshed token exists
    if not creds or not creds.valid:
        print("Starting full authorization flow...")
        
        # Check if the credentials file exists (simple relative path check)
        if not os.path.exists(credentials_file):
            print(f"ERROR: Credentials file '{credentials_file}' not found.")
            print(f"Please ensure '{credentials_file}' is in the current working directory.")
            print(credentials_file)
            return
        

        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        
        # Opens a browser for user login and consent
        creds = flow.run_local_server(port=8080, success_message="Authorization complete. You can close this tab.")
        
        # Save the new credentials
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"\nSuccessfully generated and saved new token to '{token_file}'.")
    else:
        print(f"Valid token found at '{token_file}'. No action needed.")


# --- Example of how to call the function ---
if __name__ == '__main__':
    # Make sure to run this script from the directory 
    # where your 'credentials.json' file is located.
    generate_google_token_simple()