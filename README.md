## AI Code Reviewer

AI Code Reviewer is a full-stack application that helps developers analyze and review source code using AI. The project combines FastAPI, React, Groq LLMs, and ChromaDB to provide automated code review suggestions, bug detection, security analysis, and code quality improvements.

## What it does

* Upload source code files
* Analyze code using AI
* Detect bugs and potential vulnerabilities
* Suggest performance and code quality improvements
* Store and search code context using a RAG pipeline
* Support GitHub-based code review workflows

## Tech Stack

**Frontend**

* React
* TypeScript
* Vite
* Tailwind CSS

**Backend**

* FastAPI
* Python

**AI & Vector Search**

* Groq
* LangGraph
* ChromaDB
* Sentence Transformers

**Tools**

* Docker
* GitHub

## Project Structure

backend/ – FastAPI application, APIs, services, RAG pipeline

frontend/ – React frontend

Dockerfile – Container configuration

requirements.txt – Python dependencies

## Running Locally

Backend:

```bash
cd backend
pip install -r ../requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## What I Learned

While building this project, I learned:

* FastAPI backend development
* REST API design
* Retrieval-Augmented Generation (RAG)
* Vector databases with ChromaDB
* LLM integration using Groq
* Docker containerization
* Full-stack application development

## Future Improvements

* Repository-level code analysis
* Automated GitHub PR reviews
* CI/CD integration
* Advanced security auditing
* Multi-model support

## Application Screenshots
UPLOAD PAGE
<img width="1915" height="991" alt="image" src="https://github.com/user-attachments/assets/ba196919-231b-4b77-b60a-0600212633fa" />
REVIEW PAGE[AFTER UPLOADING]
<img width="1916" height="997" alt="image" src="https://github.com/user-attachments/assets/f3e42d6c-3e36-45de-8522-88a8b54eee91" />
GITHUB PR
<img width="1878" height="995" alt="image" src="https://github.com/user-attachments/assets/98a71085-0beb-44d2-a4dd-4d463ca23f1e" />
HISTORY PAGE
<img width="1894" height="1004" alt="image" src="https://github.com/user-attachments/assets/b62e8c29-50b4-44d4-80ae-3fc364fd6cd4" />
DASHBOARD
<img width="1903" height="826" alt="image" src="https://github.com/user-attachments/assets/c13f45f7-6092-47a6-aa2c-2a5ac209230f" />



##Author

Keerthika Kurmi

GitHub: https://github.com/kurmikeerthika
