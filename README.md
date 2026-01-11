# Repo2Report (R2R) 📊

**Automated "Code-to-Insight" Data Science Report Generator**

[![Status](https://img.shields.io/badge/Status-Active-success.svg)]()
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)]()

## 📖 Overview
Repo2Report is an AI-powered tool designed to bridge the gap between technical code repositories and business stakeholders. It ingests raw GitHub repositories (Jupyter Notebooks, Python scripts, Markdown), analyzes the code structure and outputs, and generates a professional **"Industry 2026" Standard Data Science Report** using Large Language Models (LLMs).

## ✨ Key Features
* **Automated Ingestion:** Clones and parses GitHub repositories instantly.
* **Notebook Intelligence:** Extracts executed outputs from `.ipynb` files to validate results without re-running code.
* **Obsidian-Ready Output:** Generates reports in clean Markdown, ready for your knowledge base.
* **Privacy-First:** Filters out PII and sensitive data before processing.
* **Context-Aware:** Uses specific "Industry 2026" templates for Executive Summaries, Methodology, and Ethics.

## 🚀 Quick Start

### Prerequisites
* Python 3.10+
* Google Gemini API Key (or OpenAI equivalent)

### Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/yourusername/repo2report.git](https://github.com/yourusername/repo2report.git)
    
    cd repo2report
    ```

2.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables**
    Create a `.env` file in the root directory:
    ```env
    GOOGLE_API_KEY=your_api_key_here
    ```

### Usage

Run the Streamlit application:
```bash
streamlit run app.py
```

1. Open the local URL provided (usually http://localhost:8501).

2. Paste a target GitHub Repository URL.

3. Click **Generate Report**.

4. Download the .md file.

## 🏗 Architecture
The system follows a Retrieve-Read-Report pipeline:

1. **Ingestion Agent**: gitpython handles cloning; custom logic filters non-text files.

2. **Parsing Layer**: nbformat flattens notebooks; AST analysis identifies libraries.

3. **LLM Critic**: Generates section-specific insights (Methodology, Risks, Results).

4. **UI/UX**: Streamlit provides the frontend interface.

## 🤝 Contributing
Please read `CONTRIBUTING.md` for details on our code of conduct, and the process for submitting pull requests.

## 📜 License
This project is licensed under the MIT License - see the LICENSE file for details.

## 🔮 Future Scope
Vision Support: Parsing actual graphs from notebook outputs using Multimodal LLMs.

PDF Export: Direct conversion from Markdown to PDF.