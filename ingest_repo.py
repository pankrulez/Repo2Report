import os
import shutil
import tempfile
import git
import nbformat
from typing import List, Dict

# CONFIGURATION
# Files to ignore to save context window space
IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', 'venv', 'env', '.idea', '.vscode'}
IGNORE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.pkl', '.h5', '.parquet', '.zip'}
# Max file size to read (approx 100KB) to prevent massive datasets from crashing the prompt
MAX_FILE_SIZE = 100 * 1024 

def clone_repository(repo_url: str) -> str:
    """Clones the repo into a temporary directory and returns the path."""
    temp_dir = tempfile.mkdtemp()
    print(f"Cloning {repo_url} into {temp_dir}...")
    try:
        git.Repo.clone_from(repo_url, temp_dir)
        return temp_dir
    except Exception as e:
        print(f"Error cloning repo: {e}")
        return ""

def parse_notebook(file_path: str) -> str:
    """
    Reads a Jupyter Notebook and converts it to a flat string.
    Crucially, it extracts OUTPUT cells so the LLM knows what the code actually produced.
    """
    content = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
            
        for cell in nb.cells:
            if cell.cell_type == 'markdown':
                content.append(f"[MARKDOWN]: {cell.source}")
            elif cell.cell_type == 'code':
                content.append(f"[CODE]:\n{cell.source}")
                # extracting outputs (text streams or error messages)
                if 'outputs' in cell:
                    for output in cell.outputs:
                        if output.output_type == 'stream':
                            content.append(f"[OUTPUT]: {output.text}")
                        elif output.output_type == 'execute_result':
                            # This often contains dataframe summaries
                            if 'text/plain' in output.data:
                                content.append(f"[RESULT]: {output.data['text/plain']}")
                        elif output.output_type == 'error':
                            content.append(f"[ERROR]: {output.evalue}")
    except Exception as e:
        return f"[Error parsing notebook: {str(e)}]"
    
    return "\n".join(content)

def read_text_file(file_path: str) -> str:
    """Reads standard text-based code files."""
    if os.path.getsize(file_path) > MAX_FILE_SIZE:
        return "[CONTENT SKIPPED: File too large]"
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"[Error reading file: {str(e)}]"

def build_repo_context(repo_path: str) -> str:
    """Walks the repo and builds the single mega-prompt string."""
    repo_content = []
    
    for root, dirs, files in os.walk(repo_path):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            _, ext = os.path.splitext(file)
            
            if ext in IGNORE_EXTENSIONS:
                continue

            # Header for each file so LLM knows boundaries
            file_header = f"\n\n{'='*20}\nFILE: {rel_path}\n{'='*20}\n"
            
            if ext == '.ipynb':
                file_content = parse_notebook(file_path)
            else:
                file_content = read_text_file(file_path)
                
            repo_content.append(file_header + file_content)
            
    return "\n".join(repo_content)

def main(repo_url):
    local_path = clone_repository(repo_url)
    if local_path:
        try:
            print("Processing repository...")
            full_context = build_repo_context(local_path)
            
            # Save or Print the Output
            # In a real app, you would pass 'full_context' to your LLM API here.
            output_filename = "repo_context.txt"
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(full_context)
            
            print(f"Success! Repository context saved to {output_filename}")
            print(f"Total Character Count: {len(full_context)}")
            
        finally:
            # Cleanup
            shutil.rmtree(local_path)

# Example Usage
if __name__ == "__main__":
    # Replace with a real GitHub URL to test
    repo = input("Enter GitHub URL: ")
    main(repo)