Aqui está o arquivo **README.md** completo e revisado, pronto para ser copiado e colado:

---

# 🤖 Siaa - Scaffoldable-IA-Assistant

O **Siaa** é um assistente de IA focado em produtividade, privacidade e expansão simplificada. Ele utiliza um sistema híbrido que combina o processamento de linguagem natural de **LLMs (Ollama)** com a velocidade e precisão de **SVMs (Support Vector Machines)** para classificação de intenções.

---

## 🧠 Classificação de Intenções: Por que SVM?

Diferente de assistentes que processam cada palavra via LLM (o que pode gerar latência e custos), o Siaa utiliza uma **SVM local** para decidir a intenção do usuário antes de disparar qualquer outra ação.

### Vantagens da SVM no Projeto:

* **Velocidade (Baixa Latência)**: A classificação é feita localmente em milissegundos.
* **Privacidade Total**: O modelo é treinado e executado no seu hardware.
* **Eficiência**: Ideal para distinguir comandos específicos como `FINANCE_ADD` de `AGENDA_ADD` de forma categórica.

### 🛠️ Treinamento e Testes

* **Como Treinar**: O `intent_handler.py` carrega um modelo `.pkl`. Para treiná-lo, utilize o script de treinamento alimentando-o com exemplos de frases etiquetadas. Isso permite que o bot "aprenda" novas formas de falar.
* **Como Testar**: O sistema permite validar se as intenções estão sendo detectadas corretamente antes de subir atualizações, evitando conflitos entre módulos.

---

## 🏗️ Arquitetura e Expansão (Scaffolding)

O Siaa foi desenhado para ser escalável. Através do script `add_module.py`, é possível criar novos domínios (como "Notas", "Tarefas" ou "Fitness") de forma automática.

### O Gerador de Módulos:

Ao executar o gerador, o sistema cria a estrutura base:

1. **Entity**: A lógica de conversa, gerenciamento de estados e confirmações.
2. **Action**: A camada de persistência com banco de dados SQL e utilitários.
3. **Injeção de Código**: O script automatiza parte da configuração nos arquivos `agent.py` e `intent_handler.py`.

---

## 🧠 Memória em 4 Camadas (Persistência Adaptativa)

O Siaa não apenas responde, ele mantém um contexto evolutivo para não se perder em conversas longas:

1. **IMPORTANT**: Regras fixas de personalidade e dados essenciais do usuário (manual).
2. **ACTUAL**: Memória de curto prazo que acumula fatos recentes. Ela possui uma lógica de **auto-resumo** que condensa as informações ao atingir o limite de caracteres, preservando o contexto sem estourar o buffer.
3. **BROADER**: Consolidação de longo prazo baseada em tópicos recorrentes extraídos das últimas interações.
4. **SQL (Long Term)**: Banco de dados bruto para buscas históricas profundas e registros financeiros/agenda.

---

## ⚙️ Configuração Obrigatória (.env)

O Siaa utiliza variáveis de ambiente para se conectar ao Ollama e ao Telegram. **Crie um arquivo `.env` na raiz do projeto** (este arquivo é ignorado pelo Git):

```env
# --- Configurações de IA (Ollama) ---
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL_CHAT=granite-2b:latest
OLLAMA_MODEL_FAST=granite-2b:latest

# --- Comunicação (Telegram) ---
TELEGRAM_TOKEN=seu_token_aqui
TELEGRAM_CHAT_ID=seu_chat_id_aqui

```

> **Dica**: Obtenha o token com o [@BotFather](https://t.me/botfather) e seu ID numérico com o [@userinfobot](https://t.me/userinfobot) no Telegram.

---

## 📅 Roadmap de Desenvolvimento

O projeto está em fase de evolução constante. Próximos passos:

* **🔔 Serviço de Lembretes**: Notificações ativas enviadas via Telegram para compromissos.
* **⚙️ Inicialização Personalizada**: Ferramentas para configurar o bot e sua personalidade no primeiro boot.
* **🧪 Suite de Testes**: Implementação de testes unitários automatizados para garantir a estabilidade das entidades.
* **📈 Refinamento de Extração**: Melhoria contínua nos prompts de extração de valores e datas para os módulos de Finanças e Agenda.

---

## 🔧 Instalação e Uso

1. **Instale as dependências**:
```bash
pip install -r requirements.txt

```


2. **Configure o arquivo `.env**` com suas chaves e URLs.
3. **Inicie o assistente**:
```bash
python3 app.py

```



---

