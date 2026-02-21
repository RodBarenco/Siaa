import re


# ------------------------------------------------------------------
# Stopwords PT-BR
# ------------------------------------------------------------------
_STOPWORDS = {
    "a", "o", "e", "de", "do", "da", "dos", "das", "em", "no", "na",
    "nos", "nas", "um", "uma", "uns", "umas", "por", "para", "com",
    "que", "se", "me", "te", "lhe", "nos", "vos", "lhes", "ao", "aos",
    "à", "às", "pelo", "pela", "pelos", "pelas", "num", "numa",
    "eu", "tu", "ele", "ela", "nós", "vós", "eles", "elas",
    "meu", "minha", "teu", "tua", "seu", "sua", "pra", "pro",
    "hj", "hoje", "já", "ja", "ai", "aí", "ah", "eh",
}


def tokenize(text: str) -> list[str]:
    """
    Tokeniza um texto removendo stopwords e retornando palavras únicas
    com 3+ caracteres. Usado para geração de keywords no banco.
    """
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list({w for w in words if len(w) >= 3 and w not in _STOPWORDS})


def is_plural(text: str) -> bool:
    """
    Heurística simples para detectar se o usuário quer múltiplos resultados.
    Ex: 'apaga todos os gastos de ontem' → True
    """
    plural_signals = [
        "todos", "tudo", "todas", "varios", "vários",
        "últimos", "ultimos", "recentes", "lista", "listar",
    ]
    tl = text.lower()
    return any(w in tl for w in plural_signals)
