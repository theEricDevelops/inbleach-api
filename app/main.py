# /app/main.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from app.models import MsgPayload
from app.utils.gmail import GmailUtils
from app.services.gmail import GmailService
from google.oauth2.credentials import Credentials
from app.config import CREDENTIALS_FILE

# Initialize the FastAPI app
app = FastAPI()
messages_list: dict[int, MsgPayload] = {}

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
gmail_service = GmailService(CREDENTIALS_FILE)

@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Welcome to the InBleach API"}

@app.get("/auth/google")
def auth_google(request: Request) -> dict[str, str]:
    """
    Generate and return a Google OAuth2 URL for authentication.
    """
    auth_url, state = gmail_service.get_auth_url()
    response = JSONResponse(content={"url": auth_url})
    response.set_cookie(key="oauth_state", value=state, httponly=True)
    return response

@app.get("/auth/callback/google")
async def auth_callback(request: Request, code: str, state: str):
    """
    Handle the callback from Google, exchange code for tokens, and redirect to frontend.
    """
    stored_state = request.cookies.get("oauth_state")
    if state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    creds = gmail_service.fetch_token(code)
    response = RedirectResponse(url="http://localhost:3000/")  # Update to your frontend URL
    response.set_cookie(key="access_token", value=creds.token, httponly=True)
    response.set_cookie(key="refresh_token", value=creds.refresh_token, httponly=True)
    response.set_cookie(key="token_uri", value=creds.token_uri, httponly=True)
    response.set_cookie(key="client_id", value=creds.client_id, httponly=True)
    response.set_cookie(key="client_secret", value=creds.client_secret, httponly=True)
    response.set_cookie(key="scopes", value=" ".join(creds.scopes), httponly=True)
    response.set_cookie(key="credentials", value=creds.to_json(), httponly=True)
    return response

@app.get("/auth/status/google")
async def auth_status(request: Request):
    """
    Check if the user is authenticated with Google.
    """
    access_token = request.cookies.get("access_token")
    if access_token:
        return {"authenticated": True}
    return {"authenticated": False}

@app.get("/messages")
async def message_items(request: Request, days_requested: int = 1):
    """
    Fetch and return Gmail messages for the authenticated user.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    creds = Credentials(
        token=access_token,
        refresh_token=request.cookies.get("refresh_token"),
        token_uri=request.cookies.get("token_uri"),
        client_id=request.cookies.get("client_id"),
        client_secret=request.cookies.get("client_secret")
    )
    service = gmail_service.get_service(creds)
    gmail_utils = GmailUtils(service)  # Pass the service directly
    messages = gmail_utils.fetch_emails(days=days_requested)
    return {"messages": messages}

@app.get("/messages/{message_id}")
async def message_item(message_id: str, request: Request):
    """
    Fetch and return a specific Gmail message for the authenticated user.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    creds = Credentials(
        token=access_token,
        refresh_token=request.cookies.get("refresh_token"),
        token_uri=request.cookies.get("token_uri"),
        client_id=request.cookies.get("client_id"),
        client_secret=request.cookies.get("client_secret")
    )
    service = gmail_service.get_service(creds)
    message = service.users().messages().get(userId='me', id=message_id).execute()
    
    return {"message": message}

@app.get("/messages/unsubscribe/{message_ids}")
async def unsubscribe_from_emails(message_ids: str, request: Request):
    """
    Unsubscribe from email lists based on message IDs.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    creds = Credentials(
        token=access_token,
        refresh_token=request.cookies.get("refresh_token"),
        token_uri=request.cookies.get("token_uri"),
        client_id=request.cookies.get("client_id"),
        client_secret=request.cookies.get("client_secret")
    )
    service = gmail_service.get_service(creds)
    gmail_utils = GmailUtils(service)

    print(f"Unsubscribing from emails: {message_ids}")

    messages = message_ids.split(",")
    results = {
        'queued': [],
        'failed': [],
        'success': []
    }

    for message_id in messages:
        message_id = message_id.strip('"')
        results['queued'].append(message_id)
        result = gmail_utils.process_email(message_id)
        if result:
            results['success'].append(message_id)
            results['queued'].remove(message_id)
        else:
            results['failed'].append(message_id)
            results['queued'].remove(message_id)
    return results
