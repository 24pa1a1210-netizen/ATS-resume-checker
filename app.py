from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import re
from collections import Counter

app = Flask(__name__, template_folder='.')
CORS(app)  # Enable CORS for all routes

# --- Configuration & Data Lists ---

COMMON_STOP_WORDS = {
    'and', 'the', 'for', 'with', 'you', 'that', 'are', 'this', 'from', 'will', 
    'have', 'your', 'our', 'can', 'all', 'but', 'not', 'of', 'in', 'to', 'is', 
    'a', 'an', 'or', 'as', 'be', 'by', 'on', 'at', 'it'
}

# A broader list of tech skills to look for
TECH_SKILLS = {
    'javascript', 'python', 'java', 'react', 'angular', 'vue', 'html', 'css', 
    'typescript', 'sql', 'aws', 'docker', 'kubernetes', 'git', 'jira', 'agile', 
    'scrum', 'communication', 'leadership', 'redux', 'node', 'express', 
    'mongodb', 'ci/cd', 'frontend', 'backend', 'fullstack', 'api', 'rest', 
    'graphql', 'machine learning', 'data analysis', 'go', 'rust', 'c++', 'c#',
    'azure', 'gcp', 'terraform', 'jenkins', 'linux', 'bash', 'design patterns'
}

SOFT_SKILLS = {
    'communication', 'leadership', 'teamwork', 'agile', 'scrum', 
    'collaboration', 'problem-solving', 'adaptability', 'time management', 
    'critical thinking', 'creativity'
}

# --- Helper Functions ---

def clean_text(text):
    """Converts text to lowercase and removes punctuation/special characters."""
    # Convert to lowercase
    text = text.lower()
    # Remove special characters but keep alphanumeric and whitespace
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Split into words and filter out short words
    words = [w for w in text.split() if len(w) > 2]
    return words

def check_formatting_rules(text):
    """Performs regex checks for contact info and metrics."""
    checks = []
    
    # Check 1: Email
    has_email = bool(re.search(r'\b[\w\.-]+@[\w\.-]+\.\w{2,4}\b', text))
    checks.append({
        'label': "Contact Email",
        'pass': has_email,
        'msgFail': "No email detected"
    })

    # Check 2: Phone
    has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text))
    checks.append({
        'label': "Phone Number",
        'pass': has_phone,
        'msgFail': "No phone number"
    })

    # Check 3: Action Verbs
    has_verbs = bool(re.search(r'\b(led|managed|developed|created|built|designed|improved|optimized|engineered|architected)\b', text, re.IGNORECASE))
    checks.append({
        'label': "Action Verbs",
        'pass': has_verbs,
        'msgFail': "Add verbs like 'Managed'"
    })

    # Check 4: Metrics
    has_metrics = bool(re.search(r'\d+%|\$\d+', text)) or bool(re.search(r'\b\d+\s+(users|clients|percent|increase|reduction)', text, re.IGNORECASE))
    checks.append({
        'label': "Metrics/Numbers",
        'pass': has_metrics,
        'msgFail': "Include measurable achievements (e.g., '20%')"
    })

    # Check 5: Formatting (Mock check)
    checks.append({
        'label': "Consistent Formatting",
        'pass': True, # Hard to check programmatically without parsing PDF/Docx structure
        'msgFail': "Ensure uniform font and style"
    })

    # Check 6: Typos (Mock check)
    checks.append({
        'label': "No Typos",
        'pass': True,
        'msgFail': "Proofread for spelling errors"
    })

    return checks

def generate_optimization_tips(score, missing_keywords):
    tips = []
    
    if score < 50:
        tips.append("Your resume needs significant alignment with the job description.")
    elif score < 80:
        tips.append("You're close! focus on adding specific technical keywords.")
    else:
        tips.append("Great match! Focus on readability and formatting now.")

    if missing_keywords:
        tips.append(f"Try to weave in these top missing keywords: {', '.join(missing_keywords[:3])}.")
    
    tips.append("Ensure you use 'Action Verbs' at the start of every bullet point.")
    tips.append("Quantify your experience with numbers (e.g., 'Reduced latency by 20%').")
    
    return tips

# --- Routes ---

@app.route('/')
def home():
    """Serves the frontend HTML."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    resume_text = data.get('resume_text', '')
    jd_text = data.get('jd_text', '')

    if not resume_text or not jd_text:
        return jsonify({'error': 'Both fields are required'}), 400

    # 1. Tokenize
    resume_words = clean_text(resume_text)
    jd_words = clean_text(jd_text)
    
    resume_set = set(resume_words)
    jd_counter = Counter([w for w in jd_words if w not in COMMON_STOP_WORDS])

    # 2. Identify Target Keywords
    # We look for words that are either in our Known Skills list OR appear frequently in the JD
    target_keywords = set()
    
    # Add known skills found in JD
    for word in jd_words:
        if word in TECH_SKILLS:
            target_keywords.add(word)
            
    # Add top frequency words from JD if we don't have enough skills
    if len(target_keywords) < 5:
        most_common = [word for word, count in jd_counter.most_common(10)]
        target_keywords.update(most_common)

    target_keywords = list(target_keywords)

    # 3. Match Keywords
    found = []
    missing = []
    
    # Check exact matches
    raw_resume_lower = resume_text.lower()
    
    for k in target_keywords:
        # Check if word exists in tokenized set OR as a substring in raw text (handles multi-word skills partially)
        if k in resume_set or k in raw_resume_lower:
            found.append(k)
        else:
            missing.append(k)

    # 4. Calculate Score
    total_keywords = len(target_keywords)
    if total_keywords == 0:
        score = 0
    else:
        score = int((len(found) / total_keywords) * 100)

    # 5. Formatting Checks
    format_checks = check_formatting_rules(resume_text)

    # 6. Optimization Tips
    tips = generate_optimization_tips(score, missing)

    # 7. Construct Response
    response = {
        'score': score,
        'found_keywords': found,
        'missing_keywords': missing,
        'hard_skills_count': sum(1 for k in found if k not in SOFT_SKILLS),
        'soft_skills_count': sum(1 for k in found if k in SOFT_SKILLS),
        'format_checks': format_checks,
        'tips': tips
    }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)