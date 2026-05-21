"""
GitHub 配置模块 - 从本地文件读取 token，不暴露在代码中
"""
import os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(CONFIG_DIR, '.github_token')

def get_github_token() -> str:
    """从本地文件读取 GitHub token"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            token = f.read().strip()
            return token
    raise FileNotFoundError(f"GitHub token file not found: {TOKEN_FILE}")

def get_github_headers() -> dict:
    """获取 GitHub API 请求头"""
    token = get_github_token()
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
