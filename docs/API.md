# API Integration Details

## Overview
This application integrates with three external services: Google Gemini (LLM), Zoom (meeting scheduling), and Gmail SMTP (email delivery).

## Google Gemini
Used via the `agno` framework's `Gemini` model wrapper.

### Model Configuration
- Model ID: `gemini-1.5-flash`
- Capabilities: Text generation, reasoning, structured output
- Usage: Resume analysis, email drafting, interview communication

### Prompt Design Principles
- Provide strict JSON format instructions for structured responses
- Include evaluation criteria explicitly
- Use lower-case style enforcement for emails
- Explicitly instruct: no markdown / no backticks for JSON

## Zoom API
Used for automatic creation of interview meetings.

### Authentication
- Flow: Server-to-Server OAuth
- Endpoint: `https://zoom.us/oauth/token`
- Grant Type: `account_credentials`
- Required Credentials: `account_id`, `client_id`, `client_secret`

### Required Scopes
```
meeting:write:meeting
meeting:write:meeting:admin
user:read:admin
```

### Endpoints Used
| Purpose | Method | Endpoint |
|---------|--------|----------|
| Create Meeting | POST | `/v2/users/me/meetings` |
| Add Registrant (optional) | POST | `/v2/meetings/{meetingId}/registrants` |

### Meeting Payload
```json
{
  "topic": "<Role> Technical Interview",
  "type": 2,
  "start_time": "2025-09-05T11:00:00",
  "duration": 60,
  "timezone": "Asia/Kolkata",
  "settings": {
    "host_video": true,
    "participant_video": true,
    "join_before_host": false,
    "waiting_room": false,
    "mute_upon_entry": true
  }
}
```

## Gmail SMTP
Used for transactional emails.

### Server Configuration
| Setting | Value |
|---------|-------|
| Host | `smtp.gmail.com` |
| Port | `587` |
| Security | STARTTLS |
| Auth | App Password (NOT regular password) |

### Failure Modes
| Error | Cause | Fix |
|-------|-------|-----|
| 535 Authentication Failed | Wrong password / not App Password | Enable 2FA + create App Password |
| Timeout | Network / firewall | Check connectivity |
| Daily Limit | Gmail quota exceeded | Wait or upgrade |

## Error Handling Strategy
| Layer | Strategy |
|-------|----------|
| Gemini | JSON cleaning + fallback message |
| Zoom | Token reuse + scope-aware error messages |
| Email | Granular exception handling + user feedback |
| PDF | Try/except around parsing + empty fallback |

## Security Notes
- Never hardcode credentials in `app.py`
- `.env` should be excluded from version control
- Use environment variables in production deployments
- Rotate keys regularly for Gemini & Zoom

## Extending Integrations
### Add Calendar Integration
1. Implement Google Calendar OAuth
2. Create event after meeting creation
3. Email event .ics attachment to candidate

### Add ATS Export
1. Serialize analysis result (JSON)
2. Push to ATS REST API endpoint
3. Log status + retry on transient failures

---
End of API integration documentation.
