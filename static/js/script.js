const resumeInput = document.getElementById('resume-input');
const fileList = document.getElementById('file-list');
const jobSelect = document.getElementById('job-select');
const analyzeBtn = document.getElementById('analyze-btn');
const results = document.getElementById('results');
const jobSearch = document.getElementById('job-search');
const jobSearchBtn = document.getElementById('job-search-btn');

let selectedFiles = [];
let allJobs = [];

analyzeBtn.disabled = true;
jobSelect.disabled = true;

function renderJobOptions(filterText = '') {
    const term = filterText.trim().toLowerCase();

    const filteredJobs = term
        ? allJobs.filter((job) => job.title.toLowerCase().includes(term))
        : allJobs;

    jobSelect.innerHTML = '<option value="">Choose a job</option>';

    filteredJobs.forEach((job) => {
        const option = document.createElement('option');
        option.value = job.id;
        option.textContent = job.title;
        jobSelect.appendChild(option);
    });

    if (!filteredJobs.length) {
        const none = document.createElement('option');
        none.value = '';
        none.textContent = 'No jobs found';
        jobSelect.appendChild(none);
    }

    jobSelect.disabled = filteredJobs.length === 0;
    updateButtonState();
}

async function loadJobs() {
    try {
        const response = await fetch('/jobs');
        const jobs = await response.json();
        allJobs = jobs;
        renderJobOptions();
    } catch (error) {
        console.error('Failed to load jobs:', error);
        allJobs = [];
        jobSelect.innerHTML = '<option value="">Choose a job</option>';
        jobSelect.disabled = true;
        analyzeBtn.disabled = true;
    }
}

function updateButtonState() {
    const hasFiles = selectedFiles.length > 0;
    const hasJob = jobSelect.value !== '' && !jobSelect.disabled && jobSelect.value !== 'No jobs found';
    analyzeBtn.disabled = !(hasFiles && hasJob);
}

jobSearchBtn.addEventListener('click', () => {
    renderJobOptions(jobSearch.value);
    if (jobSelect.options.length > 0) {
        jobSelect.selectedIndex = 1;
    }
});

jobSearch.addEventListener('input', () => {
    renderJobOptions(jobSearch.value);
});

function renderFiles() {
    fileList.innerHTML = '';
    selectedFiles.forEach((file, index) => {
        const item = document.createElement('li');
        item.innerHTML = `
            <span>${file.name}</span>
            <button type="button" aria-label="Remove ${file.name}" data-index="${index}">×</button>
        `;
        fileList.appendChild(item);
    });

    fileList.querySelectorAll('button').forEach((button) => {
        button.addEventListener('click', () => {
            const idx = Number(button.dataset.index);
            selectedFiles.splice(idx, 1);
            renderFiles();
            updateButtonState();
        });
    });
}

resumeInput.addEventListener('change', (event) => {
    const newFiles = Array.from(event.target.files || []);
    newFiles.forEach((file) => {
        if (file.type === 'application/pdf' && !selectedFiles.some(f => f.name === file.name)) {
            selectedFiles.push(file);
        }
    });
    renderFiles();
    updateButtonState();
    resumeInput.value = '';
});

jobSelect.addEventListener('change', updateButtonState);
loadJobs();

analyzeBtn.addEventListener('click', async () => {
    if (analyzeBtn.disabled || !selectedFiles.length || !jobSelect.value) {
        return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = 'Matching...';
    results.innerHTML = '<p class="placeholder">Matching resumes...</p>';

    const formData = new FormData();
    formData.append('job_id', jobSelect.value);
    selectedFiles.forEach((file) => {
        formData.append('resumes', file);
    });

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to analyze resumes.');
        }

        renderResults(data.candidates || []);
    } catch (error) {
        results.innerHTML = `<p class="placeholder">${error.message}</p>`;
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = 'Match Candidates';
        updateButtonState();
    }
});

function renderResults(candidates) {
    results.innerHTML = '';

    if (!candidates.length) {
        results.innerHTML = '<p class="placeholder">No candidates matched.</p>';
        return;
    }

    candidates.forEach((candidate) => {
        const card = document.createElement('div');
        card.className = 'card';

        const matchingTags = candidate.matching_skills.length
            ? candidate.matching_skills.map(skill => `<span class="tag">${skill}</span>`).join('')
            : '<span class="tag">No direct match</span>';

        const missingTags = candidate.missing_skills.length
            ? candidate.missing_skills.map(skill => `<span class="tag missing">${skill}</span>`).join('')
            : '<span class="tag">All required skills found</span>';

        card.innerHTML = `
            <div class="score">${candidate.score}%</div>
            <h3>${candidate.name}</h3>
            <p>Matched ${candidate.matching_skills.length} of ${candidate.total_job_skills} keywords</p>
            <div class="tag-group"><strong>Matched:</strong> ${matchingTags}</div>
            <div class="tag-group"><strong>Missing:</strong> ${missingTags}</div>
        `;
        results.appendChild(card);
    });
}
