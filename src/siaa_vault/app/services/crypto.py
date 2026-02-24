"""
app/services/crypto.py — Criptografia Fernet (AES-128-CBC + HMAC-SHA256).

A MASTER_KEY fica APENAS no .env — nunca no banco.
Se o banco vazar, os dados cifrados são inúteis sem a chave.
"""
from cryptography.fernet import Fernet, InvalidToken
from loguru import logger

from app.config import settings

try:
    _fernet = Fernet(settings.MASTER_KEY.encode())
except Exception as e:
    raise RuntimeError(
        f"❌ MASTER_KEY inválida!\n"
        f"Gere uma com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
        f"Erro: {e}"
    )


def encrypt(plain_text: str) -> str:
    """Cifra texto puro → retorna string base64 segura para o banco."""
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt(cipher_text: str) -> str:
    """Decifra valor do banco → texto puro. Lança ValueError se chave errada."""
    try:
        return _fernet.decrypt(cipher_text.encode()).decode()
    except InvalidToken:
        raise ValueError("Falha ao decifrar: token inválido ou MASTER_KEY incorreta.")


def rotate_master_key(old_key: str, new_key: str, cipher_text: str) -> str:
    """
    Utilitário para rotação emergencial da MASTER_KEY.
    Decifra com a chave antiga e cifra com a nova.
    
    USO: Execute via script admin, nunca via API.
    """
    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())
    plain = old_fernet.decrypt(cipher_text.encode())
    return new_fernet.encrypt(plain).decode()
