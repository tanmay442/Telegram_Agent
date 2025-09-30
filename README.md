
# Telegram Agent

## Objective
This project is a Telegram bot agent that provides a variety of file utilities (compression, conversion, etc.), Google services integration (calendar, mail, tasks), and HBTU updates. It is designed to automate and simplify tasks for users directly from Telegram. The project is being migrated to Notion-based workflows from Google services for better integration and automation.

## Directory Structure & File Functions

```
Telegram_Agent/
├── download.py
├── main.py
├── README.md
├── user_data.db
├── FileActions/
│   ├── img_compress.py
│   ├── img-pdf.py
│   ├── officefile-pdf.py
│   ├── pdf-compress.py
│   └── __pycache__/
├── Google_serviecs/
│   ├── caleander_services.py
│   ├── credentials.json
│   ├── mail_services.py
│   ├── tasks_services.py
│   ├── token_gen.py
│   └── __pycache__/
├── hbtu_updates/
│   ├── cheking_update.py
│   ├── fetching_links.py
│   ├── hbtu_links.txt
│   └── __pycache__/
├── Temp/
│   ├── temp_images/
│   │   ├── cache/
│   │   └── testing/
│   └── temp_pdfs/
│       ├── cache/
│       └── testing/
└── user/
		└── test_user/
				├── token.json
				└── userid/
						├── user_context
						└── user_token.json
```

### Root Files
- **main.py**: Entry point for the Telegram bot. Handles all bot logic, message routing, and integration with file actions and Google services.
- **download.py**: Handles file downloading utilities.
- **user_data.db**: Database for storing user-related data.
- **README.md**: This documentation file.

### FileActions/
- **img_compress.py**: Functions for compressing image files.
- **img-pdf.py**: Functions to convert images to PDF and extract images from PDFs.
- **officefile-pdf.py**: Functions to convert Office files (docx, pptx, xlsx) to PDF.
- **pdf-compress.py**: Functions for compressing PDF files and optimizing them.
- **__pycache__/**: Python bytecode cache for faster imports.

### Google_serviecs/
- **caleander_services.py**: Functions to interact with Google Calendar (create, view, delete events).
- **mail_services.py**: Functions to interact with Gmail (read, draft, label emails).
- **tasks_services.py**: Functions to interact with Google Tasks (create/view/modify tasks and lists).
- **token_gen.py**: Handles Google OAuth token generation and management.
- **credentials.json**: Google API credentials file.
- **__pycache__/**: Python bytecode cache.

### hbtu_updates/
- **cheking_update.py**: Checks for new updates from HBTU sources.
- **fetching_links.py**: Scrapes and fetches top links from HBTU sources.
- **hbtu_links.txt**: Stores fetched HBTU links.
- **__pycache__/**: Python bytecode cache.

### Temp/
- **temp_images/**: Temporary storage for image files.
	- **cache/**: Stores cached/compressed images.
	- **testing/**: Stores test/corrupt images for debugging.
- **temp_pdfs/**: Temporary storage for PDF files.
	- **cache/**: Stores cached/compressed PDFs.
	- **testing/**: Stores test/corrupt PDFs for debugging.

### user/
- **test_user/**: Example user directory for storing user-specific tokens and context.
	- **token.json**: Google OAuth token for the user.
	- **userid/**: Stores user context and token files for session management.
		- **user_context**: Contextual data for the user session.
		- **user_token.json**: Token file for user session.

## How It Works
- The bot receives messages/files from users on Telegram.
- Depending on the command or file type, it routes the request to the appropriate handler (file conversion, compression, Google service, or HBTU update).
- Google services are used for calendar, mail, and tasks (replacing Notion integration).
- File actions are performed using scripts in the `FileActions/` directory.
- HBTU updates are fetched and checked using scripts in the `hbtu_updates/` directory.
- Temporary files are managed in the `Temp/` directory.
- User-specific data and tokens are managed in the `user/` directory.

## Migration Note
This project is being migrated from Notion-based automation to Google services for better reliability, scalability, and integration with user workflows.

## Requirements
- Python 3.10+
- python-telegram-bot
- google-api-python-client
- google-auth
- dotenv
- pypdf, pillow, and other file processing libraries

## Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Add your Google API credentials to `Google_serviecs/credentials.json`.
4. Set up your Telegram bot token in `main.py` or via environment variable.
5. Run the bot: `python3 main.py`

---
For any questions or contributions, please open an issue or pull request.
