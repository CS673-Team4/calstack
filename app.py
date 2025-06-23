import os
from flask import Flask, redirect, url_for, session, request, render_template
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #For Testing, remove this in production
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB connection
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client.calstack

# Collections
users_col = db.users
teams_col = db.teams
polls_col = db.polls
availability_col = db.availability

# Path to client secret downloaded from Google Console
GOOGLE_CLIENT_SECRETS_FILE = "client_secret.json"

# Required scope for free/busy calendar read
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

@app.route('/')
def index():
    return render_template("login.html")

@app.route('/home')
def home():
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    my_teams = list(teams_col.find({"members": user_email}))
    return render_template("home.html", my_teams=my_teams)

@app.route('/team/create', methods=['GET', 'POST'])
def create_team():
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    if request.method == 'POST':
        team_name = request.form['team_name']
        invited_emails = [e.strip() for e in request.form['invited_emails'].split(',') if e.strip()]
        import secrets
        code = secrets.token_hex(4)
        members = list(set([user_email] + invited_emails))
        team = {"name": team_name, "members": members, "code": code}
        result = teams_col.insert_one(team)
        # Sync creator's availability for the new team
        creds_dict = session.get('credentials')
        if creds_dict:
            from google.oauth2.credentials import Credentials
            creds = Credentials(
                creds_dict['token'],
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict['token_uri'],
                client_id=creds_dict['client_id'],
                client_secret=creds_dict['client_secret'],
                scopes=creds_dict['scopes']
            )
            # Only sync for this team
            from googleapiclient.discovery import build as g_build
            service = g_build('calendar', 'v3', credentials=creds)
            import datetime
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
            busy = freebusy_result['calendars']['primary'].get('busy', [])
            availability_col.update_one(
                {"team_id": str(result.inserted_id), "user_email": user_email},
                {"$set": {"busy": busy}},
                upsert=True
            )
        return redirect(url_for('team_page', team_id=str(result.inserted_id)))
    return render_template("create_team.html")

@app.route('/team/join', methods=['GET', 'POST'])
def join_team():
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        code = request.form['team_code']
        team = teams_col.find_one({"code": code})
        if team:
            if user_email not in team['members']:
                teams_col.update_one({"_id": team['_id']}, {"$addToSet": {"members": user_email}})
            # Sync this user's availability for this team only
            creds_dict = session.get('credentials')
            if creds_dict:
                from google.oauth2.credentials import Credentials
                creds = Credentials(**creds_dict)
                # Fetch and upsert availability for this team
                from googleapiclient.discovery import build as g_build
                service = g_build('calendar', 'v3', credentials=creds)
                import datetime
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
                print("Freebusy result:", freebusy_result)
                busy = freebusy_result['calendars']['primary'].get('busy', [])
                availability_col.update_one(
                    {"team_id": str(team['_id']), "user_email": user_email},
                    {"$set": {"busy": busy}},
                    upsert=True
                )
            return redirect(url_for('team_page', team_id=str(team['_id'])))
        else:
            error = "Team code not found."
    return render_template("join_team.html", error=error)

@app.route('/team/<team_id>')
def team_page(team_id):
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    team = teams_col.find_one({"_id": ObjectId(team_id)})
    if not team:
        return "Team not found", 404
    # Get all members
    members = team.get('members', [])
    # Get current user's availability
    avail_doc = availability_col.find_one({"team_id": team_id, "user_email": user_email})
    busy = avail_doc['busy'] if avail_doc else []
    return render_template("team_page.html", team=team, user_email=user_email, members=members, busy=busy)

@app.route('/team/<team_id>/availability/<email>')
def get_member_availability(team_id, email):
    avail_doc = availability_col.find_one({"team_id": team_id, "user_email": email})
    busy = avail_doc['busy'] if avail_doc else []
    return {"busy": busy}

from flask import request, jsonify
@app.route('/team/<team_id>/suggest_slots', methods=['GET', 'POST'])
def suggest_slots(team_id):
    import datetime
    data = request.get_json() if request.method == 'POST' else {}
    # Parameters
    slot_minutes = int(data.get('duration', 60))
    max_slots = 5
    participants = data.get('participants')
    if not participants:
        # fallback: all members
        team = teams_col.find_one({"_id": ObjectId(team_id)})
        if not team:
            return jsonify({"error": "Team not found"}), 404
        participants = team.get('members', [])
    days = data.get('days', list(range(7)))
    end_hour = int(data.get('end_hour', 18))
    # Get all busy intervals for selected participants
    avail_docs = availability_col.find({"team_id": team_id, "user_email": {"$in": participants}})
    member_busy = {doc['user_email']: doc.get('busy', []) for doc in avail_docs}
    # Build list of busy intervals per member as tuples (start, end) in UTC
    busy_map = {}
    for user, busy_list in member_busy.items():
        busy_map[user] = [(
            datetime.datetime.fromisoformat(b['start'].replace('Z','+00:00')),
            datetime.datetime.fromisoformat(b['end'].replace('Z','+00:00'))
        ) for b in busy_list]
    # Define candidate slots: next 7 days, blocks of chosen duration, filtered by days/hours
    now = datetime.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    slots = []
    for day in range(7):
        d = now + datetime.timedelta(days=day)
        weekday = d.weekday() # 0=Mon,6=Sun
        if weekday in days:
            # Allow slots from 6am to end_hour
            for h in range(6, end_hour):
                slot_start = d.replace(hour=h, minute=0)
                slot_end = slot_start + datetime.timedelta(minutes=slot_minutes)
                slots.append((slot_start, slot_end))
    # Filter slots: must be free for all selected participants
    def slot_is_free(slot):
        for user in participants:
            for b_start, b_end in busy_map.get(user, []):
                # Overlap if slot_start < b_end and slot_end > b_start
                if slot[0] < b_end and slot[1] > b_start:
                    return False
        return True
    free_slots = [s for s in slots if slot_is_free(s)]
    # Get up to 5 earliest
    suggested = [{
        "start": s[0].isoformat() + 'Z',
        "end": s[1].isoformat() + 'Z'
    } for s in free_slots[:max_slots]]
    return jsonify({"suggested_slots": suggested})

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=os.environ.get('OAUTH2_REDIRECT_URI')  # match Google OAuth redirect URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

def sync_user_availability(email, creds):
    """
    Fetch user's Google Calendar busy times for next 7 days and upsert for all their teams.
    """
    print("Syncing availability for", email)
    from googleapiclient.discovery import build as g_build
    service = g_build('calendar', 'v3', credentials=creds)
    import datetime
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
    busy = freebusy_result['calendars']['primary'].get('busy', [])
    print("Busy times:", busy)
    # Upsert for each team
    user_teams = teams_col.find({"members": email})
    for team in user_teams:
        print("Upserting availability for", email, "for team", team['name'])
        availability_col.update_one(
            {"team_id": str(team['_id']), "user_email": email},
            {"$set": {"busy": busy}},
            upsert=True
        )

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

    # Fetch user's email
    from googleapiclient.discovery import build as g_build
    people_service = g_build('people', 'v1', credentials=creds)
    profile = people_service.people().get(resourceName='people/me', personFields='emailAddresses').execute()
    print("Profile:", profile)
    email = None
    if 'emailAddresses' in profile:
        email = profile['emailAddresses'][0]['value']
    if not email and hasattr(creds, 'id_token') and creds.id_token:
        email = creds.id_token.get('email')
    if not email:
        return "Could not retrieve email from Google profile.", 400
    session['email'] = email

    # Optionally: create user document if not exists
    if not users_col.find_one({'email': email}):
        users_col.insert_one({'email': email, 'name': email.split('@')[0]})

    # Sync availability for all teams
    sync_user_availability(email, creds)

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)