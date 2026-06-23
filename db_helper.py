import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recruitment.db")

def init_db() -> None:
    """Initialize the SQLite database and create tables if they do not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            role TEXT,
            status TEXT,
            feedback TEXT,
            meeting_id TEXT,
            meeting_link TEXT,
            meeting_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(email, role)
        )
    """)
    
    # Check if we need to alter table to add new columns (resume_text, sent_emails)
    cursor.execute("PRAGMA table_info(candidates)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "resume_text" not in columns:
        cursor.execute("ALTER TABLE candidates ADD COLUMN resume_text TEXT")
    if "sent_emails" not in columns:
        cursor.execute("ALTER TABLE candidates ADD COLUMN sent_emails TEXT")
        
    conn.commit()
    conn.close()

def save_candidate(email: str, role: str, status: str, feedback: str, resume_text: str = None) -> None:
    """Save or update candidate selection status, feedback, and resume text."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if resume_text:
        cursor.execute("""
            INSERT INTO candidates (email, role, status, feedback, resume_text)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(email, role) DO UPDATE SET
                status = excluded.status,
                feedback = excluded.feedback,
                resume_text = excluded.resume_text,
                created_at = CURRENT_TIMESTAMP
        """, (email, role, status, feedback, resume_text))
    else:
        cursor.execute("""
            INSERT INTO candidates (email, role, status, feedback)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email, role) DO UPDATE SET
                status = excluded.status,
                feedback = excluded.feedback,
                created_at = CURRENT_TIMESTAMP
        """, (email, role, status, feedback))
        
    conn.commit()
    conn.close()

def update_candidate_meeting(email: str, role: str, meeting_id: str, meeting_link: str, meeting_time: str) -> None:
    """Update scheduled interview details for a candidate."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE candidates
        SET meeting_id = ?, meeting_link = ?, meeting_time = ?
        WHERE email = ? AND role = ?
    """, (meeting_id, meeting_link, meeting_time, email, role))
    conn.commit()
    conn.close()

def log_sent_email(email: str, role: str, subject: str, body: str) -> None:
    """Log a sent email to the candidate's record in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Retrieve current sent_emails JSON string
    cursor.execute("SELECT sent_emails FROM candidates WHERE email = ? AND role = ?", (email, role))
    row = cursor.fetchone()
    
    emails = []
    if row and row[0]:
        try:
            emails = json.loads(row[0])
            if not isinstance(emails, list):
                emails = []
        except Exception:
            emails = []
            
    # Append the new email record
    new_email = {
        "subject": subject,
        "body": body,
        "timestamp": datetime.now().isoformat()
    }
    emails.append(new_email)
    
    # Write back to database
    cursor.execute("""
        UPDATE candidates
        SET sent_emails = ?
        WHERE email = ? AND role = ?
    """, (json.dumps(emails), email, role))
    
    conn.commit()
    conn.close()

def get_candidates(role_filter: str = "All") -> list:
    """Retrieve candidate records, optionally filtered by role."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if role_filter and role_filter != "All":
        cursor.execute("""
            SELECT * FROM candidates 
            WHERE role = ? 
            ORDER BY created_at DESC
        """, (role_filter,))
    else:
        cursor.execute("""
            SELECT * FROM candidates 
            ORDER BY created_at DESC
        """)
        
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]
