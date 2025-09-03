# Troubleshooting Guide

## Email Issues
### 1. Authentication Failed (535)
**Cause:** Using normal Gmail password instead of App Password.  
**Fix:** Enable 2FA → Create App Password → Replace in sidebar.

### 2. Email Not Delivered
- Check spam folder
- Ensure `EMAIL_SENDER` matches the authenticated account
- Reduce frequency to avoid rate limiting

### 3. Timeout Errors
- Local firewall blocking SMTP
- Try switching networks

## Zoom Issues
### 1. Invalid Access Token / Missing Scopes
**Message:** `Invalid access token, does not contain scopes`  
**Fix:** Add required scopes:  
```
meeting:write:meeting
meeting:write:meeting:admin
user:read:admin
```

### 2. Registrant Add Fails (400)
Common if registration isn't enabled. Not critical. The meeting link still works.

### 3. Meeting Not Created
- Confirm app type: must be Server-to-Server OAuth
- Ensure account has meeting privileges

## Gemini Issues
### 1. JSON Parsing Errors
**Cause:** Model returned extra text or markdown fences.  
**Fix:** Already handled by cleaning logic. If persistent, tighten prompt.

### 2. Rate Limits
- Add retry with exponential backoff
- Cache static role requirements

### 3. Model Unavailable
Switch to a fallback model ID if exposed by provider.

## Resume Processing Issues
### 1. Blank Extraction
- PDF is scanned image (needs OCR) – integrate Tesseract for enhancement
- Corrupt or encrypted PDF

### 2. Unicode Artifacts
Strip control characters before analysis.

## General Debug Steps
1. Use sidebar test buttons
2. Check Streamlit console output
3. Validate environment variables loaded
4. Re-run with `--server.runOnSave true` during dev

## Logging Enhancements (Optional)
Add rotating file handler:
```python
import logging
handler = logging.handlers.RotatingFileHandler('app.log', maxBytes=1_000_000, backupCount=3)
logger.addHandler(handler)
```

## When to Open an Issue
Open a ticket if:
- Reproducible crash with stack trace
- Consistent API failure despite correct credentials
- Feature request with clear acceptance criteria

---
End of troubleshooting guide.
