# Hunter Pro CRM System

## Overview

Hunter Pro is an intelligent customer relationship management (CRM) system designed for lead generation in the Arabic-speaking market, specifically targeting the Egyptian real estate sector. The application uses AI-powered search and lead extraction to help agencies find potential clients efficiently.

**Current Version**: 3.1.0

## User Preferences

- Preferred communication style: Simple, everyday language (Arabic)
- UI Language: Arabic (RTL)
- Theme: Dark mode (Navy Blue/Purple/Gold)

## System Architecture

### Project Structure (Modular)

```
hunter-pro-crm/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # Modular entry point (future)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py           # Authentication routes
│   │       ├── chat.py           # AI chat & search routes
│   │       ├── leads.py          # Lead management routes
│   │       └── admin.py          # Admin panel routes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Centralized settings (dataclass)
│   │   ├── database.py           # Database connections (PG/Supabase/Local)
│   │   └── security.py           # Rate limiting, sanitization
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py         # Hybrid AI (OpenAI/Gemini/Claude/Groq)
│   │   ├── search_service.py     # Hybrid search (Serper/DuckDuckGo)
│   │   ├── user_service.py       # User management
│   │   └── lead_service.py       # Lead management
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── requests.py           # Pydantic request models
│   ├── models/                   # Database models (future)
│   ├── utils/                    # Helper utilities
│   └── static/                   # Static assets
│       ├── css/
│       ├── js/
│       └── images/
├── templates/
│   └── index.html                # Main SPA interface
├── main.py                       # Current entry point
├── Dockerfile                    # Docker container config
├── docker-compose.yml            # Multi-container setup
├── requirements.txt              # Python dependencies
└── .env.example                  # Environment template
```

### Main Entry Point

**main.py** - Single FastAPI application providing:
- Hybrid AI Engine (OpenAI GPT-4o-mini primary, Google Gemini 1.5 Flash fallback)
- Hybrid Search System (Serper API primary, DuckDuckGo fallback)
- Wallet/Token Balance System (2 tokens/chat, 20 tokens/hunt)
- User Management and Authentication
- Lead Management and Storage

### Frontend

**templates/index.html** - Modern, responsive SPA using:
- TailwindCSS for styling
- Font Awesome for icons
- Marked.js for Markdown rendering
- Arabic (RTL) language support
- Dark theme with Navy Blue/Purple/Gold colors

### Database (Flexible - Auto Fallback)

**Priority Order:**
1. **Replit PostgreSQL** (automatic, free)
2. **Supabase** (if SUPABASE_URL + SUPABASE_KEY provided)
3. **Local Storage** (temporary fallback)

**Tables:**
- `users` - User accounts with wallet_balance
- `leads` - Customer leads
- `chat_history` - AI conversation history
- `feedback` - Customer ratings
- `shared_leads` - Lead sharing between users

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main SPA interface |
| `/api/login` | POST | User authentication |
| `/api/wallet/{user_id}` | GET | Get wallet balance |
| `/api/chat/{user_id}` | POST | AI chat (2 tokens) |
| `/api/hunt/{user_id}` | POST | Lead search with strategy & country (20 tokens) |
| `/api/hunt/strategies` | GET | Get available hunting strategies |
| `/api/hunt/countries` | GET | Get available countries with cities |
| `/api/leads/{user_id}` | GET | Get user leads |
| `/api/stats/{user_id}` | GET | Get user statistics |
| `/health` | GET | Health check |

### Environment Variables

Required secrets:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase API key
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `GOOGLE_API_KEY` - Google AI API key (optional)
- `SERPER_KEYS` - Serper API keys (comma-separated)

### Token System

- Default balance: 100 tokens
- Chat: 2 tokens | Hunt: 20 tokens | Campaign: 50 tokens
- Ad Creation: 15 tokens | Ad Analysis: 10 tokens | Optimization: 25 tokens

### Security Features

- Rate Limiting: 60 requests/minute per IP
- Auto-blocking: 5 minutes for excessive requests
- Input Sanitization: XSS/Script injection protection
- Security Headers: X-Frame-Options, X-XSS-Protection, CSP
- Input Validation: All user inputs validated and sanitized
- API Documentation disabled in production

### Docker Support

Run with Docker:
```bash
# Build and run
docker-compose up -d

# Or standalone
docker build -t hunter-pro .
docker run -p 5000:5000 --env-file .env hunter-pro
```

### Ad Automation System

- Ad Creation with A/B Testing
- Campaign Planning
- Performance Analysis (CTR, CPC, CPA, ROAS)
- Multi-platform support (Facebook, Instagram, Google, TikTok)

### Data Sharing System

- Share leads with other users
- View received/sent shared leads
- Track who shared what with whom

### Feedback System

- Customer ratings (1-5 stars)
- Comments from clients
- Average rating calculation
- Full feedback history

### Sales Funnel System

- **Bait Messages**: 6 templates (curiosity, problem, urgency, social_proof, question, value)
- **Funnel Stages**: 7 stages (bait_sent → replied → interested → negotiating → hot → closed → lost)
- **AI Sales Chatbot**: Generates smart replies based on conversation stage (2 tokens)
- **Stage Tracking**: Track each lead's progress through the funnel
- **WhatsApp Integration**: Send bait messages and AI replies directly via WhatsApp

### Self-Learning AI System

The AI learns from successful conversations to improve responses over time.

- **Conversation Import**: Import conversations from WhatsApp/Messenger
- **Pattern Learning**: Extract successful reply patterns from conversations
- **Conversation Rating**: Rate conversations (1-5 stars) to train the AI
- **Smart Replies**: Generate AI replies enhanced by learned patterns
- **Learning Statistics**: Track patterns learned, improvement level, and conversion rates

### Recent Changes

- **2024-12-07**: Project Restructuring:
  - Created modular architecture (app/core, app/services, app/api)
  - Separated config, security, and database modules
  - Created Pydantic schemas for request validation
  - Created service layer for business logic
  - Added Docker and docker-compose support
  - Updated requirements.txt with proper versions
- **2024-12-07**: Added Self-Learning AI System
- **2024-12-07**: Added Sales Funnel & AI Chatbot System
- **2024-12-06**: Added Replit PostgreSQL as primary database

### Admin Links

- **Admin Panel:** `/admin-panel`
- **Keys Guide:** `/keys-guide`
- **Usage Guide:** `/guide`

## Running the Application

```bash
# Development
python main.py

# With Docker
docker-compose up -d
```

Server runs on port 5000.

## Deployment

Configured for Replit Autoscale deployment. Click "Publish" to deploy.
