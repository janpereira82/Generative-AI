# Agente Pesquisador Web
Um sistema avançado de pesquisa web automatizada construído com crewAI, que utiliza múltiplos agentes especializados para realizar pesquisas abrangentes, extrair conteúdo relevante e sintetizar informações em relatórios detalhados.

## Visão Geral
O Agente Pesquisador Web é uma aplicação que automatiza o processo de pesquisa na internet, utilizando inteligência artificial para descobrir, extrair e sintetizar informações sobre qualquer tópico. O sistema emprega uma arquitetura de múltiplos agentes especializados, cada um responsável por uma etapa específica do processo de pesquisa.

## Funcionalidades
- **Busca Web Automatizada**: Utiliza a API SerperDev para encontrar fontes relevantes e diversificadas
- **Extração Inteligente de Conteúdo**: Processa páginas web para extrair informações significativas
- **Síntese de Informações**: Cria relatórios detalhados baseados exclusivamente no conteúdo extraído
- **Rastreamento de Referências**: Mantém registro de todas as fontes consultadas
- **Armazenamento de Resultados**: Salva automaticamente os relatórios em arquivos de texto
- **Interface em Linha de Comando**: Fácil de usar, com instruções em português

## Requisitos
- Python 3.8 ou superior
- Chaves de API:
  - OpenAI API Key
  - SerperDev API Key

## Instalação
1. Clone o repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```
3. Configure as variáveis de ambiente no arquivo `.env`:
```env
OPENAI_API_KEY=sua_chave_openai
SERPER_API_KEY=sua_chave_serperdev
```

## Bibliotecas Utilizadas
- **crewAI**: Framework para criação e orquestração de agentes autônomos
- **langchain_openai**: Integração com modelos de linguagem da OpenAI
- **crewai_tools**: Ferramentas específicas para o crewAI, incluindo SerperDevTool
- **BeautifulSoup4**: Biblioteca para análise e extração de conteúdo HTML
- **requests**: Biblioteca para realizar requisições HTTP
- **python-dotenv**: Gerenciamento de variáveis de ambiente
- **datetime**: Manipulação de datas e horas
- **re**: Processamento de expressões regulares

## Como Funciona

O script `main.py` implementa uma arquitetura de três agentes especializados que trabalham em sequência:

### 1. Agente Explorador

- **Função**: Especialista em busca web
- **Objetivo**: Encontrar e coletar URLs relevantes para o tópico de pesquisa
- **Ferramentas**: SerperDevTool para busca web
- **Modelo**: GPT-4o-mini

### 2. Agente Pesquisador

- **Função**: Especialista em extração de conteúdo
- **Objetivo**: Extrair conteúdo web dos URLs fornecidos e armazená-lo para análise
- **Ferramentas**: Ferramenta personalizada de extração de conteúdo
- **Modelo**: GPT-4-turbo-preview

### 3. Agente Sintetizador

- **Função**: Sintetizador de pesquisa
- **Objetivo**: Criar um relatório abrangente baseado no conteúdo web extraído
- **Ferramentas**: Ferramenta de acesso ao conteúdo extraído
- **Modelo**: GPT-4-turbo-preview

### Fluxo de Trabalho
1. O usuário fornece um tópico de pesquisa
2. O Agente Explorador busca e identifica pelo menos 15 URLs relevantes
3. O Agente Pesquisador extrai o conteúdo de cada URL, removendo elementos irrelevantes
4. O Agente Sintetizador analisa todo o conteúdo extraído e cria um relatório detalhado
5. O sistema adiciona uma seção de referências ao relatório
6. O relatório final é salvo em um arquivo de texto na pasta "resultados"

## Uso
Execute o script principal:
```bash
python main.py
```

Siga as instruções na interface de linha de comando:
1. Digite o tópico que deseja pesquisar
2. Aguarde enquanto os agentes realizam a pesquisa (pode levar alguns minutos)
3. O resultado será exibido no terminal e salvo automaticamente na pasta "resultados"

## Estrutura do Projeto
- `main.py`: Script principal contendo a implementação dos agentes e do fluxo de trabalho
- `requirements.txt`: Lista de dependências do projeto
- `.env`: Arquivo de configuração para chaves de API
- `resultados/`: Diretório onde os relatórios de pesquisa são salvos

## Resultados
O sistema gera relatórios detalhados que incluem:

- Informações abrangentes sobre o tópico pesquisado
- Análise baseada exclusivamente no conteúdo extraído das fontes web
- Citações adequadas para todas as informações apresentadas
- Lista completa de referências (URLs) consultadas durante a pesquisa

Os relatórios são salvos como arquivos de texto na pasta "resultados" com nomes que incluem o tópico pesquisado e um timestamp, por exemplo: `inteligencia_artificial_20230615_143022.txt`.

## Tratamento de Erros
O sistema inclui tratamento robusto de erros para lidar com:

- Problemas de conexão com a internet
- URLs inválidos ou inacessíveis
- Páginas web com conteúdo insuficiente
- Falhas nas APIs externas

## Limitações
- Requer chaves de API válidas para OpenAI e SerperDev
- O tempo de processamento pode variar dependendo da complexidade do tópico
- A qualidade dos resultados depende da disponibilidade de informações online sobre o tópico

## 👨‍💻 Autor
[Jan Pereira](https://github.com/janpereira82)