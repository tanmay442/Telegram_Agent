import google.generativeai as genai
import os

def generate_response(
    api_key: str,
    model_name: str,
    prompt: str,
    system_instruction: str = None,
    file_path: str = None,
    conversation_history: list = None
):
    """
    Generates a response from the Gemini model, handling text, files, and history.
    """
    try:
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel(
            model_name,
            system_instruction=system_instruction
        )
        
        # Start with the existing conversation history if it exists
        chat_history = conversation_history or []

        # Prepare the user's new message (prompt)
        user_prompt_parts = []
        
        # If there's a file, upload it and add it to the parts
        uploaded_file = None
        if file_path:
            uploaded_file = genai.upload_file(path=file_path)
            user_prompt_parts.append(uploaded_file)
        
        # Add the text part of the prompt
        user_prompt_parts.append(prompt)

        # Combine the history with the new user message
        content_to_send = chat_history + [{'role': 'user', 'parts': user_prompt_parts}]

        # Generate the content
        response = model.generate_content(content_to_send)

        # Clean up the uploaded file if it exists
        if uploaded_file:
            genai.delete_file(uploaded_file.name)

        return response.text

    except Exception as e:
        # It's good practice to log the full error for debugging
        print(f"Error in generate_response: {e}")
        return f"An error occurred: {e}"