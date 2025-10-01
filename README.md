


# Telegram Agent

## Objective
This project is a Telegram bot agent that provides a variety of file utilities (compression, conversion, etc.), Google services integration (calendar, mail, tasks), and HBTU updates. The project is currently migrating to Notion for future task and knowledge management, but all Google services code and files remain present and documented (though currently dormant).

**Developer:** Tanmay Goel ([goeltanmay442@outlook.com](mailto:goeltanmay442@outlook.com))

## Directory Structure & File Functions

```
Telegram_Agent/
├── media_extractor.py
├── main.py
├── README.md
├── requirements.txt
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
				└── userid/
						├── user_context
						└── user_token.json
```

### Root Files
- **main.py**: Entry point for the Telegram bot. Handles all bot logic, message routing, file actions, and update integration. Also contains dormant Google/Notion integration logic.
- **media_extractor.py**: Handles file downloading and saving utilities.
- **requirements.txt**: Python dependencies for the project.
- **user_data.db**: Database for storing user-related data, history, and context.(not in repo cause for hosting purpose using supbase)
- **README.md**: This documentation file.

### FileActions/
- **img_compress.py**: Functions for compressing image files (JPEG, PNG, etc.).
- **img-pdf.py**: Functions to convert images to PDF and extract images from PDFs.
- **officefile-pdf.py**: Functions to convert Office files (docx, pptx, xlsx) to PDF.(not active )
- **pdf-compress.py**: Functions for compressing and optimizing PDF files.
- **__pycache__/**: Python bytecode cache for faster imports.

### Google_serviecs/ (Dormant, but present)
- **caleander_services.py**: Functions to interact with Google Calendar (create, view, delete events).
- **mail_services.py**: Functions to interact with Gmail (read, draft, label emails).
- **tasks_services.py**: Functions to interact with Google Tasks (create/view/modify tasks and lists).
- **token_gen.py**: Handles Google OAuth token generation and management.
- **credentials.json**: Google API credentials file.
- **__pycache__/**: Python bytecode cache.

### hbtu_updates/
- **cheking_update.py**: Checks for new updates from HBTU sources and notifies users.
- **fetching_links.py**: Scrapes and fetches top links from HBTU sources.
- **hbtu_links.txt**: Stores fetched HBTU links for quick access.
- **__pycache__/**: Python bytecode cache.

### Temp/
- **temp_images/**: Temporary storage for image files.
	- **cache/**: Stores cached/compressed images.
	- **testing/**: Stores test/corrupt images for debugging.
- **temp_pdfs/**: Temporary storage for PDF files.
	- **cache/**: Stores cached/compressed PDFs.
	- **testing/**: Stores test/corrupt PDFs for debugging.

### user/
- **test_user/**: Example user directory for storing user-specific context and tokens.
	- **userid/**: Stores user context and token files for session management.
		- **user_context**: Contextual data for the user session.
		- **user_token.json**: Token file for user session.

## How It Works
- The bot receives messages/files from users on Telegram.
- Depending on the command or file type, it routes the request to the appropriate handler (file conversion, compression, Google service, or HBTU update).
- Google services code is present but currently dormant as the project migrates to Notion for future task and knowledge management.
- File actions are performed using scripts in the `FileActions/` directory.
- HBTU updates are fetched and checked using scripts in the `hbtu_updates/` directory.
- Temporary files are managed in the `Temp/` directory.
- User-specific data and tokens are managed in the `user/` directory.

## Best Practices
- Use environment variables or a `.env` file for all sensitive credentials (Telegram token, Google API key, etc.).
- Keep all third-party API keys out of source control.
- Write modular, reusable functions for each file action and Google/Notion operation.
- Use logging and error handling throughout the codebase for easier debugging.
- Maintain clear separation between bot logic, file actions, and service integrations.
- Regularly update dependencies and check for security vulnerabilities.
- Document all new modules and functions with docstrings.



## Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Add your Telegram bot token and Google API credentials to a `.env` file and `Google_serviecs/credentials.json`.
4. Run the bot: `python3 main.py`

---
For any questions or contributions, please contact Tanmay Goel at [goeltanmay442@outlook.com](mailto:goeltanmay442@outlook.com) or open an issue/pull request.
