"""
Serviço de criptografia do Vault.

Usa Fernet (AES-128-CBC + HMAC-SHA256).
A MASTER_KEY fica APENAS no .env — nunca no banco.
Se o banco vazar, os dados cifrados são inúteis sem a chave.
"""
from cryptography.fernet import Fernet, InvalidToken
from loguru import logger
from app.config import settings

# Instância única — carregada na inicialização
try:
    _fernet = Fernet(settings.MASTER_KEY.encode())
except Exception as e:
    raise RuntimeError(
        f"❌ MASTER_KEY inválida! Gere uma com:\n"
        f"   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
        f"Erro: {e}"
    )


def encrypt(plain_text: str) -> str:
    """Cifra um texto e retorna string base64 segura para guardar no banco."""
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt(cipher_text: str) -> str:
    """Decifra um valor do banco. Lança ValueError se a chave estiver errada."""
    try:
        return _fernet.decrypt(cipher_text.encode()).decode()
    except InvalidToken:
        raise ValueError("Falha ao decifrar: token inválido ou MASTER_KEY incorreta.")


def rotate_key(old_key: str, new_key: str, cipher_text: str) -> str:
    """
    Utilitário para rotação de chave.
    Decifra com a chave antiga e cifra com a nova.
    Use ao trocar a MASTER_KEY (raro, mas possível).
    """
    old_fernet = Fernet(old_key.encode())
    new_fernet = Fernet(new_key.encode())
    plain = old_fernet.decrypt(cipher_text.encode())
    return new_fernet.encrypt(plain).decode()
