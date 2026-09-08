"""模型凭据的应用级加密存储。"""

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

# 固定落在 backend/app 目录，避免因启动 cwd 不同生成多把密钥。
# Docker 可通过 MODEL_SECRET_KEY 或 MODEL_SECRET_KEY_FILE 挂到持久卷。
_DEFAULT_KEY_FILE = Path(__file__).resolve().parents[1] / ".model-secret.key"


def _resolve_key_file(key_file: Path | None) -> Path:
    if key_file is not None:
        return key_file
    configured_path = os.getenv("MODEL_SECRET_KEY_FILE", "").strip()
    if configured_path:
        return Path(configured_path)
    return _DEFAULT_KEY_FILE


class SecretStore:
    def __init__(self, key_file: Path | None = None):
        configured_key = os.getenv("MODEL_SECRET_KEY", "").strip()
        if configured_key:
            key = configured_key.encode()
        else:
            path = _resolve_key_file(key_file)
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
