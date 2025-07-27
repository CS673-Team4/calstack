import os
from flask import Flask, redirect, url_for, session, request, render_template
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import requests  # For Microsoft Graph API

# Microsoft OAuth2 config (fill these from Azure Portal)
MS_SCOPES = [
    "openid",
    "profile",
    "offline_access",
    "Calendars.Read",
    "MailboxSettings.Read"
]

MS_AUTHORITY = 'https://login.microsoftonline.com/common'
# Log env at import time
try:
    with open('/tmp/ms_env_debug.txt', 'w') as f:
        f.write(f"IMPORT: OAUTH2_REDIRECT_URI={os.environ.get('OAUTH2_REDIRECT_URI')}\nIMPORT: MS_CLIENT_ID={os.environ.get('MS_CLIENT_ID')}\n")
except Exception:
    pass


import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' #For Testing, remove this in production
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.debug = os.environ.get('FLASK_DEBUG') == '1'
app.secret_key = os.environ.get('FLASK_SECRET_KEY')

# MongoDB connection
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI)
db = client.calstack

from flask import jsonify, request
from datetime import datetime, timedelta, time as dt_time
import pytz

def slot_overlaps(slot_start, slot_end, busy_times):
    for busy in busy_times:
        busy_start = busy['start']
        busy_end = busy['end']
        if slot_start < busy_end and slot_end > busy_start:
            return True
    return False

@app.route('/api/propose_slots', methods=['POST'])
def propose_slots():
    import random
    data = request.get_json()
    participants = data['participants']  # list of emails
    days_js = data.get('days_of_week', list(range(7)))
    days_of_week = [(d - 1) % 7 for d in days_js]
    duration = int(data['duration'])
    start_hour = int(data['start_hour'])
    end_hour = int(data['end_hour'])
    team_id = data['team_id']
    user_email = session.get('email')
    user_doc = db.users.find_one({'email': user_email})
    timezone = user_doc.get('timezone', 'UTC') if user_doc else 'UTC'
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    
    # New options
    algorithm = data.get('algorithm', 'next')
    num_slots = int(data.get('num_slots', 5))
    avoid_work_hours = bool(data.get('avoid_work_hours', False))
    
    all_slots = []
    for day_offset in range(7):
        day = now + timedelta(days=day_offset)
        if day.weekday() not in days_of_week:
            continue
        day_start = tz.localize(datetime.combine(day.date(), dt_time(hour=start_hour)))
        day_end = tz.localize(datetime.combine(day.date(), dt_time(hour=end_hour)))
        slot_start = day_start
        while slot_start + timedelta(minutes=duration) <= day_end:
            slot_end = slot_start + timedelta(minutes=duration)
            # Work hours filter: skip 9am-5pm Mon-Fri if avoid_work_hours
            if avoid_work_hours and day.weekday() < 5:
                if slot_start.hour < 17:
                    slot_start += timedelta(minutes=duration)
                    continue
            conflict = False
            for email in participants:
                avail_doc = db.availability.find_one({'user_email': email, 'team_id': team_id})
                busy_times = []
                if avail_doc and 'busy' in avail_doc:
                    for busy in avail_doc['busy']:
                        busy_start = datetime.fromisoformat(busy['start'])
                        if busy_start.tzinfo is None:
                            busy_start = tz.localize(busy_start)
                        busy_end = datetime.fromisoformat(busy['end'])
                        if busy_end.tzinfo is None:
                            busy_end = tz.localize(busy_end)
                        busy_times.append({'start': busy_start, 'end': busy_end})
                if slot_overlaps(slot_start, slot_end, busy_times):
                    conflict = True
                    break
            if not conflict:
                all_slots.append({
                    'start': slot_start.isoformat(),
                    'end': slot_end.isoformat(),
                    'day': day.date().isoformat()
                })
            slot_start += timedelta(minutes=duration)
    # Algorithm selection
    slots = []
    if algorithm == 'split':
        # Distribute slots across days
        slots_by_day = {}
        for slot in all_slots:
            slots_by_day.setdefault(slot['day'], []).append(slot)
        days = sorted(slots_by_day.keys())
        i = 0
        while len(slots) < num_slots and any(slots_by_day.values()):
            for day in days:
                if slots_by_day[day]:
                    slots.append(slots_by_day[day].pop(0))
                    if len(slots) >= num_slots:
                        break
    elif algorithm == 'random':
        slots = random.sample(all_slots, min(num_slots, len(all_slots))) if all_slots else []
    else:  # 'next' (default)
        slots = all_slots[:num_slots]
    # Remove 'day' key before returning
    for slot in slots:
        slot.pop('day', None)
    return jsonify({'slots': slots})

# Collections
users_col = db.users
teams_col = db.teams
polls_col = db.polls

from bson import ObjectId

@app.route('/api/team/<team_id>/polls', methods=['GET'])
def get_team_polls(team_id):
    user_email = session.get('email')
    if not user_email:
        return jsonify({'error': 'Authentication required'}), 401
    # Return all open polls for a team
    polls = list(polls_col.find({'team_id': team_id, 'status': 'open'}))
    for poll in polls:
        poll['_id'] = str(poll['_id'])
    return jsonify({'polls': polls})

import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Attachment, FileContent, FileName, FileType, Disposition

def generate_ics(meeting, team_name="Your Team", user_tz="UTC"):
    from datetime import datetime
    import pytz
    slot = meeting['slot']
    start = slot['start']  # ISO format string
    end = slot['end']      # ISO format string
    # Parse as UTC then convert to user_tz
    start_dt_utc = datetime.fromisoformat(start.replace('Z', '+00:00'))
    end_dt_utc = datetime.fromisoformat(end.replace('Z', '+00:00'))
    try:
        tz = pytz.timezone(user_tz)
    except Exception:
        tz = pytz.UTC
        user_tz = 'UTC'
    start_dt = start_dt_utc.astimezone(tz)
    end_dt = end_dt_utc.astimezone(tz)
    dtstamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    uid = f"{meeting.get('_id', 'meeting')}-{dtstamp}@chronoconqueror.com"
    summary = f"{team_name} Meeting"
    # Add TZID to DTSTART/DTEND, and VTIMEZONE block for compatibility
    ics = f"""BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//ChronoConqueror//Calstack//EN\nCALSCALE:GREGORIAN\nMETHOD:REQUEST\nBEGIN:VEVENT\nDTSTART;TZID={user_tz}:{start_dt.strftime('%Y%m%dT%H%M%S')}\nDTEND;TZID={user_tz}:{end_dt.strftime('%Y%m%dT%H%M%S')}\nDTSTAMP:{dtstamp}\nUID:{uid}\nSUMMARY:{summary}\nDESCRIPTION:Scheduled via Calstack\nEND:VEVENT\nEND:VCALENDAR\n"""
    return ics

def send_meeting_invites(meeting, participants, team_name="Your Team"):
    import os
    import pytz
    from sendgrid.helpers.mail import Content
    from datetime import datetime
    sg_api_key = os.environ.get('SENDGRID_API_KEY')
    if not sg_api_key:
        print("SendGrid API key not set!")
        return
    slot = meeting['slot']
    subject = f"New Meeting Scheduled for {team_name}"
    for email in participants:
        # Fetch user timezone from MongoDB
        user_doc = users_col.find_one({'email': email})
        user_tz = user_doc.get('timezone', 'UTC') if user_doc else 'UTC'
        ics_content = generate_ics(meeting, team_name, user_tz=user_tz)
        try:
            tz = pytz.timezone(user_tz)
        except Exception:
            tz = pytz.UTC
        # Parse UTC times and convert to local
        start_utc = datetime.fromisoformat(slot['start'].replace('Z', '+00:00'))
        end_utc = datetime.fromisoformat(slot['end'].replace('Z', '+00:00'))
        start_local = start_utc.astimezone(tz)
        end_local = end_utc.astimezone(tz)
        # Format with timezone name
        start_str = start_local.strftime('%Y-%m-%d %I:%M %p (%Z)')
        end_str = end_local.strftime('%Y-%m-%d %I:%M %p (%Z)')
        body = (
            f"A new meeting has been scheduled for your team.\n\n"
            f"Start: {start_str}\n"
            f"End: {end_str}\n\n"
            f"This invite should appear in your calendar."
        )
        message = Mail(
            from_email=Email('scheduler@chronoconqueror.com', team_name),
            to_emails=To(email),
            subject=subject,
            plain_text_content=body
        )
        # Add calendar invite as an alternative content (inline, not just attachment)
        message.add_content(Content("text/calendar", ics_content))
        try:
            sg = SendGridAPIClient(sg_api_key)
            response = sg.send(message)
            print(f"Email sent to {email}: {response.status_code}")
        except Exception as e:
            print(f"Error sending email to {email}: {e}")

@app.route('/api/team/<team_id>/polls/<poll_id>/vote', methods=['POST'])
def vote_poll(team_id, poll_id):
    data = request.get_json()
    user_email = data['user_email']
    selected_slots = data['selected_slots']  # list of {start, end}
    # Add or update the user's vote in the poll
    poll = polls_col.find_one({'_id': ObjectId(poll_id), 'team_id': team_id})
    if not poll:
        return jsonify({'error': 'Poll not found'}), 404
    # Remove existing vote by this user
    poll['votes'] = [v for v in poll.get('votes', []) if v['user_email'] != user_email]
    poll['votes'].append({'user_email': user_email, 'selected_slots': selected_slots})
    polls_col.update_one({'_id': ObjectId(poll_id)}, {'$set': {'votes': poll['votes']}})

    # Finalize poll if all participants have voted
    all_voted = set(v['user_email'] for v in poll['votes']) == set(poll['participants'])
    if all_voted:
        from collections import Counter
        slot_counter = Counter()
        for v in poll['votes']:
            for slot in v['selected_slots']:
                slot_tuple = (slot['start'], slot['end'])
                slot_counter[slot_tuple] += 1
        if slot_counter:
            max_votes = max(slot_counter.values())
            top_slots = [s for s, c in slot_counter.items() if c == max_votes]
            import random
            chosen_slot = random.choice(top_slots)
            meeting = {
                'team_id': poll['team_id'],
                'slot': {'start': chosen_slot[0], 'end': chosen_slot[1]},
                'attendees': poll['participants'],
                'poll_id': str(poll['_id'])  # Reference to the poll that created this meeting
            }
            db.meetings.insert_one(meeting)
            polls_col.update_one({'_id': ObjectId(poll_id)}, {'$set': {'status': 'closed', 'result': {'start': chosen_slot[0], 'end': chosen_slot[1]}}})
            # Send calendar invites
            team = teams_col.find_one({'_id': ObjectId(team_id)})
            team_name = team.get('name', 'Your Team') if team else 'Your Team'
            send_meeting_invites(meeting, poll['participants'], team_name)
    return jsonify({'success': True})
polls_col = db.polls
availability_col = db.availability

@app.route('/api/team/<team_id>/leave', methods=['POST'])
def leave_team(team_id):
    user_email = session.get('email')
    team = teams_col.find_one({'_id': ObjectId(team_id)})
    if not team or user_email not in team['members']:
        return jsonify({'error': 'Not a member of this team'}), 403
    # Remove user from team
    teams_col.update_one({'_id': ObjectId(team_id)}, {'$pull': {'members': user_email}})
    team = teams_col.find_one({'_id': ObjectId(team_id)})
    if not team['members']:
        # Delete team, polls, meetings if no members remain
        teams_col.delete_one({'_id': ObjectId(team_id)})
        polls_col.delete_many({'team_id': team_id})
        db.meetings.delete_many({'team_id': team_id})
    return jsonify({'success': True})

@app.route('/api/team/<team_id>/meetings/<meeting_id>', methods=['DELETE'])
def delete_meeting(team_id, meeting_id):
    user_email = session.get('email')
    meeting = db.meetings.find_one({'_id': ObjectId(meeting_id), 'team_id': team_id})
    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404
    poll_id = meeting.get('poll_id')
    poll = polls_col.find_one({'_id': ObjectId(poll_id)}) if poll_id else None
    if not poll or poll.get('creator') != user_email:
        return jsonify({'error': 'Not authorized'}), 403
    db.meetings.delete_one({'_id': ObjectId(meeting_id)})
    return jsonify({'success': True})

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
        # Input validation
        team_name = request.form.get('team_name', '').strip()
        if not team_name:
            return render_template('create_team.html', error='Team name is required')
        if len(team_name) > 100:
            return render_template('create_team.html', error='Team name too long (max 100 characters)')
        
        invited_emails_raw = request.form.get('invited_emails', '')
        invited_emails = [e.strip() for e in invited_emails_raw.split(',') if e.strip()]
        
        # Validate email formats
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for email in invited_emails:
            if not re.match(email_pattern, email):
                return render_template('create_team.html', error=f'Invalid email format: {email}')
        import secrets
        code = secrets.token_hex(4)
        members = [user_email]  # Only creator is a member at first
        team = {"name": team_name, "members": members, "code": code}
        result = teams_col.insert_one(team)
        # Send invites to invited_emails using the same logic as invite_members endpoint
        if invited_emails:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To
            import os
            sg_api_key = os.environ.get('SENDGRID_API_KEY')
            if sg_api_key:
                team_name = team_name
                invite_code = code
                join_url = f"{request.host_url.rstrip('/')}/team/join?code={invite_code}"
                for email in invited_emails:
                    subject = f"You're invited to join {team_name} on Calstack!"
                    html_content = f"""
                    <p>{user_email} has invited you to join the team <b>{team_name}</b> on Calstack.</p>
                    <p>Click the link below to join the team (after logging in):</p>
                    <p><a href='{join_url}'>{join_url}</a></p>
                    <p>Or use this invite code: <b>{invite_code}</b></p>
                    <br><p>Best,<br>The Calstack Team</p>
                    """
                    message = Mail(
                        from_email=Email('scheduler@chronoconqueror.com', 'Calstack'),
                        to_emails=To(email),
                        subject=subject,
                        html_content=html_content
                    )
                    try:
                        sg = SendGridAPIClient(sg_api_key)
                        sg.send(message)
                    except Exception as e:
                        print(f"Error sending invite to {email}: {e}")
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
    code = request.args.get('code', '')
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
    return render_template("join_team.html", error=error, code=code)

@app.route('/team/<team_id>')
def team_page(team_id):
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    team = teams_col.find_one({"_id": ObjectId(team_id)})
    if not team:
        return "Team not found", 404
    # Convert ObjectId to string for JSON serialization
    team['_id'] = str(team['_id'])
    # Get all members
    members = team.get('members', [])
    # Get current user's availability
    avail_doc = availability_col.find_one({"team_id": team_id, "user_email": user_email})
    busy = avail_doc['busy'] if avail_doc else []
    # Fetch user's timezone from users_col
    user_doc = users_col.find_one({'email': user_email})
    user_timezone = user_doc.get('timezone', 'UTC') if user_doc else 'UTC'
    return render_template("team_page.html", team=team, user_email=user_email, members=members, busy=busy, user_timezone=user_timezone)

@app.route('/team/<team_id>/availability/<email>')
def get_member_availability(team_id, email):
    # Security: Require authentication and team membership
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    
    # Verify user is member of the team
    team = teams_col.find_one({"_id": ObjectId(team_id)})
    if not team or user_email not in team.get('members', []):
        return jsonify({"error": "Access denied"}), 403
    
    # Verify requested email is also a team member
    if email not in team.get('members', []):
        return jsonify({"error": "User not found in team"}), 404
    
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
    # JS: 0=Sun, 1=Mon, ..., 6=Sat; Python: 0=Mon, ..., 6=Sun
    days_js = data.get('days', list(range(7)))
    days_py = [(d - 1) % 7 for d in days_js]  # remap JS to Python
    end_hour = int(data.get('end_hour', 18))
    # Get all busy intervals for selected participants
    avail_docs = availability_col.find({"team_id": team_id, "user_email": {"$in": participants}})
    member_busy = {doc['user_email']: doc.get('busy', []) for doc in avail_docs}
    # Build list of busy intervals per member as tuples (start, end) in UTC
    busy_map = {}
    utc = datetime.timezone.utc
    for user, busy_list in member_busy.items():
        busy_map[user] = [(
            datetime.datetime.fromisoformat(b['start'].replace('Z','+00:00')).astimezone(utc),
            datetime.datetime.fromisoformat(b['end'].replace('Z','+00:00')).astimezone(utc)
        ) for b in busy_list]
    # Define candidate slots: next 7 days, blocks of chosen duration, filtered by days/hours
    now = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    slots = []
    for day in range(7):
        d = now + datetime.timedelta(days=day)
        weekday = d.weekday() # 0=Mon,6=Sun
        if weekday in days_py:
            # Allow slots from 6am to end_hour
            for h in range(6, end_hour):
                slot_start = d.replace(hour=h, minute=0, tzinfo=datetime.timezone.utc)
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

# --- Invite Members Endpoint ---
@app.route('/api/team/<team_id>/invite', methods=['POST'])
def invite_members(team_id):
    user_email = session.get('email')
    team = teams_col.find_one({'_id': ObjectId(team_id)})
    if not team or user_email not in team['members']:
        return jsonify({'error': 'Not authorized'}), 403
    data = request.get_json()
    emails = data.get('emails', [])
    if not emails or not isinstance(emails, list):
        return jsonify({'error': 'No emails provided'}), 400
    import os
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, To, Content
    sg_api_key = os.environ.get('SENDGRID_API_KEY')
    if not sg_api_key:
        return jsonify({'error': 'Email service not configured'}), 500
    team_name = team.get('name', 'Your Team')
    invite_code = team.get('code')
    join_url = f"{request.host_url.rstrip('/')}/team/join?code={invite_code}"
    sent = 0
    for email in emails:
        subject = f"You're invited to join {team_name} on Calstack!"
        html_content = f"""
        <p>{user_email} has invited you to join the team <b>{team_name}</b> on Calstack.</p>
        <p>Click the link below to join the team (after logging in):</p>
        <p><a href='{join_url}'>{join_url}</a></p>
        <p>Or use this invite code: <b>{invite_code}</b></p>
        <br><p>Best,<br>The Calstack Team</p>
        """
        message = Mail(
            from_email=Email('scheduler@chronoconqueror.com', 'Calstack'),
            to_emails=To(email),
            subject=subject,
            html_content=html_content
        )
        try:
            sg = SendGridAPIClient(sg_api_key)
            sg.send(message)
            sent += 1
        except Exception as e:
            print(f"Error sending invite to {email}: {e}")
    return jsonify({'success': True, 'sent': sent})

# --- Poll and Meeting Endpoints ---
from bson import ObjectId as BsonObjectId

@app.route('/api/team/<team_id>/polls/<poll_id>', methods=['DELETE'])
def delete_poll(team_id, poll_id):
    user_email = session.get('email')
    poll = polls_col.find_one({'_id': ObjectId(poll_id), 'team_id': team_id})
    if not poll:
        return jsonify({'error': 'Poll not found'}), 404
    if poll.get('creator') != user_email:
        return jsonify({'error': 'Not authorized'}), 403
    polls_col.delete_one({'_id': ObjectId(poll_id)})
    return jsonify({'success': True})

@app.route('/team/<team_id>/create_poll', methods=['POST'])
def create_poll(team_id):
    data = request.get_json()
    slots = data.get('slots', [])
    user_email = session.get('email')
    team = teams_col.find_one({'_id': ObjectId(team_id)})
    if not team or not slots or not user_email:
        return jsonify({'error': 'Missing data'}), 400
    participants = team['members']
    poll = {
        'team_id': team_id,
        'proposed_slots': slots,  # [{start, end}, ...]
        'participants': participants,
        'votes': {},  # email: slot_index
        'status': 'open',
        'creator': user_email
    }
    poll_id = polls_col.insert_one(poll).inserted_id
    return jsonify({'poll_id': str(poll_id)})

@app.route('/poll/<poll_id>/legacy_vote', methods=['POST'])
def legacy_vote_poll(poll_id):
    data = request.get_json()
    slot_index = data.get('slot_index')
    user_email = session.get('email')
    poll = polls_col.find_one({'_id': BsonObjectId(poll_id)})
    if not poll or poll['status'] != 'open' or user_email not in poll['participants']:
        return jsonify({'error': 'Invalid poll or user'}), 400
    # Record vote
    polls_col.update_one({'_id': BsonObjectId(poll_id)}, {f'$set': {f'votes.{user_email}': slot_index}})
    poll = polls_col.find_one({'_id': BsonObjectId(poll_id)})
    # If all have voted, close poll and schedule meeting
    if len(poll['votes']) == len(poll['participants']):
        from collections import Counter
        vote_counts = Counter(poll['votes'].values())
        top = vote_counts.most_common()
        if len(top) == 0:
            return jsonify({'error': 'No votes'}), 400
        max_votes = top[0][1]
        winners = [i for i, c in vote_counts.items() if c == max_votes]
        import random
        chosen_index = random.choice(winners)
        slot_list = poll.get('proposed_slots') or poll.get('options', [])
        chosen_slot = slot_list[int(chosen_index)]
        # Create meeting
        meeting = {
            'team_id': poll['team_id'],
            'slot': chosen_slot,
            'attendees': poll['participants']
        }
        meetings_col = db.meetings
        meetings_col.insert_one(meeting)
        # Close poll
        polls_col.update_one({'_id': BsonObjectId(poll_id)}, {'$set': {'status': 'closed', 'result': chosen_slot}})
    return jsonify({'success': True})

@app.route('/team/<team_id>/polls')
def get_team_polls_page(team_id):
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    polls = list(polls_col.find({'team_id': team_id, 'status': 'open'}))
    for poll in polls:
        poll['_id'] = str(poll['_id'])
    return jsonify({'polls': polls})

@app.route('/team/<team_id>/meetings')
def get_team_meetings(team_id):
    user_email = session.get('email')
    if not user_email:
        return redirect(url_for('index'))
    meetings_col = db.meetings
    meetings = list(meetings_col.find({'team_id': team_id}))
    for meeting in meetings:
        meeting['_id'] = str(meeting['_id'])
        # Add poll_id_creator if meeting has poll_id
        poll_id = meeting.get('poll_id')
        if poll_id:
            poll = polls_col.find_one({'_id': ObjectId(poll_id)})
            meeting['poll_id_creator'] = poll.get('creator') if poll else None
    return jsonify({'meetings': meetings})

@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        GOOGLE_CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=os.environ.get('OAUTH2_REDIRECT_URI')  # match Google OAuth redirect URI
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

@app.route('/login/outlook')
def login_outlook():
    # Start Microsoft OAuth2 flow
    ms_client_id = os.environ.get('MS_CLIENT_ID')
    # Use dedicated redirect URI for Microsoft
    ms_redirect_uri = os.environ.get('MS_OUTLOOK_REDIRECT_URI', 'https://calstack.com/oauth2callback/outlook')
    ms_auth_url = (
        f"{MS_AUTHORITY}/oauth2/v2.0/authorize?"
        f"client_id={ms_client_id}&response_type=code&redirect_uri={ms_redirect_uri}"
        f"&response_mode=query&scope={' '.join(MS_SCOPES)}&state=12345"
    )
    # Write debug info to a file for troubleshooting
    try:
        with open('/tmp/ms_oauth_debug.txt', 'w') as f:
            f.write(ms_auth_url + '\n')
        # Log env at runtime
        with open('/tmp/ms_env_debug.txt', 'a') as f:
            f.write(f"RUNTIME: MS_OUTLOOK_REDIRECT_URI={ms_redirect_uri}\nRUNTIME: MS_CLIENT_ID={ms_client_id}\n")
    except Exception as e:
        pass
    print('[DEBUG] Microsoft OAuth2 URL:', ms_auth_url)
    return redirect(ms_auth_url)



@app.route('/oauth2callback/outlook')
def oauth2callback_outlook():
    # Handle Microsoft OAuth2 callback
    code = request.args.get('code')
    if not code:
        return "Missing code in callback", 400
    # Exchange code for token
    ms_client_id = os.environ.get('MS_CLIENT_ID')
    ms_client_secret = os.environ.get('MS_CLIENT_SECRET')
    # Use dedicated redirect URI for Microsoft token exchange
    ms_redirect_uri = os.environ.get('MS_OUTLOOK_REDIRECT_URI', 'https://calstack.com/oauth2callback/outlook')
    token_url = f"{MS_AUTHORITY}/oauth2/v2.0/token"
    data = {
        'client_id': ms_client_id,
        'scope': ' '.join(MS_SCOPES),
        'code': code,
        'redirect_uri': ms_redirect_uri,
        'grant_type': 'authorization_code',
        'client_secret': ms_client_secret
    }
    resp = requests.post(token_url, data=data)
    if resp.status_code != 200:
        return f"Token exchange failed: {resp.text}", 400
    token_data = resp.json()
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    if not access_token:
        return "No access token received", 400
    # Get user email
    user_resp = requests.get('https://graph.microsoft.com/v1.0/me', headers={'Authorization': f'Bearer {access_token}'})
    if user_resp.status_code != 200:
        return "Failed to fetch user info", 400
    ms_profile = user_resp.json()
    email = ms_profile.get('mail') or ms_profile.get('userPrincipalName')
    if not email:
        return "Could not retrieve email from Microsoft profile.", 400
    session['email'] = email
    session['ms_credentials'] = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'scopes': MS_SCOPES
    }
    # Fetch mailbox settings to get timezone
    try:
        print(f"[DEBUG] access_token: {access_token[:5]}...{access_token[-5:]}")
        tz_resp = requests.get('https://graph.microsoft.com/v1.0/me/mailboxSettings', headers={'Authorization': f'Bearer {access_token}'})
        print(f"[DEBUG] tz_resp.status_code: {tz_resp.status_code}")
        print(f"[DEBUG] tz_resp.text: {tz_resp.text}")
    except Exception as e:
        print(f"[DEBUG] Exception during mailboxSettings fetch: {e}")
        tz_resp = None
    user_tz = 'UTC'
    if tz_resp and tz_resp.status_code == 200:
        try:
            mailbox_settings = tz_resp.json()
            print(f"[DEBUG] mailbox_settings: {mailbox_settings}")
            ms_tz = mailbox_settings.get('timeZone', 'UTC')
            print(f"[DEBUG] ms_tz (raw Outlook timeZone): {ms_tz}")
            # Map Windows to IANA timezone if possible
            WINDOWS_TO_IANA = {
                # US
                'UTC': 'UTC',
                'Eastern Standard Time': 'America/New_York',
                'Central Standard Time': 'America/Chicago',
                'Pacific Standard Time': 'America/Los_Angeles',
                'Mountain Standard Time': 'America/Denver',
                'Alaskan Standard Time': 'America/Anchorage',
                'Hawaiian Standard Time': 'Pacific/Honolulu',
                'Atlantic Standard Time': 'America/Halifax',
                'Arizona Standard Time': 'America/Phoenix',
                'Pacific Standard Time (Mexico)': 'America/Tijuana',
                # Europe
                'GMT Standard Time': 'Europe/London',
                'W. Europe Standard Time': 'Europe/Berlin',
                'Central Europe Standard Time': 'Europe/Budapest',
                'Romance Standard Time': 'Europe/Paris',
                'Central European Standard Time': 'Europe/Warsaw',
                'E. Europe Standard Time': 'Europe/Bucharest',
                'FLE Standard Time': 'Europe/Kiev',
                'Turkey Standard Time': 'Europe/Istanbul',
                'Russian Standard Time': 'Europe/Moscow',
                # Asia
                'China Standard Time': 'Asia/Shanghai',
                'Singapore Standard Time': 'Asia/Singapore',
                'Tokyo Standard Time': 'Asia/Tokyo',
                'Korea Standard Time': 'Asia/Seoul',
                'SE Asia Standard Time': 'Asia/Bangkok',
                'India Standard Time': 'Asia/Kolkata',
                'Myanmar Standard Time': 'Asia/Yangon',
                'Arabian Standard Time': 'Asia/Dubai',
                'Israel Standard Time': 'Asia/Jerusalem',
                'Iran Standard Time': 'Asia/Tehran',
                # Australia/NZ
                'AUS Eastern Standard Time': 'Australia/Sydney',
                'AUS Central Standard Time': 'Australia/Adelaide',
                'E. Australia Standard Time': 'Australia/Brisbane',
                'Tasmania Standard Time': 'Australia/Hobart',
                'New Zealand Standard Time': 'Pacific/Auckland',
                # Africa
                'South Africa Standard Time': 'Africa/Johannesburg',
                'Egypt Standard Time': 'Africa/Cairo',
                'Morocco Standard Time': 'Africa/Casablanca',
                # South America
                'Argentina Standard Time': 'America/Argentina/Buenos_Aires',
                'SA Eastern Standard Time': 'America/Sao_Paulo',
                'Venezuela Standard Time': 'America/Caracas',
                # Add more as needed; see: https://github.com/unicode-org/cldr/blob/main/common/supplemental/windowsZones.xml
            }
            user_tz = WINDOWS_TO_IANA.get(ms_tz, 'UTC')
        except Exception as e:
            print(f"[DEBUG] Exception during mailboxSettings parsing: {e}")
    else:
        print(f"[DEBUG] tz_resp.status_code: {tz_resp.status_code}")
        print(f"[DEBUG] tz_resp.text: {tz_resp.text}")
    # Upsert user with timezone
    users_col.update_one({'email': email}, {'$set': {'name': email.split('@')[0], 'timezone': user_tz}}, upsert=True)
    print(f"[DEBUG] Outlook login: {email} timezone set to {user_tz}")
    # Sync Outlook availability
    sync_user_availability(email, None, provider='outlook')
    return redirect(url_for('home'))


def sync_user_availability(email, creds, provider='google'):
    """
    Fetch user's Calendar busy times for next 7 days and upsert for all their teams.
    Supports both Google and Outlook providers.
    """
    print(f"Syncing availability for {email} (provider={provider})")
    busy = []
    import datetime
    now = datetime.datetime.utcnow()
    seven_days_later = now + datetime.timedelta(days=7)
    time_min = now.isoformat() + 'Z'
    time_max = seven_days_later.isoformat() + 'Z'
    if provider == 'google':
        from googleapiclient.discovery import build as g_build
        service = g_build('calendar', 'v3', credentials=creds)
        freebusy_query = {
            "timeMin": time_min,
            "timeMax": time_max,
            "timeZone": "UTC",
            "items": [{"id": "primary"}]
        }
        freebusy_result = service.freebusy().query(body=freebusy_query).execute()
        busy = freebusy_result['calendars']['primary'].get('busy', [])
    elif provider == 'outlook':
        # Get access token from session
        ms_creds = session.get('ms_credentials')
        if not ms_creds:
            print('No Outlook credentials in session')
            return
        access_token = ms_creds.get('access_token')
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        # Use getSchedule for free/busy info
        # See: https://learn.microsoft.com/en-us/graph/api/calendar-getschedule
        graph_url = 'https://graph.microsoft.com/v1.0/me/calendar/getSchedule'
        body = {
            "schedules": [email],
            "startTime": {
                "dateTime": now.strftime('%Y-%m-%dT%H:%M:%S'),
                "timeZone": "UTC"
            },
            "endTime": {
                "dateTime": seven_days_later.strftime('%Y-%m-%dT%H:%M:%S'),
                "timeZone": "UTC"
            },
            "availabilityViewInterval": 60
        }
        resp = requests.post(graph_url, headers=headers, json=body)
        if resp.status_code != 200:
            print('Failed to fetch Outlook free/busy:', resp.text)
            busy = []
        else:
            data = resp.json()
            # Parse busy times to match Google format: [{start, end}]
            busy = []
            if data.get('value'):
                for sched in data['value']:
                    for b in sched.get('scheduleItems', []):
                        if b['status'] == 'busy':
                            busy.append({
                                'start': b['start']['dateTime'],
                                'end': b['end']['dateTime']
                            })
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

    # Fetch user's timezone from Google Calendar API
    calendar_service = g_build('calendar', 'v3', credentials=creds)
    tz_settings = calendar_service.settings().get(setting='timezone').execute()
    user_tz = tz_settings.get('value', 'UTC')

    # Upsert user with timezone
    users_col.update_one({'email': email}, {'$set': {'name': email.split('@')[0], 'timezone': user_tz}}, upsert=True)
    print(f"[DEBUG] Google login: {email} timezone set to {user_tz}")

    # Sync availability for all teams
    sync_user_availability(email, creds)

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)