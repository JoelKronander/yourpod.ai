import requests

def get_random_wikipedia_article_title():
    wiki_url = "https://en.wikipedia.org/wiki/Special:Random"

    response = requests.get(wiki_url)
    article_url = response.url

    # Extract the article title from the URL
    # Wikipedia URLs have the format "https://en.wikipedia.org/wiki/Article_Title"
    article_title = article_url.split("/wiki/")[-1].replace("_", " ")

    return article_title
