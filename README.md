# CalStack - Team Scheduling Made Simple

A productivity app that intelligently finds mutually available time slots for groups by integrating with your favorite calendar platforms, providing seamless team coordination.

## Features

- **Multi-Platform Calendar Integration**: Google Calendar and Microsoft Outlook support
- **Privacy-First**: Only accesses busy/free times, never event details
- **Multiple Authentication Methods**: Google OAuth, Outlook OAuth, and email/password
- **Team Management**: Create teams, invite members, and coordinate schedules
- **Smart Scheduling**: Algorithm-powered time slot suggestions based on team availability
- **Manual Calendar Upload**: Support for .ics file uploads for non-OAuth users
- **Timezone Awareness**: Automatic timezone detection and conversion
- **Email Notifications**: Meeting invites and team notifications via SendGrid

## Quick Start

### Option 1: Quick Development Setup (Recommended for Testing)

For immediate testing without OAuth setup:

```bash
git clone https://github.com/CS673-Team4/calstack.git
cd calstack
pip install -r requirements.txt

# Copy mock configuration files
cp .env.test .env
cp client_secret_mock.json client_secret.json

# Start the application
python app.py
```

**Note**: This setup uses mock OAuth credentials. Google/Outlook login won't work, but you can test the manual login system and other features.

### Option 2: Full Production Setup

For complete OAuth integration:

### Environment Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-here-min-32-chars
FLASK_DEBUG=1  # Set to 0 for production

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/calstack

# Domain Configuration (for production)
OAUTH2_REDIRECT_URI=https://yourdomain.com/oauth2callback
MS_OUTLOOK_REDIRECT_URI=https://yourdomain.com/oauth2callback/outlook

# SendGrid Email Configuration
SENDGRID_API_KEY=your-sendgrid-api-key-here

# Google OAuth Configuration (uses client_secret.json file)
# Download client_secret.json from Google Cloud Console and place in project root

# Microsoft OAuth Configuration
MS_CLIENT_ID=your-microsoft-application-id
MS_CLIENT_SECRET=your-microsoft-client-secret
AZURE_APPLICATION_ID=your-azure-application-id
AZURE_DIRECTORY_ID=your-azure-directory-tenant-id
```

### Environment Variable Details

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `FLASK_SECRET_KEY` | Flask session encryption key (min 32 chars) | `your-super-secret-key-here-min-32-chars` | ✅ |
| `FLASK_DEBUG` | Enable Flask debug mode (0=off, 1=on) | `1` for dev, `0` for production | ✅ |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017/calstack` | ✅ |
| `OAUTH2_REDIRECT_URI` | Google OAuth redirect URL | `https://yourdomain.com/oauth2callback` | ✅ |
| `MS_OUTLOOK_REDIRECT_URI` | Microsoft OAuth redirect URL | `https://yourdomain.com/oauth2callback/outlook` | ✅ |
| `SENDGRID_API_KEY` | SendGrid API key for email sending | `SG.xyz...` | ✅ |
| `MS_CLIENT_ID` | Microsoft application client ID | `12345678-1234-1234-1234-123456789012` | ✅ |
| `MS_CLIENT_SECRET` | Microsoft application client secret | `abc123~...` | ✅ |
| `AZURE_APPLICATION_ID` | Azure application ID (same as MS_CLIENT_ID) | `12345678-1234-1234-1234-123456789012` | ✅ |
| `AZURE_DIRECTORY_ID` | Azure tenant/directory ID | `87654321-4321-4321-4321-210987654321` | ✅ |

### Getting Environment Variable Values

**Flask Secret Key:**

The Flask secret key is used to encrypt session data and secure cookies. It's critical for security.

```bash
# Generate a secure secret key (32+ characters recommended)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Example output: 'K7Jx9mP2nQ8vR5tY1wE4uI0oP3sA6dF9gH2jK5lN8qT1'
```

**Important:**
- **Keep it secret**: Never commit the secret key to version control
- **Use a strong key**: Minimum 32 characters, randomly generated
- **Unique per environment**: Use different keys for development, staging, and production
- **Rotate regularly**: Change the key periodically for security

**What it does:**
- Encrypts Flask session data (login state, user info)
- Signs secure cookies to prevent tampering
- Protects against CSRF attacks
- Essential for OAuth flows and user authentication

**MongoDB URI:**
- Local development: `mongodb://localhost:27017/calstack`
- Production with auth: `mongodb://username:password@localhost:27017/calstack?authSource=admin`

**OAuth Redirect URIs:**
- Development: `http://localhost:5000/oauth2callback` and `http://localhost:5000/oauth2callback/outlook`
- Production: `https://yourdomain.com/oauth2callback` and `https://yourdomain.com/oauth2callback/outlook`

**SendGrid API Key:**
- Sign up at [SendGrid](https://sendgrid.com/)
- Go to Settings → API Keys → Create API Key
- Choose "Full Access" or "Restricted Access" with Mail Send permissions

**Google OAuth Credentials:**
- Follow the [Google OAuth Setup](#2-google-oauth-setup) section below for complete setup
- Download and configure `client_secret.json` file (see instructions below)

**Downloading Google OAuth client_secret.json:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create a new one)
3. Navigate to **APIs & Services** → **Credentials**
4. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
5. Choose **Web application** as the application type
6. Set **Name** to something like "CalStack Local Dev"
7. Add **Authorized redirect URIs**:
   - For development: `http://localhost:5000/oauth2callback`
   - For production: `https://yourdomain.com/oauth2callback`
8. Click **CREATE**
9. **Immediately after creation**, a popup will show your client ID and secret
10. Click **DOWNLOAD JSON** button in this popup (this downloads `client_secret.json`)
11. **Alternative**: If you missed the popup, go back to the credentials list, find your OAuth 2.0 Client ID, and click the **Download** icon (⬇️)
12. Save the downloaded file as `client_secret.json` in your CalStack project root directory
13. Verify the file is at `/path/to/calstack/client_secret.json` (same level as `app.py`)

**Microsoft OAuth Credentials:**
- Follow the [Microsoft Outlook OAuth Setup](#3-microsoft-outlook-oauth-setup) section below
- Get from Azure Portal → App Registrations → Your App

### Start the Application

```bash
# Activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the development server
python app.py
```

The application will be available at `http://localhost:5000`

## Production Deployment Guide

### Prerequisites

- Linux server (Ubuntu 20.04+ recommended)
- Domain name with DNS control
- SSL certificate (Let's Encrypt recommended)
- Email service (SendGrid account)
- Google Cloud Platform account (for Google OAuth)
- Microsoft Azure account (for Outlook OAuth)

---

## 1. Server Setup

### 1.1 System Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx git curl

# Install MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org

# Start and enable MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod
```

### 1.2 Application Setup

```bash
# Create application user
sudo useradd -m -s /bin/bash calstack
sudo su - calstack

# Clone repository
git clone https://github.com/CS673-Team4/calstack.git
cd calstack

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Environment Configuration

Create `.env` file:

```bash
# Flask Configuration
FLASK_SECRET_KEY=your-super-secret-key-here
FLASK_DEBUG=0

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/calstack

# Domain Configuration
DOMAIN=yourdomain.com
OAUTH2_REDIRECT_URI=https://yourdomain.com/oauth2callback
MS_OUTLOOK_REDIRECT_URI=https://yourdomain.com/oauth2callback/outlook

# SendGrid Configuration
SENDGRID_API_KEY=your-sendgrid-api-key

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft OAuth Configuration
MS_CLIENT_ID=your-microsoft-client-id
MS_CLIENT_SECRET=your-microsoft-client-secret
```

---

## 2. Google OAuth Setup

### 2.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API:
   - Go to **APIs & Services** → **Library**
   - Search for "Google Calendar API" and enable it
   - Search for "People API" and enable it

### 2.2 Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** user type
3. Fill out the required information:
   - **App name**: CalStack
   - **User support email**: support@yourdomain.com
   - **App homepage**: https://yourdomain.com
   - **Privacy Policy**: https://yourdomain.com/privacy-policy
   - **Terms of Service**: https://yourdomain.com/terms-of-service

### 2.3 Add OAuth Scopes

1. In OAuth consent screen, go to **Scopes** section
2. Click **Add or Remove Scopes**
3. Add these scopes:
   - `openid`
   - `https://www.googleapis.com/auth/userinfo.email`
   - `https://www.googleapis.com/auth/userinfo.profile`
   - `https://www.googleapis.com/auth/calendar.events.freebusy`
   - `https://www.googleapis.com/auth/calendar.settings.readonly`

### 2.4 Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Add authorized redirect URIs:
   - `https://yourdomain.com/oauth2callback`
5. Download the client secret JSON file
6. Rename it to `client_secret.json` and place in your app directory

---

## 3. Microsoft Outlook OAuth Setup

### 3.1 Create Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Fill out:
   - **Name**: CalStack
   - **Supported account types**: Accounts in any organizational directory and personal Microsoft accounts
   - **Redirect URI**: Web - `https://yourdomain.com/oauth2callback/outlook`

### 3.2 Configure API Permissions

1. In your app registration, go to **API permissions**
2. Click **Add a permission** → **Microsoft Graph**
3. Choose **Delegated permissions** and add:
   - `openid`
   - `profile`
   - `offline_access`
   - `Calendars.Read`
   - `MailboxSettings.Read`

### 3.3 Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add description and choose expiration
4. Copy the secret value (you won't see it again)
5. Add to your `.env` file as `MS_CLIENT_SECRET`

---

## 4. SendGrid Email Setup

### 4.1 Create SendGrid Account

1. Sign up at [SendGrid](https://sendgrid.com/)
2. Verify your account
3. Create an API key:
   - Go to **Settings** → **API Keys**
   - Click **Create API Key**
   - Choose **Full Access** or **Restricted Access** with Mail Send permissions
   - Copy the API key to your `.env` file

### 4.2 Domain Authentication

1. Go to **Settings** → **Sender Authentication**
2. Click **Authenticate Your Domain**
3. Enter your domain (e.g., `yourdomain.com`)
4. Choose **Yes** for link branding
5. Copy the provided DNS records

### 4.3 DNS Configuration

Add these CNAME records to your DNS provider:

```
# Example records (yours will be different)
s1._domainkey.yourdomain.com → s1.domainkey.u1234567.wl.sendgrid.net
s2._domainkey.yourdomain.com → s2.domainkey.u1234567.wl.sendgrid.net
em1234.yourdomain.com → u1234567.wl.sendgrid.net
```

**Note**: DNS propagation can take up to 24 hours

---

## 5. Web Server Configuration

### 5.1 Gunicorn Setup

Create systemd service file:

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Add this content:

```ini
[Unit]
Description=Gunicorn instance to serve CalStack
After=network.target

[Service]
User=calstack
Group=www-data
WorkingDirectory=/home/calstack/calstack
Environment="PATH=/home/calstack/calstack/venv/bin"
ExecStart=/home/calstack/calstack/venv/bin/gunicorn --workers 3 --bind unix:calstack.sock -m 007 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
```

### 5.2 Nginx Configuration

Create Nginx site configuration:

```bash
sudo nano /etc/nginx/sites-available/calstack
```

Add this content:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/calstack/calstack/calstack.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/calstack/calstack/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/calstack /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

---

## 6. DNS Configuration

### 6.1 Basic DNS Records

Add these records to your DNS provider:

```
# A Records
yourdomain.com → your-server-ip
www.yourdomain.com → your-server-ip

# SendGrid CNAME Records (from step 4.3)
s1._domainkey.yourdomain.com → s1.domainkey.u1234567.wl.sendgrid.net
s2._domainkey.yourdomain.com → s2.domainkey.u1234567.wl.sendgrid.net
em1234.yourdomain.com → u1234567.wl.sendgrid.net
```

**Note**: DNS propagation can take up to 24 hours

---

## 7. SSL Certificate Setup

### 7.1 Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### 7.2 Obtain SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 7.3 Auto-renewal

```bash
sudo crontab -e
```

Add this line:

```
0 12 * * * /usr/bin/certbot renew --quiet
```

---

## 7. DNS Configuration

### 7.1 Basic DNS Records

Add these records to your DNS provider:

```
# A Records
yourdomain.com → your-server-ip
www.yourdomain.com → your-server-ip

# SendGrid CNAME Records (from step 4.3)
s1._domainkey.yourdomain.com → s1.domainkey.u1234567.wl.sendgrid.net
s2._domainkey.yourdomain.com → s2.domainkey.u1234567.wl.sendgrid.net
em1234.yourdomain.com → u1234567.wl.sendgrid.net
```
