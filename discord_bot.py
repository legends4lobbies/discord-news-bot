import requests
from bs4 import BeautifulSoup
import json
import time
import openai
from datetime import datetime

# URL du site à surveiller
site_url = 'https://www.leagueoflegends.com/fr-fr/news/game-updates/'
# URL du webhook Discord
discord_webhook_url = 'https://discord.com/api/webhooks/...'

# Clé API OpenAI
openai.api_key = 'VOTRE_CLE_OPENAI'

# Fonction pour extraire les dernières actualités du site
def get_latest_news():
    response = requests.get(site_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.find_all('a', class_='style__Wrapper-n3ovyt-3')  # Ajustez la classe CSS si nécessaire
    latest_news = []

    for article in articles:
        link = article['href']
        if link.startswith('/fr-fr/news/game-updates/'):
            full_link = f"https://www.leagueoflegends.com{link}"
            latest_news.append(full_link)

    return latest_news

# Fonction pour récupérer et formater le contenu d'un article
def generate_content(article_url):
    response = requests.get(article_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extraire les détails nécessaires
    article_title = soup.find('h1').text.strip()
    article_content = soup.find('div', class_='article-content')
    author_tag = soup.find('meta', {'name': 'author'})
    author = author_tag['content'] if author_tag else 'Riot Games'
    time_tag = soup.find('time')
    published_date = datetime.fromisoformat(time_tag['datetime']) if time_tag else datetime.now()
    days_since_published = (datetime.now() - published_date).days

    # Identifier dynamiquement les sections et leur contenu
    sections = {}
    current_section = None
    section_content = ""

    for element in article_content.children:
        if element.name in ['h2', 'h3']:
            if current_section and section_content:
                sections[current_section] = section_content.strip()
            current_section = element.text.strip()
            section_content = ""
        elif element.name == 'p':
            section_content += element.text.strip() + "\n"

    # Ajouter la dernière section si elle existe
    if current_section and section_content:
        sections[current_section] = section_content.strip()

    # Préparer le prompt pour GPT-4
    prompt = (
        f"Title: {article_title}\n\n"
        f"Author: {author}\n\n"
        f"Days since published: {days_since_published}\n\n"
        f"Content sections:\n"
    )

    for section_title, section_content in sections.items():
        prompt += f"\n{section_title}:\n{section_content}\n"

    prompt += "\nGenerate a Discord post with a structured format including a call to action."

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        temperature=0.7
    )

    return response.choices[0].message['content'].strip()

# Fonction pour publier sur Discord
def post_to_discord(content):
    data = {
        'content': content
    }
    response = requests.post(discord_webhook_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
    if response.status_code == 204:
        print(f"Publié sur Discord : {content}")
    else:
        print(f"Erreur lors de la publication : {response.status_code} - {response.text}")

# Fonction principale pour vérifier les mises à jour
def check_for_updates():
    latest_news = get_latest_news()
    try:
        with open('published_news.json', 'r') as file:
            published_news = json.load(file)
    except FileNotFoundError:
        published_news = []

    new_news = [article for article in latest_news if article not in published_news]

    if new_news:
        for article_url in new_news:
            generated_content = generate_content(article_url)
            post_to_discord(generated_content)
            print(f"Nouveau post : {generated_content}")

        with open('published_news.json', 'w') as file:
            json.dump(latest_news, file)

# Exécuter la vérification toutes les x minutes
if __name__ == "__main__":
    check_for_updates()
