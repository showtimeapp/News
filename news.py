import streamlit as st
from GoogleNews import GoogleNews
import pandas as pd
from textblob import TextBlob
from datetime import datetime
import nltk
import plotly.express as px
import plotly.graph_objects as go
import io
import re
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
    /* Metrics row styling */
    .metrics-container {
        display: flex;
        justify-content: space-between;
        margin-bottom: 20px;
        gap: 15px;
    }
    .metric-box {
        flex: 1;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        color: white;
    }
    .metric-positive {
        background: linear-gradient(135deg, #4CAF50, #2E7D32);
    }
    .metric-neutral {
        background: linear-gradient(135deg, #78909C, #455A64);
    }
    .metric-negative {
        background: linear-gradient(135deg, #F44336, #C62828);
    }
    .metric-total {
        background: linear-gradient(135deg, #3F51B5, #1A237E);
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .metric-label {
        font-size: 14px;
        opacity: 0.9;
    }        
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h2 style='text-align:center;color:#fff;background:#262730;padding:10px;border-radius:10px;'>📰 Showtime's News Search and Analysis Portal</h2>
""", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1
if 'all_results' not in st.session_state:
    st.session_state.all_results = []
if 'seen_titles' not in st.session_state:
    st.session_state.seen_titles = set()
if 'sources_list' not in st.session_state:
    st.session_state.sources_list = []
if 'selected_sources' not in st.session_state:
    st.session_state.selected_sources = []
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'has_searched' not in st.session_state:
    st.session_state.has_searched = False
# New session state flag to trigger the load more functionality only when the button is clicked
if 'load_more_clicked' not in st.session_state:
    st.session_state.load_more_clicked = False
if 'button_key' not in st.session_state:
    st.session_state.button_key = 0  # Used to create unique button keys

# Function to clean Google News links
def clean_url(url):
    if not url:
        return ""
    
    # Handle YouTube links
    youtube_match = re.search(r'youtube.com/watch%3Fv%3D([^&]+)', url)
    if youtube_match:
        video_id = youtube_match.group(1)
        # Replace %26 with & for any YouTube parameters
        video_id = video_id.replace('%26', '&')
        return f"https://www.youtube.com/watch?v={video_id}"
    
    # Handle regular links - remove &ved and everything after it
    if '&ved=' in url:
        clean_link = url.split('&ved=')[0]
        return clean_link
    
    return url

# Function to reset when new search is performed
def reset_search_state():
    st.session_state.current_page = 1
    st.session_state.all_results = []
    st.session_state.seen_titles = set()
    st.session_state.sources_list = []
    st.session_state.has_searched = True
    st.session_state.load_more_clicked = False
    st.session_state.button_key += 1  # Change the button key to force a fresh button

# Header - Inputs
st.subheader("Search Filters")
col1, col2, col3 = st.columns([3, 2, 2])
with col1:
    query = st.text_input("Enter search keyword", "Dharavi Redevelopment")
with col2:
    start_date = st.date_input("Start date", datetime(2025, 1, 1))
with col3:
    end_date = st.date_input("End date", datetime(2025, 4, 29))

lang = "en"
region = "IN"

# Search button - moved above Source filter
if st.button("Search News"):
    reset_search_state()
    
    with st.spinner(f"Fetching news from page {st.session_state.current_page}..."):
        st.session_state.googlenews = GoogleNews(lang=lang, region=region)
        st.session_state.googlenews.set_time_range(start_date.strftime('%m/%d/%Y'), end_date.strftime('%m/%d/%Y'))
        st.session_state.googlenews.search(query)
        
        # Get first page
        st.session_state.googlenews.get_page(1)
        
        for result in st.session_state.googlenews.results():
            if result['title'] not in st.session_state.seen_titles:
                # Clean the URL before adding to results
                result['link'] = clean_url(result['link'])
                
                st.session_state.seen_titles.add(result['title'])
                st.session_state.all_results.append(result)
                
                # Add new source to sources list if not already there
                if result['media'] not in st.session_state.sources_list:
                    st.session_state.sources_list.append(result['media'])
        
        # Create DataFrame
        st.session_state.df = pd.DataFrame(st.session_state.all_results).drop_duplicates(subset='title')

# Source filter (shows up after first search)
if st.session_state.sources_list:
    st.subheader("Filter by Source")
    st.session_state.selected_sources = st.multiselect(
        "Select news sources to display", 
        options=st.session_state.sources_list,
        default=[]
    )

# Display results if we have data
if not st.session_state.df.empty:
    # Apply source filter if selected
    display_df = st.session_state.df.copy()
    if st.session_state.selected_sources:
        display_df = display_df[display_df['media'].isin(st.session_state.selected_sources)]
    
    # Sentiment Analysis
    display_df['polarity'] = display_df['desc'].apply(lambda x: TextBlob(str(x)).sentiment.polarity)
    display_df['sentiment'] = display_df['polarity'].apply(lambda x: 'Positive' if x > 0 else ('Negative' if x < 0 else 'Neutral'))

    sentiment_colors = {'Positive': 'green', 'Negative': 'red', 'Neutral': 'gray'}

    # Display metrics
    st.success(f"Showing {len(display_df)} articles from {len(st.session_state.selected_sources) if st.session_state.selected_sources else 'all'} sources.")
    
    # Format the DataFrame for display
    df_display = display_df[['title', 'media', 'date', 'desc', 'link', 'sentiment']].copy()
    df_display['Sentiment'] = df_display['sentiment'].apply(lambda x: f"<span style='color:{sentiment_colors[x]}'>{x}</span>")
    df_display['Title'] = df_display.apply(lambda row: f"<a href='{row['link']}' target='_blank'>{row['title']}</a>", axis=1)
    df_display = df_display.rename(columns={
        'media': 'Source',
        'date': 'Published Date',
        'desc': 'Description'
    })
    df_display = df_display[['Title', 'Source', 'Published Date', 'Description', 'Sentiment']]

    st.subheader("Search Results")
    st.markdown(df_display.to_html(escape=False, index=False, classes='news-table'), unsafe_allow_html=True)
    
    # Create a DataFrame for download (without HTML formatting)
    download_df = display_df[['title', 'media', 'date', 'desc', 'link', 'sentiment']].copy()
    download_df = download_df.rename(columns={
        'title': 'Title',
        'media': 'Source',
        'date': 'Published Date',
        'desc': 'Description',
        'link': 'URL',
        'sentiment': 'Sentiment'
    })
    
    # Excel download button and Load More News button side by side
    col1, col2 = st.columns([6, 1])
    
    with col1:
        # Download as Excel button
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            download_df.to_excel(writer, sheet_name="News Data", index=False)
        
        excel_data = excel_buffer.getvalue()
        st.download_button(
            label="📥 Download Results as Excel",
            data=excel_data,
            file_name=f"news_search_{query}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel",
            key="download-excel"
        )
    
    with col2:
        # Load next page button - moved here to rightmost position
        if st.session_state.has_searched:
            # Callback function to set the flag when the button is clicked
            def load_more_callback():
                st.session_state.load_more_clicked = True
            
            # Generate a dynamic key for the button to avoid reusing cached states
            button_key = f"load_more_button_{st.session_state.button_key}"
            
            # Button with a callback to set the flag
            st.button("Load More News", key=button_key, on_click=load_more_callback)
            
            # Execute the load more logic if the button was clicked
            if st.session_state.load_more_clicked:
                # Fetch the next page
                next_page = st.session_state.current_page + 1
                
                with st.spinner(f"Fetching news from page {next_page}..."):
                    # Get next page
                    st.session_state.googlenews.get_page(next_page)
                    
                    new_results_count = 0
                    for result in st.session_state.googlenews.results():
                        if result['title'] not in st.session_state.seen_titles:
                            # Clean the URL before adding to results
                            result['link'] = clean_url(result['link'])
                            
                            st.session_state.seen_titles.add(result['title'])
                            st.session_state.all_results.append(result)
                            new_results_count += 1
                            
                            # Add new source to sources list if not already there
                            if result['media'] not in st.session_state.sources_list:
                                st.session_state.sources_list.append(result['media'])
                    
                    # Update DataFrame
                    st.session_state.df = pd.DataFrame(st.session_state.all_results).drop_duplicates(subset='title')
                    
                    if new_results_count > 0:
                        st.session_state.current_page = next_page
                    else:
                        st.info(f"No new articles found on page {next_page}")
                    
                    # Reset the flag so it doesn't keep loading on every rerun
                    st.session_state.load_more_clicked = False

    # ===================== Charts Section =====================
    st.subheader("Overall Tone Summary")

    # 1. Total Count with improved aesthetics
    total_articles = len(display_df)
    counts = display_df['sentiment'].value_counts().reindex(['Positive', 'Neutral', 'Negative'], fill_value=0)
    
    # Create beautiful metric boxes in one row
    metric_html = """
    <div class="metrics-container">
        <div class="metric-box metric-positive">
            <div class="metric-value">{positive}</div>
            <div class="metric-label">Positive</div>
        </div>
        <div class="metric-box metric-neutral">
            <div class="metric-value">{neutral}</div>
            <div class="metric-label">Neutral</div>
        </div>
        <div class="metric-box metric-negative">
            <div class="metric-value">{negative}</div>
            <div class="metric-label">Negative</div>
        </div>
        <div class="metric-box metric-total">
            <div class="metric-value">{total}</div>
            <div class="metric-label">Total Articles</div>
        </div>
    </div>
    """.format(
        positive=counts['Positive'],
        neutral=counts['Neutral'],
        negative=counts['Negative'],
        total=total_articles
    )
    
    st.markdown(metric_html, unsafe_allow_html=True)

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

    source_stats = display_df.groupby(['media', 'sentiment']).size().unstack(fill_value=0)
    # Make sure we have all sentiment columns
    for sentiment in ['Negative', 'Neutral', 'Positive']:
        if sentiment not in source_stats.columns:
            source_stats[sentiment] = 0
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

    if not source_stats.empty:
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
elif st.session_state.has_searched:
    st.warning("No articles found for the given query and date range.")
