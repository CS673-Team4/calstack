import os
from flask import Flask, redirect, url_for, session, request, render_template
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime
from dotenv import load_dotenv

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #For Testing, remove this in production
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Path to client secret downloaded from Google Console
GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json"

# Required scope for free/busy calendar read
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

@app.route('/')
def index():
    return render_template("login.html")

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=os.environ.get('OAUTH2_REDIRECT_URI')  # match Google OAuth redirect URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=os.environ.get('OAUTH2_REDIRECT_URI')
    )
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.datetime.utcnow()
    seven_days_later = now + datetime.timedelta(days=7)

    time_min = now.isoformat() + 'Z'
    time_max = seven_days_later.isoformat() + 'Z'

    freebusy_query = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": "UTC",
        "items": [{"id": "primary"}]
    }

    freebusy_result = service.freebusy().query(body=freebusy_query).execute()

    print("🟢 Free/busy data:")
    print(freebusy_result)

    return "Logged in! Check server logs for free/busy info."

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)