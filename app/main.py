# /app/main.py

import os
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
    response = RedirectResponse(url="http://localhost:3000/dashboard")  # Update to your frontend URL
    response.set_cookie(key="access_token", value=creds.token, httponly=True)
    response.set_cookie(key="refresh_token", value=creds.refresh_token, httponly=True)
    return response

@app.get("/messages")
async def message_items(request: Request):
    """
    Fetch and return Gmail messages for the authenticated user.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    creds = Credentials(token=access_token)
    service = gmail_service.get_service(creds)
    gmail_utils = GmailUtils(service)  # Pass the service directly
    messages = gmail_utils.fetch_emails(days=1)
    return {"messages": messages}

@app.get("/messages/{message_id}")
async def message_item(message_id: str, request: Request):
    """
    Fetch and return a specific Gmail message for the authenticated user.
    """
    access_token = request.cookies.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    creds = Credentials(token=access_token)
    service = gmail_service.get_service(creds)
    message = service.users().messages().get(userId='me', id=message_id).execute()
    gmail = GmailUtils(service)
    body = gmail._get_html_body(message)
    return {"message": body}