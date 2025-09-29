import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request # Needed for token refresh
from typing import List, Optional

# The scope MUST match the scope used to generate your token.json
TASKS_SCOPES = ['https://www.googleapis.com/auth/tasks'] 

# Helper to find the default task list ID (usually 'My Tasks')
def get_default_tasklist_id(service):
    """Retrieves the ID of the first task list found (usually 'My Tasks')."""
    try:
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get('items', [])
        if items:
            # We'll use the first one as the default, but a real-world app 
            # might search by title ('My Tasks').
            return items[0]['id']
        return None
    except Exception as e:
        print(f"Error getting task list ID: {e}")
        return None

def get_tasks_service(token_file: str = 'token.json'):
    """Helper function to load credentials and build the Tasks service."""
    try:
        creds = Credentials.from_authorized_user_file(token_file, TASKS_SCOPES)
        
        # Check and refresh if expired
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        
        return build('tasks', 'v1', credentials=creds)
        
    except FileNotFoundError:
        print(f"ERROR: Token file '{token_file}' not found. Run the generator script first.")
        return None
    except Exception as e:
        print(f"ERROR creating Tasks service: {e}")
        return None

def create_task_list(token_file: str, list_details: List[str]):
    """
    Creates a new Task List (a container for tasks).

    Args:
        token_file (str): Path to the generated token.json.
        list_details (List[str]): List containing [title].
    """
    service = get_tasks_service(token_file)
    if not service:
        return

    try:
        title = list_details[0] if len(list_details) > 0 else "New API List"
        
        result = service.tasklists().insert(
            body={'title': title}
        ).execute()
        
        print(f"\n[TASK LIST SUCCESS] Created new Task List: {result['title']}")
        print(f"   ID: {result['id']}")

    except IndexError:
        print("[TASK LIST ERROR] List title is required.")
    except HttpError as error:
        print(f"\n[TASK LIST API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[TASK LIST GENERIC ERROR] An unexpected error occurred: {e}")

def create_task(token_file: str, task_details: List[str]):
    """
    Creates a new task in a specified (or default) task list.

    Args:
        token_file (str): Path to the generated token.json.
        task_details (List[str]): List containing:
            [title, notes_or_description, optional_due_date_rfc3339, optional_task_list_id]
            Due Date Example: '2025-10-01T10:00:00.000Z'
    """
    service = get_tasks_service(token_file)
    if not service:
        return

    try:
        default_list_id = get_default_tasklist_id(service)
        if not default_list_id:
            print("ERROR: Could not find any task list ID.")
            return

        # Gracefully unpack list, providing default placeholders
        title = task_details[0] if len(task_details) > 0 else "New Task Title"
        notes = task_details[1] if len(task_details) > 1 else ""
        due_date = task_details[2] if len(task_details) > 2 else "" # RFC3339 format
        task_list_id = task_details[3] if len(task_details) > 3 else default_list_id
        
        task_body = {'title': title, 'notes': notes}
        if due_date:
            task_body['due'] = due_date # Must be in RFC3339 format with time component
        
        result = service.tasks().insert(
            tasklist=task_list_id, 
            body=task_body
        ).execute()
        
        print(f"\n[TASK SUCCESS] Created new Task: {result['title']}")
        print(f"   ID: {result['id']}")
        print(f"   List ID: {task_list_id}")

    except IndexError:
        print("[TASK ERROR] Task title is required.")
    except HttpError as error:
        print(f"\n[TASK API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[TASK GENERIC ERROR] An unexpected error occurred: {e}")

def view_tasks(token_file: str, view_details: List[str]):
    """
    Retrieves tasks based on criteria (pending, completed, due, etc.).

    Args:
        token_file (str): Path to the generated token.json.
        view_details (List[str]): List containing:
            [count_str, optional_status, optional_due_time_min_rfc3339, optional_task_list_id]
            - status: 'needsAction' (Pending, default), 'completed'
            - due_time_min: RFC3339 time string to filter for tasks due *after* this time.
    """
    service = get_tasks_service(token_file)
    if not service:
        return

    try:
        default_list_id = get_default_tasklist_id(service)
        if not default_list_id:
            print("ERROR: Could not find any task list ID.")
            return

        # Gracefully unpack list, providing default placeholders
        try:
            max_results = int(view_details[0]) if len(view_details) > 0 else 10
        except (ValueError, IndexError):
            max_results = 10
            
        status = view_details[1] if len(view_details) > 1 else 'needsAction' # Default: Pending
        due_min = view_details[2] if len(view_details) > 2 else ""
        task_list_id = view_details[3] if len(view_details) > 3 else default_list_id

        print(f"\n[VIEW TASKS] Searching for {max_results} tasks (Status: {status}) in list ID: {task_list_id}")
        
        # Build the optional parameters for the list call
        optional_params = {
            'maxResults': max_results,
            'showCompleted': (status == 'completed'),
            'showDeleted': False,
            'showHidden': False,
            'dueMin': due_min if due_min else None,
        }
        
        # If showing pending tasks, filter by status
        if status == 'needsAction':
            optional_params['showCompleted'] = False 

        # Remove None values
        optional_params = {k: v for k, v in optional_params.items() if v is not None}
        
        tasks_result = service.tasks().list(
            tasklist=task_list_id, 
            **optional_params
        ).execute()
        
        tasks = tasks_result.get('items', [])
        
        if not tasks:
            print("No tasks found matching the criteria.")
            return

        print(f"Found {len(tasks)} task(s):")
        for task in tasks:
            print("-" * 30)
            print(f"ID: {task['id']}")
            print(f"Title: {task.get('title', 'No Title')}")
            print(f"Status: {task.get('status', 'N/A')}")
            print(f"Due: {task.get('due', 'N/A')}")

    except HttpError as error:
        print(f"\n[VIEW API ERROR] An error occurred: {error}")
    except Exception as e:
        print(f"\n[VIEW GENERIC ERROR] An unexpected error occurred: {e}")

def modify_task(token_file: str, update_details: List[str]):
    """
    Modifies an existing task (e.g., completes it, postpones/updates due date, deletes).

    Args:
        token_file (str): Path to the generated token.json.
        update_details (List[str]): List containing:
            [action, task_id, optional_task_list_id, optional_new_value]
            - action: 'complete', 'uncomplete', 'delete', 'postpone', 'update_title'
            - new_value: (Required for 'postpone'/'update_title') New due date (RFC3339) or new title.
    """
    service = get_tasks_service(token_file)
    if not service:
        return

    try:
        # Check for minimum required arguments
        if len(update_details) < 2:
            print("[UPDATE ERROR] Insufficient arguments. Requires at least [action, task_id].")
            return
            
        action = update_details[0].lower()
        task_id = update_details[1]
        
        # Get default list ID
        default_list_id = get_default_tasklist_id(service)
        if not default_list_id:
            print("ERROR: Could not find any task list ID.")
            return
            
        task_list_id = update_details[2] if len(update_details) > 2 else default_list_id
        new_value = update_details[3] if len(update_details) > 3 else ""

        print(f"\n[MODIFY TASK] Task ID: {task_id}, Action: {action}, List ID: {task_list_id}")

        # --- Handle Deletion Separately (uses a different API method) ---
        if action == 'delete':
            service.tasks().delete(tasklist=task_list_id, task=task_id).execute()
            print(f"Successfully **DELETED** task ID: {task_id}")
            return
            
        # --- Handle Update Actions (GET the task first to modify it) ---
        task = service.tasks().get(tasklist=task_list_id, task=task_id).execute()
        
        if action == 'complete':
            task['status'] = 'completed'
            task['completed'] = datetime.datetime.utcnow().isoformat() + 'Z' # Set completed time
            print(f"Marking task ID {task_id} as COMPLETED.")
        elif action == 'uncomplete':
            task['status'] = 'needsAction'
            task.pop('completed', None) # Remove completed timestamp
            print(f"Marking task ID {task_id} as PENDING.")
        elif action == 'postpone':
            if not new_value: raise ValueError("Action 'postpone' requires a new due date (RFC3339 format).")
            task['due'] = new_value
            print(f"Postponing task ID {task_id} to {new_value}.")
        elif action == 'update_title':
            if not new_value: raise ValueError("Action 'update_title' requires a new title string.")
            task['title'] = new_value
            print(f"Updating task ID {task_id} title to: {new_value}.")
        else:
            print(f"Unknown modification action: {action}")
            return

        # Execute the update
        service.tasks().update(
            tasklist=task_list_id, 
            task=task_id, 
            body=task
        ).execute()

        print(f"Successfully executed action '{action}' on task ID: {task_id}")

    except HttpError as error:
        print(f"\n[UPDATE API ERROR] An error occurred (e.g., Task ID not found): {error}")
    except ValueError as e:
        print(f"\n[UPDATE VALIDATION ERROR] {e}")
    except Exception as e:
        print(f"\n[UPDATE GENERIC ERROR] An unexpected error occurred: {e}")


# --- Demonstration ---
if __name__ == '__main__':
    TOKEN_FILE_PATH = 'token.json' 

    # --- Helper for Demo Dates ---
    tomorrow = datetime.datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    tomorrow_str = tomorrow.isoformat() + 'Z'
    day_after_str = (tomorrow + datetime.timedelta(days=1)).isoformat() + 'Z'

    # --- 1. CREATE TASK LIST Example (Optional) ---
    print("\n" + "="*50)
    print("STARTING CREATE TASK LIST EXAMPLE")
    # create_task_list(TOKEN_FILE_PATH, ["New Project Ideas"])

    # --- 2. CREATE TASK Example ---
    # task_details: [title, notes, optional_due_date_rfc3339, optional_task_list_id]
    print("\n" + "="*50)
    print("STARTING CREATE TASK EXAMPLE")
    
    # Task 1: New task due tomorrow
    task1_details = [
        "Pay Bills", 
        "Check all recurring subscriptions and settle them.", 
        tomorrow_str 
    ]
    create_task(TOKEN_FILE_PATH, task1_details) # This will create the task

    # --- 3. VIEW TASKS Example ---
    # view_details: [count, optional_status, optional_due_time_min_rfc3339]
    print("\n" + "="*50)
    print("STARTING VIEW PENDING TASKS EXAMPLE")
    
    # View 5 pending tasks
    view_tasks(TOKEN_FILE_PATH, ['5', 'needsAction']) 

    print("\n" + "="*50)
    print("STARTING VIEW UPCOMING TASKS (Due after now) EXAMPLE")
    # View 5 tasks due after right now
    view_tasks(TOKEN_FILE_PATH, ['5', 'needsAction', datetime.datetime.utcnow().isoformat() + 'Z']) 

    # --- 4. MODIFY TASK Example ---
    # update_details: [action, task_id, optional_task_list_id, optional_new_value]
    print("\n" + "="*50)
    print("STARTING MODIFY TASK EXAMPLE (POSTPONE & COMPLETE)")
    
    TASK_ID_TO_MODIFY = 'YOUR_TASK_ID_HERE' # <<< REPLACE THIS!

    if TASK_ID_TO_MODIFY != 'YOUR_TASK_ID_HERE':
        # Example 1: Postpone the task to the day after tomorrow
        postpone_details = ['postpone', TASK_ID_TO_MODIFY, '', day_after_str]
        modify_task(TOKEN_FILE_PATH, postpone_details)
        
        # Example 2: Complete the task
        complete_details = ['complete', TASK_ID_TO_MODIFY]
        modify_task(TOKEN_FILE_PATH, complete_details)

        # Example 3: Delete the task (uncomment to test)
        # delete_details = ['delete', TASK_ID_TO_MODIFY]
        # modify_task(TOKEN_FILE_PATH, delete_details)
    else:
        print("Please replace 'YOUR_TASK_ID_HERE' with a real Task ID to test modification functions.")
        
    print("\n" + "="*50)