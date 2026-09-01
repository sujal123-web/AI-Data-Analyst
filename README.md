# 🤖 AI Data Analyst

> **Ask questions about your data in natural language. Get analysis without writing SQL or Python.**

AI Data Analyst is a full-stack, AI-assisted data analysis platform that lets users upload CSV/Excel datasets and interact with them through a conversational interface.

The project combines a **React frontend**, **FastAPI backend**, **Pandas/NumPy data processing**, a modular **question-processing pipeline**, an **LLM layer**, and a **visualization engine** to turn structured datasets into understandable insights.

---

## 🌐 Live Demo

**Frontend:** https://ai-data-analyst-sandy.vercel.app

**Backend API:** https://ai-data-analyst-95px.onrender.com

Production validation:
- `/upload` → `200 OK`
- `/ask` → `200 OK`
- CORS preflight → `200 OK`
- End-to-end dataset upload and question answering verified successfully

---

# 🎯 Problem Statement

Traditional data analysis often requires knowledge of SQL, Python/Pandas, Excel, BI tools, or visualization software.

That creates a barrier for users who simply want answers from their data.

For example, answering:

> **Which country generated the highest total sales?**

may require filtering records, grouping data, calculating aggregates, and interpreting the result.

AI Data Analyst provides a conversational alternative:

```text
Upload Dataset
      ↓
Ask a Question
      ↓
Understand the Question
      ↓
Analyze the Dataset
      ↓
Generate Result
      ↓
Return a Natural-Language Answer
```

---

# 💡 Solution

Instead of manually writing analytical code, users can ask questions such as:

```text
What are the total sales?
```

The application processes the question, performs the relevant analysis against the uploaded dataset, and returns an understandable response.

The objective is to provide a **natural-language interface over structured data**.

---

# ✨ Key Features

## 📂 Dataset Upload
- CSV support
- Excel support
- Multipart file upload through FastAPI
- Automatic dataset loading
- Dataset profiling after upload

## 🔍 Dataset Processing
The backend contains a dedicated data-engine layer for loading and profiling uploaded datasets.

## 💬 Natural-Language Questions
Examples:

```text
What are the total sales?
What is the average sales?
Which product line has the highest sales?
Which country has the highest total sales?
Compare sales between Classic Cars and Motorcycles.
How do sales vary by month?
```

## 🧠 Question Processing Pipeline
The backend contains:
- `question_pipeline.py`
- `question_planner.py`
- `question_router.py`

These components provide a modular architecture for interpreting questions and routing them through appropriate analytical workflows.

## 🤖 LLM-Assisted Interaction
The AI layer supports natural-language interaction. The intended architecture separates question interpretation from dataset-backed analytical results.

```text
User Question
      ↓
Question Interpretation
      ↓
Analytical Operation
      ↓
Dataset Result
      ↓
AI / Natural-Language Explanation
```

## 📈 Visualization Architecture
The project includes a visualization engine and visualization-pipeline tests. Plotly is used for interactive visualization capabilities.

## 🌐 Production Deployment
- Frontend → Vercel
- Backend → Render
- Communication → REST API over HTTPS
- Backend server → Uvicorn + FastAPI

---

# 🏗️ System Architecture

```text
                         ┌───────────────────────┐
                         │         USER          │
                         │ Upload Dataset        │
                         │ Ask Questions         │
                         └───────────┬───────────┘
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │    React Frontend     │
                         │       Vercel          │
                         └───────────┬───────────┘
                                     │
                              REST API / HTTPS
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │     FastAPI API       │
                         │       Render          │
                         └───────────┬───────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
          ┌────────────────┐ ┌───────────────┐ ┌─────────────────┐
          │  Data Engine   │ │   Question    │ │ Visualization   │
          │                │ │   Pipeline    │ │     Engine      │
          └───────┬────────┘ └───────┬───────┘ └─────────────────┘
                  │                  │
                  │                  ▼
                  │         ┌────────────────┐
                  │         │ Router /       │
                  │         │ Planner        │
                  │         └───────┬────────┘
                  │                 │
                  └─────────────────┤
                                    ▼
                           ┌──────────────────┐
                           │   LLM / AI Layer │
                           └────────┬─────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │ Analytical Result│
                           │ + Explanation    │
                           └────────┬─────────┘
                                    │
                                    ▼
                           ┌──────────────────┐
                           │   Chat Interface │
                           └──────────────────┘
```

---

# 🔄 End-to-End Workflow

### 1. Upload
The user selects a CSV or Excel file in the React application.

### 2. Ingestion
The frontend sends the file to:

```text
POST /upload
```

### 3. Processing
FastAPI receives the file and passes it through the data-loading/profiling layer.

### 4. Dataset Initialization
The processed dataset becomes available to the analytical workflow.

### 5. Question
The user asks a natural-language question.

```text
What are the total sales?
```

### 6. Question Pipeline
The request is processed through the question pipeline, planner, and router.

### 7. Analysis
The required analytical operation is executed against the dataset.

### 8. Response
The result is returned to the React chat interface as a natural-language answer.

Example:

```text
The total sales are 10,032,628.85.
```

---

# 🧩 Project Structure

```text
AI-Data-Analyst/
│
├── backend/
│   ├── agents/
│   ├── data_engine/
│   ├── llm/
│   ├── tools/
│   │
│   ├── api.py
│   ├── main.py
│   ├── data_loader.py
│   ├── question_pipeline.py
│   ├── question_planner.py
│   ├── question_router.py
│   │
│   ├── test_employee_dataset.py
│   ├── test_question_pipeline.py
│   ├── test_question_planner.py
│   ├── test_question_router.py
│   ├── test_visualization_pipeline.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── package.json
│   └── ...
│
├── data/
├── .gitignore
└── README.md
```

---

# 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Build Tool | Vite |
| Styling | CSS |
| Backend | Python |
| API Framework | FastAPI |
| Server | Uvicorn |
| Data Processing | Pandas |
| Numerical Processing | NumPy |
| Visualization | Plotly |
| Validation | Pydantic |
| Communication | REST API |
| AI | LLM integration |
| Frontend Deployment | Vercel |
| Backend Deployment | Render |
| Version Control | Git + GitHub |
| Development | VS Code |

---

# 🔌 API Endpoints

## `GET /health`

Health-check endpoint.

Example response:

```json
{
  "status": "ok",
  "message": "AI Data Analyst API is running."
}
```

## `POST /upload`

Uploads a CSV or Excel dataset and initializes it for analysis.

Workflow:

```text
Receive File
    ↓
Load Dataset
    ↓
Process / Profile
    ↓
Make Dataset Available
```

## `POST /ask`

Processes a natural-language question against the loaded dataset.

Example request:

```json
{
  "question": "What are the total sales?"
}
```

Example response:

```json
{
  "answer": "The total sales are 10,032,628.85."
}
```

> Response schemas may evolve as the project grows.

---

# 🧪 Testing

The backend contains dedicated tests for core analytical components, including:

```text
test_question_pipeline.py
test_question_planner.py
test_question_router.py
test_visualization_pipeline.py
```

This allows individual components to be validated independently instead of relying only on manual frontend testing.

---

# 💻 Local Development

## Prerequisites

Install:
- Python 3.x
- Node.js
- npm
- Git

## Backend

From the project root:

```bash
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Start the API:

```bash
uvicorn backend.api:app --reload
```

Backend:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

## Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite will display the local frontend URL in the terminal.

---

# 🔐 Environment Variables & Security

Never commit secrets to GitHub.

Keep credentials such as:
- API keys
- Access tokens
- Passwords
- Private configuration

inside environment variables.

Typical secret files such as:

```text
.env
.env.*
```

should be excluded through `.gitignore`.

Also exclude generated/dependency directories such as:

```text
venv/
node_modules/
frontend/dist/
__pycache__/
```

---

# 🌍 Deployment Architecture

```text
                     INTERNET
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
       ┌───────────┐           ┌────────────┐
       │  Vercel   │           │   Render   │
       │ Frontend  │ ────────► │  Backend   │
       └───────────┘   HTTPS   └────────────┘
                                    │
                                    ▼
                              FastAPI / Uvicorn
```

Benefits:
- Independent frontend/backend deployment
- Clear API boundary
- Easier debugging
- Independent scaling
- Cleaner production architecture

---

# 📸 Screenshots

Recommended repository assets:

```text
docs/
└── screenshots/
    ├── upload.png
    ├── dataset-loaded.png
    ├── question.png
    ├── analysis-result.png
    └── visualization.png
```

Then add:

```markdown
## 📸 Application Preview

![Upload Interface](docs/screenshots/upload.png)

![AI Analysis](docs/screenshots/analysis-result.png)

![Visualization](docs/screenshots/visualization.png)
```

---

# 📊 Example Analysis

Question:

```text
What are the total sales?
```

Result from the tested sales dataset:

```text
10,032,628.85
```

The production request sequence was verified as:

```text
POST /upload
      ↓
200 OK
      ↓
Dataset Loaded
      ↓
POST /ask
      ↓
200 OK
      ↓
Analytical Response
```

---

# 🎯 Design Goals

### Accessibility
Make data analysis approachable for users who do not know SQL or Python.

### Modularity
Separate API, data processing, question processing, AI, and visualization responsibilities.

### Data Grounding
Use the uploaded dataset as the basis for analytical results.

### Extensibility
Make it easy to add new question types, analytical operations, visualizations, and data sources.

### Production Readiness
Deploy the application as a real web system with independent frontend and backend services.

---

# 🧠 Engineering Highlights

## Backend Engineering
- REST API development with FastAPI
- File upload handling
- Health monitoring
- Modular backend architecture
- CORS configuration

## Data Analytics
- Dataset ingestion
- Dataset profiling
- Aggregations
- Grouping
- Ranking
- Comparative analysis
- Statistical operations

## AI Engineering
- Natural-language interaction
- LLM integration
- Question planning
- Question routing
- AI-assisted analytical explanations

## Frontend Engineering
- React conversational UI
- Dataset upload workflow
- API integration
- Chat-style result presentation
- Production deployment

## Software Engineering
- Modular project structure
- Automated tests
- Git/GitHub version control
- Separate frontend/backend deployments

---

# ⚠️ Current Limitations

- Very large datasets may require more processing resources.
- Render free-tier instances may experience cold-start delays.
- Supported question types depend on the current analytical pipeline.
- Visualization capabilities are still being expanded.
- Multi-user persistence and dataset isolation can be improved in future versions.

---

# 🔮 Future Roadmap

## Analytics
- [ ] Advanced filtering
- [ ] Statistical analysis
- [ ] Outlier detection
- [ ] Correlation analysis
- [ ] Automated data-quality checks
- [ ] More analytical operations

## Visualization
- [ ] Automatic chart selection
- [ ] Natural-language chart generation
- [ ] Interactive dashboards
- [ ] Chart export

## AI
- [ ] Improved question planning
- [ ] More robust reasoning
- [ ] Query explanation
- [ ] Follow-up questions
- [ ] Conversational context
- [ ] Result validation / confidence indicators

## Data Platform
- [ ] SQL database connections
- [ ] Multi-dataset analysis
- [ ] Dataset history
- [ ] User authentication
- [ ] User workspaces
- [ ] Saved analyses

## Reporting
- [ ] Automated EDA reports
- [ ] PDF export
- [ ] Excel export
- [ ] Shareable analysis links
- [ ] Scheduled reports

---

# 💼 Why This Project Is Recruiter-Relevant

This project demonstrates more than a simple chatbot or dashboard.

It combines:

```text
Data Analytics
      +
Data Engineering
      +
AI / LLMs
      +
Backend Development
      +
Frontend Development
      +
Data Visualization
      +
Testing
      +
Cloud Deployment
```

It demonstrates the ability to build a complete data product from **data ingestion → processing → analytical reasoning → API → user interface → production deployment**.

---

# 🏆 Project Highlights

- ✅ Full-stack AI-assisted data analysis platform
- ✅ Natural-language interface for structured datasets
- ✅ CSV and Excel ingestion
- ✅ FastAPI REST backend
- ✅ Pandas / NumPy data processing
- ✅ Modular question pipeline
- ✅ Question planning and routing
- ✅ LLM-assisted interaction
- ✅ Plotly visualization architecture
- ✅ Backend test suite
- ✅ Vercel + Render deployment
- ✅ Production CORS configuration
- ✅ Verified production upload workflow
- ✅ Verified production question-answer workflow

---

# 👨‍💻 Author

**Sujal Rajput**

B.Tech — Robotics and Automation  
Symbiosis Institute of Technology, Pune

**Interests:** Data Analytics · Data Engineering · AI Applications · Backend Development · Software Engineering

---

# ⭐ Project Status

**Status: Active Development**

The core production workflow is operational. The project is being continuously improved with additional analytical capabilities, visualizations, AI reasoning, and data-platform features.

---

## 📄 License

This project is currently intended as a portfolio and learning project.

Add an explicit open-source license if you decide to distribute the source code under one.
