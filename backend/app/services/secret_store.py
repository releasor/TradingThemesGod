"""模型凭据的应用级加密存储。"""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

# 固定落在 backend 目录，避免因启动 cwd 不同生成多把密钥
_DEFAULT_KEY_FILE = Path(__file__).resolve().parents[1] / ".model-secret.key"


class SecretStore:
    def __init__(self, key_file: Path | None = None):
        configured_key = os.getenv("MODEL_SECRET_KEY", "").strip()
        if configured_key:
            key = configured_key.encode()
        else:
            path = key_file or _DEFAULT_KEY_FILE
            if path.exists():
                key = path.read_bytes().strip()
            else:
                key = Fernet.generate_key()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(key)
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        if not value:
            return ""
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        if not value:
            return ""
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("模型凭据无法解密，请重新保存配置") from exc
