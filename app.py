import streamlit as st
import os
import shutil
import tempfile
import git
import nbformat
import base64
import re
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
from groq import Groq
from git import Repo
from fpdf import FPDF
# CRITICAL IMPORT FIX: Added Union to handle multiple types
from typing import List, Dict, Any, Union 

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode', 'site-packages'}
IGNORE_FILES = {'.env', 'package-lock.json', 'yarn.lock'} 
IGNORE_EXTENSIONS = {'.pkl', '.h5', '.zip', '.parquet', '.exe', '.bin', '.txt', '.pyc', '.png', '.jpg'}
MAX_FILE_SIZE = 150 * 1024 
MAX_IMAGES = 3

# --- UI STYLING ---
st.set_page_config(page_title="Repo2Report", layout="wide", page_icon="⚡")

def local_css():
    st.markdown("""
    <style>
        .stApp { background-color: #0E1117; font-family: 'Inter', sans-serif; }
        
        h1 {
            background: -webkit-linear-gradient(45deg, #FF4B4B, #FF914D);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-weight: 800 !important; font-size: 3.5rem !important; padding-bottom: 20px;
        }
        
        h2 { 
            color: #E0E0E0 !important; font-size: 1.8rem !important; 
            margin-top: 40px !important; margin-bottom: 15px !important;
            border-bottom: 1px solid #333; padding-bottom: 10px;
        }
        
        h3 { color: #FF914D !important; font-size: 1.3rem !important; margin-top: 20px !important; }

        div.stButton > button {
            background: linear-gradient(90deg, #FF4B4B 0%, #FF914D 100%);
            color: white; border: none; padding: 12px 24px; font-weight: bold; border-radius: 8px;
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4);
        }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; white-space: pre-wrap; background-color: #161B22; border-radius: 5px 5px 0px 0px;
            gap: 1px; padding-top: 10px; padding-bottom: 10px; color: #FFF;
        }
        .stTabs [aria-selected="true"] { background-color: #262730; color: #FF4B4B; border-bottom: 2px solid #FF4B4B; }
        
        [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- HELPER FUNCTIONS ---

def clean_report_text(text):
    text = re.sub(r"##\s*\[(.*?)\]", r"## \1", text)
    return text

def create_pdf(markdown_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    clean_text = markdown_text.encode('latin-1', 'replace').decode('latin-1')
    lines = clean_text.split('\n')
    
    for line in lines:
        if line.startswith("## "):
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, line.replace("## ", ""), ln=True)
            pdf.ln(2)
        elif line.startswith("**") and "**" in line[2:]:
            pdf.set_font("Arial", "B", 11)
            pdf.multi_cell(0, 8, line.replace("**", ""))
        elif line.startswith("---"):
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)
        else:
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, line)
            pdf.ln(1)
            
    return pdf.output(dest='S')

def encode_image_to_base64(pil_image):
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def extract_images_from_notebook(notebook_path):
    images = []
    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        for cell in nb.cells:
            if 'outputs' in cell:
                for output in cell.outputs:
                    if hasattr(output, 'data') and 'image/png' in output.data:
                        try:
                            img_data = base64.b64decode(output.data['image/png'])
                            img = Image.open(BytesIO(img_data))
                            img.thumbnail((512, 512)) 
                            images.append(img)
                            if len(images) >= MAX_IMAGES: return images
                        except: continue
    except: pass
    return images

def parse_notebook(file_path):
    content = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                content.append(f"[MD]: {cell.source}")
            elif cell.cell_type == 'code':
                content.append(f"[CODE]:\n{cell.source}")
                if 'outputs' in cell:
                    for output in cell.outputs:
                        if output.output_type == 'stream':
                            content.append(f"[OUT]: {output.text}")
                        elif output.output_type == 'execute_result':
                             if 'text/plain' in output.data:
                                content.append(f"[RES]: {output.data['text/plain']}")
    except: return "[Error parsing notebook]"
    return "\n".join(content)

@st.cache_data(show_spinner=False)
def process_repository(repo_url):
    temp_dir = tempfile.mkdtemp()
    extracted_images = []
    repo_content = []
    file_count = 0
    try:
        Repo.clone_from(repo_url, temp_dir)
        for root, dirs, files in os.walk(temp_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for file in files:
                if file in IGNORE_FILES: continue
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                if ext in IGNORE_EXTENSIONS: continue
                rel_path = os.path.relpath(file_path, temp_dir)
                if ext == '.ipynb':
                    text_content = parse_notebook(file_path)
                    if len(extracted_images) < MAX_IMAGES:
                        extracted_images.extend(extract_images_from_notebook(file_path))
                elif os.path.getsize(file_path) < MAX_FILE_SIZE:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            text_content = f.read()
                    except: text_content = "[Read Error]"
                else: text_content = "[Skipped: File too large]"

                repo_content.append(f"\n\n--- FILE: {rel_path} ---\n{text_content}")
                file_count += 1
        return "\n".join(repo_content), extracted_images[:MAX_IMAGES], file_count
    except Exception as e: return None, None, str(e)
    finally: shutil.rmtree(temp_dir, ignore_errors=True)

def get_groq_client(api_key):
    return Groq(api_key=api_key)

# --- GENERATION FUNCTIONS ---

def generate_tech_summary(client, text_context):
    """Generates ONLY the Technical Deep Dive (Recruiter View)."""
    system_prompt = """
    You are a Lead Software Architect.
    TASK: Analyze the code and generate a 'Technical Deep Dive' cheat sheet for recruiters.
    OUTPUT FORMAT:
    ### 🛠️ Technical Deep Dive
    **Architecture Style:** (e.g., MVC, RAG, ETL Pipeline)
    **Core Libraries:** (List top 5)
    **Code Complexity:** (Low/Medium/High)
    **Cloud/Infra:** (Docker, AWS, Streamlit, etc.)
    **Key Algorithms:** - (Bullet point 1)
    - (Bullet point 2)
    """
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze this repository code:\n{text_context[:85000]}"}
    ]

    try:
        completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=1024, 
            stream=False,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error generating Tech Summary: {str(e)}"

def generate_full_report(client, text_context, images):
    """Generates ONLY the Professional Report (Manager View)."""
    system_prompt = """
    You are a Lead Data Scientist.
    TASK: Generate a Professional Portfolio Report.
    
    1. METADATA BLOCK
    - CRITICAL: Ensure there is a FULL BLANK LINE between Authors, Date, Tech Stack, and Business Value.
    - Format exactly like this:
    
    ## [Project Name]
    
    **Authors:** [Author Name]
    
    **Date:** [Date]
    
    **Tech Stack:** [Comma separated list]
    
    **Business Value:** [1 sentence summary]
    
    ---
    
    2. REPORT BODY
    ## 1. Executive Summary
    - High-level overview.
    - Summary Table (Metric | Details).
    
    ## 2. Business Problem & Objectives
    ## 3. Data Overview / System Architecture
    ## 4. Exploratory Analysis / Logic Flow
    ## 5. Methodology & Algorithms
    ## 6. Results & Performance
    ## 7. Explainability / Inner Workings
    ## 8. Implementation Pipeline
    ## 9. Recommendations
    ## 10. Conclusion & Future Work
    
    Constraint: Use professional Markdown. Do not output raw code blocks.
    """
    
    # TYPE FIX: Declare that user_content can be EITHER a List OR a String
    user_content: Union[List[Dict[str, Any]], str]

    if images:
        model_id = "meta-llama/llama-4-scout-17b-16e-instruct"
        
        user_content = [
            {"type": "text", "text": f"Analyze this repository code:\n{text_context[:85000]}"},
            {"type": "text", "text": "Visuals found in notebooks:"}
        ]
        
        for img in images:
            b64_str = encode_image_to_base64(img)
            # This is now valid because we defined List[Dict[str, Any]] as part of the Union
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64_str}"}
            })
    else:
        model_id = "llama-3.3-70b-versatile"
        # This is now valid because we defined 'str' as part of the Union
        user_content = f"Analyze this repository code:\n{text_context[:85000]}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]

    try:
        completion = client.chat.completions.create(
            messages=messages,
            model=model_id, 
            temperature=0.3,
            max_tokens=4096, 
            stream=False,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error generating Report: {str(e)}"

# --- MAIN UI ---

if "report_data" not in st.session_state:
    st.session_state.report_data = None
if "tech_data" not in st.session_state:
    st.session_state.tech_data = None

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2103/2103633.png", width=60)
    st.title("Settings")
    api_key_input = st.text_input("🔑 Groq API Key", type="password")
    st.info("Template: Professional Report 2026")

col1, col2 = st.columns([0.8, 0.2])
with col1:
    st.title("Repo2Report ⚡")
    st.markdown("#### The AI-Powered Data Science Auditor")

input_col, btn_col = st.columns([0.85, 0.15])
with input_col:
    repo_url = st.text_input("", placeholder="🔗 Paste GitHub Repository URL...", label_visibility="collapsed")
with btn_col:
    analyze_btn = st.button("Generate")

if analyze_btn:
    final_key = api_key_input if api_key_input else GROQ_API_KEY
    if not repo_url or not final_key:
        st.toast("⚠️ Missing URL or API Key!", icon="⚠️")
    else:
        client = get_groq_client(final_key)
        
        with st.status("🚀 Analyzing Repository...", expanded=True) as status:
            context, images, count = process_repository(repo_url)
            
            if context:
                status.write(f"✅ Found {count} files & {len(images) if images else 0} charts.")
                if len(context) > 90000: status.warning("⚠️ Large Repo: Truncating context.")
                
                status.write("🛠️ Generating Technical Deep Dive...")
                tech_part = generate_tech_summary(client, context)
                
                status.write("📄 Writing Professional Report...")
                report_part = generate_full_report(client, context, images)
                
                report_part = clean_report_text(report_part)
                
                st.session_state.tech_data = tech_part
                st.session_state.report_data = report_part
                
                status.update(label="Analysis Complete!", state="complete", expanded=False)
            else:
                status.update(label="Analysis Failed", state="error")
                st.error(f"Failed to process repo: {count}")

if st.session_state.report_data:
    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🛠️ Technical Deep Dive", "📄 Generated Report"])
    
    with tab1:
        if st.session_state.tech_data and st.session_state.tech_data.strip():
            with st.container(border=True):
                st.markdown(st.session_state.tech_data)
        else:
            st.info("No technical details generated.")
            
    with tab2:
        if st.session_state.report_data and st.session_state.report_data.strip():
            with st.container(border=True):
                st.markdown(st.session_state.report_data)
                
            st.markdown("<br>", unsafe_allow_html=True)
            col_d1, col_d2, col_d3 = st.columns([1, 1, 3])
            
            with col_d1:
                st.download_button(
                    label="📥 Download .MD",
                    data=st.session_state.report_data,
                    file_name="report.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col_d2:
                pdf_output = create_pdf(st.session_state.report_data)
                if isinstance(pdf_output, str):
                    pdf_output = pdf_output.encode('latin-1')
                    
                st.download_button(
                    label="📄 Download .PDF",
                    data=pdf_output,
                    file_name="report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )