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
    
    try:
        
        genai.configure(api_key=api_key)

        
        model = genai.GenerativeModel(
            model_name,
            system_instruction=system_instruction
        )

        
        content_to_send = []

        # conversation history 
        if conversation_history:
            content_to_send.extend(conversation_history)

        # file upload .
        uploaded_file = None
        if file_path:
            uploaded_file = genai.upload_file(path=file_path)
            content_to_send.append(uploaded_file)


        # user prompt.
        content_to_send.append(prompt)

        # Generate the content.
        response = model.generate_content(content_to_send)

        return response.text

    except Exception as e:
        return f"An error occurred: {e}"





