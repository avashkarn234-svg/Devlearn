import requests
import json
from django.conf import settings

class PistonExecutor:
    API_URL = "https://api.piston.rocks/execute"
    
    LANGUAGE_MAP = {
        'lua': 'lua',
        'python': 'python',
        'c': 'c',
        'javascript': 'javascript',
        'bash': 'bash',
        'html': 'html',
        'css': 'css',
    }
    
    @staticmethod
    def execute(language, code, stdin=""):
        """Execute code using Piston API"""
        try:
            lang = PistonExecutor.LANGUAGE_MAP.get(language, language)
            
            payload = {
                "language": lang,
                "version": "*",
                "files": [
                    {
                        "name": f"main.{PistonExecutor.get_extension(language)}",
                        "content": code
                    }
                ],
                "stdin": stdin,
                "args": [],
                "compile_timeout": 10000,
                "run_timeout": 3000,
                "compile_memory_limit": -1,
                "run_memory_limit": -1
            }
            
            response = requests.post(PistonExecutor.API_URL, json=payload, timeout=15)
            result = response.json()
            
            if response.status_code == 200:
                output = result.get('run', {}).get('stdout', '')
                error = result.get('run', {}).get('stderr', '')
                
                return {
                    'status': 'ERROR' if error else 'SUCCESS',
                    'output': output,
                    'error': error,
                    'execution_time': result.get('run', {}).get('signal', 0)
                }
            else:
                return {
                    'status': 'ERROR',
                    'output': '',
                    'error': 'Execution service unavailable',
                    'execution_time': 0
                }
        
        except requests.exceptions.Timeout:
            return {
                'status': 'ERROR',
                'output': '',
                'error': 'Execution timeout (3s max)',
                'execution_time': 0
            }
        except Exception as e:
            return {
                'status': 'ERROR',
                'output': '',
                'error': str(e),
                'execution_time': 0
            }
    
    @staticmethod
    def get_extension(language):
        extensions = {
            'lua': 'lua',
            'python': 'py',
            'c': 'c',
            'javascript': 'js',
            'bash': 'sh',
            'html': 'html',
            'css': 'css',
        }
        return extensions.get(language, 'txt')