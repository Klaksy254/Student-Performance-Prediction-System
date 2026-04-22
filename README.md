# Student Performance Prediction System

A Flask web application that predicts student pass/fail outcomes using a trained machine learning model.

## Project Structure

```
student_performance_system/
├── backend/
│   ├── app.py                  # Flask application
│   └── templates/
│       └── index.html          # Dashboard UI
├── data/
│   └── student_performance.csv # Training dataset
├── models/
│   └── student_performance_model.pkl
├── notebooks/
│   ├── data_simulation.ipynb
│   └── model_training.ipynb
├── tests/
│   └── test_app.py
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Dev + notebook dependencies
└── .gitignore
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
cd backend
python app.py
# Open http://127.0.0.1:5000
```

## Test

```bash
pip install pytest
pytest tests/
```

## API Endpoints

| Method | Endpoint    | Description              |
|--------|-------------|--------------------------|
| GET    | `/`         | Dashboard UI             |
| POST   | `/predict`  | Single student prediction|
| POST   | `/upload`   | Bulk CSV prediction      |
| GET    | `/download` | Download results CSV     |
| GET    | `/history`  | User prediction history  |
| GET    | `/admin`    | Admin dashboard (admin only) |
| GET    | `/explainability` | Feature importance JSON |
| POST   | `/api/predict` | API-key protected prediction |
| GET    | `/openapi.json` | OpenAPI schema |
| GET    | `/api/docs` | Swagger UI documentation |

### `/predict` payload

```json
{
  "Attendance": 85,
  "CAT_Score": 72,
  "Assignment_Score": 78,
  "Final_Exam": 65
}
```

## Deployment Notes

- Set a strong secret key in production:
  - `FLASK_SECRET_KEY` should be a long random value and never committed to git.
- Enable secure session cookies behind HTTPS:
  - Set `SESSION_COOKIE_SECURE=True` in your deployment environment.
- Recommended workflow:
  - Make changes locally/staging first, run tests, then deploy.
  - Avoid editing code directly on production servers.
- Logs:
  - Structured app events are written to `backend/logs/app.log` with rotation.
