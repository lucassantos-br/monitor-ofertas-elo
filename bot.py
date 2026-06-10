import pandas as pd
import re
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def validar_status(texto_validade):
    padrao = re.search(r'(\d{2}/\d{2}/\d{2,4})', texto_validade)
    if not padrao:
        return "Indeterminado"
        
    data_str = padrao.group(1)
    hoje = datetime.now().date()
    
    for formato in ('%d/%m/%Y', '%d/%m/%y'):
        try:
            data_obj = datetime.strptime(data_str, formato).date()
            if data_obj >= hoje:
                return "Vigente"
            else:
                return "Expirado"
        except ValueError:
            continue
            
    return "Indeterminado"

def extrair_validade_interna(pagina, url_completa):
    try:
        pagina.goto(url_completa, wait_until="domcontentloaded", timeout=15000)
        html_interno = pagina.content()
        soup = BeautifulSoup(html_interno, 'html.parser')
        
        texto_limpo = soup.get_text(separator=' ', strip=True)
        padrao_data = re.search(r'(?i)(?:válido até|validade).*?(\d{2}/\d{2}/\d{2,4})', texto_limpo)
        
        if padrao_data:
            return padrao_data.group(1)
            
        for elemento in soup.find_all(['p', 'span', 'li', 'div']):
            texto_elemento = elemento.get_text(strip=True)
            texto_lower = texto_elemento.lower()
            if "válido até" in texto_lower or "validade:" in texto_lower:
                if len(texto_elemento) < 100: 
                    return texto_elemento
                    
        return "Não informada no texto padrão"
        
    except Exception:
        return "Erro ao carregar link"

def criar_tabela_html(df, cor_fundo):
    if df.empty:
        return ""
    
    html = f"""
    <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif; font-size: 13px; text-align: left; margin-bottom: 20px;">
        <thead>
            <tr style="background-color: {cor_fundo}; color: #ffffff;">
                <th style="padding: 8px; border: 1px solid #dddddd;">Categoria</th>
                <th style="padding: 8px; border: 1px solid #dddddd;">Parceiro</th>
                <th style="padding: 8px; border: 1px solid #dddddd;">Oferta</th>
                <th style="padding: 8px; border: 1px solid #dddddd;">Validade</th>
                <th style="padding: 8px; border: 1px solid #dddddd;">Status</th>
                <th style="padding: 8px; border: 1px solid #dddddd;">Ação</th>
            </tr>
        </thead>
        <tbody>
    """
    for _, row in df.iterrows():
        html += f"""
            <tr style="background-color: #f9f9f9; color: #333333;">
                <td style="padding: 8px; border: 1px solid #dddddd;">{row.get('Categoria', '')}</td>
                <td style="padding: 8px; border: 1px solid #dddddd;"><strong>{row.get('Parceiro', '')}</strong></td>
                <td style="padding: 8px; border: 1px solid #dddddd;">{row.get('Benefício / Oferta', '')}</td>
                <td style="padding: 8px; border: 1px solid #dddddd;">{row.get('Validade', '-')}</td>
                <td style="padding: 8px; border: 1px solid #dddddd;">{row.get('Status', '-')}</td>
                <td style="padding: 8px; border: 1px solid #dddddd;"><a href="{row.get('Link', '#')}" style="color: #005A9C; text-decoration: none;">Acessar Link</a></td>
            </tr>
        """
    html += """
        </tbody>
    </table>
    """
    return html

def enviar_notificacao_outlook(assunto, corpo_html, caminho_anexo=None):
    email_remetente = "lucassantosdasilva697@gmail.com"
    email_destinatario = "lucas.santossilva@verdecard.com.br,samuel.aiedo@verdecard.com.br,mathias.silva@verdecard.com.br,alexia.muniz@verdecard.com.br,giovani.zanella@verdecard.com.br,weslei.nunes@verdecard.com.br"
    
    senha = os.environ.get("SENHA_OUTLOOK") 
    
    if not senha:
        print("❌ Senha não encontrada! Configure o secret SENHA_OUTLOOK no GitHub.")
        return

    smtp_server = "smtp.gmail.com"
    porta = 587
    
    msg = MIMEMultipart()
    msg['From'] = email_remetente
    msg['To'] = email_destinatario
    msg['Subject'] = assunto
    msg.attach(MIMEText(corpo_html, 'html'))
    
    if caminho_anexo and os.path.exists(caminho_anexo):
        with open(caminho_anexo, "rb") as anexo:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(anexo.read())
        encoders.encode_base64(part)
        nome_arquivo_anexo = os.path.basename(caminho_anexo)
        part.add_header("Content-Disposition", f"attachment; filename={nome_arquivo_anexo}")
        msg.attach(part)
    
    try:
        server = smtplib.SMTP(smtp_server, porta)
        server.starttls() 
        server.login(email_remetente, senha)
        server.send_message(msg)
        server.quit()
        print("✉️ E-mail enviado com sucesso para a equipe!")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")

def monitorar_beneficios_elo():
    print("Iniciando navegador e acessando o site da Elo...")
    
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        pagina = navegador.new_page()
        
        print("\n[Fase 1] Mapeando ofertas na página principal...")
        url_base = "https://www.elo.com.br"
        pagina.goto(f"{url_base}/ofertas/", wait_until="load", timeout=60000)
        
        try:
            pagina.wait_for_selector('text="Explorar benefício"', timeout=30000)
        except Exception:
            print("Tempo esgotado. Site fora do ar ou estrutura mudou.")
            navegador.close()
            return

        botao_mais = pagina.locator("button").filter(
            has_text=re.compile(r"mostrar mais|carregar mais|ver mais", re.IGNORECASE)
        ).first
        
        cliques = 0
        while cliques < 30:
            try:
                if botao_mais.is_visible(timeout=2000):
                    botao_mais.scroll_into_view_if_needed()
                    botao_mais.click()
                    cliques += 1
                    pagina.wait_for_timeout(1500)
                else:
                    break
            except Exception:
                break
            
        html = pagina.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        botoes = [tag for tag in soup.find_all(['a', 'button']) if "Explorar benefício" in tag.get_text()]
        ofertas_basicas = []
        
        for botao in botoes:
            link_parcial = botao.get('href')
            if not link_parcial:
                pai_link = botao.find_parent('a', href=True)
                if pai_link:
                    link_parcial = pai_link.get('href')
                else:
                    continue 
                
            link_completo = link_parcial if link_parcial.startswith("http") else f"{url_base}{link_parcial}"
            
            container = botao.parent
            while container and container.name != 'body':
                if "Explorar benefício" in container.get_text():
                    if len(list(container.stripped_strings)) >= 3:
                        break
                container = container.parent
                
            if not container or container.name == 'body':
                continue

            for tag in container.find_all(['strong', 'b', 'em', 'i', 'span']):
                tag.unwrap()
            for tag in container.find_all('br'):
                tag.replace_with(' ')
                
            partes = [p for p in list(container.stripped_strings) if "Explorar" not in p]
            
            if len(partes) >= 3:
                if "Exclusivo" in partes[1] and len(partes) >= 4:
                    categoria = f"{partes[0]} ({partes[1]})"
                    parceiro = partes[2]
                    descricao = " ".join(partes[3:])
                else:
                    categoria = partes[0]
                    parceiro = partes[1]
                    descricao = " ".join(partes[2:])
                    
                ofertas_basicas.append({
                    "Categoria": categoria,
                    "Parceiro": parceiro,
                    "Benefício / Oferta": descricao,
                    "Link": link_completo 
                })
                
        if not ofertas_basicas:
            print("\n[Aviso] Nenhuma oferta foi localizada.")
            navegador.close()
            return
            
        df_temporario = pd.DataFrame(ofertas_basicas).drop_duplicates(subset=['Link'])
        ofertas_unicas = df_temporario.to_dict('records')
        
        total_ofertas = len(ofertas_unicas)
        print(f"Total de {total_ofertas} ofertas únicas mapeadas.")
        print("\n[Fase 2] Acessando cada página para buscar a Validade e validar Status...")
        
        for index, oferta in enumerate(ofertas_unicas, 1):
            print(f"Lendo [{index}/{total_ofertas}]: {oferta['Parceiro']}...", end=" ", flush=True)
            validade_texto = extrair_validade_interna(pagina, oferta['Link'])
            status_vigencia = validar_status(validade_texto)
            oferta['Validade'] = validade_texto
            oferta['Status'] = status_vigencia
            print(f"({validade_texto}) -> [{status_vigencia.upper()}]")
            
        navegador.close()

    print("\n[Fase 3] Preparando arquivos e e-mails...")
    df_hoje = pd.DataFrame(ofertas_unicas)
    
    pasta_atual = os.path.dirname(os.path.abspath(__file__))
    nome_arquivo = os.path.join(pasta_atual, "relatorio_elo_completo.csv")
    
    df_hoje['Movimentação'] = "Mantido"
    
    assunto_email = ""
    html_email = ""

    if os.path.exists(nome_arquivo):
        df_ontem = pd.read_csv(nome_arquivo, sep=";")
        
        links_ontem = set(df_ontem['Link'].dropna())
        links_hoje = set(df_hoje['Link'].dropna())
        
        adicionados = links_hoje - links_ontem
        removidos = links_ontem - links_hoje
        
        if adicionados or removidos:
            print("🚨 Mudanças detectadas! Montando alerta...")
            assunto_email = "🚨 [Alerta Bot] Alterações nas Ofertas Elo"
            
            html_email = """
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #005A9C;">🚨 Atualização nas Ofertas Elo</h2>
                <p>O robô detectou as seguintes alterações no portal de benefícios hoje:</p>
            """
            
            if adicionados:
                df_hoje.loc[df_hoje['Link'].isin(adicionados), 'Movimentação'] = "Novo Benefício"
                novos_df = df_hoje[df_hoje['Link'].isin(adicionados)]
                html_email += f"<h3 style='color: #4CAF50; margin-top: 25px;'>➕ {len(adicionados)} NOVO(S) BENEFÍCIO(S) ADICIONADO(S):</h3>"
                html_email += criar_tabela_html(novos_df, "#4CAF50")
                    
            if removidos:
                removidos_df = df_ontem[df_ontem['Link'].isin(removidos)]
                html_email += f"<h3 style='color: #F44336; margin-top: 25px;'>➖ {len(removidos)} BENEFÍCIO(S) REMOVIDO(S):</h3>"
                html_email += criar_tabela_html(removidos_df, "#F44336")
                
            html_email += "<br><p><em>A planilha completa e atualizada com todos os dados segue em anexo.</em></p></body></html>"
            
        else:
            print("Nenhum benefício foi adicionado ou removido. Preparando e-mail de status...")
            assunto_email = "✅ [Status Diário] Ofertas Elo (Sem Mudanças)"
            html_email = """
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <h2 style="color: #005A9C;">📊 Status Diário: Ofertas Elo</h2>
                <p>A varredura foi concluída com sucesso. Nenhuma mudança (adição ou remoção) foi detectada no portal de benefícios hoje.</p>
                <p>A base de dados completa segue em anexo para consulta da equipe.</p>
            </body>
            </html>
            """
            
    else:
        print(f"Primeira execução detectada. Criando arquivo base '{nome_arquivo}'...")
        df_hoje['Movimentação'] = "Novo Benefício"
        assunto_email = "🚀 [Start Bot] Primeira Carga de Ofertas Elo"
        html_email = """
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #005A9C;">🚀 Primeira Varredura: Ofertas Elo</h2>
            <p>O robô realizou a carga inicial de dados com sucesso.</p>
            <p>A base completa gerada segue em anexo.</p>
        </body>
        </html>
        """

    ordem_colunas = ['Categoria', 'Parceiro', 'Benefício / Oferta', 'Validade', 'Status', 'Movimentação', 'Link']
    df_hoje = df_hoje[ordem_colunas].sort_values(by="Parceiro").reset_index(drop=True)
    df_hoje.to_csv(nome_arquivo, index=False, encoding="utf-8-sig", sep=";")
    print("Sucesso! O relatório foi salvo localmente.")

    enviar_notificacao_outlook(assunto=assunto_email, corpo_html=html_email, caminho_anexo=nome_arquivo)

if __name__ == "__main__":
    monitorar_beneficios_elo()
