# Finance Chatbot

An AI-powered finance chatbot that processes financial reports and provides automated analysis.

## Features
- PDF financial report processing and text extraction
- Automated data parsing and categorization
- Financial metrics extraction (revenue, debt, etc.)
- Database storage for structured financial data
- AI-powered financial analysis and recommendations
- Support for Vietnamese financial reports

## Project Structure


src/
├── backend/
│   ├── api/                   # API endpoints
│   │   └── v1/               
│   │       └── routes/        # Route definitions
│   │       └── schemas/       # Pydantic models for request/response
│   ├── core/                  # Application core components
│   │   ├── config.py          # Configuration (move from backend root)
│   │   ├── security.py        # Authentication/authorization
│   │   └── exceptions.py      # Custom exceptions
│   ├── domain/                # Business logic
│   │   ├── models/            # Domain models
│   │   ├── services/          # Business services
│   │   └── repositories/      # Repository interfaces
│   ├── adapter/        # External implementation details
│   │   ├── database/          # Database connection and models
│   │   │   ├── models/        # SQLAlchemy models
│   │   │   ├── repositories/  # Repository implementations
│   │   │   └── session.py     # Database session management
│   │   ├── ai/                # AI integration
│   │   │   ├── llm_client.py
│   │   │   └── prompt_templates.py
│   │   └── pdf/               # PDF processing tools
│   └── main.py                # Application entry point
├── tests/                    # Test suite
│   ├── unit/                  # Unit tests for individual functions
│   ├── integration/           # Tests for component interactions
│   ├── e2e/                   # End-to-end API tests
│   └── conftest.py            # Test fixtures and configuration
└── requirements/             # Dependency management
    ├── base.txt
    ├── dev.txt
    └── prod.txt