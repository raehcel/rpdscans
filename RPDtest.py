import streamlit as st
import feedparser
import logging
import requests
from html import unescape
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime
from collections import defaultdict
import os
from pprint import pformat

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator='\n', strip=True)

def parse_feed(url, domain):
    logger.debug(f"Attempting to parse feed: {url}")
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            logger.warning(f"Feed parsing error for {url}: {feed.bozo_exception}")
        articles = []
        for entry in feed.entries:
            title = entry.get('title', '')
            content = entry.get('content', [{}])[0].get('value', '')
            if not content:
                content = entry.get('summary', '') or entry.get('description', '')
            content = unescape(content)
            content = clean_html_content(content)
            link = entry.get('link', '')
            pub_date = entry.get('published', '')
            
            articles.append({
                'title': title,
                'content': content,
                'link': link,
                'date': pub_date,
                'domain': domain,
                'source_url': url
            })
        logger.info(f"Collected {len(articles)} articles from {url}")
        return articles
    except Exception as e:
        logger.error(f"Error parsing RSS feed {url}: {str(e)}")
        return []

def get_top_articles(articles_text, prompt):
    try:
        chat_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant tasked with selecting the top 10 articles most relevant to stakeholders in Singapore's food safety and security."},
                {"role": "user", "content": f"{prompt}\n\nHere is a list of articles:\n\n{articles_text}\n\nPlease select the top 10 articles that are most relevant to stakeholders in Singapore's food safety and security. For each article, provide the name, link, a brief description, and explain why it's important."}
            ],
            max_tokens=2000,
            n=1,
            temperature=0.5,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {str(e)}"

def parse_date(date_string):
    try:
        return parser.parse(date_string).replace(tzinfo=None)
    except:
        return None

def main():
    st.set_page_config(page_title="SG Food Tech Scanner", page_icon="🍜🔬")
    
    st.title("🍜🔬 Singapore Food Tech Scanner 🌾🐠")
    
    st.markdown("""
    Welcome to the Singapore Food Tech Scanner! 🇸🇬🚀

    This app helps stakeholders in Singapore's food safety and security ecosystem stay updated on the latest technological advancements and applications in four key domains:
    
    - 🌾 Agriculture
    - 🐠 Aquaculture
    - 🍽️ Future Foods
    - 🧪 Food Safety
    
    The app fetches articles from various reputable sources, analyzes them, and presents the most relevant ones to keep you informed about developments that could impact Singapore's food landscape.
    """)

    # ... [Rest of the main function remains the same] ...

    # Define sources with RSS feeds
    rss_sources = [
        ('https://vegconomist.com/feed/', 'Future Food'),
        ('https://www.just-food.com/feed/', 'Future Food'),
        ('https://www.fooddive.com/feeds/news/', 'Future Food'),
        ('https://www.sciencenews.org/feed', 'Food Safety'),
        ('https://www.food-safety.com/rss/topic/296-news', 'Food Safety'),
        ('https://www.nature.com/natfood.rss', 'Agriculture'),
        ('https://phys.org/rss-feed/biology-news/agriculture/', 'Agriculture'),
        ('https://www.agriculturedive.com/feeds/news/', 'Agriculture'),
        ('https://feeds.thefishsite.com/thefishsite-all', 'Aquaculture'),
        ('https://aquaculturemag.com/feed/', 'Aquaculture')
    ]

    # Initialize session state to store articles
    if 'all_articles' not in st.session_state:
        st.session_state.all_articles = []

    # Fetch Articles button
    if st.button("🔍 Fetch Articles"):
        with st.spinner("Fetching articles... 🕵️‍♂️"):
            # ... [Fetching logic remains the same] ...

        # Display summary message
        st.success("✅ Articles fetched successfully!")
        st.write(f"📊 Fetched {len(all_articles)} articles in total:")
        for domain, count in article_counts.items():
            emoji = {"Agriculture": "🌾", "Aquaculture": "🐠", "Future Food": "🍽️", "Food Safety": "🧪"}.get(domain, "📰")
            st.write(f"- {emoji} {domain}: {count} articles")
        st.write(f"📅 Date range: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}")

    # Display original articles
    if st.session_state.all_articles:
        st.header("📚 Original Articles")
        for i, article in enumerate(st.session_state.all_articles, 1):
            with st.expander(f"Article {i}: {article['title']}"):
                st.write(f"📅 Date: {article['date']}")
                st.write(f"🏷️ Domain: {article['domain']}")
                st.write(f"🔗 Source: {article['source_url']}")
                st.write(f"🔗 Link: {article['link']}")
                st.write("📝 Content:")
                st.write(article['content'])

    # Prompt editing
    st.header("🎛️ Customize Prompt")
    default_prompt = "The intent of the tech scans is to share the potential relevance and application of technology and knowledge that applies to the four domains (agriculture, aquaculture, future foods, and food safety) that will impact Singapore's ecosystem. Evaluation should ignore any developments in Singapore as these are likely already known to the stakeholders. Additionally, disregard articles that are just think pieces about the potential of technology without any real application. Prioritize articles that highlight specific technological advancements or applications over those that simply discuss emerging risks."
    prompt = st.text_area("Edit the prompt if desired:", value=default_prompt, height=200)

    # Get top articles
    if st.button("🏆 Get Top Articles") and st.session_state.all_articles:
        articles_text = pformat(st.session_state.all_articles)
        with st.spinner("Processing articles... 🤖"):
            top_articles = get_top_articles(articles_text, prompt)
        st.header("🏅 Top 10 Articles")
        st.write(top_articles)

if __name__ == "__main__":
    main()
