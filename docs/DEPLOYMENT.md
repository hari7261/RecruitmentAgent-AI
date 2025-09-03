# Deployment Guide

## Local Development
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Production Options
| Method | Pros | Cons |
|--------|------|------|
| Streamlit Community Cloud | Easiest | Limited secrets mgmt |
| Docker + VPS | Full control | More setup |
| Kubernetes | Scales well | Overhead |
| Hugging Face Spaces | Fast deploy | Cold starts |

## Docker Deployment
### 1. Create `Dockerfile`
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
ENV PYTHONUNBUFFERED=1
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 2. Build & Run
```bash
docker build -t ai-recruitment .
docker run -p 8501:8501 --env-file .env ai-recruitment
```

## Environment Variables (Recommended)
Set in `.env` or deployment secret store. See `.env.example` for full list.

## Scaling Considerations
| Component | Strategy |
|-----------|----------|
| Streamlit | Behind reverse proxy (nginx) |
| AI Calls | Add caching layer |
| Email | Queue + worker for bulk |
| Zoom | Rate limit aware retries |

## Monitoring
- Add basic request logging
- Track meeting creation success rate
- Log resume parsing failures for QA

## Security Checklist
- [ ] Never commit real `.env`
- [ ] Rotate API keys periodically
- [ ] Limit model prompts to necessary data
- [ ] Use HTTPS in production
- [ ] Restrict outbound network if possible

## Backup & Recovery
- Config: Stored in env/secret manager
- No database state (stateless) unless you extend
- Add persistence only if tracking history

## Hardening Ideas
- Add auth layer (Streamlit `st.experimental_user` or OAuth proxy)
- Rate limit resume uploads
- Virus scan uploaded PDFs

---
End of deployment guide.
