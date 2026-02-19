import re

def pre_process(text):
    """Garante que o '?' seja tratado como um token e limpa caracteres especiais."""
    if not isinstance(text, str): return ""
    text = text.lower()
    text = re.sub(r'(\?)', r' \1', text)
    text = re.sub(r'[^a-z0-9\s\?áéíóúâêîôûãõç]', '', text)
    return text.strip()

def tokenize(text):
    """Transforma a frase em uma lista de palavras úteis."""
    return [w.lower() for w in re.findall(r'\b\w+\b', text) if len(w) > 2]

def is_plural(message):
    """Detecta se o usuário usou palavras no plural."""
    tokens = set(message.lower().split())
    
    # Artigos e pronomes no plural
    plurais_claros = {'os', 'as', 'todos', 'todas', 'esses', 'essas', 'últimos', 'vários', 'alguns', 'uns', 'umas'}
    if plurais_claros.intersection(tokens):
        return True
        
    # Substantivos comuns do bot no plural
    substantivos_plurais = {'gastos', 'compras', 'reuniões', 'eventos', 'itens', 'contas', 'coisas', 'despesas', 'lembretes'}
    if substantivos_plurais.intersection(tokens):
        return True
        
    # Checagem genérica rápida (palavras que terminam com 's' e têm mais de 3 letras, ignorando exceções comuns)
    excecoes = {'mas', 'das', 'dos', 'nos', 'nas', 'mês', 'após', 'antes', 'depois', 'mais', 'menos'}
    for token in tokens:
        if token.endswith('s') and len(token) > 3 and token not in excecoes:
            return True
            
    return False

def normalize_amount(text):
    """Extrai e converte valores monetários para float."""
    text = text.lower()
    match_rs = re.search(r'r\$\s*(\d+(?:\.\d{3})*(?:,\d{1,2})?)', text)
    if match_rs:
        num_str = match_rs.group(1)
    else:
        matches_virgula = re.findall(r'\b\d+(?:\.\d{3})*,\d{1,2}\b', text)
        if matches_virgula:
            num_str = matches_virgula[-1]
        else:
            all_nums = re.findall(r'\b\d+(?:[.,]\d+)?\b', text)
            valid_nums = [n for n in all_nums if not (len(n) == 4 and n.startswith('202'))]
            num_str = valid_nums[-1] if valid_nums else "0"

    clean_num = num_str.replace('.', '').replace(',', '.')
    try:
        return float(clean_num)
    except:
        return 0.0