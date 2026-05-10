# authenticate.py

from google_auth_oauthlib.flow import InstalledAppFlow
import json

# These are the permissions we're asking Google for
# Read Gmail, read/write Sheets, read/write Calendar
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

def authenticate():
    # Load your credentials.json and start the OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",  # the file you downloaded from Google Console
        SCOPES
    )
    
    # This opens your browser for you to log in
    creds = flow.run_local_server(port=0)
    
    # Save the token so you never have to log in again
    with open("token.json", "w") as f:
        f.write(creds.to_json())
    
    print("Authentication successful! token.json saved.")

if __name__ == "__main__":
    authenticate()