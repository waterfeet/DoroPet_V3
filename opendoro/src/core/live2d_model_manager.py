import os
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PyQt5.QtCore import QObject, pyqtSignal
from src.resource_utils import resource_path


@dataclass
class Live2DModelInfo:
    model_id: str
    name: str
    model_path: str
    icon_path: Optional[str]
    description: str
    
    def to_dict(self) -> Dict:
        return {
            'model_id': self.model_id,
            'name': self.name,
            'model_path': self.model_path,
            'icon_path': self.icon_path,
            'description': self.description
        }


class Live2DModelManager(QObject):
    model_loaded = pyqtSignal(str)
    model_load_failed = pyqtSignal(str, str)
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._models: Dict[str, Live2DModelInfo] = {}
        self._scan_models()
    
    def _scan_models(self):
        models_dir = resource_path("models")
        if not os.path.exists(models_dir):
            return
        
        for model_folder in os.listdir(models_dir):
            model_path = os.path.join(models_dir, model_folder)
            if not os.path.isdir(model_path):
                continue
            
            model_info = self._load_model_info(model_path, model_folder)
            if model_info:
                self._models[model_info.model_id] = model_info
    
    def _load_model_info(self, model_path: str, folder_name: str) -> Optional[Live2DModelInfo]:
        model_json_files = [f for f in os.listdir(model_path) if f.endswith('.model3.json')]
        
        if not model_json_files:
            return None
        
        model_json_path = os.path.join(model_path, model_json_files[0])
        
        try:
            with open(model_json_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            model_data = {}
        
        name = model_data.get('Name', folder_name)
        description = model_data.get('Description', f"Live2D 模型: {name}")
        
        icon_path = None
        possible_icons = ['icon.png', 'icon.jpg', f'{folder_name}.png', f'{folder_name}.jpg']
        for icon_name in possible_icons:
            potential_icon = os.path.join(model_path, icon_name)
            if os.path.exists(potential_icon):
                icon_path = potential_icon
                break
        
        if not icon_path:
            textures = model_data.get('FileReferences', {}).get('Textures', [])
            if textures:
                texture_path = os.path.join(model_path, textures[0])
                if os.path.exists(texture_path):
                    icon_path = texture_path
        
        return Live2DModelInfo(
            model_id=folder_name,
            name=name,
            model_path=model_json_path,
            icon_path=icon_path,
            description=description
        )
    
    def get_all_models(self) -> List[Live2DModelInfo]:
        return list(self._models.values())
    
    def get_model(self, model_id: str) -> Optional[Live2DModelInfo]:
        return self._models.get(model_id)
    
    def get_model_by_path(self, model_path: str) -> Optional[Live2DModelInfo]:
        for model in self._models.values():
            if model.model_path == model_path:
                return model
        return None
    
    def validate_model(self, model_path: str) -> Tuple[bool, str]:
        if not os.path.exists(model_path):
            return False, f"模型文件不存在: {model_path}"
        
        if not model_path.endswith('.model3.json'):
            return False, "模型文件必须是 .model3.json 格式"
        
        try:
            with open(model_path, 'r', encoding='utf-8') as f:
                model_data = json.load(f)
        except json.JSONDecodeError:
            return False, "模型配置文件格式错误"
        except IOError as e:
            return False, f"无法读取模型文件: {str(e)}"
        
        file_refs = model_data.get('FileReferences', {})
        moc_file = file_refs.get('Moc', '')
        
        if not moc_file:
            return False, "模型配置缺少 Moc 文件引用"
        
        model_dir = os.path.dirname(model_path)
        moc_path = os.path.join(model_dir, moc_file)
        
        if not os.path.exists(moc_path):
            return False, f"模型数据文件不存在: {moc_file}"
        
        return True, "模型验证通过"
    
    def get_default_model_path(self) -> str:
        default_model = self._models.get('Doro')
        if default_model:
            return default_model.model_path
        
        if self._models:
            first_model = list(self._models.values())[0]
            return first_model.model_path
        
        return resource_path("models/Doro/Doro.model3.json")
    
    def refresh_models(self):
        self._models.clear()
        self._scan_models()


live2d_model_manager = Live2DModelManager()
