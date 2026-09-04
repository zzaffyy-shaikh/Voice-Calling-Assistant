import os
import requests
import json

VAPI_PRIVATE_KEY = "326bd058-48ec-4624-bebc-b5b03ac83ae9"
VAPI_PUBLIC_KEY = "a6aa7113-a4b5-46a6-9c7a-b3bc6fcfa31d"
NGROK_URL = "https://unmarked-startling-hurricane.ngrok-free.dev"

HEADERS = {
    "Authorization": f"Bearer {VAPI_PRIVATE_KEY}",
    "Content-Type": "application/json"
}

SYSTEM_PROMPT = """
You are Alex, a warm and highly efficient intake coordinator for CloudCare.
You are speaking on the phone. Your tone must be friendly, professional, and conversational. 
Never sound like a robot, an IVR menu, or read raw JSON errors aloud.

GOAL: Collect the caller's demographic info to register them as a new patient, or update their record if they already exist.

FLOW:
1. Greet: "Hi, thanks for calling CloudCare. This is Alex — I can help get you registered today. Can I start with your first and last name?"
2. As soon as you hear a name and a phone number (often provided via caller ID), silently call `find_patient_by_phone`.
   - If found: "It looks like we already have a record for {first} {last}. Would you like to update your information instead?" If yes, switch to update flow.
3. Collect REQUIRED fields one at a time. Ask a maximum of 1 or 2 questions per turn to keep the conversation flowing. You MUST collect:
   - first_name and last_name (Verify spelling if it's unusual)
   - date_of_birth (Format: YYYY-MM-DD. Ask for the year if omitted)
   - biological sex (Must be exactly "Male", "Female", or "Other")
   - phone_number (10 digits)
   - address_line_1, city, state (State MUST be a 2-letter abbreviation, e.g., "NY" for New York), zip_code
4. Validate conversationally:
   - If the date of birth is in the future: "Hmm, that date doesn't look quite right — could you repeat your date of birth for me?"
   - If the state is provided as a full word, silently convert it to the 2-letter abbreviation for the system.
5. CONFIRMATION (Critical): Before saving, you MUST read back ALL collected fields for accuracy: 
   "Let me just read that back to make sure I have everything right: {full name}, born {DOB}, phone {number}, living at {address}... Did I get that all correct?"
   - If the caller corrects anything, acknowledge the correction gently ("Oh, my apologies, let me fix that"), update only that field, and re-confirm it.
6. Once confirmed, call `register_patient` (or `update_patient`) with the final data payload.
7. Relay the outcome:
   - Success: "You're all set, {first_name}! Your registration is complete. Thanks for calling, and have a great day."
   - Failure: "I'm sorry, I'm having a little trouble saving your info on my end. Let me try that one more time." Retry once. If it fails again: "I apologize for the trouble — our system seems to be down. A team member will follow up with you shortly." Then end the call.

RULES:
- If the caller wants to start over, say "No problem, let's take it from the top" and clear your context.
- If the user interrupts you, stop speaking and listen.
- Accept information out of order naturally (e.g., if they give their zip code with their city).
- Keep every response under 2 sentences unless reading back the full confirmation.
"""

def create_assistant():
    url = "https://api.vapi.ai/assistant"
    
    server_url = f"{NGROK_URL}/voice/tool-call"
    
    payload = {
        "name": "CloudCare Intake",
        "voice": {
            "provider": "11labs",
            "voiceId": "bIHbv24MWmeRgasZH58o" # Rachel
        },
        "model": {
            "provider": "google",
            "model": "gemini-2.5-flash",
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "async": False,
                    "messages": [
                        {
                            "type": "request-start",
                            "content": "Let me check our records for a moment..."
                        }
                    ],
                    "function": {
                        "name": "find_patient_by_phone",
                        "description": "Look up an existing patient by their phone number to see if they are already registered.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "phone_number": {
                                    "type": "string",
                                    "description": "The 10-digit phone number."
                                }
                            },
                            "required": ["phone_number"]
                        }
                    },
                    "server": {
                        "url": server_url,
                        "secret": "mwstesting"
                    }
                },
                {
                    "type": "function",
                    "async": False,
                    "messages": [
                        {
                            "type": "request-start",
                            "content": "Just a second while I save this to our system..."
                        }
                    ],
                    "function": {
                        "name": "register_patient",
                        "description": "Save a new patient to the database after they have confirmed all details.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "first_name": {"type": "string"},
                                "last_name": {"type": "string"},
                                "date_of_birth": {"type": "string", "description": "YYYY-MM-DD"},
                                "sex": {"type": "string", "enum": ["Male", "Female", "Other"]},
                                "phone_number": {"type": "string"},
                                "address_line_1": {"type": "string"},
                                "city": {"type": "string"},
                                "state": {"type": "string", "description": "2-letter abbreviation"},
                                "zip_code": {"type": "string"}
                            },
                            "required": ["first_name", "last_name", "date_of_birth", "sex", "phone_number", "address_line_1", "city", "state", "zip_code"]
                        }
                    },
                    "server": {
                        "url": server_url,
                        "secret": "mwstesting"
                    }
                },
                {
                    "type": "function",
                    "async": False,
                    "messages": [
                        {
                            "type": "request-start",
                            "content": "Updating your file now..."
                        }
                    ],
                    "function": {
                        "name": "update_patient",
                        "description": "Update an existing patient record.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "patient_id": {"type": "string", "description": "The UUID of the patient to update"},
                                "address_line_1": {"type": "string"},
                                "city": {"type": "string"},
                                "state": {"type": "string"},
                                "zip_code": {"type": "string"}
                            },
                            "required": ["patient_id"]
                        }
                    },
                    "server": {
                        "url": server_url,
                        "secret": "mwstesting"
                    }
                }
            ]
        }
    }
    
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code in [200, 201]:
        print(f"Assistant created successfully! ID: {response.json().get('id')}")
        return response.json().get('id')
    else:
        print(f"Error creating assistant: {response.status_code}")
        print(response.text)
        return None

def buy_phone_number(assistant_id):
    url = "https://api.vapi.ai/phone-number"
    
    # Buy a random US phone number
    payload = {
        "provider": "twilio",
        "assistantId": assistant_id,
        "name": "CloudCare Demo"
    }
    
    print("Attempting to buy a phone number (this requires billing set up on Vapi)...")
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code in [200, 201]:
        print(f"Phone number provisioned! Number: {response.json().get('number')}")
    else:
        print(f"Skipping phone number creation (probably no billing on account). Use Web Dialer instead.")
        print(f"Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    assistant_id = create_assistant()
    if assistant_id:
        buy_phone_number(assistant_id)
        
        # Create .env.local for frontend
        env_content = f"NEXT_PUBLIC_VAPI_PUBLIC_KEY={VAPI_PUBLIC_KEY}\nNEXT_PUBLIC_VAPI_ASSISTANT_ID={assistant_id}\nNEXT_PUBLIC_API_BASE_URL={NGROK_URL}\n"
        with open("frontend/.env.local", "w") as f:
            f.write(env_content)
        print("Updated frontend/.env.local with Assistant ID!")
