import sqlite3
import requests
import sys

# --- Configuration ---
# IMPORTANT: Paste the SAME bot token you use in your bot.py
BOT_TOKEN = "8363793520:AAFTIHaFXRgvdxTVHWLHNc58064JbTWXiXw"
DATABASE_FILE = "user_data.db"

def download_telegram_file(file_id: str, output_filename: str):
    """
    Downloads a file from Telegram using its file_id.
    This is the "librarian" function that fetches the file.
    """
    # 1. Get the file_path from the Telegram API
    get_file_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile"
    params = {'file_id': file_id}
    
    print(f"\n---> Asking Telegram for file path using file_id: {file_id[:20]}...")
    response = requests.get(get_file_url, params=params)
    
    data = response.json()
    if not data.get('ok'):
        print(f"Error: Could not get file info. Telegram says: {data.get('description')}")
        return

    file_path = data['result']['file_path']
    print(f"---> Got file path: {file_path}")

    # 2. Construct the full download URL and download the actual file
    download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    
    print(f"---> Downloading the image from Telegram servers...")
    file_response = requests.get(download_url, stream=True)

    if file_response.status_code == 200:
        with open(output_filename, 'wb') as f:
            for chunk in file_response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Success! Image saved as '{output_filename}'")
    else:
        print(f"Error: Failed to download the file. Status code: {file_response.status_code}")

def main():
    """
    Main function to connect to the DB, list photos, and download a chosen one.
    """
    print(f"Connecting to database: {DATABASE_FILE}")
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        # 1. Find all photos in the database
        # We select `rowid` which is a unique number for each row, perfect for a menu!
        cursor.execute("SELECT rowid, user_id, timestamp, content FROM messages WHERE message_type = 'photo'")
        photos = cursor.fetchall()
        conn.close()

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return

    if not photos:
        print("No photos found in the database.")
        return

    # 2. Display a menu of available photos
    print("\n--- Found Photos in Database ---")
    for i, photo in enumerate(photos):
        rowid, user_id, timestamp, _ = photo
        print(f"  {i + 1}: Photo from user {user_id} at {timestamp} (DB row {rowid})")
    print("--------------------------------")

    # 3. Ask the user which one to download
    try:
        choice = int(input("Enter the number of the photo you want to download: "))
        if not (1 <= choice <= len(photos)):
            print("Invalid number. Please run the script again.")
            return
            
        # Get the selected photo's data
        selected_photo = photos[choice - 1]
        row_id = selected_photo[0]
        user_id = selected_photo[1]
        file_id_to_download = selected_photo[3] # The content is the file_id

    except (ValueError, IndexError):
        print("Invalid input. Please enter a number from the list.")
        return

    # 4. Download the chosen file
    output_filename = f"photo_from_user_{user_id}_row_{row_id}.jpg"
    download_telegram_file(file_id_to_download, output_filename)

if __name__ == '__main__':
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("!!! ERROR: Please open view_from_db.py and replace 'YOUR_TELEGRAM_BOT_TOKEN' with your actual bot token.")
    else:
        main()