# CourseConnect

CourseConnect is a full-stack semantic course search engine for graduate students. It lets users search for courses using natural-language interests instead of exact keywords, then returns ranked results using Sentence-BERT embeddings, FAISS similarity search, a FastAPI backend, and a React frontend.
=======

CourseConnect is a full-stack semantic course search engine for graduate students. Instead of relying on exact keyword matching, it lets users search for courses using natural-language interests such as `deep learning for computer vision`, `distributed cloud systems`, or `privacy in machine learning`, then returns the most relevant graduate courses using Sentence-BERT embeddings and FAISS similarity search.

The system is built around a reproducible pipeline: scrape course data from the Texas A&M graduate catalog, clean and store it in structured formats, generate semantic embeddings, build a persistent vector index, serve results through a FastAPI backend, and present them in a polished React + Tailwind frontend.

## Why CourseConnect

Traditional course catalogs are useful for browsing, but they are not especially good at understanding intent. A student interested in `robotics and spatial intelligence` may not know which exact terms appear in a course title or description. CourseConnect closes that gap by ranking courses based on conceptual similarity rather than plain keyword overlap.

This makes the app especially helpful for:

- graduate students exploring research-aligned coursework
- students entering interdisciplinary areas
- users comparing related courses across departments
- quicker discovery during advising, demo presentations, or academic planning

## Core Features

- Semantic search powered by `sentence-transformers/all-mpnet-base-v2`
- FAISS-based cosine similarity retrieval using normalized embeddings
- Python scraper for the Texas A&M graduate course catalog
- Structured persistence in JSON, CSV, and SQLite
- FastAPI backend with CORS enabled for local frontend development
- React frontend with a clean academic search experience
- Relevance scoring visualized with badges and progress bars
- Expandable descriptions and prerequisite display
- Recent-search history stored in the browser
- Saved-course shortlist for comparing interesting results
- Department and credit-based filtering
- Highlighted query terms in result descriptions
- Helpful loading, empty, and fallback states
- Automatic exclusion of `Special Topics in ...` courses so semester-varying entries do not distort results

## Tech Stack

### Data Pipeline

- Python
- `requests`
- `BeautifulSoup`
- `SQLAlchemy`
- `pandas`

### Semantic Retrieval

- `sentence-transformers`
- `all-mpnet-base-v2`
- `faiss-cpu`
- `numpy`

### Backend

- FastAPI
- Uvicorn

### Frontend

- React
- Vite
- Tailwind CSS

## Architecture

CourseConnect follows a simple three-layer architecture:

1. Data layer
   Scrapes graduate course catalog pages, cleans records, and stores them in JSON, CSV, and SQLite.
2. Retrieval layer
   Generates dense embeddings for each course and builds a FAISS similarity index for fast semantic search.
3. Application layer
   Exposes search and course endpoints through FastAPI and renders results in a responsive React interface.

## Project Structure

```text
CourseConnect/
|-- backend/
|   `-- app/
|       |-- __init__.py
|       |-- config.py
|       |-- db.py
|       |-- main.py
|       |-- models.py
|       `-- search.py
|-- data/
|   |-- index/
|   |-- processed/
|   `-- raw/
|-- frontend/
|   |-- public/
|   `-- src/
|       |-- App.jsx
|       |-- index.css
|       `-- main.jsx
|-- scripts/
|   |-- embed.py
|   `-- scrape.py
|-- .gitignore
|-- index.html
|-- package.json
|-- postcss.config.js
|-- requirements.txt
|-- tailwind.config.js
|-- vite.config.js
`-- README.md
```

## Data Schema

Each course record is stored with the following schema:

- `id`
- `code`
- `title`
- `credits`
- `description`
- `prerequisites`

The SQLite database is created at:

- `data/processed/courseconnect.db`

## Setup

## 1. Prerequisites

Install the following before running the app:

- Python 3.10 or newer
- Node.js LTS
- npm

You can verify your installation with:

```powershell
python --version
node -v
npm -v
```

If `npm` is not recognized in PowerShell, install Node.js from [nodejs.org](https://nodejs.org/) and reopen your terminal.

## 2. Clone or open the project

Open a terminal in the project root:

```powershell
cd C:\Users\swaya\Downloads\CourseConnect
```

## 3. Create and activate a Python virtual environment

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
```

## 4. Install Python dependencies

```powershell
pip install -r requirements.txt
```

## 5. Install frontend dependencies

```powershell
npm install
```

## Running the Full App

Run the project in this exact order the first time.

## Step 1. Scrape graduate catalog data

```powershell
python scripts/scrape.py
```

This script:

- discovers subject pages from the Texas A&M graduate catalog index
- extracts course code, title, credits, description, and prerequisites
- skips entries containing `Special Topics in`
- writes cleaned outputs to JSON, CSV, and SQLite

Generated files:

- `data/processed/courses.json`
- `data/processed/courses.csv`
- `data/processed/courseconnect.db`

## Step 2. Build embeddings and FAISS index

```powershell
python scripts/embed.py
```

This script:

- loads cleaned course records
- combines title and description text
- generates embeddings with `all-mpnet-base-v2`
- normalizes embeddings for cosine-style similarity search
- builds and saves a FAISS index for reuse

Generated files:

- `data/index/course_embeddings.npy`
- `data/index/course_metadata.json`
- `data/index/course_index.faiss`

## Step 3. Start the backend

```powershell
uvicorn backend.app.main:app --reload --port 8000
```

The backend will be available at:

- [http://localhost:8000](http://localhost:8000)

## Step 4. Start the frontend

Open a second terminal in the same project folder and run:

```powershell
npm run dev
```

The frontend will be available at:

- [http://localhost:3000](http://localhost:3000)

## API Endpoints

### `GET /health`

Health check for backend readiness.

Example:

- [http://localhost:8000/health](http://localhost:8000/health)

### `GET /courses`

Returns all scraped courses from SQLite.

Example:

- [http://localhost:8000/courses](http://localhost:8000/courses)

### `GET /search`

Runs semantic search over the FAISS index.

Query parameters:

- `q` required natural-language query
- `top_k` optional result count, default `10`
- `department` optional subject filter such as `CSCE`
- `min_credits` optional minimum credit filter
- `max_credits` optional maximum credit filter

Examples:

- [http://localhost:8000/search?q=deep%20learning%20for%20computer%20vision&top_k=10](http://localhost:8000/search?q=deep%20learning%20for%20computer%20vision&top_k=10)
- [http://localhost:8000/search?q=distributed%20cloud%20systems&top_k=10](http://localhost:8000/search?q=distributed%20cloud%20systems&top_k=10)
- [http://localhost:8000/search?q=machine%20learning&department=CSCE&top_k=10](http://localhost:8000/search?q=machine%20learning&department=CSCE&top_k=10)

## How to Test the App

Once both servers are running:

1. Open [http://localhost:3000](http://localhost:3000)
2. Enter a query such as `deep learning for computer vision`
3. Confirm that ranked course cards appear
4. Check that relevance scores and progress bars display
5. Expand a result description
6. Save a course and verify it appears in the shortlist sidebar
7. Try department or credit filters
8. Try a narrow query that returns few results and verify the empty-state guidance appears

Suggested demo queries:

- `deep learning for computer vision`
- `distributed cloud systems`
- `privacy in machine learning`
- `robotics and spatial intelligence`
- `cybersecurity data analytics`
- `computational biology and genomics`

## Frontend Experience

The frontend is intentionally minimal, academic, and presentation-friendly. It includes:

- a large semantic search bar
- guided example queries
- a refinement sidebar
- recent-search memory
- a saved-course shortlist
- visual relevance indicators
- highlighted query matches
- expandable result cards

These additions make the app more engaging during demos and more useful for repeat exploration.

## Data Notes

- Source catalog: [Texas A&M Graduate Course Descriptions](https://catalog.tamu.edu/graduate/course-descriptions/)
- Subject pages are discovered automatically from the catalog index
- Courses with titles containing `Special Topics in` are skipped
- Search uses normalized embeddings with FAISS inner-product search, equivalent to cosine similarity after normalization
- Department labels shown in search results are inferred from course codes

## Troubleshooting

### `ModuleNotFoundError: No module named 'backend'`

The project scripts have been updated to add the repo root to `sys.path`, so running the scripts directly should work:

```powershell
python scripts/scrape.py
python scripts/embed.py
```

### `npm` is not recognized

Node.js is not installed or not on your PATH. Install Node.js LTS from [nodejs.org](https://nodejs.org/) and reopen PowerShell.

### `localhost:3000` does not load

Make sure the frontend dev server is running:

```powershell
npm run dev
```

Also make sure the terminal actually shows a local Vite URL after startup.

### `localhost:8000/search` returns an index error or 503

You likely skipped one of the data pipeline steps. Run:

```powershell
python scripts/scrape.py
python scripts/embed.py
```

Then restart the backend.

### Dependency conflict involving `numpy` and `faiss-cpu`

This project pins `numpy==1.26.4` because `faiss-cpu==1.8.0.post1` requires `numpy < 2.0`.

## Suggested Presentation Flow

If you plan to demo this in class, a clean order is:

1. Explain the problem with keyword-only course discovery
2. Show a traditional catalog page briefly
3. Open CourseConnect
4. Enter a natural-language query
5. Show ranked, semantically relevant results
6. Point out prerequisites, saved courses, filters, and relevance indicators
7. Mention the underlying pipeline: scraper, embeddings, FAISS, FastAPI, React

## Future Enhancements

- syllabus ingestion when publicly available
- reranking using prerequisite alignment
- personalization or user profiles
- analytics on popular interest clusters
- explanation-aware ranking signals
- exportable course comparison views

## License / Academic Note

This project was created for an Information Storage and Retrieval course as an educational semantic retrieval application built on publicly accessible course catalog data.
>>>>>>> master
