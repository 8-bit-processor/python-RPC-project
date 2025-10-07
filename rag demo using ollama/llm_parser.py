

import requests
import json
import os

# Use the service name 'ollama' from docker-compose as the hostname
OLLAMA_URL = "http://localhost:11434/api/generate"

# This is the detailed prompt that instructs the LLM how to behave.
PROMPT_TEMPLATE = """
You are an expert medical note parser. Your task is to analyze the following medical note and extract the text corresponding to the specified categories. The output MUST be a valid JSON object.

The categories to extract are:
- hpi
- medical_diagnosis
- past_surgical_history
- tobacco_use_history
- alcohol_and_illicit_use_history
- family_history
- ear_nose_and_throat_history
- cardiac_history
- pulmonary_history
- gastroenterology_history
- neurology_history
- musculoskeletal_history
- urology_history
- gynecology_history
- unknown_text

Rules:
1. Extract the text for each category VERBATIM from the note.
2. If a category is not mentioned in the note, the value for that key MUST be null.
3. Do not add any information that is not present in the source document.
4. Ignore all formatting junk, empty spaces, and irrelevant text like '--- FAXED NOTE ---' or '*** END OF NOTE ***'.
5. Ensure the final output is ONLY the JSON object and nothing else.

Here is the medical note:

---
{note_text}
---

JSON Output:
"""

def parse_note_with_ollama(note_text: str, model_name: str = "ollama3.2") -> dict:
    """Connects to the Ollama service to parse a medical note."""
    print(f"Connecting to Ollama with model: {model_name}...")
    full_prompt = PROMPT_TEMPLATE.format(note_text=note_text)

    payload = {
        "model": model_name,
        "prompt": full_prompt,
        "stream": False,
        "format": "json" # Ollama will ensure the output is valid JSON
    }

    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(OLLAMA_URL, headers=headers, json=payload, timeout=300)
        response.raise_for_status() # Raise an exception for bad status codes

        # The actual JSON string is in the 'response' field
        response_json_str = response.json().get('response', '{}')
        
        # Parse the JSON string into a Python dictionary
        parsed_data = json.loads(response_json_str)
        return parsed_data

    except requests.exceptions.ConnectionError as e:
        print("\n--- CONNECTION ERROR ---")
        print("Could not connect to the Ollama service.")
        print(f"Please ensure the docker-compose environment is running with 'docker-compose up'")
        return {"error": str(e)}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": str(e)}

if __name__ == '__main__':
    print("--- Running LLM Parser Demonstration ---")
    
    # Read one of our messy sample files
    file_path = os.path.join(os.path.dirname(__file__), "sample_note_1.txt")

    if not os.path.exists(file_path):
        print(f"Error: Sample file not found at {file_path}")
    else:
        with open(file_path, 'r', encoding='utf-8') as f:
            note_content = f.read()
        
        # Parse the note using the LLM
        # Using a small, fast model is good for this task
        structured_note = parse_note_with_ollama(note_content, model_name="ollama3.2")

        print("\n--- LLM Parsing Result ---")
        print(json.dumps(structured_note, indent=2))
