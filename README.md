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

```
src/
├── backend/
│   ├── api/v1/
│   │   ├── routes/
│   │   └── schemas.py
│   ├── domain/                   # Core business logic (pure Python)
│   │   ├── models/               
│   │   ├── repositories/
│   │   └── services/             # Domain services (core logic)
│   ├── adapter/                  # External integrations clearly defined here
│   │   ├── database/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── session.py
│   │   ├── ai/
│   │   │   ├── llm_client.py
│   │   │   ├── prompt_templates.py
│   │   │   └── services/         # External AI service integrations
│   │   ├── pdf/
│   │   │   ├── services/         # PDF parsing services clearly here
│   │   │   └── pdf_parsing.py
│   ├── core/                     # Shared utilities (config, security)
│   └── main.py                   # App entrypoint
```
```
User uploads a PDF financial statement:
⬇️
PDF is processed by your backend service:
⬇️
Relevant data extracted and structured into database:
⬇️
User interacts via chatbot API, asking for insights:
⬇️
AI retrieves data, analyzes, and returns a clear, conversational response:
⬇️
User views the AI-generated insights or extracts structured data through API calls.
```     
### Prompt:
```
You are an expert financial analyst. Perform a fundamental analysis on the provided financial data for {{company_name}} (Ticker: {{ticker}}) as of {{report_date}}.

Here is the financial information and calculated metrics:

- Revenue: ${{financials.revenue}}
- Net Income: ${{financials.net_income}}
- Total Debt: ${{financials.total_debt}}
- Total Equity: ${{financials.total_equity}}
- Earnings Per Share (EPS): {{financials.earnings_per_share}}
- Dividend Per Share: {{financials.dividend_per_share}}
- Current Share Price: ${{financials.share_price}}

Calculated Metrics:
- Price-to-Earnings Ratio (P/E): {{calculated_metrics.pe_ratio}}
- Dividend Yield (%): {{calculated_metrics.dividend_yield}}
- Debt-to-Equity Ratio: {{calculated_metrics.debt_equity_ratio}}
- Return on Equity (ROE) (%): {{calculated_metrics.roe}}
```
**Analysis Task:**
1. Briefly explain the meaning and implications of each calculated metric.
2. Provide your insights about the company's financial health and investment attractiveness based on these metrics.
3. Clearly state any potential financial risks or opportunities you observe.

### Architecture:
```


┌─────────────────────────────────────────┐
│                 core/                   │
│(config, security, exceptions, utilities)│
└─────────────────────────────────────────┘
          │                 │
          ▼                 ▼
┌──────────────────┐  ┌───────────────────────────────────┐
│  api (routes)    │  │  domain (business logic)          │
│                  │  │  (domain models, services)        │
└──────────────────┘  │  (no database, pure Python)       │
                      └───────────────────────────────────┘
                              │        ▲
                              ▼        │
                ┌──────────────────────┴──────────────────┐
                │        adapter/database                 │
                │  (ORM models, sessions, repository impl)│
                └─────────────────────────────────────────┘
```

```
┌───────────────────────────────────┐
│         Domain (Core Logic)       │
│ ┌───────────────────────────────┐ │
│ │ Abstract Interfaces (Ports)   │ │
│ └───────────────────────────────┘ │
│        ▲                          │
└────────┼──────────────────────────┘
         │
         │ Implements
         │
┌────────┴───────────────────────────┐
│     Adapter (Concrete Details)     │
│ ┌───────────────────────────────┐  │
│ │ Concrete Implementations      │  │
│ └───────────────────────────────┘  │
└────────────────────────────────────┘
```

```

```
