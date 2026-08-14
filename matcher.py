import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def rank_resumes(cleaned_resumes, cleaned_jd):
    if not cleaned_resumes or not cleaned_jd:
        return pd.DataFrame(columns=["Rank", "Resume", "Match Score (%)"])
        
    filenames = [r["filename"] for r in cleaned_resumes]
    texts = [r["cleaned_text"] for r in cleaned_resumes]
    
    # Add JD as the last document
    documents = texts + [cleaned_jd]
    
    # Use TfidfVectorizer with english stop words
    vectorizer = TfidfVectorizer(stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
        
        # Calculate cosine similarity between each resume and the JD (last row)
        resume_vectors = tfidf_matrix[:-1]
        jd_vector = tfidf_matrix[-1:]
        
        cosine_similarities = cosine_similarity(resume_vectors, jd_vector)
        scores = cosine_similarities.flatten() * 100
    except ValueError:
        # In case all documents are empty or contain only stop words
        scores = [0] * len(filenames)
    
    results = pd.DataFrame({
        "Rank": range(1, len(filenames) + 1),
        "Resume": filenames,
        "Match Score (%)": [round(score, 2) for score in scores]
    })
    
    # Sort by score descending
    results = results.sort_values(by="Match Score (%)", ascending=False).reset_index(drop=True)
    results["Rank"] = range(1, len(filenames) + 1)
    
    return results
