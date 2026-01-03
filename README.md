# Meeting App - FastAPI Project

A FastAPI application for managing meetings with MySQL database integration.

## Prerequisites

- Python 3.10 or higher
- XAMPP (for MySQL database)
- MySQL database named `meeting_app` (create it in phpMyAdmin)

## Setup Instructions

### 1. Activate Virtual Environment

On Windows:
```bash
venv\Scripts\activate
```

On Linux/Mac:
```bash
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

1. Start XAMPP and ensure MySQL is running
2. Open phpMyAdmin: http://localhost/phpmyadmin
3. Create a database named `meeting_app`
4. Create a `.env` file in the project root with your database credentials:
   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=
   DB_NAME=meeting_app
   ```
   Note: If your MySQL root user has a password, add it to `DB_PASSWORD`. For default XAMPP installation, leave it empty.

### 4. Run the Application

**Option 1: Using the run script (Recommended)**
```bash
python run.py
```

**Option 2: Using the batch file (Windows)**
```bash
run.bat
```

**Option 3: Using uvicorn directly**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## Endpoints

### Hello World
- **GET** `/` - Returns "Hello World" message

### Meetings
- **GET** `/meetings/list` - List all meetings
- **GET** `/meetings/{meeting_id}` - Get a specific meeting
- **POST** `/meetings/create/{token}` - Create a new meeting

### Links
- Check `app/routers/link_router.py` for link-related endpoints

## Project Structure

```
meetingApp/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection setup
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   ├── schemas/             # Pydantic models
│   ├── models/              # SQLAlchemy models
│   └── storage/             # In-memory storage (temporary)
├── venv/                    # Virtual environment
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── run.py                   # Application runner script
└── README.md               # This file
```

## Notes

- The database connection is configured in `app/config.py`
- Database credentials are loaded from `.env` file
- The application uses SQLAlchemy ORM for database operations
- Auto-reload is enabled for development (changes will restart the server)

