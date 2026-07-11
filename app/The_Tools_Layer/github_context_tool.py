"""
Advanced Context Extraction Layer for Sentinel-Agent.
Surgically extracts culprit files, function definitions, global code dependencies, 
and historical git commit diffs via the official GitHub REST API.
"""

import os
import base64
import re
import ast
import logging
import httpx
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class GitHubContextOrchestrator:
    def __init__(self):
        """
        Initializes the GitHub API client using credentials stored in the .env file.
        """
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = os.getenv("GITHUB_OWNER")
        self.repo = os.getenv("GITHUB_REPO")
        
        if not self.token or not self.owner or not self.repo:
            raise ValueError(
                "CRITICAL: Missing GitHub configurations in .env file. "
                "Ensure GITHUB_TOKEN, GITHUB_OWNER, and GITHUB_REPO are set."
            )
            
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"

    def fetch_file_content(self, file_path: str) -> str:
        """
        Pulls the current raw content of the target file from the repository.
        """
        url = f"{self.base_url}/contents/{file_path}"
        try:
            with httpx.Client() as client:
                response = client.get(url, headers=self.headers)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("encoding") == "base64":
                        return base64.b64decode(data["content"]).decode("utf-8")
                    return data.get("content", "")
                else:
                    logger.error(f"GitHub contents API returned status {response.status_code} for {file_path}")
                    return f"// Error: Unable to fetch file content. Status code {response.status_code}"
        except Exception as e:
            logger.error(f"Exception fetching file content for {file_path}: {e}")
            return f"// Exception occurred while fetching content: {str(e)}"

    def extract_function_names(self, source_code: str) -> List[str]:
        """
        Uses Python's native AST parser to extract all local function definitions.
        Falls back to regex if the target file uses JavaScript/TypeScript formatting.
        """
        if not source_code or source_code.startswith("// Error"):
            return []
        try:
            tree = ast.parse(source_code)
            return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        except SyntaxError:
            # Fallback regex search for JS/TS function styles
            return re.findall(r"function\s+([a-zA-Z0-9_]+)", source_code)

    def find_global_dependencies(self, function_name: str) -> List[str]:
        """
        Leverages GitHub's Global Code Search API to identify every other file
        in a massive codebase that calls or references the target function.
        """
        search_url = f"https://api.github.com/search/code?q={function_name}+repo:{self.owner}/{self.repo}"
        dependent_files = []
        
        try:
            with httpx.Client() as client:
                response = client.get(search_url, headers=self.headers)
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    for item in items:
                        dependent_files.append(item["path"])
                elif response.status_code == 403:
                    logger.warning("GitHub Search API rate-limited. Skipping dependency exploration branch.")
        except Exception as e:
            logger.error(f"Exception during GitHub code search for {function_name}: {e}")
            
        return list(set(dependent_files))  # Deduplicate paths

    def fetch_recent_timeline_context(self, file_path: str, per_page: int = 3) -> List[Dict[str, Any]]:
        """
        Pulls a rolling history window of recent commits touching a file, 
        extracting the exact line diffs to catch hidden regression bugs.
        """
        url = f"{self.base_url}/commits?path={file_path}&per_page={per_page}"
        timeline_history = []

        try:
            with httpx.Client() as client:
                response = client.get(url, headers=self.headers)
                if response.status_code == 200:
                    commits = response.json()
                    
                    for commit in commits:
                        sha = commit["sha"]
                        author = commit["commit"]["author"]["name"]
                        message = commit["commit"]["message"]
                        date = commit["commit"]["author"]["date"]
                        
                        # Fetch the concrete code additions/deletions (diff patch) for this SHA
                        diff_url = f"{self.base_url}/commits/{sha}"
                        diff_response = client.get(diff_url, headers=self.headers)
                        
                        patch_diff = ""
                        if diff_response.status_code == 200:
                            files_changed = diff_response.json().get("files", [])
                            for f in files_changed:
                                if f.get("filename") == file_path:
                                    patch_diff = f.get("patch", "// No structural line changes recorded.")
                        
                        timeline_history.append({
                            "sha": sha[:7],
                            "date": date,
                            "author": author,
                            "message": message,
                            "code_diff_applied": patch_diff
                        })
        except Exception as e:
            logger.error(f"Failed to fetch historical timeline for {file_path}: {e}")
            
        return timeline_history

    def compile_surgical_context(self, suspect_file: str) -> Dict[str, Any]:
        """
        Master Orchestrator: Combines targeted retrieval, functional mapping, 
        and timeline regression analysis into a high-density AI context payload.
        """
        logger.info(f"🔍 Executing dynamic deep-context extraction loop for: {suspect_file}")
        
        # 1. Fetch current code state
        source_code = self.fetch_file_content(suspect_file)
        
        # 2. Fetch recent git timeline for regression analysis
        timeline = self.fetch_recent_timeline_context(suspect_file, per_page=3)
        
        # 3. Analyze what functions live here
        functions = self.extract_function_names(source_code)
        
        # 4. Scan the repo for dependent architectural nodes
        global_deps = []
        # Cap at first 2 functions to protect GitHub API search quotas
        for func in functions[:2]:
            global_deps.extend(self.find_global_dependencies(func))
            
        # Deduplicate and remove the source file itself from the dependencies array
        clean_deps = list(set([d for d in global_deps if d != suspect_file]))
        
        return {
            "target_file": suspect_file,
            "source_code": source_code,
            "timeline_history": timeline,
            "global_dependencies": clean_deps
        }