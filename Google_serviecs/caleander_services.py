import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request # Needed for token refresh
from typing import List, Optional

# The scope MUST match the scope used to generate your token.json
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar'] 
CALENDAR_ID = 'primary' # Use the user's primary calendar

def get_calendar_service(token_file: str = 'token.json'):
    """Helper function to load credentials and build the Calendar service."""
    try:
        creds = Credentials.from_authorized_user_file(token_file, CALENDAR_SCOPES)
        
        # Check and refresh if expired
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        
        return build('calendar', 'v3', credentials=creds)
        
    except FileNotFoundError:
        print(f"ERROR: Token file '{token_file}' not found. Run the generator script first.")
        return None
    except Exception as e:
        print(f"ERROR creating Calendar service: {e}")
        return None

def create_event(token_file: str, event_details: List[str]):
    """
    Creates a new event on the user's primary calendar.

    Args:
        token_file (str): Path to the generated token.json.
        event_details (List[str]): List containing:
            [summary, start_time_rfc3339, end_time_rfc3339, attendees_str (comma-sep), optional_meet_link_or_description]
            Example start_time: '2025-10-01T10:00:00Z' (for 10:00 AM UTC)
    """
    service = get_calendar_service(token_file)
    if not service:
        return

    try:
        # Gracefully unpack list, providing default placeholders if info is missing
        summary = event_details[0] if len(event_details) > 0 else "Quick Meeting"
        start_time = event_details[1] if len(event_details) > 1 else (datetime.datetime.utcnow().isoformat() + 'Z')
        end_time = event_details[2] if len(event_details) > 2 else (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + 'Z'
        attendees_str = event_details[3] if len(event_details) > 3 else ""
        meet_link_or_desc = event_details[4] if len(event_details) > 4 else "Automatically created event."
        
        # Convert comma-separated string to list of attendee dictionaries
        attendees = [{'email': a.strip()} for a in attendees_str.split(',') if a.strip()]

        event = {
            'summary': summary,
            'description': meet_link_or_desc,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time, 'timeZone': 'UTC'},
            'attendees': attendees,
            # Conference data request: This tells Google to automatically create a Meet link.
            'conferenceData': {
                'createRequest': {
                    'requestId': f"py-meet-{datetime.datetime.now().timestamp()}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        }

        event_result = service.events().insert(
            calendarId=CALENDAR_ID, 
            body=event,
            conferenceDataVersion=1 # Must be 1 to enable Meet link creation
        ).execute()
        
        print(f"\n[EVENT SUCCESS] Event created: {event_result['summary']}")
        print(f"   ID: {event_result['id']}")
        print(f"   Link: {event_result.get('htmlLink')}")
        print(f"   Meet Link: {event_result.get('conferenceData', {}).get('uri', 'N/A')}")


    except HttpError as error:
        print(f"\n[EVENT API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[EVENT GENERIC ERROR] An unexpected error occurred: {e}")

def view_events(token_file: str, view_details: List[str]):
    """
    Retrieves upcoming events from the user's primary calendar.

    Args:
        token_file (str): Path to the generated token.json.
        view_details (List[str]): List containing [count_str, optional_start_time_rfc3339].
                                  Example: ['5', '2025-10-01T00:00:00Z']
    """
    service = get_calendar_service(token_file)
    if not service:
        return

    try:
        # Gracefully unpack list, providing default placeholders
        try:
            max_results = int(view_details[0]) if len(view_details) > 0 else 5
        except (ValueError, IndexError):
            max_results = 5
            
        # Time minimum: defaults to now (UTC) if not provided
        time_min = view_details[1] if len(view_details) > 1 else (datetime.datetime.utcnow().isoformat() + 'Z')

        print(f"\n[VIEW EVENTS] Searching for {max_results} events starting from: {time_min}")
        
        events_result = service.events().list(
            calendarId=CALENDAR_ID, 
            timeMin=time_min,
            maxResults=max_results, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print("No upcoming events found.")
            return

        print(f"Found {len(events)} event(s):")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            
            print("-" * 30)
            print(f"ID: {event['id']}")
            print(f"Title: {event.get('summary', 'No Title')}")
            print(f"Start: {start}")
            print(f"End: {end}")
            print(f"Organizer: {event['organizer'].get('email', 'N/A')}")

    except HttpError as error:
        print(f"\n[VIEW API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[VIEW GENERIC ERROR] An unexpected error occurred: {e}")

def delete_event(token_file: str, delete_details: List[str]):
    """
    Deletes a specific event from the user's primary calendar.

    Args:
        token_file (str): Path to the generated token.json.
        delete_details (List[str]): List containing [event_id].
    """
    service = get_calendar_service(token_file)
    if not service:
        return
        
    try:
        if not delete_details:
            print("[DELETE ERROR] Event ID is required.")
            return

        event_id = delete_details[0]
        
        print(f"\n[DELETE EVENT] Attempting to delete event ID: {event_id}")

        # The delete function returns a 204 No Content on success (no body)
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        
        print(f"Successfully deleted event with ID: {event_id}")

    except HttpError as error:
        # 404 means the event wasn't found (which is common)
        if error.resp.status == 404:
            print(f"[DELETE API ERROR] Event ID '{event_id}' not found.")
        else:
            print(f"\n[DELETE API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[DELETE GENERIC ERROR] An unexpected error occurred: {e}")


# --- Demonstration ---
if __name__ == '__main__':
    # NOTE: These examples require a valid 'token.json' 
    # and the 'google-auth...' libraries to be installed.
    
    TOKEN_FILE_PATH = 'token.json' 
    
    # --- Helper for Demo Dates ---
    now = datetime.datetime.utcnow().replace(microsecond=0)
    start_time_str = (now + datetime.timedelta(minutes=5)).isoformat() + 'Z'
    end_time_str = (now + datetime.timedelta(minutes=35)).isoformat() + 'Z'
    
    # --- 1. CREATE EVENT Example ---
    # event_details: [summary, start_time_rfc3339, end_time_rfc3339, attendees_str, description]
    print("\n" + "="*50)
    print("STARTING CREATE EVENT EXAMPLE")
    
    event_details = [
        "Python API Test Event", 
        start_time_str,             # 5 minutes from now
        end_time_str,               # 35 minutes from now
        "attendee1@example.com, attendee2@example.com", # Replace with real emails
        "Testing event creation with automatic Google Meet link."
    ]
    create_event(TOKEN_FILE_PATH, event_details)

    # --- 2. VIEW EVENTS Example ---
    # view_details: [count, optional_start_time_rfc3339]
    print("\n" + "="*50)
    print("STARTING VIEW EVENTS EXAMPLE")
    
    # View 5 upcoming events from now
    view_events(TOKEN_FILE_PATH, ['5'])

    # --- 3. DELETE EVENT Example ---
    # delete_details: [event_id]
    print("\n" + "="*50)
    print("STARTING DELETE EVENT EXAMPLE")
    
    EVENT_ID_TO_DELETE = 'YOUR_EVENT_ID_HERE' # <<< REPLACE THIS!

    if EVENT_ID_TO_DELETE != 'YOUR_EVENT_ID_HERE':
        delete_event(TOKEN_FILE_PATH, [EVENT_ID_TO_DELETE])
    else:
        print("Please replace 'YOUR_EVENT_ID_HERE' with a real event ID from the VIEW EVENTS output to test deletion.")
        
    print("\n" + "="*50)