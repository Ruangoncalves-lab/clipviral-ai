# ClipViral AI 🚀

**ClipViral AI** é uma ferramenta MVP gratuita para uso pessoal que transforma vídeos longos (horizontais ou verticais) em cortes curtos prontos para postar no Reels, TikTok e YouTube Shorts. O aplicativo transcreve o vídeo automaticamente, usa Inteligência Artificial ou lógica local para pontuar a viralização de trechos relevantes, corta e formata os vídeos na resolução vertical 9:16 com fundo desfocado, adiciona título estilizado e gera legendas dinâmicas perfeitamente sincronizadas.

O projeto foi estruturado para ser leve, eficiente e executável em CPU de forma gratuita tanto localmente quanto no **Hugging Face Spaces**.

---

## 📋 Funcionalidades

1. **Upload Flexível:** Suporte a formatos de vídeo `MP4`, `MOV`, `MKV` e `WEBM`.
2. **Definição de Parâmetros de Cortes:** Ajuste do número de cortes (5, 10, 15 ou 20), duração mínima e máxima (com limite estrito de 120 segundos).
3. **Transcrição Automática:** Utiliza a biblioteca otimizada `faster-whisper` localmente em CPU (com suporte aos modelos `tiny`, `base` e `small`).
4. **Análise de Viralização:** 
   - Análise inteligente e contextualizada usando a **Gemini API (Free Tier)**.
   - Sistema de **fallback local por regras** caso a chave do Gemini não seja fornecida ou o limite de requisições falte.
5. **Edição Automática FFmpeg:**
   - Redimensionamento automático de horizontal para vertical (1080x1920) aplicando um fundo desfocado a partir do próprio vídeo original.
   - Legendas queimadas dinâmicas (sincronizadas a cada 3-5 palavras) usando a fonte profissional **Montserrat-Bold**.
   - Título curto e chamativo fixado no topo do corte.
6. **Download Facilitado:** Galeria interativa para pré-visualização e área de download individual para os arquivos `.mp4` e o relatório completo `relatorio_cortes.json`.
7. **Relatório Detalhado:** Resumo em formato JSON e Markdown com score de viralização, título gerado, gancho inicial, motivo da escolha e duração de cada corte.

---

## 🛠️ Stack Tecnológica

- **Python 3.10+**
- **Gradio** (para a interface web responsiva)
- **FFmpeg** & **ffprobe** (para o processamento de áudio/vídeo)
- **faster-whisper** (reconhecimento automático de fala por CPU)
- **Google Generative AI SDK** (integração opcional com Gemini 1.5 Flash)
- **Pydantic** (organização de dados)

---

## 📦 Estrutura de Arquivos

```text
clipviral-ai/
├── app.py                  # Interface Gradio e orquestração do pipeline
├── requirements.txt        # Dependências do Python
├── packages.txt            # Dependência do sistema do Hugging Face Spaces (ffmpeg)
├── README.md               # Documentação do projeto
├── .gitignore              # Arquivos e pastas ignoradas pelo Git
└── src/
    ├── __init__.py         # Inicialização do pacote python
    ├── config.py           # Constantes e diretórios globais
    ├── transcriber.py      # Extração de áudio e transcrição via Whisper
    ├── clip_selector.py    # Geração de candidatos e seleção final de cortes
    ├── gemini_analyzer.py  # Análise de viralização por IA (Gemini API)
    ├── rule_analyzer.py    # Fallback de análise via regras de palavras-chave locais
    ├── video_editor.py     # Edição de vídeo (FFmpeg), legendagem e renderização
    ├── subtitles.py        # Conversão de trechos em legendas SRT dinâmicas
    └── utils.py            # Download de fontes, validação de arquivos e logs
```

---

## 💻 Como Rodar Localmente

### Pré-requisitos
1. Certifique-se de que o **FFmpeg** esteja instalado no seu sistema e configurado no `PATH` do sistema.
   - *Windows:* Baixe o build essencial pelo gyan.dev e adicione o caminho da pasta `/bin` nas variáveis de ambiente.
   - *Linux (Ubuntu/Debian):* `sudo apt update && sudo apt install ffmpeg -y`
   - *Mac (Homebrew):* `brew install ffmpeg`

### Instalação

1. Clone ou extraia o repositório em seu ambiente.
2. Navegue até a pasta do projeto:
   ```bash
   cd clipviral-ai
   ```
3. Crie e ative um ambiente virtual (opcional, mas recomendado):
   ```bash
   python -m venv venv
   # No Windows:
   venv\Scripts\activate
   # No Linux/Mac:
   source venv/bin/activate
   ```
4. Instale as dependências listadas:
   ```bash
   pip install -r requirements.txt
   ```
5. Inicie a interface Gradio:
   ```bash
   python app.py
   ```
6. Abra o navegador no endereço indicado (geralmente `http://127.0.0.1:7860`).

---

## ☁️ Como Subir no Hugging Face Spaces

1. Crie uma conta em [huggingface.co](https://huggingface.co).
2. Clique em **New Space** (Novo Espaço).
3. Insira o nome do espaço (ex: `clipviral-ai`).
4. Selecione a SDK do **Gradio**.
5. Deixe a máquina padrão recomendada (**CPU Basic - Gratuita**).
6. Configure a visibilidade como *Public* ou *Private* (uso pessoal).
7. Faça o commit de todos os arquivos do projeto (incluindo `app.py`, `packages.txt`, `requirements.txt`, `src/`, etc.) para o repositório Git do Space.
8. O Hugging Face lerá o `packages.txt` para instalar o **FFmpeg** no ambiente do contêiner Linux automaticamente e depois o `requirements.txt` para carregar as dependências.
9. Em poucos minutos, a ferramenta estará online!

---

## 🔑 Como Configurar a Chave Gemini

Você pode habilitar a análise avançada com o Gemini de duas formas:

### 1. Interface Web (Temporário)
Cole a sua chave diretamente na tela do app, no campo **Gemini API Key**, antes de clicar em gerar cortes.

### 2. Variável de Ambiente / Secret (Recomendado)
- **Localmente:** Crie um arquivo `.env` na raiz da pasta `clipviral-ai/` e adicione:
  ```env
  GEMINI_API_KEY=sua_chave_aqui
  ```
- **No Hugging Face Spaces:** Vá na aba **Settings** (Configurações) do seu Space, procure pela seção **Variables and Secrets**, clique em **New Secret**, dê o nome `GEMINI_API_KEY` e adicione o valor de sua chave gratuita. A chave do Gemini será carregada automaticamente por segundo plano de forma oculta.

---

## ⚙️ Como Usar sem Chave Gemini (Regras Locais)

Se você não tiver uma chave Gemini, não se preocupe! Basta **desmarcar** a opção **"Usar análise com Gemini AI"** na interface (ou deixar o campo de chave vazio). O aplicativo usará o analisador local (`src/rule_analyzer.py`).

O analisador por regras locais mapeia a transcrição buscando:
- **Gatilhos de Atenção/Ganchos:** Palavras como *"Você sabia"*, *"Presta atenção"*, *"O segredo"*, *"O maior erro"*.
- **Estruturas Verbais:** Perguntas (`?`), exclamações (`!`), dicas passo a passo e listas.
- **Penalização de Ruídos:** Identifica e reduz a pontuação de trechos com excesso de termos como *"tipo"*, *"né"*, *"ééé"*.
- **Otimização de Tempo:** Pontua mais alto os trechos que possuem a duração ideal recomendada de engajamento (entre 30 e 60 segundos).

---

## ⚠️ Limitações do Plano Gratuito

Para uso em Spaces gratuitos com recursos de CPU limitados, algumas regras são cruciais:
- **Lentidão no Processamento:** Como a transcrição e renderização rodam em CPU, a exportação de vários vídeos pode demorar alguns minutos. Tenha paciência.
- **Armazenamento Volátil:** Os arquivos gerados na pasta `temp/` e `output/` são apagados quando o Space é reiniciado ou após o término de novas execuções para evitar estouro de disco. Certifique-se de fazer o download dos seus vídeos logo após o processamento.
- **Limite do Gemini Free Tier:** O Gemini Free Tier permite até 15 requisições por minuto. Caso esse limite seja atingido ou a API retorne erro, o app migrará automaticamente para o analisador de regras locais sem interromper o fluxo de exportação.

---

## ⏱️ Duração Máxima dos Cortes: 2 Minutos

O limite absoluto de duração de cada corte é de **120 segundos (2 minutos)** para garantir compatibilidade com o formato de vídeos verticais das plataformas Reels, TikTok e Shorts.
- O campo de duração máxima na interface está limitado a no máximo 120 segundos.
- Caso o Gemini sugira ou o sistema monte um candidato com mais de 120 segundos, a função de corte do FFmpeg cortará o vídeo exatamente no limite de 120 segundos.
- O relatório final exibe o tempo exato e a duração final de cada trecho.

---

## 🧪 Recomendações de Teste

### Teste Inicial (Vídeo Curto)
1. Carregue um vídeo curto de **2 a 5 minutos**.
2. Selecione **5 cortes**.
3. Defina a duração mínima como **25 segundos** e a máxima como **60 segundos**.
4. Clique em gerar para testar todo o pipeline (transcrição, pontuação, layout vertical com blur e legendas) rapidamente.

### Teste Completo (Vídeo de 40 Minutos)
1. Carregue um vídeo longo de até **40 minutos**.
2. Selecione **10 cortes**.
3. Defina a duração mínima como **25 segundos** e a máxima como **120 segundos**.
4. Deixe o app rodar até finalizar o processamento e faça o download do pacote.

---

## 💡 Dicas para Melhorar a Qualidade dos Cortes

- **Áudio Limpo:** O Whisper detecta melhor as palavras e os timestamps quando não há música de fundo extremamente alta ou ruídos extremos.
- **Dicção Firme:** Vídeos onde a pessoa fala de forma contínua geram melhores candidatos com sentenças fechadas.
- **Modelos Whisper:** O modelo `base` oferece uma ótima relação velocidade/precisão. Se notar erros de português, teste o modelo `small`.

---

## 🚀 Próximos Upgrades (Ideias para Evolução)

Para aproximar o ClipViral AI ainda mais de ferramentas comerciais como o OpusClip:
- [ ] **Legendas Estilizadas:** Adicionar suporte a cores dinâmicas destacando palavra por palavra conforme a fala (legenda estilo *Karaokê*).
- [ ] **Templates de Estilo:** Seleção de diferentes fontes, animações de transição de legenda e posições.
- [ ] **Detecção Facial / Auto-Reenquadramento:** Uso de modelos de visão computacional (como MediaPipe) para focar automaticamente na pessoa em movimento no vídeo centralizado.
- [ ] **Cortes por Mudança de Cena:** Detectar cortes abruptos para ajustar as transições e evitar quebras no meio do vídeo original.
- [ ] **Remoção Automática de Silêncios:** Remover trechos silenciosos longos no áudio final para deixar o corte mais dinâmico.
- [ ] **Upload Direto:** Integração de APIs para exportar diretamente para YouTube Shorts, TikTok e Instagram Reels.
- [ ] **Armazenamento em Nuvem:** Envio direto dos cortes prontos para o Cloudflare R2 ou AWS S3.
- [ ] **Fila de Processamento (Queue):** Sistema com Redis/Celery para gerenciar múltiplas renderizações em background de forma assíncrona.
