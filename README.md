# 🤖 AI Recruitment System

An intelligent, automated recruitment platform that streamlines the hiring process using AI-powered resume analysis, automated email communications, and integrated video interview scheduling.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-v1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🌟 Features

### Core Functionality
- **AI-Powered Resume Analysis** - Intelligent evaluation of candidate skills using Google Gemini
- **Automated Email Communications** - Professional selection/rejection emails with personalized feedback
- **Smart Interview Scheduling** - Automatic Zoom meeting creation with calendar integration
- **Multi-Role Support** - Tailored evaluation criteria for different engineering positions
- **Real-time PDF Processing** - Instant resume text extraction and analysis

### Technical Capabilities
- **Streamlit Web Interface** - User-friendly, responsive web application
- **Google Gemini Integration** - Advanced AI for resume analysis and email generation
- **Zoom API Integration** - Automated video meeting creation and management
- **Gmail SMTP Integration** - Reliable email delivery system
- **PDF Viewer Integration** - In-app resume preview and download
- **Session Management** - Persistent state management across user interactions

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Streamlit     │    │   Google     │    │     Zoom        │
│   Frontend      │◄──►│   Gemini     │    │     API         │
│                 │    │     AI       │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                      │                     │
         ▼                      ▼                     ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│     Gmail       │    │   Resume     │    │   Interview     │
│     SMTP        │    │  Analysis    │    │  Scheduling     │
│                 │    │   Engine     │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Gmail account with 2FA enabled
- Google Gemini API key
- Zoom Pro account (for meeting creation)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ai-recruitment-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional)
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Access the application**
   - Open your browser to `http://localhost:8501`
   - Configure your API keys in the sidebar
   - Start processing applications!

## ⚙️ Configuration

### Required API Keys

| Service | Purpose | How to Get |
|---------|---------|------------|
| **Google Gemini** | AI resume analysis | [aistudio.google.com](https://aistudio.google.com) |
| **Gmail App Password** | Email notifications | Gmail Settings → Security → App Passwords |
| **Zoom OAuth** | Meeting creation | [Zoom App Marketplace](https://marketplace.zoom.us) |

### Detailed Setup Instructions

#### 🔑 Google Gemini Setup
1. Visit [Google AI Studio](https://aistudio.google.com)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key for use in the application

#### 📧 Gmail Setup
1. Enable 2-Factor Authentication on your Gmail account
2. Go to Google Account Settings → Security
3. Generate an App Password (16-character code)
4. Use this app password (NOT your regular Gmail password)

#### 🔗 Zoom Setup
1. Go to [Zoom App Marketplace](https://marketplace.zoom.us)
2. Create a new "Server-to-Server OAuth" app
3. Add required scopes:
   - `meeting:write:meeting`
   - `meeting:write:meeting:admin`
   - `user:read:admin`
4. Copy Account ID, Client ID, and Client Secret

## 📋 Supported Roles

The system supports evaluation for three engineering roles:

### 🤖 AI/ML Engineer
- Python, PyTorch/TensorFlow
- Machine Learning algorithms
- Deep Learning and Neural Networks
- Data preprocessing and analysis
- MLOps and model deployment
- RAG, LLM, Finetuning, and Prompt Engineering

### 🌐 Frontend Engineer
- React/Vue.js/Angular
- HTML5, CSS3, JavaScript/TypeScript
- Responsive design
- State management
- Frontend testing

### ⚙️ Backend Engineer
- Python/Java/Node.js
- REST APIs
- Database design and management
- System architecture
- Cloud services (AWS/GCP/Azure)
- Kubernetes, Docker, CI/CD

## 🔄 User Workflow

### For Candidates
1. **Select Role** - Choose target engineering position
2. **Upload Resume** - PDF format with automatic text extraction
3. **Provide Email** - For communication and interview scheduling
4. **AI Analysis** - Automated skill matching and evaluation
5. **Receive Feedback** - Instant email with results and next steps

### For Recruiters
1. **One-time Setup** - Configure API keys and credentials
2. **Automated Processing** - Hands-off candidate evaluation
3. **Review Results** - AI-generated analysis and recommendations
4. **Interview Scheduling** - Automatic Zoom meeting creation
5. **Communication** - Automated professional email notifications

## 🧪 Testing Features

The application includes built-in testing tools:

- **Email Test** - Verify Gmail SMTP configuration
- **Zoom Test** - Validate Zoom API credentials and scopes
- **PDF Processing** - Real-time resume text extraction preview

## 📊 Evaluation Criteria

### Selection Algorithm
- **70% Skill Match** - Minimum threshold for role requirements
- **Experience Weight** - Values both theoretical and practical knowledge
- **Project Experience** - Considers real-world applications
- **Transferable Skills** - Recognizes similar technology experience
- **Learning Indicators** - Identifies continuous learning patterns

### Feedback Generation
- **Detailed Analysis** - Specific skill matching breakdown
- **Constructive Feedback** - Actionable improvement suggestions
- **Resource Recommendations** - Learning materials for skill gaps
- **Encouragement** - Positive reinforcement for reapplication

## 🛠️ Development

### Project Structure
```
ai-recruitment-system/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
├── LICENSE               # MIT license
├── .env.example          # Environment template
├── docs/                 # Additional documentation
│   ├── API.md           # API integration details
│   ├── DEPLOYMENT.md    # Deployment guide
│   └── TROUBLESHOOTING.md # Common issues and solutions
└── tests/               # Test files (future)
```

### Adding New Roles

To add support for new engineering roles:

1. **Update `ROLE_REQUIREMENTS`** in `app.py`
2. **Add role to selectbox options**
3. **Test with sample resumes**
4. **Update documentation**

### Customizing Email Templates

Email content is AI-generated but can be customized by modifying the prompt instructions in:
- `send_selection_email()` function
- `send_rejection_email()` function

## 🔒 Security Considerations

- **API Key Storage** - Never commit API keys to version control
- **Session Management** - Secure handling of user data
- **Email Security** - App passwords instead of account passwords
- **Data Privacy** - Resume text processed in memory only
- **Zoom Security** - OAuth 2.0 with proper scopes

## 🐛 Troubleshooting

### Common Issues

#### Email Authentication Errors
```
Error 535: Username and Password not accepted
```
**Solution**: Use Gmail App Password, not regular password

#### Zoom Meeting Creation Fails
```
Invalid access token, does not contain scopes
```
**Solution**: Add required meeting scopes to your Zoom app

#### Resume Processing Errors
```
Could not process the PDF
```
**Solution**: Ensure PDF is not password-protected or corrupted

### Debug Tools
- Use sidebar test buttons to verify configurations
- Check Streamlit logs for detailed error messages
- Enable debug mode for additional logging

## 📈 Performance

- **Resume Analysis**: ~5-10 seconds per resume
- **Email Delivery**: ~2-3 seconds per email
- **Zoom Meeting Creation**: ~1-2 seconds per meeting
- **Concurrent Users**: Supports multiple simultaneous sessions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code style
- Add docstrings for new functions
- Test new features with multiple scenarios
- Update documentation for new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google Gemini** - AI-powered resume analysis
- **Streamlit** - Beautiful web application framework
- **Zoom** - Video conferencing integration
- **PyPDF2** - PDF text extraction
- **Agno Framework** - AI agent orchestration

## 📞 Support

For support and questions:
- Open an issue on GitHub
- Check the [troubleshooting guide](docs/TROUBLESHOOTING.md)
- Review the [API documentation](docs/API.md)

---

**Made with ❤️ for modern recruitment teams**
