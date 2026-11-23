# Enterprise RAG Knowledge Assistant

A multi-tenant, AI-powered document retrieval and question-answering backend built with FastAPI, PostgreSQL, pgvector, OpenAI, Redis, and JWT authentication.

## Features

- JWT-based user registration and authentication
- Organization-level data isolation
- PDF document upload and text extraction
- Document chunking and OpenAI embeddings
- Vector similarity search using PostgreSQL and pgvector
- Context-aware AI question answering
- Redis caching with organization-scoped cache keys
- SQLAlchemy ORM and Alembic migrations
- Automated testing with pytest
- Interactive Swagger API documentation

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Vector Search | pgvector |
| AI | OpenAI |
| Authentication | JWT, Argon2id |
| Caching | Redis |
| Migrations | Alembic |
| Testing | pytest |

## Architecture

```text
Client
  |
  v
FastAPI REST API
  |
  +-- JWT Authentication
  |
  +-- Organization Authorization
  |
  +-- Document Upload
  |     |
  |     +-- PDF Extraction
  |     +-- Text Chunking
  |     +-- OpenAI Embeddings
  |     +-- PostgreSQL + pgvector
  |
  +-- RAG Question Answering
        |
        +-- Organization-Scoped Redis Cache
        +-- Vector Similarity Search
        +-- Relevant Document Context
        +-- OpenAI Answer Generation
```

## Prerequisites

- Python 3.14 or a compatible version
- PostgreSQL with pgvector installed
- Redis server
- OpenAI API key

## Installation

Clone the repository:

```bash
git clone https://github.com/divyp7642/enterprise-rag-knowledge-assistant.git
cd enterprise-rag-knowledge-assistant
```

Create a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Environment Configuration

Create a `.env` file in the project root:

```dotenv
DB_USER=your_postgres_user
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

JWT_SECRET_KEY=replace_with_a_long_random_secret
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

OPENAI_API_KEY=your_openai_api_key
```

Never commit your `.env` file or real credentials.

## Database Setup

Create a PostgreSQL database and enable pgvector:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Run database migrations:

```powershell
alembic upgrade head
```

## Run the Application

```powershell
python -m uvicorn app.main:app --reload
```

API documentation:

http://127.0.0.1:8000/docs

Health endpoint:

http://127.0.0.1:8000/health

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API status |
| GET | `/health` | Health response |
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Authenticate and obtain JWT |
| GET | `/auth/me` | Get authenticated user |
| POST | `/documents/upload` | Upload a PDF document |
| POST | `/rag/ask` | Ask a document-grounded question |

Protected endpoints require JWT authentication.

## RAG Workflow

1. An authenticated user uploads a PDF.
2. The backend extracts and chunks document text.
3. OpenAI generates vector embeddings.
4. PostgreSQL stores document chunks and embeddings.
5. The user submits a question.
6. The system searches relevant chunks within the user's organization.
7. OpenAI generates an answer using retrieved context.
8. The API returns the answer and source chunk references.
9. Redis caches eligible answers using organization-scoped keys.

## Multi-Tenant Isolation

Users and documents belong to organizations.

Document retrieval is filtered using the authenticated user's organization ID.

Redis cache keys also include the organization ID to prevent cross-organization cache reuse.

## Testing

Run the automated test suite:

```powershell
python -m pytest -q
```

The project has previously passed 59 automated tests covering authentication, security, document upload, embeddings, semantic search, caching, answer generation, and organization isolation.

## Current Scope

This repository provides a backend API with Swagger documentation. A production frontend, deployment configuration, and comprehensive production security review are not yet included.

## Author

Divykumar Patel

GitHub: https://github.com/divyp7642
