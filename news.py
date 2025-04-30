import streamlit as st
from GoogleNews import GoogleNews
import pandas as pd
from textblob import TextBlob
from datetime import datetime
import nltk
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import base64
import io
nltk.download('punkt')

st.set_page_config(page_title="Showtime News Search & Analysis", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    .news-table {
        font-family: 'Segoe UI', sans-serif;
        border-collapse: collapse;
        width: 100%;
    }
    .news-table td, .news-table th {
        border: 1px solid #ddd;
        padding: 8px;
        vertical-align: top;
    }
    .news-table tr:nth-child(even) {
        background-color: #f2f2f2;
    }
    .news-table tr:hover {
        background-color: #ddd;
    }
    .news-table th {
        padding-top: 12px;
        padding-bottom: 12px;
        text-align: left;
        background-color: #4CAF50;
        color: white;
    }
    .st-emotion-cache-18ni7ap {
        padding: 1rem 2rem 1rem 2rem;
    }
    .download-btn {
        margin-top: 10px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h2 style='text-align:center;color:#fff;background:#262730;padding:10px;border-radius:10px;'>📰 Showtime's News Search and Analysis Portal</h2>
""", unsafe_allow_html=True)

# Header - Inputs
st.subheader("Search Filters")
col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
with col1:
    query = st.text_input("Enter search keyword", "Dharavi Redevelopment")
with col2:
    start_date = st.date_input("Start date", datetime(2025, 1, 1))
with col3:
    end_date = st.date_input("End date", datetime(2025, 4, 29))
with col4:
    max_pages = st.slider("Select number of pages to fetch", 1, 10, 3)

lang = "en"
region = "IN"

# Function to generate download link for dataframe
def get_table_download_link(df, filename, link_text):
    """Generate a link to download the dataframe as CSV or Excel"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="download-btn">{link_text}</a>'
    return href

# Excel download function
def get_excel_download_link(df, filename, link_text):
    """Generate a link to download the dataframe as Excel"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='News')
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" class="download-btn">{link_text}</a>'
    return href

if st.button("Search News"):
    with st.spinner("Fetching news articles..."):
        googlenews = GoogleNews(lang=lang, region=region)
        googlenews.set_time_range(start_date.strftime('%m/%d/%Y'), end_date.strftime('%m/%d/%Y'))
        googlenews.search(query)

        all_results = []
        seen_titles = set()
        for page in range(1, max_pages + 1):
            googlenews.get_page(page)
            for result in googlenews.results():
                if result['title'] not in seen_titles:
                    seen_titles.add(result['title'])
                    all_results.append(result)

        df = pd.DataFrame(all_results).drop_duplicates(subset='title')

    if not df.empty:
        st.success(f"Fetched {len(df)} unique articles.")

        # Sentiment Analysis
        df['polarity'] = df['desc'].apply(lambda x: TextBlob(x).sentiment.polarity)
        df['sentiment'] = df['polarity'].apply(lambda x: 'Positive' if x > 0 else ('Negative' if x < 0 else 'Neutral'))

        sentiment_colors = {'Positive': 'green', 'Negative': 'red', 'Neutral': 'gray'}

        # Format the DataFrame for display
        df_display = df[['title', 'media', 'date', 'desc', 'link', 'sentiment']].copy()
        df_display['Sentiment'] = df_display['sentiment'].apply(lambda x: f"<span style='color:{sentiment_colors[x]}'>{x}</span>")
        df_display['Title'] = df_display.apply(lambda row: f"<a href='{row['link']}' target='_blank'>{row['title']}</a>", axis=1)
        df_display = df_display.rename(columns={
            'media': 'Source',
            'date': 'Published Date',
            'desc': 'Description'
        })
        
        # Create a clean version for downloads (without HTML formatting)
        df_download = df[['title', 'media', 'date', 'desc', 'link', 'sentiment']].copy()
        df_download = df_download.rename(columns={
            'title': 'Title',
            'media': 'Source',
            'date': 'Published Date',
            'desc': 'Description',
            'link': 'URL',
            'sentiment': 'Sentiment'
        })
        
        # Display table
        df_display_html = df_display[['Title', 'Source', 'Published Date', 'Description', 'Sentiment']]
        st.subheader("Search Results")
        st.markdown(df_display_html.to_html(escape=False, index=False, classes='news-table'), unsafe_allow_html=True)
        
        # Download buttons
        st.markdown("### Download Results")
        download_col1, download_col2 = st.columns(2)
        
        with download_col1:
            st.markdown(get_table_download_link(df_download, f"news_search_{query}_{datetime.now().strftime('%Y%m%d')}.csv", 
                                              "📥 Download as CSV"), unsafe_allow_html=True)
        
        with download_col2:
            st.markdown(get_excel_download_link(df_download, f"news_search_{query}_{datetime.now().strftime('%Y%m%d')}.xlsx", 
                                              "📊 Download as Excel"), unsafe_allow_html=True)

        # ===================== Charts Section =====================
        st.subheader("Overall Tone Summary")

        # 1. Total Count
        total_articles = len(df)
        counts = df['sentiment'].value_counts().reindex(['Positive', 'Neutral', 'Negative'], fill_value=0)

        col_pos, col_neu, col_neg = st.columns(3)
        col_pos.metric("Positive", counts['Positive'])
        col_neu.metric("Neutral", counts['Neutral'])
        col_neg.metric("Negative", counts['Negative'])
        st.markdown(f"**Total Articles:** {total_articles}")

        # 2. Pie Chart (Interactive)
        pie_fig = px.pie(
            names=counts.index,
            values=counts.values,
            title="Overall Sentiment Distribution",
            color=counts.index,
            color_discrete_map=sentiment_colors,
            hole=0.4
        )
        pie_fig.update_layout(width=600, height=400)
        st.plotly_chart(pie_fig, use_container_width=True)

        # 3. Portal Statistics (interactive stacked bar)
        st.subheader("Portal Statistics")

        source_stats = df.groupby(['media', 'sentiment']).size().unstack(fill_value=0)
        source_stats = source_stats.reindex(columns=['Negative', 'Neutral', 'Positive'], fill_value=0)

        stacked_fig = go.Figure()
        for sentiment in ['Negative', 'Neutral', 'Positive']:
            stacked_fig.add_trace(go.Bar(
                name=sentiment,
                x=source_stats.index,
                y=source_stats[sentiment],
                marker_color=sentiment_colors[sentiment],
                hoverinfo='x+y+name'
            ))

        stacked_fig.update_layout(
            barmode='stack',
            title="Articles per Source by Sentiment",
            xaxis_title="Source",
            yaxis_title="Number of Articles",
            width=800,
            height=500
        )
        st.plotly_chart(stacked_fig, use_container_width=True)

        # 4. Tone Distribution (%) - interactive horizontal bar
        st.subheader("Tone Distribution by Source (%)")

        tone_percent = source_stats.div(source_stats.sum(axis=1), axis=0) * 100
        tone_percent = tone_percent.fillna(0)

        hbar_fig = go.Figure()
        for sentiment in ['Negative', 'Neutral', 'Positive']:
            hbar_fig.add_trace(go.Bar(
                name=sentiment,
                y=tone_percent.index,
                x=tone_percent[sentiment],
                orientation='h',
                marker_color=sentiment_colors[sentiment],
                hovertemplate='%{y}: %{x:.2f}% (%{name})'
            ))

        hbar_fig.update_layout(
            barmode='stack',
            title="Tone Distribution (%) per Source",
            xaxis_title="Percentage",
            yaxis_title="Source",
            width=800,
            height=600
        )
        st.plotly_chart(hbar_fig, use_container_width=True)

    else:
        st.warning("No articles found for the given query and date range.")