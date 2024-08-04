import os
import requests
from bs4 import BeautifulSoup
import json
import openai
from datetime import datetime

# Charger les secrets depuis les variables d'environnement
openai.api_key = os.getenv('OPENAI_API_KEY')
discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

# URL du site à surveiller
site_url = 'https://www.leagueoflegends.com/fr-fr/news/game-updates/'

def get_latest_news():
    response = requests.get(site_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Trouver tous les liens vers des articles de mise à jour de jeu
    articles = soup.find_all('a', class_='style__Wrapper-n3ovyt-3')  # Ajustez la classe CSS ici si nécessaire
    latest_news = []

    for article in articles:
        link = article['href']
        if link.startswith('/fr-fr/news/game-updates/'):
            full_link = f"https://www.leagueoflegends.com{link}"
            latest_news.append(full_link)

    print(f"Found articles: {latest_news}")
    return latest_news

def generate_content(article_url):
    print(f"Processing article: {article_url}")
    response = requests.get(article_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Trouver le titre de l'article
    article_title = soup.find('h1').text.strip()
    # Trouver le contenu de l'article
    article_content = soup.find('div', class_='article-content')  # Assurez-vous que ce sélecteur est correct
    author_tag = soup.find('meta', {'name': 'author'})
    author = author_tag['content'] if author_tag else 'Riot Games'
    time_tag = soup.find('time')
    published_date = datetime.fromisoformat(time_tag['datetime']) if time_tag else datetime.now()
    days_since_published = (datetime.now() - published_date).days

    # Identifier dynamiquement les sections et leur contenu
    sections = {}
    current_section = None
    section_content = ""

    # Récupérer les éléments de la page
    for element in article_content.children:
        if element.name in ['h2', 'h3']:  # Titre de section
            if current_section and section_content:
                sections[current_section] = section_content.strip()
            current_section = element.text.strip()
            section_content = ""
        elif element.name == 'p':  # Paragraphe de section
            section_content += element.text.strip() + "\n"

    if current_section and section_content:
        sections[current_section] = section_content.strip()

    print(f"Extracted sections: {sections}")

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

def post_to_discord(content):
    print(f"Posting content to Discord:\n{content}")
    data = {
        'content': content
    }
    response = requests.post(discord_webhook_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
    if response.status_code == 204:
        print(f"Publié sur Discord : {content}")
    else:
        print(f"Erreur lors de la publication : {response.status_code} - {response.text}")

def check_for_updates():
    latest_news = get_latest_news()
    try:
        with open('published_news.json', 'r') as file:
            published_news = json.load(file)
    except FileNotFoundError:
        published_news = []

    new_news = [article for article in latest_news if article not in published_news]

    print(f"New articles found: {new_news}")

    if new_news:
        for article_url in new_news:
            generated_content = generate_content(article_url)
            post_to_discord(generated_content)
            print(f"Nouveau post : {generated_content}")

        with open('published_news.json', 'w') as file:
            json.dump(latest_news, file)

if __name__ == "__main__":
    check_for_updates()
