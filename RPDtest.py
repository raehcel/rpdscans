import streamlit as st
import feedparser
import logging
import requests
from html import unescape
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime, timezone
from collections import defaultdict
import os
from pprint import pformat
from dateutil import parser

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize the OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def clean_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator='\n', strip=True)

def parse_date(date_string):
    try:
        return parser.parse(date_string).replace(tzinfo=timezone.utc)
    except:
        return None

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

def get_top_articles(articles_by_domain, prompt):
    try:
        articles_text = pformat(articles_by_domain)
        chat_completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant tasked with selecting the top 5 articles for each domain (agriculture, aquaculture, future foods, and food safety) most relevant to stakeholders in Singapore's food safety and security."},
                {"role": "user", "content": f"{prompt}\n\nHere is a list of articles organized by domain:\n\n{articles_text}"}
            ],
            max_tokens=2500,
            n=1,
            temperature=0.5,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {str(e)}"

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

    # Define sources with RSS feeds
    rss_sources = [
        ('https://vegconomist.com/feed/', 'Future Food'),
        ('https://www.just-food.com/feed/', 'Future Food'),
        ('https://www.fooddive.com/feeds/news/', 'Future Food'),
        ('https://www.sciencenews.org/feed', 'Food Safety'),
        ('https://www.food-safety.com/rss/topic/296-news', 'Food Safety'),
        ('https://phys.org/rss-feed/biology-news/agriculture/', 'Agriculture'),
        ('https://www.agriculturedive.com/feeds/news/', 'Agriculture'),
        ('https://feeds.thefishsite.com/thefishsite-all', 'Aquaculture'),
        ('https://aquaculturemag.com/feed/', 'Aquaculture'),  
        ('https://www.globalagtechinitiative.com/digital-farming/', 'Agriculture'),
        ('https://www.thecooldown.com/green-tech/', 'Agriculture'),
        ('https://www.food-safety.com/keywords/1870-grants', 'Food Safety'),
        ('https://agfundernews.com/category/agtech-2', 'Agriculture'),
        ('https://www.newscientist.com/subject/environment/', 'Agriculture'),
        ('https://hatcheryfm.com/fish/', 'Aquaculture'),
        ('https://hatcheryfm.com/shrimp/', 'Aquaculture'),
        ('https://interestingengineering.com/science', 'Agriculture')
    ]

    # Initialize session state variables
    if 'articles_by_domain' not in st.session_state:
        st.session_state.articles_by_domain = defaultdict(list)
    if 'articles_fetched' not in st.session_state:
        st.session_state.articles_fetched = False
    if 'article_summary' not in st.session_state:
        st.session_state.article_summary = ""
    if 'date_range' not in st.session_state:
        st.session_state.date_range = ""
    if 'current_domain' not in st.session_state:
        st.session_state.current_domain = "Agriculture"
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1

    # Fetch Articles button
    if st.button("🔍 Fetch Articles", key="fetch_articles_button"):
        with st.spinner("Fetching articles... 🕵️‍♂️"):
            articles_by_domain = defaultdict(list)
            article_counts = defaultdict(int)
            earliest_date = datetime.now(timezone.utc)
            latest_date = datetime.min.replace(tzinfo=timezone.utc)

            for url, domain in rss_sources:
                articles = parse_feed(url, domain)
                articles_by_domain[domain].extend(articles)
                article_counts[domain] += len(articles)

                # Update date range
                for article in articles:
                    pub_date = parse_date(article['date'])
                    if pub_date:
                        earliest_date = min(earliest_date, pub_date)
                        latest_date = max(latest_date, pub_date)

            st.session_state.articles_by_domain = articles_by_domain
            st.session_state.articles_fetched = True

            # Create and store the summary
            summary = f"Fetched {sum(article_counts.values())} articles in total:\n"
            for domain, count in article_counts.items():
                emoji = {"Agriculture": "🌾", "Aquaculture": "🐠", "Future Food": "🍽️", "Food Safety": "🧪"}.get(domain, "📰")
                summary += f"- {emoji} {domain}: {count} articles\n"
            st.session_state.article_summary = summary
            st.session_state.date_range = f"📅 Date range: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}"

        st.success("✅ Articles fetched successfully!")

    # Display summary if articles have been fetched
    if st.session_state.articles_fetched:
        with st.expander("📊 Article Summary", expanded=True):
            st.write(st.session_state.article_summary)
            st.write(st.session_state.date_range)

        # Display original articles
        st.header("📚 Original Articles")
        
        # Domain selection
        st.session_state.current_domain = st.selectbox("Select Domain", list(st.session_state.articles_by_domain.keys()))

        articles = st.session_state.articles_by_domain[st.session_state.current_domain]
        articles_per_page = 10
        total_pages = (len(articles) - 1) // articles_per_page + 1
        
        start_idx = (st.session_state.current_page - 1) * articles_per_page
        end_idx = start_idx + articles_per_page

        for i, article in enumerate(articles[start_idx:end_idx], start_idx + 1):
            with st.expander(f"Article {i}: {article['title']}"):
                st.write(f"📅 Date: {article['date']}")
                st.write(f"🔗 Source: {article['source_url']}")
                st.write(f"🔗 Link: {article['link']}")
                st.write("📝 Content:")
                st.write(article['content'][:500] + "..." if len(article['content']) > 500 else article['content'])

        # Page navigation
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            if st.button("◀️ Previous", disabled=(st.session_state.current_page == 1)):
                st.session_state.current_page -= 1
                st.rerun()
        
        with col3:
            st.write(f"Page {st.session_state.current_page} of {total_pages}")
        
        with col5:
            if st.button("Next ▶️", disabled=(st.session_state.current_page == total_pages)):
                st.session_state.current_page += 1
                st.rerun()

        # Prompt editing
        st.header("🎛️ Customize Prompt")
        default_prompt = """The intent of the tech scans is to share the potential relevance and application of technology and knowledge that applies to the four domains (agriculture, aquaculture, future foods, and food safety) that will impact Singapore's ecosystem. Please select the top five articles for each domain (agriculture, aquaculture, future foods, and food safety) that are most relevant to stakeholders in Singapore's food safety and security. Ensure the recommended articles cover diverse topics, avoiding duplication of subject matter.
        Evaluation criteria:
        1. Ignore any developments in Singapore as these are likely already known to the stakeholders.
        2. Disregard articles that are just think pieces about the potential of technology without any real application.
        3. Prioritize articles that highlight specific technological advancements or applications over those that simply discuss emerging risks.
        4. Ensure articles are reordered every day to showcase different areas of the domain. 

        For each article, provide:
        1. The article title
        2. Embed a hyperlink within the article's title
        3. Provide QR code that links to the article  
        4. Retrieve five sentences from the article of what is the research focus, name who are the organisations and the researchers involved, what is the significance of the research focus in domain space and the benefits of the research. Provide the complete expansion of the acronym. 
        5. Retrieve four sentences from the article that state the research achievements, challenges and results 
        6. Retrieve three sentences from the article that includes what are the future steps planned or can be expected in the research
        7. All sentences in past tense

        Organize the results by domain, clearly labeling each section."""
        prompt = st.text_area("Edit the prompt if desired:", value=default_prompt, height=300)

        # Get top articles
        if st.button("🏆 Get Top Articles", key="get_top_articles_button"):
            with st.spinner("Processing articles... 🤖"):
                top_articles = get_top_articles(st.session_state.articles_by_domain, prompt)
            st.header("🏅 Top 5 Articles for Each Domain")
            st.write(top_articles)

if __name__ == "__main__":
    main()
