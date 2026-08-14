import os
import sqlite3
from flask import Flask, render_template, request, jsonify
from pypdf import PdfReader
from init_db import init_db

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')
    nltk.download('stopwords')

app = Flask(__name__)
DB_PATH = os.path.join('database', 'skills.db')
init_db()

def get_skills():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, domain FROM skills")
    skills = cursor.fetchall()
    conn.close()
    return skills

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted
    return text

def preprocess_text(text):
    # Tokenize and remove stopwords
    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(text.lower())
    filtered_text = " ".join([w for w in word_tokens if not w in stop_words and w.isalnum()])
    
    return filtered_text + " " + text.lower()

def extract_skills_from_text(text, skills_db):
    processed_text = preprocess_text(text)
    
    skill_documents = [skill[1].lower() for skill in skills_db]
    documents = [processed_text] + skill_documents
    
    vectorizer = TfidfVectorizer(ngram_range=(1, 3))
    tfidf_matrix = vectorizer.fit_transform(documents)
    
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    
    found_skills = []
    for i, skill in enumerate(skills_db):
        skill_id, skill_name, skill_domain = skill
        score = cosine_similarities[i]
        
        if score > 0.0:
            found_skills.append({
                'id': skill_id,
                'name': skill_name,
                'domain': skill_domain
            })
        else:
            if not skill_name.isalnum():
                if f" {skill_name.lower()} " in f" {text.lower()} " or f"\n{skill_name.lower()}\n" in text.lower():
                    found_skills.append({
                        'id': skill_id,
                        'name': skill_name,
                        'domain': skill_domain
                    })
                    
    # Remove duplicates
    unique_skills = list({skill['id']: skill for skill in found_skills}.values())
    return unique_skills

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    resumes = request.files.getlist('resumes')
    job_description = request.form.get('job_description', '')
    
    if not resumes or len(resumes) == 0 or resumes[0].filename == '':
        return jsonify({'error': 'No resume files uploaded'}), 400
        
    if not job_description.strip():
        return jsonify({'error': 'Job description is required'}), 400
        
    try:
        skills_db = get_skills()
        if not skills_db:
            return jsonify({'error': 'No skills found in the database'}), 500
            
        job_skills = extract_skills_from_text(job_description, skills_db)
        if not job_skills:
            return jsonify({'error': 'Could not identify any skills in the provided Job Description. Please provide a more detailed description.'}), 400

        results = []
        
        for resume_file in resumes:
            resume_text = extract_text_from_pdf(resume_file)
            if not resume_text.strip():
                continue
                
            resume_skills = extract_skills_from_text(resume_text, skills_db)
            resume_skill_ids = set(s['id'] for s in resume_skills)
            
            matching_skills = []
            missing_skills = []
            
            for job_skill in job_skills:
                if job_skill['id'] in resume_skill_ids:
                    matching_skills.append(job_skill['name'])
                else:
                    missing_skills.append(job_skill['name'])
                    
            match_score = round((len(matching_skills) / len(job_skills)) * 100) if job_skills else 0
            
            # Use filename without extension as candidate name
            candidate_name = os.path.splitext(resume_file.filename)[0].replace('_', ' ').replace('-', ' ').title()
            
            results.append({
                'name': candidate_name,
                'score': match_score,
                'matching_skills': matching_skills,
                'missing_skills': missing_skills,
                'total_job_skills': len(job_skills)
            })
            
        # Sort results by score descending
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return jsonify({'candidates': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5005)
