import os
import json
import requests
import pathlib
from datetime import datetime

# Tool Schemas for OpenAI
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate an image based on a text prompt using DALL-E 3 or compatible API and save it locally.",
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
    }
]

def generate_image(client, prompt, base_url=None, api_key=None, model=None):
    """
    Generates an image using OpenAI client or custom API and saves it locally.
    """
    try:
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
        return json.dumps({"status": "error", "message": str(e)})

# Mapping for execution
AVAILABLE_TOOLS = {
    "generate_image": generate_image
}
