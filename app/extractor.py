import re
import spacy
import requests
import os
from dotenv import load_dotenv
import os

load_dotenv()
HUGGINGFACE_API_KEY = os.getenv("HF_API_KEY")
if not HUGGINGFACE_API_KEY:
    raise ValueError("HUGGINGFACE_API_KEY environment variable not set. Please set it in your .env file.")

# Load English spaCy model
nlp = spacy.load("en_core_web_sm")


# Section headers mapped to categories (lowercase)
SECTION_HEADERS = {
    "education": ["education", "academic background", "educational qualifications", "studies"],
    "experience": ["experience", "work experience", "professional background", "employment history"],
    "skills": ["skills", "technical skills", "technologies", "tools"],
    "projects": ["projects", "personal projects", "academic projects", "professional projects", "project experience"],
    "certifications": ["certifications", "certificates"],
    "extracurriculars": ["extracurriculars", "activities", "leadership", "organizations", "volunteer experience"]
}

def is_section_header(line, section_name):
    pattern = r"^\s*" + re.escape(section_name) + r"s?\s*:?\s*$"
    return re.match(pattern, line.strip(), flags=re.IGNORECASE) is not None


def extract_resume_info(text):
    doc = nlp(text)
    info = {}


    info["Name"] = extract_name(text, doc)
    info["Email"] = extract_email(text)
    info["Phone"] = extract_phone(text)
    info["LinkedIn"] = extract_linkedin(text)
    info["GitHub"] = extract_github(text)


    sections = extract_sections(text)
    
    for section, content in sections.items():
        cleaned = content.strip()
        
        if not cleaned:
            continue

        if section.lower() == "skills":
            info["Skills"] = parse_skills(cleaned)
        elif section.lower() == "experience":
            extracted_exp = extract_experience(cleaned)
            info["Experience"] = extracted_exp if extracted_exp else cleaned
        elif section.lower() == "projects":
            extracted_projects = extract_projects(cleaned)
            info["Projects"] = extracted_projects if extracted_projects else cleaned
        elif section.lower() == "education":
            info["Education"] = extract_education(cleaned)
        else:
            info[section.capitalize()] = cleaned

    return info


# ------------------------- Field Extractors ------------------------- #
def extract_name(text, doc):
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    if lines:
        # First line heuristic — assume it's the name if it's not all uppercase or a title
        first_line = lines[0]
        if 1 <= len(first_line.split()) <= 4:
            return first_line

    # Fallback to NER
    for ent in doc.ents:
        if ent.label_ == "PERSON" and 1 <= len(ent.text.split()) <= 4:
            return ent.text.strip()

    return "Not found"

def extract_email(text):
    text = re.sub(r'(?<=\S)\s(?=\S)', '', text) 

    matches = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', text)

    return max(matches, key=len) if matches else "Not found"

def extract_phone(text):
    match = re.search(r'(\+?\d{1,3}[\s\-]?)?(\(?\d{3}\)?[\s\-]?)?[\d\s\-]{7,}', text)
    return match.group(0).strip() if match else "Not found"

def extract_github(text):
    lines = text.splitlines()[:20]  # Only search near top of resume
    github_pattern = re.compile(r"(https?://)?(www\.)?github\.com/[a-zA-Z0-9\-_.]+", re.IGNORECASE)

    for line in lines:
        match = github_pattern.search(line)
        if match:
            url = match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            return url.strip()

    return "Not found"

def extract_linkedin(text):
    lines = text.splitlines()[:20]  # Look near the top only
    linkedin_pattern = re.compile(r"(https?://)?(www\.)?linkedin\.com/in/[a-zA-Z0-9\-_/]+", re.IGNORECASE)

    for line in lines:
        # Case 1: explicit LinkedIn URL
        match = linkedin_pattern.search(line)
        if match:
            url = match.group(0)
            if not url.startswith("http"):
                url = "https://" + url
            return url.strip()

        # Case 2: just says "LinkedIn" but has a hyperlink
        if "linkedin" in line.lower():
            # Attempt to grab a URL on the same line (could be hidden in DOCX export)
            url_match = re.search(r"(https?://[^\s]+)", line)
            if url_match and "linkedin.com" in url_match.group(0):
                return url_match.group(0).strip()

    return "Not found"
# ------------------------- Section Extractor ------------------------- #
def extract_sections(text):
    lines = text.splitlines()
    sections = {}
    current_section = None

    for line in lines:
        clean_line = line.strip()
        
        # Skip empty lines
        if not clean_line:
            if current_section:
                sections[current_section] += line + "\n"
            continue

        # Check if line is a section header
        matched = False
        for key, keywords in SECTION_HEADERS.items():
            for keyword in keywords:
                # More flexible matching - handles case and optional colons
                if re.match(r'^\s*' + re.escape(keyword) + r's?\s*:?\s*$', clean_line, re.IGNORECASE):
                    current_section = key
                    sections[current_section] = ""
                    matched = True
                    break
            if matched:
                break

        # Add content to current section
        if current_section and not matched:
            sections[current_section] += line + "\n"

    return sections

# ------------------------- Subsection Parsers ------------------------- #
def parse_skills(text):
    if not text.strip():
        return ["Not found"]
    
    skills = []
    lines = text.splitlines()
    
    # Categories to ignore (these are section headers, not actual skills)
    category_patterns = [
        r'^(programming\s+languages?|technical\s+skills?|tools?(/software)?|soft\s+skills?|languages?|developer\s+tools?|libraries?)\s*:?\s*$',
        r'^skills?\s*:?\s*$'
    ]
    
    for line in lines:
        original_line = line.strip()
        if not original_line:
            continue
        
        # Skip category headers
        is_category = False
        for pattern in category_patterns:
            if re.match(pattern, original_line, re.IGNORECASE):
                is_category = True
                break
        if is_category:
            continue
        
        # Remove bullet points (●, •, -, *, etc.)
        clean_line = re.sub(r'^[\s]*[●•▪▫◦‣⁃\-\*]+\s*', '', original_line)
        
        # Handle category-prefixed lines (e.g., "Languages: Python, Java")
        colon_match = re.match(r'^([^:]+):\s*(.+)', clean_line)
        if colon_match:
            category = colon_match.group(1).strip()
            content = colon_match.group(2).strip()
            
            # Skip if the category is empty or just contains the content
            if content:
                clean_line = content
            else:
                continue
        
        # Now parse the actual skills from the clean line
        if clean_line:
            # Split by commas, but be careful with parentheses
            skills_from_line = smart_split_skills(clean_line)
            skills.extend(skills_from_line)
    
    # Clean up and deduplicate
    final_skills = []
    seen = set()
    
    for skill in skills:
        # Final cleanup
        skill = skill.strip().strip(',').strip()
        
        # Skip empty or very short skills
        if len(skill) < 2:
            continue
            
        # Skip obvious non-skills
        if re.match(r'^(and|or|with|using|including)$', skill, re.IGNORECASE):
            continue
            
        # Avoid duplicates (case-insensitive)
        skill_lower = skill.lower()
        if skill_lower not in seen:
            seen.add(skill_lower)
            final_skills.append(skill)
    
    return final_skills if final_skills else ["Not found"]

def smart_split_skills(text):
    skills = []
    current_skill = ""
    paren_depth = 0
    
    i = 0
    while i < len(text):
        char = text[i]
        
        if char == '(':
            paren_depth += 1
            current_skill += char
        elif char == ')':
            paren_depth -= 1
            current_skill += char
        elif char == ',' and paren_depth == 0:
            # This comma is not inside parentheses, so it's a separator
            if current_skill.strip():
                skills.append(current_skill.strip())
            current_skill = ""
        else:
            current_skill += char
        
        i += 1
    
    # Don't forget the last skill
    if current_skill.strip():
        skills.append(current_skill.strip())
    
    # Additional splitting for items that might be separated by other delimiters
    final_skills = []
    for skill in skills:
        # Check for other separators like " | " or " / " but only if no parentheses
        if '(' not in skill and ')' not in skill:
            # Split by pipe or forward slash
            if ' | ' in skill:
                final_skills.extend([s.strip() for s in skill.split(' | ') if s.strip()])
            elif ' / ' in skill:
                final_skills.extend([s.strip() for s in skill.split(' / ') if s.strip()])
            else:
                final_skills.append(skill)
        else:
            final_skills.append(skill)
    
    return final_skills


def extract_skills(text):
    """
    Extracts and normalizes skills from the 'skills' section.
    Handles bullets, commas, and mixed formatting.
    """
    if not text.strip():
        return ["Not found"]

    skills = set()  # Use set to avoid duplicates
    lines = text.splitlines()

    for line in lines:
        line = line.strip("•·-• ").strip()  # Remove bullet characters
        if not line:
            continue

        # If comma-separated, split it
        if "," in line:
            parts = [part.strip() for part in line.split(",") if part.strip()]
            skills.update(parts)
        else:
            skills.add(line)

    return sorted(skills) if skills else ["Not found"]

def extract_education(text):
    """
    Extracts non-empty lines as education entries.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return lines if lines else ["Not found"]

def extract_experience(text):
    if not text.strip():
        return []
        
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    experiences = []
    current = {}

    # Enhanced date pattern to catch more formats
    date_pattern = re.compile(
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}\s*[–\-~]\s*(Present|Current|\d{4})',
        re.IGNORECASE
    )
    
    # Also check for simple year ranges like "2024 - Present"
    simple_date_pattern = re.compile(r'\d{4}\s*[–\-]\s*(Present|Current|\d{4})', re.IGNORECASE)

    for line in lines:
        if not line.strip():
            continue
            
        date_match = date_pattern.search(line) or simple_date_pattern.search(line)

        # If line contains a date, treat as new experience
        if date_match:
            if current:
                experiences.append(current)
            
            # Extract title (everything before the date)
            title_part = line[:date_match.start()].strip()
            title_part = re.sub(r'[–\-•●▪]\s*$', '', title_part).strip()
            
            current = {
                "title_or_role": title_part,
                "date_range": date_match.group(0),
                "responsibilities": []
            }
        # Otherwise, treat as responsibility/description
        elif current:
            # Clean up bullet points and formatting
            responsibility = re.sub(r'^[•●▪▫◦‣⁃\-\*\s]+', '', line).strip()
            if responsibility and len(responsibility) > 10:  # Filter out very short lines
                current["responsibilities"].append(responsibility)

    if current:
        experiences.append(current)

    return experiences

def extract_projects(text):
    if not text.strip():
        return []
    
    lines = [line for line in text.splitlines()]  # Keep original formatting
    projects = []
    current = None
    
    # Common bullet patterns (including various Unicode bullets)
    bullet_pattern = re.compile(r'^[\s]*[•●▪▫◦‣⁃\-\*]\s*', re.UNICODE)
    
    for line in lines:
        stripped_line = line.strip()
        
        # Skip empty lines and section headers
        if not stripped_line or stripped_line.lower() == "projects":
            continue
            
        # Check if this line starts with a bullet
        is_bullet = bullet_pattern.match(line)
        
        if is_bullet:
            # This is a bullet point - add to current project details
            if current:
                clean_bullet = bullet_pattern.sub('', line).strip()
                current["details"].append(clean_bullet)
        else:
            # This might be a new project title
            # Save previous project if exists
            if current:
                projects.append(current)
            
            # Start new project
            current = {
                "title": stripped_line,
                "details": []
            }
    
    # Don't forget the last project
    if current:
        projects.append(current)
    
    return projects

def generate_summary_hf(extracted_data):
    """
    Generates a professional summary using Hugging Face Inference API and Mistral-7B.
    """
    model_url = "https://api-inference.huggingface.co/models/google/flan-t5-base"
    if not HUGGINGFACE_API_KEY:
        return "⚠️ Hugging Face API key not set. Please set the HUGGINGFACE_API_KEY environment variable."
    if not os.getenv("HF_API_KEY"):
        return "⚠️ Hugging Face API key not found in environment variables."
    if not extracted_data:
        return "⚠️ No data extracted from resume. Please check the input text."
    if not isinstance(extracted_data, dict):
        return "⚠️ Invalid data format. Expected a dictionary with extracted resume information."
    
    requests.get("https://api-inference.huggingface.co/models/google/flan-t5-base")

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json"
    }

    sections = []
    prompt = (
        "Summarize the following student resume into 3 short sentences highlighting education, technical experience, and projects:\n\n"
        + "\n\n".join(sections)
    )

    for key in ["Education", "Experience", "Projects", "Skills", "Extracurriculars"]:
        if key in extracted_data:
            content = extracted_data[key]
            if isinstance(content, list):
                text = "\n".join(content)
            else:
                text = str(content)
            sections.append(f"{key}:\n{text}\n")

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 250,
            "temperature": 0.7,
            "return_full_text": False
        }
    }

    response = requests.post(model_url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()[0]['generated_text'].strip()
    else:
        return f"⚠️ Hugging Face API error: {response.status_code} – {response.text}"
