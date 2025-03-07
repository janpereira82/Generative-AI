import os
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from crewai_tools import SerperDevTool
from bs4 import BeautifulSoup
import requests
from langchain.tools import Tool
from datetime import datetime
import re

# Carregar variáveis de ambiente
load_dotenv()

# Configurar chaves de API
openai_key = os.getenv('OPENAI_API_KEY')
serper_key = os.getenv('SERPER_API_KEY')

if not openai_key or not serper_key:
    raise ValueError("Por favor, configure OPENAI_API_KEY e SERPER_API_KEY no arquivo .env")

class AgentePesquisador:
    def __init__(self):
        self.ferramenta_busca = SerperDevTool()
        self.referencias = set()  # Armazenar referências únicas
        self.conteudo_extraido = []  # Armazenar conteúdo extraído das páginas web
        
        # Criar ferramenta de extração de conteúdo
        self.ferramenta_extracao = Tool(
            name="extrair_conteudo",
            func=self._extrair_conteudo,
            description="Extrai conteúdo de uma página web"
        )
        
        # Criar agentes especializados
        self.agente_explorador = Agent(
            role='Especialista em Busca Web',
            goal='Encontrar e coletar URLs relevantes para o tópico de pesquisa',
            backstory='''Sou um especialista em busca web especializado em descobrir fontes 
            relevantes e de alta qualidade na internet. Foco em encontrar sites diversos e 
            autoritativos que contenham informações valiosas sobre o tópico de pesquisa.''',
            tools=[self.ferramenta_busca],
            llm=ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7),
            verbose=True
        )
        
        self.agente_pesquisador = Agent(
            role='Especialista em Extração de Conteúdo',
            goal='Extrair conteúdo web dos URLs fornecidos e armazená-lo para análise',
            backstory='''Sou um especialista em extração de conteúdo web, habilidoso em processar 
            páginas web para extrair conteúdo significativo. Garanto que todas as informações 
            relevantes sejam devidamente armazenadas e acessíveis.''',
            tools=[self.ferramenta_extracao],
            llm=ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7),
            verbose=True
        )
        
        # Criar ferramenta de obtenção de conteúdo extraído para o sintetizador
        self.ferramenta_obter_conteudo = Tool(
            name="obter_conteudo_extraido",
            func=self.obter_conteudo_extraido,
            description="Recupera todo o conteúdo extraído das páginas web para análise"
        )
        
        self.agente_sintetizador = Agent(
            role='Sintetizador de Pesquisa',
            goal='Criar um relatório abrangente baseado no conteúdo web extraído',
            backstory='''Sou um especialista em síntese de informações que se destaca em analisar 
            conteúdo web extraído e criar relatórios bem estruturados. Foco exclusivamente nas 
            informações disponíveis em nosso conteúdo extraído para garantir que todas as conclusões 
            sejam baseadas em dados web coletados.''',
            tools=[self.ferramenta_obter_conteudo],
            llm=ChatOpenAI(model_name="gpt-4-turbo-preview", temperature=0.7),
            verbose=True
        )
    
    def buscar(self, consulta):
        """Realizar uma busca usando SerperDev"""
        try:
            resultados = self.ferramenta_busca.search(consulta)
            # Adicionar URLs dos resultados da busca às referências
            for resultado in resultados:
                if 'link' in resultado:
                    self.referencias.add(resultado['link'])
            return resultados
        except Exception as e:
            print(f'Erro ao realizar busca: {e}')
            return []
    
    def _extrair_conteudo(self, url):
        """Extrair conteúdo de uma página web"""
        try:
            # Tratar parâmetro URL se for um dicionário
            if isinstance(url, dict):
                # Verificar diferentes formatos de entrada possíveis
                if 'url' in url:
                    url = url['url']
                elif 'value' in url:
                    url = url['value']
                elif 'tool_input' in url and isinstance(url['tool_input'], dict):
                    tool_input = url['tool_input']
                    if 'value' in tool_input:
                        url = tool_input['value']
                    elif isinstance(tool_input, str):
                        url = tool_input
                else:
                    # Tentar encontrar qualquer string que pareça uma URL
                    for key, value in url.items():
                        if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                            url = value
                            break
                    else:
                        raise ValueError(f'Formato de URL inválido: {url}')
            elif not isinstance(url, str):
                raise ValueError(f'Formato de URL inválido: {url}')
            
            # Adicionar URL às referências
            self.referencias.add(url)
            
            # Buscar e analisar conteúdo da página web com cabeçalhos apropriados
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # Levantar exceção para códigos de status ruins
            
            # Verificar tipo de conteúdo
            if 'text/html' not in response.headers.get('Content-Type', '').lower():
                raise ValueError('URL não aponta para uma página HTML')
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remover elementos indesejados
            for element in soup.find_all(['script', 'style', 'nav', 'footer']):
                element.decompose()
            
            # Extrair conteúdo principal
            conteudo = soup.get_text(separator='\n', strip=True)
            
            # Validação básica de conteúdo
            if not conteudo or len(conteudo.strip()) < 100:
                raise ValueError('Conteúdo insuficiente extraído da página web')
            
            # Armazenar conteúdo extraído com seu URL fonte
            self.conteudo_extraido.append({
                'source': url,
                'content': conteudo
            })
            
            return conteudo
        except requests.exceptions.RequestException as e:
            print(f'Erro de rede ao buscar conteúdo: {e}')
            return None
        except ValueError as e:
            print(f'Erro de validação: {e}')
            return None
        except Exception as e:
            print(f'Erro inesperado ao extrair conteúdo: {e}')
            return None
    
    def formatar_referencias(self):
        """Formatar referências em uma seção legível"""
        if not self.referencias:
            return "\n\nReferências:\nNenhuma referência encontrada. Por favor, verifique se houve um problema durante a coleta de dados."
        
        texto_referencias = "\n\nReferências:\n"
        texto_referencias += "As seguintes fontes foram consultadas durante a preparação deste relatório:\n\n"
        for i, ref in enumerate(sorted(self.referencias), 1):
            texto_referencias += f"{i}. {ref}\n"
        return texto_referencias
    
    def salvar_em_arquivo(self, topico, conteudo):
        """Salvar resultados da pesquisa em um arquivo no diretório de resultados"""
        # Criar diretório de resultados se não existir
        os.makedirs('resultados', exist_ok=True)
        
        # Sanitizar tópico para nome de arquivo
        topico_seguro = re.sub(r'[^\w\s-]', '', topico).strip()
        topico_seguro = re.sub(r'[-\s]+', '_', topico_seguro)
        
        # Criar nome de arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"resultados/{topico_seguro}_{timestamp}.txt"
        
        # Salvar conteúdo no arquivo
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        return nome_arquivo
    
    def obter_conteudo_extraido(self, *args, **kwargs):
        """Obter todo o conteúdo extraído em um formato bem estruturado para o sintetizador"""
        if not self.conteudo_extraido:
            return "Nenhum conteúdo foi extraído ainda. Por favor, certifique-se de que a tarefa de extração de conteúdo foi concluída com sucesso."
        
        conteudo_formatado = "\n\n=== CONTEÚDO WEB EXTRAÍDO ===\n\n"
        
        for i, item in enumerate(self.conteudo_extraido, 1):
            conteudo_formatado += f"Fonte {i}: {item['source']}\n"
            conteudo_formatado += f"{'=' * 80}\n"
            
            # Limitar comprimento do conteúdo se for muito grande
            conteudo = item['content']
            if len(conteudo) > 10000:  # Limitar conteúdo muito grande
                conteudo = conteudo[:10000] + "\n\n[Conteúdo truncado devido ao comprimento...]\n"
                
            conteudo_formatado += f"{conteudo}\n\n"
            conteudo_formatado += f"{'=' * 80}\n\n"
        
        conteudo_formatado += f"Total de fontes extraídas: {len(self.conteudo_extraido)}\n"
        return conteudo_formatado
    
    def pesquisar(self, topico):
        """Realizar pesquisa abrangente sobre um tópico"""
        # Limpar referências e conteúdo extraído anteriores
        self.referencias.clear()
        self.conteudo_extraido.clear()
        
        # Tarefa 1: Exploração inicial do tópico
        tarefa_exploracao = Task(
            description=f'''Buscar conteúdo web relevante sobre: {topico}\n\nInstruções:\n'''  
                      f'1. Use a ferramenta de busca para encontrar sites de alta qualidade sobre o tópico\n'
                      f'2. Foque em encontrar pelo menos 15 URLs relevantes e autoritativos\n'
                      f'3. Garanta que as fontes sejam diversas (acadêmicas, indústria, notícias, etc.)\n'
                      f'4. Retorne uma lista estruturada de todos os URLs descobertos com breves descrições',
            expected_output='Uma lista abrangente de URLs relevantes com descrições,\n'
                          'organizada por tipo de fonte e relevância para o tópico.',
            agent=self.agente_explorador
        )
        
        # Tarefa 2: Extração de Conteúdo
        tarefa_pesquisa = Task(
            description=f'''Extrair conteúdo dos URLs fornecidos sobre: {topico}\n\nInstruções:\n'''  
                      f'1. Processar cada URL fornecido pelo Especialista em Busca Web\n'
                      f'2. Usar ferramenta de extração de conteúdo para raspar e armazenar conteúdo\n'
                      f'3. Garantir extração bem-sucedida de pelo menos 10 fontes diferentes\n'
                      f'4. Relatar quaisquer extrações falhas ou problemas',
            expected_output='Um relatório confirmando a extração bem-sucedida de conteúdo,\n'
                          'incluindo o número de URLs processados e quaisquer problemas encontrados.',
            agent=self.agente_pesquisador
        )
        
        # Tarefa 3: Síntese de Conteúdo
        tarefa_sintese = Task(
            description=f'''Criar um relatório a partir do conteúdo web extraído sobre: {topico}\n\nInstruções:\n'''  
                      f'1. PRIMEIRO, use a ferramenta de obtenção de conteúdo extraído para recuperar todo o conteúdo web\n'
                      f'2. Use APENAS o conteúdo extraído (sem conhecimento externo)\n'
                      f'3. Analise todo o conteúdo extraído para reunir informações abrangentes\n'
                      f'4. Crie um relatório detalhado usando apenas o conteúdo web extraído\n'
                      f'5. Inclua citações adequadas para todas as informações (use os URLs fonte fornecidos no conteúdo extraído)\n'
                      f'6. Garanta que cada afirmação seja suportada pelo conteúdo extraído\n'
                      f'7. Foque em informações factuais das fontes',
            expected_output='Um relatório detalhado baseado exclusivamente no conteúdo web extraído,\n'
                          'com citações adequadas e referências aos URLs fonte.',
            agent=self.agente_sintetizador
        )
        
        # Criar equipe de pesquisa com todos os agentes e tarefas
        # Usar processo sequencial para garantir que cada tarefa seja concluída antes da próxima começar
        equipe = Crew(
            agents=[self.agente_explorador, self.agente_pesquisador, self.agente_sintetizador],
            tasks=[tarefa_exploracao, tarefa_pesquisa, tarefa_sintese],
            verbose=True,
            process=Process.sequential  # Garantir que as tarefas sejam executadas em sequência, não em paralelo
        )
        
        # Executar o fluxo de trabalho de pesquisa
        resultado = str(equipe.kickoff())
        
        # Adicionar seção de referências ao resultado
        resultado += self.formatar_referencias()
        
        # Salvar resultados em arquivo
        nome_arquivo = self.salvar_em_arquivo(topico, resultado)
        print(f"\nPesquisa salva em: {nome_arquivo}")
        
        return resultado

def main():
    # Criar o agente pesquisador
    pesquisador = AgentePesquisador()
    
    # Solicitar tópico de pesquisa do usuário
    print("\nBem-vindo ao Assistente de Pesquisa!")
    print("Por favor, insira o tópico que você gostaria de pesquisar.")
    topico = input("Tópico de pesquisa: ")
    
    print("\nIniciando pesquisa abrangente. Por favor, aguarde...\n")
    
    try:
        # Realizar a pesquisa
        resultado = pesquisador.pesquisar(topico)
        print("\nPesquisa concluída com sucesso!")
        print(resultado)
    except Exception as e:
        print(f"\nErro durante a pesquisa: {e}")
        print("Por favor, verifique sua conexão com a internet e as chaves de API.")

if __name__ == "__main__":
    main()