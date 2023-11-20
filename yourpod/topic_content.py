import requests

def get_random_wikipedia_article_title():
    url = "https://en.wikipedia.org/wiki/Special:Random"

    response = requests.get(url)
    article_url = response.url

    # Extract the article title from the URL
    # Wikipedia URLs have the format "https://en.wikipedia.org/wiki/Article_Title"
    article_title = article_url.split("/wiki/")[-1].replace("_", " ")

    return article_title
