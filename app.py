from typing import Literal, Tuple, Dict, Optional
import os
import time
import json
import requests
import PyPDF2
from datetime import datetime, timedelta
import pytz

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import streamlit as st
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.email import EmailTools
from agno.utils.log import logger
from streamlit_pdf_viewer import pdf_viewer


class CustomZoomTool:
    def __init__(self, *, account_id: Optional[str] = None, client_id: Optional[str] = None, client_secret: Optional[str] = None, name: str = "zoom_tool"):
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.name = name
        self.token_url = "https://zoom.us/oauth/token"
        self.base_url = "https://api.zoom.us/v2"
        self.access_token = None
        self.token_expires_at = 0

    def get_access_token(self) -> str:
        if self.access_token and time.time() < self.token_expires_at:
            return str(self.access_token)
        
        if not self.account_id or not self.client_id or not self.client_secret:
            logger.error("Missing Zoom credentials")
            return ""
            
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "account_credentials", "account_id": self.account_id}

        try:
            response = requests.post(
                self.token_url, 
                headers=headers, 
                data=data, 
                auth=(self.client_id, self.client_secret),
                timeout=30
            )
            
            logger.info(f"Zoom token request status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Zoom token request failed: {response.status_code} - {response.text}")
                return ""
            
            response.raise_for_status()

            token_info = response.json()
            self.access_token = token_info["access_token"]
            expires_in = token_info["expires_in"]
            self.token_expires_at = time.time() + expires_in - 60

            logger.info("Zoom access token obtained successfully")
            return str(self.access_token)

        except requests.RequestException as e:
            logger.error(f"Error fetching access token: {e}")
            return ""
        except KeyError as e:
            logger.error(f"Missing key in token response: {e}")
            return ""

    def create_meeting(self, title: str, start_time: str, duration: int = 60, attendee_email: str = "") -> Dict:
        """Create a Zoom meeting"""
        access_token = self.get_access_token()
        if not access_token:
            return {"error": "Could not get access token. Please check your Zoom credentials."}

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        meeting_data = {
            "topic": title,
            "type": 2,  # Scheduled meeting
            "start_time": start_time,
            "duration": duration,
            "timezone": "Asia/Kolkata",
            "settings": {
                "host_video": True,
                "participant_video": True,
                "join_before_host": False,
                "mute_upon_entry": True,
                "waiting_room": False,
                "registrants_email_notification": True
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/users/me/meetings",
                headers=headers,
                json=meeting_data,
                timeout=30
            )
            
            logger.info(f"Zoom meeting creation status: {response.status_code}")
            
            if response.status_code != 201:
                error_text = response.text
                if "scopes" in error_text:
                    logger.error(f"Zoom app missing required scopes: {error_text}")
                    return {"error": f"Zoom app missing required scopes. Please add 'meeting:write:meeting' and 'meeting:write:meeting:admin' scopes to your Zoom app."}
                else:
                    logger.error(f"Zoom meeting creation failed: {response.status_code} - {error_text}")
                    return {"error": f"Meeting creation failed: {response.status_code} - {error_text}"}
            
            response.raise_for_status()
            meeting_info = response.json()

            # Add attendee if provided
            if attendee_email:
                self.add_attendee(meeting_info["id"], attendee_email)

            logger.info(f"Zoom meeting created successfully: {meeting_info.get('id')}")
            return meeting_info

        except requests.RequestException as e:
            logger.error(f"Error creating meeting: {e}")
            return {"error": f"Network error creating meeting: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error creating meeting: {e}")
            return {"error": f"Unexpected error: {str(e)}"}

    def add_attendee(self, meeting_id: str, email: str) -> bool:
        """Add an attendee to a meeting"""
        access_token = self.get_access_token()
        if not access_token:
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        registrant_data = {
            "email": email,
            "first_name": "Candidate",
            "last_name": "Interview"
        }

        try:
            response = requests.post(
                f"{self.base_url}/meetings/{meeting_id}/registrants",
                headers=headers,
                json=registrant_data
            )
            response.raise_for_status()
            return True

        except requests.RequestException as e:
            logger.error(f"Error adding attendee: {e}")
            return False


# Role requirements as a constant dictionary
ROLE_REQUIREMENTS: Dict[str, str] = {
    "ai_ml_engineer": """
        Required Skills:
        - Python, PyTorch/TensorFlow
        - Machine Learning algorithms and frameworks
        - Deep Learning and Neural Networks
        - Data preprocessing and analysis
        - MLOps and model deployment
        - RAG, LLM, Finetuning and Prompt Engineering
    """,

    "frontend_engineer": """
        Required Skills:
        - React/Vue.js/Angular
        - HTML5, CSS3, JavaScript/TypeScript
        - Responsive design
        - State management
        - Frontend testing
    """,

    "backend_engineer": """
        Required Skills:
        - Python/Java/Node.js
        - REST APIs
        - Database design and management
        - System architecture
        - Cloud services (AWS/GCP/Azure)
        - Kubernetes, Docker, CI/CD
    """
}


def init_session_state() -> None:
    """Initialize only necessary session state variables."""
    defaults = {
        'candidate_email': "", 'gemini_api_key': "", 'resume_text': "", 'analysis_complete': False,
        'is_selected': False, 'zoom_account_id': "", 'zoom_client_id': "", 'zoom_client_secret': "",
        'email_sender': "", 'email_passkey': "", 'company_name': "", 'current_pdf': None
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def create_resume_analyzer() -> Agent:
    """Creates and returns a resume analysis agent."""
    if not st.session_state.gemini_api_key:
        st.error("Please enter your Gemini API key first.")
        return None

    return Agent(
        model=Gemini(
            id="gemini-2.0-flash",
            api_key=st.session_state.gemini_api_key
        ),
        description="You are an expert technical recruiter who analyzes resumes.",
        instructions=[
            "Analyze the resume against the provided job requirements",
            "Be lenient with AI/ML candidates who show strong potential",
            "Consider project experience as valid experience",
            "Value hands-on experience with key technologies",
            "Return a JSON response with selection decision and feedback"
        ],
        markdown=True
    )

def create_email_agent() -> Agent:
    return Agent(
        model=Gemini(
            id="gemini-1.5-flash",
            api_key=st.session_state.gemini_api_key
        ),
        description="You are a professional recruitment coordinator handling email communications.",
        instructions=[
            "Draft professional recruitment emails",
            "Act like a human writing an email and use all lowercase letters",
            "Maintain a friendly yet professional tone",
            "Always end emails with exactly: 'best,\nthe ai recruiting team'",
            "Never include the sender's or receiver's name in the signature",
            f"The name of the company is '{st.session_state.company_name}'"
        ],
        markdown=True
    )


def create_scheduler_agent() -> Agent:
    zoom_tools = CustomZoomTool(
        account_id=st.session_state.zoom_account_id,
        client_id=st.session_state.zoom_client_id,
        client_secret=st.session_state.zoom_client_secret
    )

    return Agent(
        name="Interview Scheduler",
        model=Gemini(
            id="gemini-1.5-flash",
            api_key=st.session_state.gemini_api_key
        ),
        description="You are an interview scheduling coordinator.",
        instructions=[
            "You are an expert at scheduling technical interviews using Zoom.",
            "Schedule interviews during business hours (9 AM - 5 PM EST)",
            "Create meetings with proper titles and descriptions",
            "Ensure all meeting details are included in responses",
            "Use ISO 8601 format for dates",
            "Handle scheduling errors gracefully"
        ],
        markdown=True,
        show_tool_calls=True
    )


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email using SMTP"""
    try:
        if not st.session_state.email_sender or not st.session_state.email_passkey:
            st.error("Email credentials not configured properly")
            return False
            
        msg = MIMEMultipart()
        msg['From'] = st.session_state.email_sender
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Use Gmail SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(st.session_state.email_sender, st.session_state.email_passkey)
        
        text = msg.as_string()
        server.sendmail(st.session_state.email_sender, to_email, text)
        server.quit()
        
        st.success(f"Email sent successfully to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        st.error(f"Email authentication failed. Please check your email and app password: {e}")
        return False
    except smtplib.SMTPException as e:
        st.error(f"SMTP error occurred: {e}")
        return False
    except Exception as e:
        st.error(f"Error sending email: {e}")
        logger.error(f"Error sending email: {e}")
        return False


def extract_text_from_pdf(pdf_file) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error extracting PDF text: {str(e)}")
        return ""


def analyze_resume(
    resume_text: str,
    role: Literal["ai_ml_engineer", "frontend_engineer", "backend_engineer"],
    analyzer: Agent
) -> Tuple[bool, str]:
    try:
        response = analyzer.run(
            f"""Please analyze this resume against the following requirements and provide your response in valid JSON format:
            Role Requirements:
            {ROLE_REQUIREMENTS[role]}
            Resume Text:
            {resume_text}
            
            Your response must be a valid JSON object like this:
            {{
                "selected": true,
                "feedback": "Detailed feedback explaining the decision",
                "matching_skills": ["skill1", "skill2"],
                "missing_skills": ["skill3", "skill4"],
                "experience_level": "junior/mid/senior"
            }}
            
            Evaluation criteria:
            1. Match at least 70% of required skills
            2. Consider both theoretical knowledge and practical experience
            3. Value project experience and real-world applications
            4. Consider transferable skills from similar technologies
            5. Look for evidence of continuous learning and adaptability
            
            IMPORTANT: 
            - Return ONLY the JSON object 
            - Do not include any markdown formatting, backticks, or explanatory text
            - Make sure the JSON is valid and parseable
            - Use boolean values (true/false) not strings
            """
        )

        assistant_message = next((msg.content for msg in response.messages if msg.role == 'assistant'), None)
        if not assistant_message:
            raise ValueError("No assistant message found in response.")

        # Clean the response to extract JSON
        content = assistant_message.strip()
        
        # Remove markdown formatting if present
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        # Try to parse JSON
        result = json.loads(content)
        if not isinstance(result, dict) or not all(k in result for k in ["selected", "feedback"]):
            raise ValueError("Invalid response format")

        return result["selected"], result["feedback"]

    except (json.JSONDecodeError, ValueError) as e:
        st.error(f"Error processing response: {str(e)}")
        # Return a default response if JSON parsing fails
        return False, f"Resume analysis could not be completed due to parsing error: {str(e)}"
    except Exception as e:
        st.error(f"Unexpected error during analysis: {str(e)}")
        return False, f"Resume analysis failed: {str(e)}"


def send_selection_email(email_agent: Agent, to_email: str, role: str) -> None:
    # Generate email content using AI
    response = email_agent.run(
        f"""
        Draft an email to congratulate a candidate on being selected for the {role} position.
        The email should:
        1. Congratulate them on being selected
        2. Explain the next steps in the process
        3. Mention that they will receive interview details shortly
        4. The name of the company is 'AI Recruiting Team'
        5. Use all lowercase letters
        6. End with exactly: 'best,\nthe ai recruiting team'
        
        Return only the email body text, no subject line.
        """
    )
    
    # Extract the email content
    email_content = next((msg.content for msg in response.messages if msg.role == 'assistant'), "")
    
    # Send the email
    success = send_email(
        to_email=to_email,
        subject=f"congratulations! you've been selected for the {role} position",
        body=email_content
    )
    
    if not success:
        st.error("Failed to send selection email")


def send_rejection_email(email_agent: Agent, to_email: str, role: str, feedback: str) -> None:
    """
    Send a rejection email with constructive feedback.
    """
    # Generate email content using AI
    response = email_agent.run(
        f"""
        Draft an email regarding rejection for the {role} position.
        Use this specific style:
        1. use all lowercase letters
        2. be empathetic and human
        3. mention specific feedback from: {feedback}
        4. encourage them to upskill and try again
        5. suggest some learning resources based on missing skills
        6. end the email with exactly:
           best,
           the ai recruiting team
        
        Do not include any names in the signature.
        The tone should be like a human writing a quick but thoughtful email.
        Return only the email body text, no subject line.
        """
    )
    
    # Extract the email content
    email_content = next((msg.content for msg in response.messages if msg.role == 'assistant'), "")
    
    # Send the email
    success = send_email(
        to_email=to_email,
        subject=f"update on your application for {role} position",
        body=email_content
    )
    
    if not success:
        st.error("Failed to send rejection email")


def schedule_interview(scheduler: Agent, candidate_email: str, email_agent: Agent, role: str) -> None:
    """
    Schedule interviews during business hours (9 AM - 5 PM IST).
    """
    try:
        # Get current time in IST
        ist_tz = pytz.timezone('Asia/Kolkata')
        current_time_ist = datetime.now(ist_tz)

        tomorrow_ist = current_time_ist + timedelta(days=1)
        interview_time = tomorrow_ist.replace(hour=11, minute=0, second=0, microsecond=0)
        formatted_time = interview_time.strftime('%Y-%m-%dT%H:%M:%S')

        # Create Zoom meeting directly
        zoom_tool = CustomZoomTool(
            account_id=st.session_state.zoom_account_id,
            client_id=st.session_state.zoom_client_id,
            client_secret=st.session_state.zoom_client_secret
        )
        
        meeting_info = zoom_tool.create_meeting(
            title=f"{role} Technical Interview",
            start_time=formatted_time,
            duration=60,
            attendee_email=candidate_email
        )
        
        if "error" in meeting_info:
            st.warning(f"Could not create Zoom meeting automatically: {meeting_info['error']}")
            if "scopes" in meeting_info['error']:
                st.info("💡 **Fix:** Go to your Zoom app settings and add the required scopes:\n- `meeting:write:meeting`\n- `meeting:write:meeting:admin`\n- `user:read:admin`")
            # Still send email with manual scheduling note
            meeting_details = f"""
📅 Interview Details:
- Meeting Title: {role} Technical Interview
- Date & Time: {interview_time.strftime('%B %d, %Y at %I:%M %p IST')}
- Duration: 60 minutes

Note: Zoom meeting link will be shared separately by our team.
Please be available at the scheduled time.

Please join the meeting 5 minutes early and be confident! 
Time zone: IST (India Standard Time - UTC+5:30)
"""
        else:
            # Zoom meeting created successfully
            meeting_details = f"""
📅 Interview Details:
- Meeting Title: {meeting_info.get('topic', 'Technical Interview')}
- Date & Time: {interview_time.strftime('%B %d, %Y at %I:%M %p IST')}
- Duration: 60 minutes
- Join URL: {meeting_info.get('join_url', 'N/A')}
- Meeting ID: {meeting_info.get('id', 'N/A')}
- Passcode: {meeting_info.get('password', 'N/A')}

Please join the meeting 5 minutes early and be confident! 
Time zone: IST (India Standard Time - UTC+5:30)
"""

        # Generate email content
        response = email_agent.run(
            f"""Draft an interview confirmation email with these details:
            - Role: {role} position
            - Meeting Details: {meeting_details}
            
            Important:
            - Use all lowercase letters
            - Clearly specify that the time is in IST (India Standard Time)
            - Ask the candidate to join 5 minutes early
            - Ask them to be confident and not nervous and prepare well for the interview
            - End with exactly: 'best,\nthe ai recruiting team'
            
            Return only the email body text, no subject line.
            """
        )
        
        # Extract email content and send
        email_content = next((msg.content for msg in response.messages if msg.role == 'assistant'), "")
        
        success = send_email(
            to_email=candidate_email,
            subject=f"interview details for {role} position",
            body=email_content
        )
        
        if success:
            st.success("Interview scheduled successfully! Check your email for details.")
        else:
            st.error("Interview was scheduled but failed to send email notification")
        
    except Exception as e:
        logger.error(f"Error scheduling interview: {str(e)}")
        st.error("Unable to schedule interview. Please try again.")


def main() -> None:
    st.title("AI Recruitment System")

    init_session_state()
    with st.sidebar:
        st.header("Configuration")
        
        # Setup Instructions
        with st.expander("📋 Setup Instructions", expanded=False):
            st.markdown("""
            **🔑 Gemini API Key:**
            1. Go to [aistudio.google.com](https://aistudio.google.com)
            2. Sign in with Google account
            3. Create API key
            
            **📧 Gmail Setup:**
            1. Enable 2-Factor Authentication on Gmail
            2. Go to Account Settings > Security > App Passwords
            3. Generate 16-character app password
            4. Use that password (not your regular Gmail password)
            
            **🔗 Zoom Setup:**
            1. Go to [Zoom App Marketplace](https://marketplace.zoom.us)
            2. Create "Server-to-Server OAuth" app
            3. Get Account ID, Client ID, Client Secret from app settings
            4. **IMPORTANT: Add these scopes in the Scopes tab:**
               - `meeting:write:meeting`
               - `meeting:write:meeting:admin`
               - `user:read:admin`
            5. Activate the app after adding scopes
            """)
        
        # Gemini Configuration
        st.subheader("Gemini Settings")
        api_key = st.text_input("Gemini API Key", type="password", value=st.session_state.gemini_api_key, help="Get your API key from aistudio.google.com")
        if api_key: st.session_state.gemini_api_key = api_key

        st.subheader("Zoom Settings")
        st.info("🔗 **Zoom Setup Required:**\n1. Go to Zoom App Marketplace\n2. Create Server-to-Server OAuth App\n3. Add scopes: `meeting:write:meeting`, `meeting:write:meeting:admin`, `user:read:admin`\n4. Get Account ID, Client ID, Client Secret")
        zoom_account_id = st.text_input("Zoom Account ID", type="password", value=st.session_state.zoom_account_id)
        zoom_client_id = st.text_input("Zoom Client ID", type="password", value=st.session_state.zoom_client_id)
        zoom_client_secret = st.text_input("Zoom Client Secret", type="password", value=st.session_state.zoom_client_secret)
        
        st.subheader("Email Settings")
        st.info("📧 **Gmail Setup Required:**\n1. Enable 2-Factor Authentication\n2. Generate App Password (not your regular password)\n3. Use the 16-character app password below")
        email_sender = st.text_input("Sender Email", value=st.session_state.email_sender, help="Your Gmail address")
        email_passkey = st.text_input("Email App Password", type="password", value=st.session_state.email_passkey, help="16-character app password from Gmail")
        company_name = st.text_input("Company Name", value=st.session_state.company_name, help="Name to use in email communications")

        # Test Section
        st.subheader("🧪 Test Configuration")
        if st.button("Test Email Settings"):
            if st.session_state.email_sender and st.session_state.email_passkey:
                test_success = send_email(
                    to_email=st.session_state.email_sender,
                    subject="Test Email from AI Recruitment System",
                    body="This is a test email to verify your email configuration is working correctly.\n\nbest,\nthe ai recruiting team"
                )
                if test_success:
                    st.success("✅ Email test successful!")
                else:
                    st.error("❌ Email test failed!")
            else:
                st.warning("Please fill in email credentials first")
        
        if st.button("Test Zoom Settings"):
            if st.session_state.zoom_account_id and st.session_state.zoom_client_id and st.session_state.zoom_client_secret:
                zoom_test = CustomZoomTool(
                    account_id=st.session_state.zoom_account_id,
                    client_id=st.session_state.zoom_client_id,
                    client_secret=st.session_state.zoom_client_secret
                )
                token = zoom_test.get_access_token()
                if token:
                    st.success("✅ Zoom authentication successful!")
                else:
                    st.error("❌ Zoom authentication failed! Check your credentials.")
            else:
                st.warning("Please fill in Zoom credentials first")

        if zoom_account_id: st.session_state.zoom_account_id = zoom_account_id
        if zoom_client_id: st.session_state.zoom_client_id = zoom_client_id
        if zoom_client_secret: st.session_state.zoom_client_secret = zoom_client_secret
        if email_sender: st.session_state.email_sender = email_sender
        if email_passkey: st.session_state.email_passkey = email_passkey
        if company_name: st.session_state.company_name = company_name

        required_configs = {'Gemini API Key': st.session_state.gemini_api_key, 'Zoom Account ID': st.session_state.zoom_account_id,
                          'Zoom Client ID': st.session_state.zoom_client_id, 'Zoom Client Secret': st.session_state.zoom_client_secret,
                          'Email Sender': st.session_state.email_sender, 'Email Password': st.session_state.email_passkey,
                          'Company Name': st.session_state.company_name}

    missing_configs = [k for k, v in required_configs.items() if not v]
    if missing_configs:
        st.warning(f"Please configure the following in the sidebar: {', '.join(missing_configs)}")
        return

    if not st.session_state.gemini_api_key:
        st.warning("Please enter your Gemini API key in the sidebar to continue.")
        return

    role = st.selectbox("Select the role you're applying for:", ["ai_ml_engineer", "frontend_engineer", "backend_engineer"])
    with st.expander("View Required Skills", expanded=True): st.markdown(ROLE_REQUIREMENTS[role])

    # Add a "New Application" button before the resume upload
    if st.button("📝 New Application"):
        # Clear only the application-related states
        keys_to_clear = ['resume_text', 'analysis_complete', 'is_selected', 'candidate_email', 'current_pdf']
        for key in keys_to_clear:
            if key in st.session_state:
                st.session_state[key] = None if key == 'current_pdf' else ""
        st.rerun()

    resume_file = st.file_uploader("Upload your resume (PDF)", type=["pdf"], key="resume_uploader")
    if resume_file is not None and resume_file != st.session_state.get('current_pdf'):
        st.session_state.current_pdf = resume_file
        st.session_state.resume_text = ""
        st.session_state.analysis_complete = False
        st.session_state.is_selected = False
        st.rerun()

    if resume_file:
        st.subheader("Uploaded Resume")
        col1, col2 = st.columns([4, 1])
        
        with col1:
            import tempfile, os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(resume_file.read())
                tmp_file_path = tmp_file.name
            resume_file.seek(0)
            try: pdf_viewer(tmp_file_path)
            finally: os.unlink(tmp_file_path)
        
        with col2:
            st.download_button(label="📥 Download", data=resume_file, file_name=resume_file.name, mime="application/pdf")
        # Process the resume text
        if not st.session_state.resume_text:
            with st.spinner("Processing your resume..."):
                resume_text = extract_text_from_pdf(resume_file)
                if resume_text:
                    st.session_state.resume_text = resume_text
                    st.success("Resume processed successfully!")
                else:
                    st.error("Could not process the PDF. Please try again.")

    # Email input with session state
    email = st.text_input(
        "Candidate's email address",
        value=st.session_state.candidate_email,
        key="email_input"
    )
    st.session_state.candidate_email = email

    # Analysis and next steps
    if st.session_state.resume_text and email and not st.session_state.analysis_complete:
        if st.button("Analyze Resume"):
            with st.spinner("Analyzing your resume..."):
                resume_analyzer = create_resume_analyzer()
                email_agent = create_email_agent()  # Create email agent here
                
                if resume_analyzer and email_agent:
                    print("DEBUG: Starting resume analysis")
                    is_selected, feedback = analyze_resume(
                        st.session_state.resume_text,
                        role,
                        resume_analyzer
                    )
                    print(f"DEBUG: Analysis complete - Selected: {is_selected}, Feedback: {feedback}")

                    if is_selected:
                        st.success("Congratulations! Your skills match our requirements.")
                        st.session_state.analysis_complete = True
                        st.session_state.is_selected = True
                        st.rerun()
                    else:
                        st.warning("Unfortunately, your skills don't match our requirements.")
                        st.write(f"Feedback: {feedback}")
                        
                        # Send rejection email
                        with st.spinner("Sending feedback email..."):
                            try:
                                send_rejection_email(
                                    email_agent=email_agent,
                                    to_email=email,
                                    role=role,
                                    feedback=feedback
                                )
                                st.info("We've sent you an email with detailed feedback.")
                            except Exception as e:
                                logger.error(f"Error sending rejection email: {e}")
                                st.error("Could not send feedback email. Please try again.")

    if st.session_state.get('analysis_complete') and st.session_state.get('is_selected', False):
        st.success("Congratulations! Your skills match our requirements.")
        st.info("Click 'Proceed with Application' to continue with the interview process.")
        
        if st.button("Proceed with Application", key="proceed_button"):
            print("DEBUG: Proceed button clicked")  # Debug
            with st.spinner("🔄 Processing your application..."):
                try:
                    print("DEBUG: Creating email agent")  # Debug
                    email_agent = create_email_agent()
                    print(f"DEBUG: Email agent created: {email_agent}")  # Debug
                    
                    print("DEBUG: Creating scheduler agent")  # Debug
                    scheduler_agent = create_scheduler_agent()
                    print(f"DEBUG: Scheduler agent created: {scheduler_agent}")  # Debug

                    # 3. Send selection email
                    with st.status("📧 Sending confirmation email...", expanded=True) as status:
                        print(f"DEBUG: Attempting to send email to {st.session_state.candidate_email}")  # Debug
                        send_selection_email(
                            email_agent,
                            st.session_state.candidate_email,
                            role
                        )
                        print("DEBUG: Email sent successfully")  # Debug
                        status.update(label="✅ Confirmation email sent!")

                    # 4. Schedule interview
                    with st.status("📅 Scheduling interview...", expanded=True) as status:
                        print("DEBUG: Attempting to schedule interview")  # Debug
                        schedule_interview(
                            scheduler_agent,
                            st.session_state.candidate_email,
                            email_agent,
                            role
                        )
                        print("DEBUG: Interview scheduled successfully")  # Debug
                        status.update(label="✅ Interview scheduled!")

                    print("DEBUG: All processes completed successfully")  # Debug
                    st.success("""
                        🎉 Application Successfully Processed!
                        
                        Please check your email for:
                        1. Selection confirmation ✅
                        2. Interview details with Zoom link 🔗
                        
                        Next steps:
                        1. Review the role requirements
                        2. Prepare for your technical interview
                        3. Join the interview 5 minutes early
                    """)

                except Exception as e:
                    print(f"DEBUG: Error occurred: {str(e)}")  # Debug
                    print(f"DEBUG: Error type: {type(e)}")  # Debug
                    import traceback
                    print(f"DEBUG: Full traceback: {traceback.format_exc()}")  # Debug
                    st.error(f"An error occurred: {str(e)}")
                    st.error("Please try again or contact support.")

    # Reset button
    if st.sidebar.button("Reset Application"):
        for key in st.session_state.keys():
            if key != 'gemini_api_key':
                del st.session_state[key]
        st.rerun()

if __name__ == "__main__":
    main()