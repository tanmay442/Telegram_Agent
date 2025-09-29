import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Optional

# The scope MUST match the scope used to generate your token.json
GMAIL_SCOPES = ['https://mail.google.com/'] 

def get_gmail_service(token_file: str = 'token.json'):
    """Helper function to load credentials and build the Gmail service."""
    try:
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        
        return build('gmail', 'v1', credentials=creds)
        
    except FileNotFoundError:
        print(f"ERROR: Token file '{token_file}' not found. Run the generator script first.")
        return None
    except Exception as e:
        print(f"ERROR creating Gmail service: {e}")
        return None

def draft_email(token_file: str, email_details: List[str]):
    """
    Creates a draft email in the user's Gmail account.

    Args:
        token_file (str): Path to the generated token.json.
        email_details (List[str]): List containing [receiver_address, subject, content].
                                   Example: ['recipient@example.com', 'Test Subject', 'Body content']
    """
    service = get_gmail_service(token_file)
    if not service:
        return

    try:
        # Gracefully unpack list, providing default placeholders if info is missing
        receiver = email_details[0] if len(email_details) > 0 else "MISSING_RECEIVER@example.com"
        subject = email_details[1] if len(email_details) > 1 else "No Subject Provided"
        content = email_details[2] if len(email_details) > 2 else "Empty body content."
        
        # 1. Create a MIME message
        message = MIMEText(content)
        message['to'] = receiver
        message['subject'] = subject
        
        # 2. Encode to base64 for the Gmail API
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # 3. Create the draft
        draft_body = {'message': {'raw': raw_message}}
        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        
        print(f"\n[DRAFT SUCCESS] Draft created with ID: {draft['id']}")
        print(f"   To: {receiver}")
        print(f"   Subject: {subject}")

    except IndexError:
        print("\n[DRAFT ERROR] The 'email_details' list must contain at least [receiver_address].")
    except HttpError as error:
        print(f"\n[DRAFT API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[DRAFT GENERIC ERROR] An unexpected error occurred: {e}")

def read_emails(token_file: str, query_details: List[str]):
    """
    Reads a list of emails based on provided query details.

    Args:
        token_file (str): Path to the generated token.json.
        query_details (List[str]): List containing [count, query_string].
                                   Example: ['5', 'is:unread from:amazon']
                                   
                                   If list is empty, defaults to 5 emails in the Inbox.
                                   Common queries: 'is:read', 'is:unread', 'label:WORK', 'from:x@y.com'
    """
    service = get_gmail_service(token_file)
    if not service:
        return

    try:
        # Gracefully unpack list, providing default placeholders
        try:
            max_results = int(query_details[0]) if len(query_details) > 0 else 5
        except (ValueError, IndexError):
            max_results = 5
        
        query = query_details[1] if len(query_details) > 1 else "in:inbox" # Default to all in inbox

        print(f"\n[READ EMAILS] Searching for {max_results} emails with query: '{query}'")
        
        # List messages
        response = service.users().messages().list(
            userId='me', 
            maxResults=max_results, 
            q=query
        ).execute()
        
        messages = response.get('messages', [])
        
        if not messages:
            print("No messages found matching the criteria.")
            return

        print(f"Found {len(messages)} message(s). Retrieving details...")
        for msg in messages:
            # Get message metadata (faster than full body)
            msg_details = service.users().messages().get(
                userId='me', 
                id=msg['id'], 
                format='metadata'
            ).execute()
            
            headers = msg_details['payload']['headers']
            
            # Helper to find header values
            def get_header(name):
                return next((h['value'] for h in headers if h['name'] == name), 'N/A')

            snippet = msg_details.get('snippet', 'No snippet available')
            
            print("-" * 30)
            print(f"ID: {msg['id']}")
            print(f"From: {get_header('From')}")
            print(f"Subject: {get_header('Subject')}")
            print(f"Date: {get_header('Date')}")
            print(f"Snippet: {snippet[:70]}...")

    except HttpError as error:
        print(f"\n[READ API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[READ GENERIC ERROR] An unexpected error occurred: {e}")

def flag_or_label_mail(token_file: str, update_details: List[str]):
    """
    Flags (Stars) or labels a specific email by ID.

    Args:
        token_file (str): Path to the generated token.json.
        update_details (List[str]): [mail_id, action, value].
            - action: 'star', 'unstar', 'mark_read', 'mark_unread', 'add_label', 'remove_label'
            - value: (Required for 'add_label'/'remove_label') The custom label name.
    """
    service = get_gmail_service(token_file)
    if not service:
        return

    try:
        # Gracefully unpack list
        if len(update_details) < 2:
            print("\n[UPDATE ERROR] Insufficient arguments. Requires at least [mail_id, action].")
            return
            
        mail_id = update_details[0]
        action = update_details[1].lower()
        value = update_details[2] if len(update_details) > 2 else ""

        print(f"\n[UPDATE MAIL] Mail ID: {mail_id}, Action: {action}, Value: {value}")
        
        # Prepare the modification body
        body = {'addLabelIds': [], 'removeLabelIds': []}
        
        if action == 'star':
            body['addLabelIds'].append('STARRED')
        elif action == 'unstar':
            body['removeLabelIds'].append('STARRED')
        elif action == 'mark_read':
            body['removeLabelIds'].append('UNREAD')
        elif action == 'mark_unread':
            body['addLabelIds'].append('UNREAD')
        elif action == 'add_label':
            if not value: raise ValueError("Action 'add_label' requires a label name (value).")
            # Note: For custom labels, you need the Label ID. 
            # We assume the user is using an existing label name as 'value'.
            # A full implementation would first call users().labels().list() to find the ID.
            # For simplicity, we use the name as the ID, which works for system labels and sometimes custom ones.
            body['addLabelIds'].append(value.upper()) # Gmail labels are often uppercase
        elif action == 'remove_label':
            if not value: raise ValueError("Action 'remove_label' requires a label name (value).")
            body['removeLabelIds'].append(value.upper())
        else:
            print(f"Unknown action: {action}")
            return

        # Execute the modification
        service.users().messages().modify(
            userId='me', 
            id=mail_id, 
            body=body
        ).execute()

        print(f"Successfully applied action '{action}' to message ID: {mail_id}")

    except HttpError as error:
        print(f"\n[UPDATE API ERROR] An error occurred (e.g., label not found): {error}")
    except ValueError as e:
        print(f"\n[UPDATE VALIDATION ERROR] {e}")
    except Exception as e:
        print(f"\n[UPDATE GENERIC ERROR] An unexpected error occurred: {e}")


# --- Demonstration ---
if __name__ == '__main__':
    # NOTE: These examples will only work if you have a valid 'token.json' 
    # file in the same directory as this script.
    
    TOKEN_FILE_PATH = 'token.json' 

    # --- 1. DRAFT EMAIL Example ---
    # email_details: [receiver_address, subject, content]
    print("\n" + "="*50)
    print("STARTING DRAFT EMAIL EXAMPLE")
    
    draft_details = [
        "user@example.com", 
        "Automated Test Draft", 
        "This is a test body content generated by the Python script."
    ]
    draft_email(TOKEN_FILE_PATH, draft_details)

    # --- 2. READ EMAILS Example ---
    # query_details: [count, query_string]
    print("\n" + "="*50)
    print("STARTING READ EMAILS EXAMPLE")
    
    # Example 1: Read the 3 most recent UNREAD emails
    read_details_unread = ['3', 'is:unread']
    read_emails(TOKEN_FILE_PATH, read_details_unread)
    
    # Example 2: Read 2 emails from a specific sender (replace with a real sender you have)
    # read_details_sender = ['2', 'from:support@github.com']
    # read_emails(TOKEN_FILE_PATH, read_details_sender)

    # --- 3. FLAG OR LABEL Example ---
    # update_details: [mail_id, action, value (optional)]
    print("\n" + "="*50)
    print("STARTING FLAG/LABEL EMAIL EXAMPLE")
    
    # NOTE: You MUST replace 'YOUR_MESSAGE_ID_HERE' with an actual Mail ID 
    # from the output of the 'read_emails' function or from your Gmail API console.
    
    MESSAGE_ID_TO_UPDATE = '1999384975ca8ea8' 
    
    if MESSAGE_ID_TO_UPDATE != 'YOUR_MESSAGE_ID_HERE':
        # Example 1: Flag (Star) the email
        flag_details_star = [MESSAGE_ID_TO_UPDATE, 'star']
        flag_or_label_mail(TOKEN_FILE_PATH, flag_details_star)
        
        # Example 2: Mark the email as Read
        flag_details_read = [MESSAGE_ID_TO_UPDATE, 'mark_read']
        flag_or_label_mail(TOKEN_FILE_PATH, flag_details_read)

        # Example 3: Add a custom label (e.g., 'WORK' or a label that exists in your account)
        # flag_details_label = [MESSAGE_ID_TO_UPDATE, 'add_label', 'WORK']
        # flag_or_label_mail(TOKEN_FILE_PATH, flag_details_label)
    else:
        print("Please replace 'YOUR_MESSAGE_ID_HERE' in the code to test FLAG/LABEL function.")
        
    print("\n" + "="*50)