from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import requests
from config import token, base_url, headersAuth, baseApi_url
from key import kwords

def get_id(url):
    ids = []
    reqid = requests.get(url, headers=headersAuth).json()

    for i in reqid:
        ids.append(i['id'])
    return ids

def get_articles():
    params = {
        'fields': 'summary,content',
    }

    ids = get_id(baseApi_url)
    articles = []

    for id in ids:
        article = requests.get(baseApi_url + id, headers=headersAuth, params=params).json()
        articles.append({'title': f'{article["summary"]}', 'text': f'{article["content"]}', "id": f"{id}"})

    return articles

def find_article(text):
    articles = get_articles()

    model = SentenceTransformer('all-MiniLM-L6-v2')
    target_embedding = model.encode([text])[0]
    similarities = []

    for article in articles:
        article_embedding = model.encode([article["text"]])[0]
        sim = cosine_similarity([target_embedding], [article_embedding])[0][0]
        similarities.append((article["title"], sim, article["text"], article['id']))

    return sorted(similarities, key=lambda x: x[1], reverse=True)

# target = "как работать с webrtc"
#
# results = find_article(target)
# print(results)
# print(articles)