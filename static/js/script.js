// DOM Elements
const uploadBtn = document.getElementById('upload-btn');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const jobDesc = document.getElementById('job-desc');
const analyzeBtn = document.getElementById('analyze-btn');
const candidateGrid = document.getElementById('candidate-grid');

let uploadedFiles = [];

// 1. Trigger hidden file input when the big '+' button is clicked
uploadBtn.addEventListener('click', () => {
    fileInput.click();
});

// 2. Handle file selection
fileInput.addEventListener('change', (event) => {
    const files = Array.from(event.target.files);

    files.forEach(file => {
        // Ensure it's a PDF and not already in the list
        if (file.type === 'application/pdf' && !uploadedFiles.some(f => f.name === file.name)) {
            uploadedFiles.push(file);
        }
    });

    renderFileList();
    checkReadyState();

    // Reset input so the same file can be selected again if removed
    fileInput.value = '';
});

// 3. Render the list of selected PDFs
function renderFileList() {
    fileList.innerHTML = '';

    uploadedFiles.forEach((file, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>📄 ${file.name}</span>
            <button class="remove-btn" onclick="removeFile(${index})" aria-label="Remove ${file.name}">×</button>
        `;
        fileList.appendChild(li);
    });
}

// Global function to remove files from the array
window.removeFile = function (index) {
    uploadedFiles.splice(index, 1);
    renderFileList();
    checkReadyState();
};

// 4. Check if we have files and a job description to enable the Analyze button
function checkReadyState() {
    if (uploadedFiles.length > 0 && jobDesc.value.trim().length > 10) {
        analyzeBtn.disabled = false;
    } else {
        analyzeBtn.disabled = true;
    }
}

// Listen for typing in the Job Description box
jobDesc.addEventListener('input', checkReadyState);

// 5. Run Real Analysis
analyzeBtn.addEventListener('click', async () => {
    // Change button state to indicate processing
    const originalText = analyzeBtn.textContent;
    analyzeBtn.textContent = 'Processing with AI...';
    analyzeBtn.disabled = true;

    const formData = new FormData();
    formData.append('job_description', jobDesc.value.trim());
    
    // Append all selected files
    uploadedFiles.forEach(file => {
        formData.append('resumes', file);
    });

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Something went wrong during analysis.');
        }
        
        displayRealResults(data.candidates);
        
    } catch (err) {
        alert("Error: " + err.message);
    } finally {
        analyzeBtn.textContent = originalText;
        analyzeBtn.disabled = false;
    }
});

// Utility to escape HTML and prevent XSS
function escapeHTML(str) {
    const p = document.createElement('p');
    p.appendChild(document.createTextNode(str));
    return p.innerHTML;
}

// 6. Display Real Candidate Data
function displayRealResults(candidates) {
    candidateGrid.innerHTML = ''; // Clear placeholder text

    if (!candidates || candidates.length === 0) {
        candidateGrid.innerHTML = '<p class="placeholder-text">No valid candidates found.</p>';
        return;
    }

    candidates.forEach(candidate => {
        const isHighMatch = candidate.score >= 80 ? 'high-match' : '';
        const safeName = escapeHTML(candidate.name);

        const card = document.createElement('div');
        card.className = `candidate-card ${isHighMatch}`;

        const matchFraction = `${candidate.matching_skills.length}/${candidate.total_job_skills}`;

        const matchingHtml = candidate.matching_skills.length > 0 
            ? candidate.matching_skills.map(skill => `<span class="skill-tag">${escapeHTML(skill)}</span>`).join('') 
            : '<span style="font-size:0.8rem; color:var(--text-muted);">No matching skills</span>';

        const missingHtml = candidate.missing_skills.length > 0
            ? candidate.missing_skills.map(skill => `<span class="skill-tag missing-skill">${escapeHTML(skill)}</span>`).join('')
            : '<span style="font-size:0.8rem; color:var(--text-muted);">No missing skills!</span>';

        card.innerHTML = `
            <div class="score">${candidate.score}%</div>
            <h3>${safeName}</h3>
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 0.5rem;">
                Matched <strong>${matchFraction}</strong> Required Skills
            </p>
            
            <div style="margin-bottom: 1rem;">
                <p style="font-size: 0.85rem; font-weight: bold; color: var(--text-main); margin-bottom: 0.3rem;">Found in Resume:</p>
                <div class="skills-matched">${matchingHtml}</div>
            </div>
            
            <div>
                <p style="font-size: 0.85rem; font-weight: bold; color: var(--text-main); margin-bottom: 0.3rem;">Missing from Resume:</p>
                <div class="skills-matched">${missingHtml}</div>
            </div>
        `;

        candidateGrid.appendChild(card);
    });
}
