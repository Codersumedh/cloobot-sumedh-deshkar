# Contract Analyzer

A powerful legal document analysis system with AI-powered risk assessment and querying capabilities.

## Overview

Contract Analyzer is a Flask-based web application that helps legal professionals and business users analyze contracts, NDAs, invoices, and other legal documents. The system uses OCR, natural language processing, and advanced LLM capabilities to extract text, identify important clauses, assess risks, and provide intelligent answers to document-related questions.

## Features

- **Document Processing**: Extract text from PDFs, JPGs, and PNGs using OCR
- **Document Classification**: Automatically identify document types (NDA, Invoice, Contract)
- **Clause Identification**: Recognize key legal clauses like payment terms, liability, confidentiality
- **Risk Assessment**: Score and explain risks for each clause
- **Vector Embeddings**: Store document content as vector embeddings for semantic search
- **AI-Powered Summaries**: Generate concise document summaries
- **Interactive Querying**: Ask natural language questions about document content
- **User Authentication**: Secure login system with JWT authentication

## Technologies

- **Backend**: Python, Flask, PostgreSQL
- **AI Components**: 
  - Together AI (Llama-3.3-70B-Instruct-Turbo-Free)
  - Sentence Transformers
  - PyTesseract (OCR)
- **Security**: JWT-based authentication
- **Text Processing**: PDF extraction, OCR, text chunking

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Tesseract OCR

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/Codersumedh/cloobot-sumedh-deshkar.git
   cd backend
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Install Tesseract OCR if not already installed:
   - On Ubuntu: `sudo apt-get install tesseract-ocr`
   - On macOS: `brew install tesseract`
   - On Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

5. Create a PostgreSQL database:
   ```
   createdb contract_db
   ```

6. Create a `.env` file with the following variables:
   ```
   DB_NAME=contract_db
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   SECRET_KEY=your_secret_key
   TOGETHER_API_KEY=your_together_ai_key
   UPLOAD_FOLDER=uploads
   ```

7. Initialize the database:
   ```
   python init_db.py
   ```

### Running the Application

1. Start the Flask server:
   ```
   python app.py
   ```

2. The server will run on `http://localhost:5000`

## Usage

### API Endpoints

#### Authentication

- `POST /api/auth/register`: Register a new user
- `POST /api/auth/login`: Log in and get JWT token

#### Document Operations

- `POST /api/documents/upload`: Upload and analyze a document
- `GET /api/documents/<document_id>`: Get analysis for a specific document
- `GET /api/documents/user`: Get all documents for the current user
- `POST /api/documents/<document_id>/query`: Query a document with natural language
- `GET /api/documents/<document_id>/download`: Download original document
- `GET /api/documents/<document_id>/report`: Download analysis report as JSON

### Command-Line Usage

The contract analyzer can also be used from the command line:

```
python contract_analyzer.py path/to/document.pdf --query
```

Options:
- `--query` or `-q`: Enter interactive query mode after analysis
- `--quiet` or `-s`: Suppress detailed output

## Architecture

```
├── app.py                  # Flask web server and API endpoints
├── contract_analyzer.py    # Core analysis functionality
├── uploads/                # Uploaded documents
└── .env                    # Environment variables
```

### Core Components

1. **DatabaseManager**: Handles database connections and operations
2. **ContractAnalyzer**: Main class for document analysis
   - Text extraction from various file formats
   - Document type detection
   - Clause identification
   - Risk assessment
   - AI-powered summary generation
   - Query handling with Together AI

## Environment Variables

- `DB_NAME`: PostgreSQL database name
- `DB_USER`: Database username
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port
- `SECRET_KEY`: Secret key for JWT token generation
- `TOGETHER_API_KEY`: API key for Together AI
- `UPLOAD_FOLDER`: Folder for uploaded documents

## Database Schema

The application uses PostgreSQL with the following tables:

1. **users**: User authentication information
2. **documents**: Uploaded document metadata and full text
3. **embeddings**: Vector embeddings for document chunks
4. **risk_analysis**: Risk assessment results for document clauses

