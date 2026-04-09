---
name: gws
description: "Google Workspace -- Gmail, Calendar, Drive, Sheets, Docs, Tasks. Use when: send email, check calendar, read/write spreadsheets, manage Drive files, Google Tasks."
user-invocable: true
argument-hint: "[service] [action]"
---

# GWS -- Google Workspace

CLI: `gws` (Google official). Requires OAuth 2.0 setup.

## Setup

```bash
# 1. Install gws CLI
pip install google-workspace-cli

# 2. Create OAuth credentials at https://console.cloud.google.com
#    APIs & Services > Credentials > Create OAuth Client ID
#    Download as client_secret.json

# 3. Place credentials
mkdir -p ~/.config/gws
cp client_secret.json ~/.config/gws/

# 4. Authenticate (opens browser)
gws auth login

# 5. Verify
gws auth status
```

## Health Check

```bash
bash $CLAUDE_SKILL_DIR/scripts/health-check.sh
```

## Gmail

```bash
# List recent emails
gws gmail users messages list --params '{"userId":"me","maxResults":10,"q":"newer_than:7d"}'

# Read email
gws gmail users messages get --params '{"userId":"me","id":"MSG_ID","format":"full"}'

# Search
gws gmail users messages list --params '{"userId":"me","q":"from:someone@email.com subject:urgent","maxResults":5}'

# Send email (CONFIRM with operator before sending)
python3 -c "
import base64, json, subprocess
from email.mime.text import MIMEText

msg = MIMEText('Email body here')
msg['to'] = 'recipient@email.com'
msg['subject'] = 'Subject'
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
result = subprocess.run([
    'gws', 'gmail', 'users', 'messages', 'send',
    '--params', '{\"userId\":\"me\"}',
    '--json', json.dumps({'raw': raw})
], capture_output=True, text=True)
print(result.stdout)
"
```

## Calendar

```bash
# List calendars
gws calendar calendarList list

# Events for a period
gws calendar events list --params '{
  "calendarId":"primary",
  "timeMin":"2026-01-01T00:00:00Z",
  "timeMax":"2026-01-07T00:00:00Z",
  "singleEvents":true,
  "orderBy":"startTime"
}'

# Create event (CONFIRM with operator)
gws calendar events insert --params '{"calendarId":"primary"}' --json '{
  "summary":"Meeting",
  "start":{"dateTime":"2026-01-02T10:00:00+03:00"},
  "end":{"dateTime":"2026-01-02T11:00:00+03:00"},
  "reminders":{"useDefault":false,"overrides":[
    {"method":"popup","minutes":1440},
    {"method":"popup","minutes":180},
    {"method":"popup","minutes":15}
  ]}
}'
```

## Drive

```bash
# List files
gws drive files list --params '{"pageSize":10,"q":"name contains \"report\""}'

# Download file
gws drive files get --params '{"fileId":"FILE_ID","alt":"media"}' --output /tmp/file.pdf

# Upload file
gws drive files create --params '{"uploadType":"multipart"}' --json '{"name":"file.txt","parents":["FOLDER_ID"]}' --upload /path/to/file.txt
```

## Sheets

```bash
# Read data
gws sheets spreadsheets values get --params '{"spreadsheetId":"SHEET_ID","range":"Sheet1!A1:D10"}'

# Write data
gws sheets spreadsheets values update --params '{
  "spreadsheetId":"SHEET_ID",
  "range":"Sheet1!A1:B2",
  "valueInputOption":"USER_ENTERED"
}' --json '{"values":[["A","B"],["1","2"]]}'

# Append rows
gws sheets spreadsheets values append --params '{
  "spreadsheetId":"SHEET_ID",
  "range":"Sheet1!A:C",
  "valueInputOption":"USER_ENTERED",
  "insertDataOption":"INSERT_ROWS"
}' --json '{"values":[["x","y","z"]]}'
```

## Docs

```bash
# Read document
gws docs documents get --params '{"documentId":"DOC_ID"}'

# Export to text
gws drive files export --params '{"fileId":"DOC_ID","mimeType":"text/plain"}' --output /tmp/doc.txt
```

## Tasks

```bash
# List task lists
gws tasks tasklists list

# List tasks
gws tasks tasks list --params '{"tasklist":"TASKLIST_ID"}'
```

## Rules

1. **CONFIRM** before sending email or creating calendar events
2. All output is JSON by default
3. Use `--page-all` for pagination
4. Token auto-refreshes -- no manual renewal needed
5. Credentials in `~/.config/gws/` -- chmod 600
