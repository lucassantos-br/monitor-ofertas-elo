# 🤖 Crawler & Monitor de Benefícios — Portal Elo

Este repositório contém um bot de automação e web scraping desenvolvido em Python para mapear, analisar e alertar sobre mudanças nas ofertas e benefícios disponíveis no portal oficial da bandeira Elo.

## 🎯 O Problema
Para manter a competitividade do produto de cartão de crédito, é necessário acompanhar de perto as parcerias e vantagens ativas da bandeira. Realizar essa verificação manualmente no site é um processo lento, repetitivo e sujeito a erros, dificultando a identificação rápida de novas oportunidades ou a remoção de parceiros.

## 💡 A Solução
O crawler atua como uma solução de automação (RPA) que realiza a varredura do site da Elo de forma 100% autônoma. Ele extrai as ofertas, entra em cada regulamento para ler as datas de validade, cruza os dados com o histórico do dia anterior e envia um relatório executivo automático por e-mail, destacando visualmente quais benefícios foram adicionados ou removidos.

## 🛠️ Tecnologias e Ferramentas Utilizadas
* **Python:** Linguagem base da automação.
* **Playwright:** Automação de navegador para lidar com carregamento dinâmico (interação com botões "Mostrar Mais").
* **BeautifulSoup4 (BS4):** Parsing de HTML para extração dos textos de regulamento e condições das ofertas.
* **Pandas:** Manipulação dos dados tabulares e cruzamento de bases (Set/Anti-Join) para identificar variações diárias.
* **Expressões Regulares (RegEx):** Para varredura e extração de datas de vigência ocultas nos textos.
* **GitHub Actions (CI/CD):** Arquitetura serverless para rodar o script automaticamente na nuvem todos os dias úteis.

## ⚙️ Como Funciona o Fluxo de Execução
1. O agendador (Cron) do **GitHub Actions** dispara o script `bot.py` todas as manhãs.
2. O **Playwright** abre o portal da Elo em background (headless) e coleta os links das ofertas.
3. O bot acessa cada link para classificar o status (`Vigente`, `Expirado` ou `Indeterminado`).
4. O **Pandas** compara a base de dados de "hoje" com o arquivo `relatorio_elo_completo.csv` gerado "ontem".
5. Se houver variação, um e-mail com tabelas HTML customizadas (Verde para adições, Vermelho para remoções) e o CSV atualizado em anexo é disparado para a equipe comercial e de produto.
6. A base histórica é atualizada automaticamente no repositório.

## 🚀 Como Rodar Localmente

1. Clone este repositório:
   ```bash
   git clone [https://github.com/lucassantos-br/monitor-ofertas-elo.git](https://github.com/lucassantos-br/monitor-ofertas-elo.git)

2. Instale as dependências:
    ```bash
    pip install -r requirements.txt
    playwright install chromium

3. Configure a variável de ambiente com a sua senha de app do e-mail:
    Windows: set SENHA_OUTLOOK="sua_senha"

4. Execute o script:
    ```bash
    python bot.py
