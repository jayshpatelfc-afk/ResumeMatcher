import os
import re
import sqlite3
from flask import Flask, render_template, request, jsonify
from pypdf import PdfReader

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'database')
DB_PATH = os.path.join(DB_DIR, 'resume_matching.db')
os.makedirs(DB_DIR, exist_ok=True)

app = Flask(__name__)

DEFAULT_JOBS = [
    ("Frontend Developer", "Build responsive web interfaces using HTML, CSS, JavaScript, React, and UI best practices."),
    ("Backend Developer", "Develop REST APIs, server-side logic, databases, authentication, and scalable application services."),
    ("Full Stack Developer", "Work across frontend and backend systems with modern frameworks, APIs, databases, and deployment workflows."),
    ("Python Developer", "Write Python applications, automate scripts, optimize backend services, and build data-driven features."),
    ("Java Developer", "Design and implement Java enterprise applications, APIs, and backend integrations with strong testing."),
    ("Data Analyst", "Analyze datasets, create dashboards, interpret trends, and communicate insights using SQL and reporting tools."),
    ("Data Scientist", "Build predictive models, analyze large data sets, and deploy machine learning solutions using Python and analytics."),
    ("DevOps Engineer", "Automate deployments, monitor infrastructure, manage CI/CD, and ensure application reliability."),
    ("QA Engineer", "Create automated tests, validate software quality, and improve release confidence across products."),
    ("UX Designer", "Design intuitive user experiences, wireframes, prototypes, and accessible interfaces using research insights."),
    ("Product Manager", "Prioritize product features, coordinate cross-functional teams, and translate customer needs into execution."),
    ("Project Manager", "Manage timelines, resources, risks, and stakeholders to deliver successful business projects."),
    ("Mobile Developer", "Build native or cross-platform mobile experiences with Android, iOS, and app performance optimization."),
    ("Cloud Engineer", "Deploy applications to cloud platforms, manage infrastructure, security, scalability, and automation."),
    ("Cybersecurity Analyst", "Monitor systems, analyze security threats, respond to incidents, and maintain compliance controls."),
    ("AI Engineer", "Develop AI-powered features, integrate models, and optimize production systems with data and APIs."),
    ("Business Analyst", "Gather requirements, document workflows, and support process improvement with stakeholder alignment."),
    ("Machine Learning Engineer", "Train models, build pipelines, deploy intelligent features, and monitor model performance in production."),
    ("Database Administrator", "Maintain databases, optimize queries, ensure backups, and enforce performance and security best practices."),
    ("Systems Engineer", "Support infrastructure, troubleshoot systems, automate operations, and improve platform reliability."),
]


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_description TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                score INTEGER NOT NULL,
                matched_skills TEXT,
                missing_skills TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing = conn.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        if existing < len(DEFAULT_JOBS):
            conn.executemany(
                'INSERT OR IGNORE INTO jobs (title, description) VALUES (?, ?)',
                DEFAULT_JOBS,
            )
        conn.commit()


init_db()
STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your",
    "have", "will", "must", "should", "been", "were", "using", "skills",
    "experience", "about", "over", "under", "through", "their", "there",
    "where", "what", "when", "work", "team", "role", "job", "developer",
    "engineer", "candidate", "resume", "responsible", "strong", "ability",
    "required", "include", "including", "years", "year", "month", "months",
    "also", "such", "as", "on", "of", "to", "in", "a", "an", "is", "are",
    "be", "by", "or", "at", "it", "we", "you", "our", "us", "if", "but",
    "not", "can", "could", "would", "did", "do", "does", "new", "old"
}
def extract_pdf_text(file_storage):
    try:
        file_storage.seek(0)
        reader = PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
        return text
    except Exception:
        return ""
def normalize_text(text):
    text = text.lower()
    return re.sub(r"[^a-z0-9\s+-]", " ", text)
def extract_keywords(text):
    clean = normalize_text(text)
    words = re.findall(r"[a-z0-9][a-z0-9+.#/-]*", clean)
    keywords = []
    for word in words:
        if len(word) > 2 and word not in STOP_WORDS:
            keywords.append(word)
    return sorted(set(keywords))
def build_match_result(job_description, resume_text):
    job_keywords = extract_keywords(job_description)
    resume_keywords = extract_keywords(resume_text)
    if not job_keywords:
        return 0, [], []
    matched = sorted(set(job_keywords) & set(resume_keywords))
    missing = sorted(set(job_keywords) - set(resume_keywords))
    score = round((len(matched) / len(job_keywords)) * 100) if job_keywords else 0
    return score, matched, missing
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/jobs')
def jobs():
    with get_db_connection() as conn:
        rows = conn.execute('SELECT id, title, description FROM jobs ORDER BY id').fetchall()
    return jsonify([{'id': row['id'], 'title': row['title'], 'description': row['description']} for row in rows])


@app.route('/analyze', methods=['POST'])
def analyze():
    job_id = request.form.get('job_id', '')
    resumes = request.files.getlist('resumes')

    if not resumes or resumes[0].filename == '':
        return jsonify({'error': 'Please upload at least one resume PDF.'}), 400

    if not job_id:
        return jsonify({'error': 'Please select a job.'}), 400

    with get_db_connection() as conn:
        job = conn.execute('SELECT title, description FROM jobs WHERE id = ?', (job_id,)).fetchone()

    if not job:
        return jsonify({'error': 'Selected job was not found.'}), 400

    job_description = job['description']
    job_keywords = extract_keywords(job_description)
    if not job_keywords:
        return jsonify({'error': 'Please choose another job with clear skill requirements.'}), 400

    results = []
    for resume in resumes:
        if not resume.filename.lower().endswith('.pdf'):
            continue
        resume_text = extract_pdf_text(resume)
        if not resume_text.strip():
            continue

        score, matched, missing = build_match_result(job_description, resume_text)
        candidate_name = os.path.splitext(resume.filename)[0].replace('_', ' ').replace('-', ' ').title()

        results.append({
            'name': candidate_name,
            'score': score,
            'matching_skills': matched[:10],
            'missing_skills': missing[:10],
            'total_job_skills': len(job_keywords)
        })

    if not results:
        return jsonify({'error': 'No readable PDF resumes were detected.'}), 400

    results.sort(key=lambda item: item['score'], reverse=True)

    with get_db_connection() as conn:
        for result in results:
            conn.execute(
                '''
                INSERT INTO results (
                    job_description,
                    candidate_name,
                    score,
                    matched_skills,
                    missing_skills
                ) VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    job_description,
                    result['name'],
                    result['score'],
                    ', '.join(result['matching_skills']),
                    ', '.join(result['missing_skills']),
                ),
            )
        conn.commit()

    return jsonify({'candidates': results})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5006)
