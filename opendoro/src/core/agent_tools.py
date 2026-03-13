import os
import json
import glob
import requests
import pathlib
import subprocess
import sys
from datetime import datetime
from bs4 import BeautifulSoup
from src.core.skill_manager import SkillManager


def _get_similar_files_suggestion(file_path, project_dir):
    similar_files = glob.glob(os.path.join(project_dir, '**', f'*{os.path.basename(file_path)}*'), recursive=True)
    similar_names = [os.path.relpath(f, project_dir) for f in similar_files[:5]]
    if similar_names:
        return f" 相似文件: {', '.join(similar_names)}"
    return ""


def _format_permission_error(abs_path, project_dir):
    return json.dumps({
        "status": "error",
        "message": f"Permission denied: 只能访问项目目录 '{project_dir}' 内的文件。当前路径 '{abs_path}' 超出允许范围。",
        "allowed_dir": project_dir
    }, ensure_ascii=False)


def _format_file_not_found_error(file_path, project_dir):
    suggestion = _get_similar_files_suggestion(file_path, project_dir)
    return json.dumps({
        "status": "error",
        "message": f"File not found: {file_path}.{suggestion}",
        "suggestion": "请检查文件路径是否正确"
    }, ensure_ascii=False)

# Tool Schemas for OpenAI
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image based on a text prompt using compatible API and save it locally.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The description of the image to generate."
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_baidu",
            "description": "Search for real-time information on the internet using Baidu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search keywords."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_bing",
            "description": "Search for real-time information using Bing. Optimized for Chinese users and general queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search keywords."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "visit_webpage",
            "description": "Visit a specific URL and extract its text content. Use this to read full articles, check real-time data from specific sites, or browse pages found via search.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to visit."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_expression",
            "description": "Change the facial expression of the Live2D model. Use this to reflect the mood or emotion of the response.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression_name": {
                        "type": "string",
                        "description": "The name of the expression to set (e.g.)."
                    }
                },
                "required": ["expression_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_pet_attribute",
            "description": "Modify the pet's attributes. Use this when interacting with Doro (feeding, playing, cleaning, resting, etc.). Supports both legacy format and new semantic format.",
            "parameters": {
                "type": "object",
                "properties": {
                    "interaction": {
                        "type": "string",
                        "enum": [
                            "feed_snack", "feed_meal", "feed_feast", "feed_bad",
                            "play_gentle", "play_fun", "play_exhausting",
                            "clean_wipe", "clean_wash",
                            "rest_nap", "rest_sleep",
                            "pet_affection", "scold", "comfort"
                        ],
                        "description": "Semantic interaction type. Options: feed_snack(零食), feed_meal(正餐), feed_feast(大餐), feed_bad(变质食物); play_gentle(轻度), play_fun(愉快), play_exhausting(剧烈); clean_wipe(擦拭), clean_wash(洗澡); rest_nap(小憩), rest_sleep(沉睡); pet_affection(抚摸), scold(责备), comfort(安慰)."
                    },
                    "intensity": {
                        "type": "string",
                        "enum": ["light", "moderate", "heavy"],
                        "description": "Interaction intensity level. Only applies when using legacy action format. light=0.5x, moderate=1.0x, heavy=1.5x."
                    },
                    "attribute": {
                        "type": "string",
                        "enum": ["hunger", "mood", "cleanliness", "energy"],
                        "description": "[Legacy] The attribute to modify. Use 'interaction' instead for new format."
                    },
                    "action": {
                        "type": "string",
                        "enum": ["feed", "play", "clean", "rest"],
                        "description": "[Legacy] The interaction action. Use 'interaction' instead for new format."
                    }
                },
                "anyOf": [
                    {"required": ["interaction"]},
                    {"required": ["attribute", "action"]}
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python_script",
            "description": "Run a Python script from the local filesystem and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path of the python file to run (e.g., 'plugin/hello.py' or 'src/utils.py')."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file in the local filesystem. Overwrites if exists. Creates directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to write (e.g., 'plugin/my_script.py', 'index.html')."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file."
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the content of a file from the local filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative path to the file to read."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files and directories in a specific directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "The path to the directory to list (defaults to current directory)."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search for files by name pattern (glob) in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The glob pattern to match (e.g., '*.py', 'src/**/*.ts')."
                    },
                    "dir_path": {
                        "type": "string",
                        "description": "The root directory to search in (defaults to current directory)."
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by searching for specific content and replacing it with new content. Supports exact match replacement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to edit."
                    },
                    "search": {
                        "type": "string",
                        "description": "The exact text to search for in the file."
                    },
                    "replace": {
                        "type": "string",
                        "description": "The text to replace the search content with."
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "If true, replace all occurrences. Default is false (replace first occurrence only)."
                    },
                    "fuzzy_match": {
                        "type": "boolean",
                        "description": "是否启用模糊匹配（忽略空格和制表符差异）。当精确匹配失败时可尝试启用。"
                    },
                    "context_before": {
                        "type": "string",
                        "description": "目标内容前的上下文（帮助定位重复内容）"
                    },
                    "context_after": {
                        "type": "string",
                        "description": "目标内容后的上下文"
                    }
                },
                "required": ["file_path", "search", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "insert_at_line",
            "description": "Insert content at a specific line number in a file. Lines are 1-indexed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to modify."
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "The line number where to insert content (1-indexed). Use 0 to prepend at the beginning."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to insert."
                    }
                },
                "required": ["file_path", "line_number", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_lines",
            "description": "Delete a range of lines from a file. Lines are 1-indexed and inclusive.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to modify."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "The starting line number to delete (1-indexed, inclusive)."
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "The ending line number to delete (1-indexed, inclusive). If not specified, only the start_line is deleted."
                    }
                },
                "required": ["file_path", "start_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_in_file",
            "description": "在文件中搜索内容并返回精确位置信息。支持正则表达式模式。返回匹配行的行号、内容和上下文。用于定位内容后再进行精确编辑。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "要搜索的文件路径"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "搜索模式（支持正则表达式）"
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "返回匹配行前后的上下文行数（默认2行）",
                        "default": 2
                    }
                },
                "required": ["file_path", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "install_agent_skill",
            "description": "Install an agent skill from various sources: GitHub (owner/repo), GitLab URL, zip URL, or local path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "The source to install from. Supports: GitHub (owner/repo or full URL), GitLab URL, zip file URL, or local directory path."
                    },
                    "skill_name": {
                        "type": "string",
                        "description": "Optional custom name for the skill. If not provided, name will be detected from SKILL.md or manifest.json."
                    }
                },
                "required": ["source"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_agent_skills",
            "description": "List all installed agent skills with their descriptions and types.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_skill_content",
            "description": "Get the full content/instructions of a document-type skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The name of the skill to get content for."
                    }
                },
                "required": ["skill_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_agent_skill",
            "description": "Remove an installed agent skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "The name of the skill to remove."
                    }
                },
                "required": ["skill_name"]
            }
        }
    }
]

def visit_webpage(client=None, url="", **kwargs):
    """
    Visits a webpage and extracts its text content.
    """
    try:
        # Handle case where url might be passed as first positional arg
        if isinstance(client, str) and not url:
             url = client
             
        if not url:
             return json.dumps({"status": "error", "message": "URL parameter is required."})

        # Basic validation
        if not url.startswith("http"):
            url = "https://" + url

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Use explicit encoding if provided, else let requests/chardet guess
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove unwanted tags
        for script in soup(["script", "style", "nav", "footer", "header", "meta", "noscript", "svg", "iframe", "ad"]):
            script.extract()
            
        text = soup.get_text(separator="\n", strip=True)
        
        # Limit content length to avoid overflowing context
        # 4000 chars is roughly 1-2k tokens depending on language
        content = text[:4000] + "..." if len(text) > 4000 else text
        
        if not content:
            content = "No readable text found on this page."
            
        return json.dumps({
            "status": "success",
            "message": f"Successfully visited {url}",
            "content": content
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Failed to visit webpage: {str(e)}"})

def search_baidu(client=None, query="", **kwargs):
    """
    Searches Baidu for the given query and returns the top results.
    """
    try:
        # Handle case where query might be passed as first positional arg if client is omitted
        if isinstance(client, str) and not query:
             query = client
             
        if not query:
             return json.dumps({"status": "error", "message": "Query parameter is required."})

        url = "https://www.baidu.com/s"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        params = {"wd": query}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Baidu search results are typically in div with class 'result c-container' or similar
        # We look for common patterns
        
        for item in soup.select('.result.c-container, .result-op.c-container'):
            try:
                title_elem = item.select_one("h3")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link = title_elem.select_one("a")["href"] if title_elem.select_one("a") else ""
                
                # Abstract/Snippet
                abstract = ""
                # Try multiple common selectors for Baidu snippets
                abstract_elem = (
                    item.select_one(".c-abstract") or 
                    item.select_one(".content-right_8Zs40") or 
                    item.select_one(".c-span18") or
                    item.select_one(".c-font-normal") or
                    item.select_one("div[class*='content']")
                )
                
                if abstract_elem:
                    abstract = abstract_elem.get_text(strip=True)
                else:
                    # Fallback: Get all text and remove title
                    full_text = item.get_text(strip=True)
                    if title in full_text:
                        abstract = full_text.replace(title, "", 1).strip()
                    else:
                        abstract = full_text
                
                if title and link:
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": abstract
                    })
                    
                if len(results) >= 5: # Limit to top 5
                    break
            except Exception:
                continue
                
        if not results:
            return json.dumps({"status": "success", "message": "No results found.", "results": []})
            
        return json.dumps({
            "status": "success", 
            "message": f"Found {len(results)} results.", 
            "results": results
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def search_bing(client=None, query="", **kwargs):
    """
    Searches Bing (CN) for the given query and returns the top results.
    """
    try:
        # Handle query positional arg
        if isinstance(client, str) and not query:
             query = client
             
        if not query:
             return json.dumps({"status": "error", "message": "Query parameter is required."})

        # Use cn.bing.com for better accessibility in China
        url = "https://cn.bing.com/search"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        }
        params = {"q": query}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Bing CN results: <li class="b_algo">
        for item in soup.select('.b_algo'):
            try:
                title_elem = item.select_one("h2 a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link = title_elem["href"]
                
                snippet_elem = item.select_one(".b_caption p")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if title and link:
                    results.append({
                        "title": title,
                        "link": link,
                        "snippet": snippet
                    })
                    
                if len(results) >= 5:
                    break
            except Exception:
                continue
                
        if not results:
            return json.dumps({"status": "success", "message": "No results found on Bing.", "results": []})
            
        return json.dumps({
            "status": "success", 
            "message": f"Found {len(results)} results from Bing.", 
            "results": results
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})



def generate_image(client, prompt, base_url=None, api_key=None, model=None):
    """
    Generates an image using OpenAI client or custom API and saves it locally.
    """
    try:
        print(f"[AgentTools] Generating image. Model: {model}, BaseURL: {base_url}")
        image_url = ""
        
        # Use custom API if configured
        if base_url and api_key:
            # Assume OpenAI-compatible Image Generation API
            # POST /images/generations
            endpoint = f"{base_url.rstrip('/')}/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": model if model else "dall-e-3",
                "prompt": prompt,
            }
            
            # Special handling for SiliconFlow or similar APIs that deviate from OpenAI spec
            if "siliconflow" in base_url.lower():
                data["image_size"] = "1024x1024"
                data["batch_size"] = 1
            elif "ai.gitee.com" in base_url.lower():
                data["size"] = "1024x1024"
                data["guidance_scale"] = 5
                data["num_inference_steps"] = 30
            else:
                # Standard OpenAI parameters
                data["n"] = 1
                data["size"] = "1024x1024"
            
            response = requests.post(endpoint, headers=headers, json=data, timeout=120)
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # Include response body in error message for debugging
                return json.dumps({"status": "error", "message": f"{str(e)} - Response: {response.text}"})
                
            res_json = response.json()
            
            # SiliconFlow might return 'images' list instead of 'data'
            # But based on docs/search result 4, it returns: { "images": [ { "url": "..." } ] }
            # OpenAI returns: { "data": [ { "url": "..." } ] }
            
            if "data" in res_json and len(res_json["data"]) > 0:
                image_url = res_json["data"][0]["url"]
            elif "images" in res_json and len(res_json["images"]) > 0:
                image_url = res_json["images"][0]["url"]
            else:
                return json.dumps({"status": "error", "message": f"Invalid response from custom API: {res_json}"})

        else:
            # Fallback to default client (DALL-E 3)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
        
        # Download the image
        # Note: If the custom API returns a local path (e.g. file://), handle it?
        # Usually APIs return http URL.
        
        img_data = requests.get(image_url).content
        
        # Ensure a directory exists for generated images
        save_dir = os.path.join(os.getcwd(), "generated_images")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gen_{timestamp}.png"
        file_path = os.path.join(save_dir, filename)
        
        with open(file_path, 'wb') as handler:
            handler.write(img_data)
        
        # Convert to URI for Markdown (handles Windows paths and spaces)
        file_uri = pathlib.Path(file_path).as_uri()

        # Return Markdown image syntax so UI can detect it
        return json.dumps({
            "status": "success", 
            "message": f"Image generated successfully.\n![Generated Image]({file_uri})",
            "image_path": file_path,
            "image_url": image_url
        })
        
    except Exception as e:
        error_msg = str(e)
        # Check for SiliconFlow/Model Not Found errors
        if "1211" in error_msg or "Model does not exist" in error_msg or "400" in error_msg:
             # Provide a helpful hint
             return json.dumps({
                 "status": "error", 
                 "message": f"Image generation failed. Provider returned error: {error_msg}. \nHint: Check if the model '{model if model else 'dall-e-3'}' is valid for your provider. If using SiliconFlow, ensure you configured a specific image model (e.g. 'stabilityai/stable-diffusion-3-5-large') in Settings > Image."
             }, ensure_ascii=False)
        return json.dumps({"status": "error", "message": str(e)})


def edit_file(client=None, file_path="", search="", replace="", replace_all=False, fuzzy_match=False, context_before="", context_after="", **kwargs):
    """
    Edit a file by searching for specific content and replacing it with new content.
    Supports fuzzy matching and context-based positioning.
    """
    import re
    try:
        if isinstance(client, str) and not file_path:
            file_path = client
        
        if not file_path:
            return json.dumps({"status": "error", "message": "File path is required."})
        if not search:
            return json.dumps({"status": "error", "message": "Search content is required."})
        
        abs_path = os.path.abspath(file_path)
        project_dir = os.getcwd()
        
        if not os.path.exists(abs_path):
            return _format_file_not_found_error(file_path, project_dir)
        
        if not abs_path.startswith(project_dir):
            return _format_permission_error(abs_path, project_dir)
        
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        def find_with_context(content, search, context_before, context_after):
            if not context_before and not context_after:
                return -1
            
            occurrences = []
            start = 0
            while True:
                pos = content.find(search, start)
                if pos == -1:
                    break
                occurrences.append(pos)
                start = pos + 1
            
            if len(occurrences) <= 1:
                return -1
            
            for pos in occurrences:
                context_start = max(0, pos - len(context_before) - 100) if context_before else pos
                context_end = min(len(content), pos + len(search) + len(context_after) + 100) if context_after else pos + len(search)
                surrounding = content[context_start:context_end]
                
                if context_before and context_before in surrounding[:pos - context_start + len(search) + 50]:
                    if context_after and context_after in surrounding:
                        return pos
                    elif not context_after:
                        return pos
                elif not context_before and context_after and context_after in surrounding:
                    return pos
            
            return -1
        
        context_pos = find_with_context(content, search, context_before, context_after)
        
        if search in content:
            if context_pos != -1 and not replace_all:
                new_content = content[:context_pos] + replace + content[context_pos + len(search):]
                count = 1
            elif replace_all:
                new_content = content.replace(search, replace)
                count = content.count(search)
            else:
                new_content = content.replace(search, replace, 1)
                count = 1
        elif fuzzy_match:
            normalized_content = re.sub(r'[ \t]+', ' ', content)
            normalized_search = re.sub(r'[ \t]+', ' ', search)
            
            if normalized_search in normalized_content:
                norm_pos = normalized_content.find(normalized_search)
                orig_pos = 0
                norm_idx = 0
                
                for i, char in enumerate(content):
                    if norm_idx == norm_pos:
                        orig_pos = i
                        break
                    if char in ' \t':
                        if norm_idx < len(normalized_content) and normalized_content[norm_idx] == ' ':
                            norm_idx += 1
                    else:
                        norm_idx += 1
                
                orig_end = orig_pos
                search_chars_consumed = 0
                for char in search:
                    if char in ' \t':
                        while orig_end < len(content) and content[orig_end] in ' \t':
                            orig_end += 1
                        search_chars_consumed += 1
                    else:
                        while orig_end < len(content) and content[orig_end] in ' \t':
                            orig_end += 1
                        if orig_end < len(content):
                            orig_end += 1
                        search_chars_consumed += 1
                
                while orig_end < len(content) and content[orig_end] in ' \t':
                    orig_end += 1
                
                new_content = content[:orig_pos] + replace + content[orig_end:]
                count = 1
            else:
                lines = content.split('\n')
                search_words = [w for w in search.lower().split()[:3] if len(w) > 2]
                similar_lines = []
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if any(word in line_lower for word in search_words):
                        similar_lines.append(f"Line {i+1}: {line.strip()[:100]}")
                
                if similar_lines:
                    return json.dumps({
                        "status": "error", 
                        "message": f"搜索内容未找到。文件中最相似的内容：\n" + "\n".join(similar_lines[:5])
                    }, ensure_ascii=False)
                else:
                    return json.dumps({
                        "status": "error", 
                        "message": f"搜索内容未找到，且未找到相似内容。请检查搜索文本是否正确。"
                    }, ensure_ascii=False)
        else:
            hint = "Try fuzzy_match=true for flexible matching."
            return json.dumps({
                "status": "error", 
                "message": f"Search content not found in file. Make sure to use the exact text including whitespace. {hint}"
            })
        
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return json.dumps({
            "status": "success", 
            "message": f"Replaced {count} occurrence(s) in {file_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def insert_at_line(client=None, file_path="", line_number=0, content="", **kwargs):
    """
    Insert content at a specific line number in a file.
    Lines are 1-indexed. Use 0 to prepend at the beginning.
    """
    try:
        if isinstance(client, str) and not file_path:
            file_path = client
        
        if not file_path:
            return json.dumps({"status": "error", "message": "File path is required."})
        
        abs_path = os.path.abspath(file_path)
        project_dir = os.getcwd()
        
        if not os.path.exists(abs_path):
            return _format_file_not_found_error(file_path, project_dir)
        
        if not abs_path.startswith(project_dir):
            return _format_permission_error(abs_path, project_dir)
        
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if not content.endswith("\n"):
            content += "\n"
        
        if line_number < 0:
            line_number = 0
        elif line_number > len(lines):
            line_number = len(lines)
        
        lines.insert(line_number, content)
        
        with open(abs_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return json.dumps({
            "status": "success", 
            "message": f"Inserted content at line {line_number} in {file_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def delete_lines(client=None, file_path="", start_line=1, end_line=None, **kwargs):
    """
    Delete a range of lines from a file.
    Lines are 1-indexed and inclusive.
    """
    try:
        if isinstance(client, str) and not file_path:
            file_path = client
        
        if not file_path:
            return json.dumps({"status": "error", "message": "File path is required."})
        
        if start_line < 1:
            return json.dumps({"status": "error", "message": "Start line must be 1 or greater."})
        
        abs_path = os.path.abspath(file_path)
        project_dir = os.getcwd()
        
        if not os.path.exists(abs_path):
            return _format_file_not_found_error(file_path, project_dir)
        
        if not abs_path.startswith(project_dir):
            return _format_permission_error(abs_path, project_dir)
        
        with open(abs_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        if end_line is None:
            end_line = start_line
        
        if start_line > total_lines:
            return json.dumps({"status": "error", "message": f"Start line {start_line} exceeds file length ({total_lines} lines)."})
        
        if end_line > total_lines:
            end_line = total_lines
        
        deleted_count = end_line - start_line + 1
        del lines[start_line - 1:end_line]
        
        with open(abs_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        return json.dumps({
            "status": "success", 
            "message": f"Deleted {deleted_count} line(s) ({start_line}-{end_line}) from {file_path}"
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def find_in_file(client=None, file_path="", pattern="", context_lines=2, **kwargs):
    """
    在文件中搜索内容并返回精确位置信息。
    """
    import re
    try:
        if isinstance(client, str) and not file_path:
            file_path = client
        
        if not file_path:
            return json.dumps({"status": "error", "message": "File path is required."})
        if not pattern:
            return json.dumps({"status": "error", "message": "Pattern is required."})
        
        project_dir = os.getcwd()
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return _format_file_not_found_error(file_path, project_dir)
        
        if not os.path.isfile(abs_path):
            return json.dumps({"status": "error", "message": f"Path is not a file: {file_path}"})
        
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(abs_path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            except:
                return json.dumps({"status": "error", "message": "Failed to decode file content."})
        
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            if regex.search(line):
                start = max(0, i - context_lines - 1)
                end = min(len(lines), i + context_lines)
                context = "".join(lines[start:end])
                matches.append({
                    "line_number": i,
                    "line_content": line.rstrip('\n\r'),
                    "context": context.rstrip('\n\r')
                })
        
        if not matches:
            return json.dumps({
                "status": "info",
                "message": f"Pattern '{pattern}' not found in {file_path}",
                "matches": []
            })
        
        return json.dumps({
            "status": "success",
            "message": f"Found {len(matches)} match(es) in {file_path}",
            "matches": matches[:20]
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def write_file(client=None, file_path="", content="", **kwargs):
    """
    Writes content to a file in the local filesystem.
    Restricted to project directory for safety.
    """
    try:
        if isinstance(client, str) and not file_path:
             file_path = client
             
        if not file_path:
             return json.dumps({"status": "error", "message": "File path is required."})

        abs_path = os.path.abspath(file_path)
        project_dir = os.getcwd()
        
        if not abs_path.startswith(project_dir):
            return _format_permission_error(abs_path, project_dir)
        
        protected_dirs = [
            os.path.join(project_dir, "src", "core"),
        ]
        for protected in protected_dirs:
            if abs_path.startswith(protected):
                return json.dumps({"status": "error", "message": f"Permission denied: Cannot write to protected directory '{protected}'."})
        
        dir_name = os.path.dirname(abs_path)
        if not os.path.exists(dir_name):
             os.makedirs(dir_name)
             
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        return json.dumps({"status": "success", "message": f"File written to {file_path}"})
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def run_python_script(client=None, file_path="", **kwargs):
    """
    Runs a Python script from the local filesystem.
    Restricted to project directory for safety.
    """
    try:
        if isinstance(client, str) and not file_path:
             file_path = client

        if not file_path:
             return json.dumps({"status": "error", "message": "File path is required."})

        if not os.path.dirname(file_path) and not os.path.exists(file_path):
             plugin_path = os.path.join("plugin", file_path)
             if os.path.exists(plugin_path):
                 file_path = plugin_path
        
        abs_path = os.path.abspath(file_path)
        project_dir = os.getcwd()

        if not abs_path.startswith(project_dir):
            return _format_permission_error(abs_path, project_dir)

        protected_dirs = [
            os.path.join(project_dir, "src", "core"),
        ]
        for protected in protected_dirs:
            if abs_path.startswith(protected):
                return json.dumps({"status": "error", "message": f"Permission denied: Cannot run scripts from protected directory '{protected}'."})

        if not os.path.exists(abs_path):
            return _format_file_not_found_error(file_path, project_dir)

        # Run the script
        result = subprocess.run([sys.executable, abs_path], capture_output=True, text=False, timeout=30)
        
        def decode_bytes(b):
            try:
                # Try UTF-8 first (common for Python 3 scripts)
                return b.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    # Try system default (likely GBK on Windows)
                    return b.decode('gbk')
                except UnicodeDecodeError:
                    # Fallback
                    return b.decode('utf-8', errors='replace')

        output = decode_bytes(result.stdout)
        if result.stderr:
            output += "\nErrors:\n" + decode_bytes(result.stderr)
            
        return json.dumps({
            "status": "success", 
            "message": f"Script executed. Exit code: {result.returncode}",
            "output": output
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "error", "message": "Script execution timed out."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def read_file(client=None, file_path="", **kwargs):
    """
    Reads the content of a file from the local filesystem.
    """
    try:
        if isinstance(client, str) and not file_path:
             file_path = client
        
        if not file_path:
            return json.dumps({"status": "error", "message": "File path is required."})

        project_dir = os.getcwd()
        abs_path = os.path.abspath(file_path)
        
        if not os.path.exists(abs_path):
            return _format_file_not_found_error(file_path, project_dir)
            
        if not os.path.isfile(abs_path):
            return json.dumps({"status": "error", "message": f"Path is not a file: {file_path}"})
            
        # Try to read text
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(abs_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                 return json.dumps({"status": "error", "message": "Failed to decode file content (binary or unknown encoding)."})

        # Truncate if too long (e.g. > 100KB) to avoid context overflow
        MAX_CHARS = 100000 
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + f"\n... (truncated, total {len(content)} chars)"
            
        return json.dumps({
            "status": "success",
            "message": f"Read {len(content)} characters from {file_path}",
            "content": content
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def list_files(client=None, dir_path=".", **kwargs):
    """
    Lists files in a directory.
    """
    try:
        # Handle case where dir_path might be client if client is string
        if isinstance(client, str):
            # If client is string, it might be dir_path passed positionally
            # But wait, signature is list_files(client=None, dir_path=".", ...)
            # If called as list_files("some/path"), client="some/path", dir_path="."
            if client != "list_files": # careful check
                 dir_path = client
        
        target_dir = os.path.abspath(dir_path)
        
        if not os.path.exists(target_dir):
             return json.dumps({"status": "error", "message": f"Directory not found: {dir_path}"})
             
        items = os.listdir(target_dir)
        
        # Sort items: directories first, then files
        dirs = []
        files = []
        for item in items:
            full_path = os.path.join(target_dir, item)
            if os.path.isdir(full_path):
                dirs.append(item + "/")
            else:
                files.append(item)
                
        dirs.sort()
        files.sort()
        
        return json.dumps({
            "status": "success",
            "message": f"Found {len(items)} items in {dir_path}",
            "items": dirs + files,
            "cwd": target_dir
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def search_files(client=None, pattern="", dir_path=".", **kwargs):
    """
    Search for files by glob pattern.
    """
    import glob
    try:
        if isinstance(client, str) and not pattern:
             pattern = client
             
        if not pattern:
             return json.dumps({"status": "error", "message": "Pattern is required."})

        target_dir = os.path.abspath(dir_path)
        search_pattern = os.path.join(target_dir, pattern)
        
        # recursive=True allows ** usage
        matches = glob.glob(search_pattern, recursive=True)
        
        # Convert to relative paths for cleaner output
        rel_matches = []
        for m in matches:
            try:
                rel = os.path.relpath(m, target_dir)
                rel_matches.append(rel)
            except:
                rel_matches.append(m)
                
        return json.dumps({
            "status": "success",
            "message": f"Found {len(matches)} files matching '{pattern}'",
            "matches": rel_matches[:100] # Limit to 100 results
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def set_expression(expression_name="", **kwargs):
    """
    Dummy function for setting expression. 
    The actual implementation is handled via signal in LLMWorker.
    """
    return json.dumps({
        "status": "success", 
        "message": f"已修改为{expression_name}表情"
    }, ensure_ascii=False)


def modify_pet_attribute(interaction="", intensity="", attribute="", action="", **kwargs):
    """
    Dummy function for modifying pet attribute.
    The actual implementation is handled via signal in LLMWorker.
    
    Supports two formats:
    - New format: interaction="play_fun", intensity="moderate"
    - Legacy format: attribute="mood", action="play"
    """
    from src.core.pet_constants import INTERACTION_NAMES
    
    if interaction:
        interaction_name = INTERACTION_NAMES.get(interaction, interaction)
        return json.dumps({
            "status": "success",
            "message": f"已执行{interaction_name}互动"
        }, ensure_ascii=False)
    
    legacy_action_names = {
        "feed": "投喂",
        "play": "玩耍",
        "clean": "清洁",
        "rest": "休息"
    }
    
    attr_names = {
        "hunger": "饱食度",
        "mood": "心情值", 
        "cleanliness": "清洁度",
        "energy": "能量值"
    }
    
    attr_name = attr_names.get(attribute, attribute)
    action_name = legacy_action_names.get(action, action)
    
    return json.dumps({
        "status": "success",
        "message": f"已对{attr_name}执行{action_name}操作"
    }, ensure_ascii=False)


_skill_manager_instance = None

def _get_skill_manager():
    global _skill_manager_instance
    if _skill_manager_instance is None:
        _skill_manager_instance = SkillManager()
    return _skill_manager_instance

def install_agent_skill(source="", skill_name=None, **kwargs):
    """
    Installs an agent skill from various sources.
    Supports: GitHub (owner/repo), GitLab URL, zip URL, or local path.
    """
    try:
        if not source:
            return json.dumps({"status": "error", "message": "Source parameter is required."})
            
        manager = _get_skill_manager()
        result = manager.install_skill(source, skill_name)
        return result
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def list_agent_skills(**kwargs):
    """
    Lists all installed agent skills.
    """
    try:
        manager = _get_skill_manager()
        skills = manager.list_skills()
        return json.dumps({
            "status": "success",
            "skills": skills,
            "count": len(skills)
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def get_skill_content(skill_name="", **kwargs):
    """
    Gets the full content of a document-type skill.
    """
    try:
        if not skill_name:
            return json.dumps({"status": "error", "message": "skill_name parameter is required."})
            
        manager = _get_skill_manager()
        content = manager.get_skill_content(skill_name)
        
        if content is None:
            return json.dumps({"status": "error", "message": f"Skill '{skill_name}' not found."})
        
        return json.dumps({
            "status": "success",
            "skill_name": skill_name,
            "content": content
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

def remove_agent_skill(skill_name="", **kwargs):
    """
    Removes an installed agent skill.
    """
    try:
        if not skill_name:
            return json.dumps({"status": "error", "message": "skill_name parameter is required."})
            
        manager = _get_skill_manager()
        result = manager.remove_skill(skill_name)
        return result
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})

AVAILABLE_TOOLS = {
    "generate_image": generate_image,
    "search_baidu": search_baidu,
    "search_bing": search_bing,
    "visit_webpage": visit_webpage,
    "write_file": write_file,
    "edit_file": edit_file,
    "insert_at_line": insert_at_line,
    "delete_lines": delete_lines,
    "find_in_file": find_in_file,
    "run_python_script": run_python_script,
    "read_file": read_file,
    "list_files": list_files,
    "search_files": search_files,
    "set_expression": set_expression,
    "modify_pet_attribute": modify_pet_attribute,
    "install_agent_skill": install_agent_skill,
    "list_agent_skills": list_agent_skills,
    "get_skill_content": get_skill_content,
    "remove_agent_skill": remove_agent_skill,
}

def get_dynamic_skill_schemas():
    """
    Returns tool schemas for executable skills loaded from skill manager.
    """
    manager = _get_skill_manager()
    return manager.get_tool_schemas()

def get_all_tool_schemas():
    """
    Returns all tool schemas including static tools and dynamic skills.
    """
    return TOOLS_SCHEMA + get_dynamic_skill_schemas()

def execute_skill(skill_name, **kwargs):
    """
    Executes a dynamically loaded skill.
    """
    manager = _get_skill_manager()
    return manager.execute_skill(skill_name, **kwargs)

def get_skill_descriptions():
    """
    Returns a dict of skill names to descriptions for context injection.
    """
    manager = _get_skill_manager()
    return manager.get_all_skill_descriptions()
