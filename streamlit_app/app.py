import streamlit as st
import requests
from bs4 import BeautifulSoup
import os
import asyncio
import sys
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
import zipfile
from io import BytesIO
import time

# Fix for Windows Playwright NotImplementedError
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Page configuration
st.set_page_config(
    page_title="BdStall Web Scraper",
    page_icon="🕷️",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sofia+Sans:wght@300;400;500;600;700&display=swap');

/* Global font family */
* {
    font-family: 'Sofia Sans', sans-serif !important;
}

/* Center all content */
.main .block-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
}

.main-header {
    font-size: 2.5rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
    font-weight: 600;
}
.sub-header {
    font-size: 1.5rem;
    color: #ff7f0e;
    margin-bottom: 1rem;
    text-align: center;
    font-weight: 500;
}
.success-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    text-align: center;
}
.error-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
    text-align: center;
}
.info-box {
    padding: 1rem;
    border-radius: 0.5rem;
    background-color: #d1ecf1;
    border: 1px solid #bee5eb;
    color: #0c5460;
    text-align: center;
}

/* Center buttons and inputs */
.stButton > button {
    display: block;
    margin: 0 auto;
}

/* Center progress bars and status messages */
.stProgress {
    text-align: center;
}

/* Center sidebar content */
.css-1d391kg {
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">🕷️ BdStall Web Scraper</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Extract product data from BdStall pages and convert to markdown format</p>', unsafe_allow_html=True)

# Sidebar configuration
with st.sidebar:
    st.markdown('<h2 class="sub-header">⚙️ Configuration</h2>', unsafe_allow_html=True)
    
    # URL input
    base_url = st.text_input(
        "Base URL",
        help="Enter the BdStall category URL to scrape products from"
    )
    
    # Advanced options
    st.markdown("### Advanced Options")
    output_folder = st.text_input("Output Folder Name", value="f:\\GitHub\\Projects\\BdStall Chatbot\\Dataset\\Web scraping\\bdstall_markdown")
    
    # Scraping options
    st.markdown("### Scraping Options")
    max_products = st.number_input("Max Products to Scrape", min_value=1, max_value=1000, value=40, help="Maximum number of products to scrape")
    concurrent_scraping = st.checkbox("Enable Concurrent Scraping", help="Faster but may hit rate limits")
    skip_existing = st.checkbox("Skip Existing Files", value=True)

# Headers for requests
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_product_links(url, max_products=40):
    """Extract product links from the given URL"""
    try:
        st.info(f"🔍 Fetching URL: {url}")
        res = requests.get(url, headers=HEADERS, timeout=10)
        
        if res.status_code != 200:
            st.error(f"❌ Failed to fetch URL. Status code: {res.status_code}")
            return []
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Find all anchor tags with detail links
        all_anchors = soup.find_all("a", href=True)
        detail_links = []
        
        for a in all_anchors:
            href = a.get("href")
            if href and "/details/" in href:
                # Ensure the link is absolute
                if href.startswith("http"):
                    full_url = href
                else:
                    base_domain = "/".join(url.split("/")[:3])
                    full_url = base_domain + href
                detail_links.append(full_url)
        
        # Remove duplicates and limit
        unique_links = list(dict.fromkeys(detail_links))[:max_products]
        
        st.success(f"✅ Found {len(unique_links)} unique product links")
        return unique_links
        
    except requests.RequestException as e:
        st.error(f"❌ Network error: {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ Error parsing page: {str(e)}")
        return []

async def scrape_product(crawler, url, output_dir, skip_existing=True):
    """Scrape a single product page"""
    try:
        # Create filename from URL
        file_name = url.strip("/").split("/")[-1] + ".md"
        file_path = os.path.join(output_dir, file_name)
        
        # Skip if already exists
        if skip_existing and os.path.exists(file_path):
            return f"⏭️ Skipped {file_name} (already exists)"
        
        run_conf = CrawlerRunConfig(cache_mode=CacheMode.BYPASS)
        result = await crawler.arun(url, config=run_conf)
        
        if result and result.markdown:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result.markdown)
            return f"✅ Saved {file_name}"
        else:
            return f"⚠️ No content found for {file_name}"
            
    except Exception as e:
        return f"❌ Error scraping {url}: {str(e)}"

async def scrape_all_products(product_links, output_dir, concurrent=False, skip_existing=True):
    """Scrape all product pages"""
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Install playwright browsers if needed
        import subprocess
        subprocess.run(["playwright", "install", "chromium"], capture_output=True)
        
        browser_conf = BrowserConfig(headless=True)
        results = []
        
        async with AsyncWebCrawler(config=browser_conf) as crawler:
            if concurrent:
                # Concurrent scraping
                tasks = [scrape_product(crawler, url, output_dir, skip_existing) for url in product_links]
                results = await asyncio.gather(*tasks, return_exceptions=True)
            else:
                # Sequential scraping
                for i, url in enumerate(product_links):
                    result = await scrape_product(crawler, url, output_dir, skip_existing)
                    results.append(result)
                    
                    # Update progress
                    progress = (i + 1) / len(product_links)
                    st.session_state.progress_bar.progress(progress)
                    st.session_state.status_text.text(f"Processing {i + 1}/{len(product_links)}: {result}")
        
        return results
    except Exception as e:
        st.error(f"Crawler initialization failed: {str(e)}")
        st.info("Falling back to simple requests-based scraping...")
        return await fallback_scrape_products(product_links, output_dir, skip_existing)

async def fallback_scrape_products(product_links, output_dir, skip_existing=True):
    """Fallback scraping using requests and BeautifulSoup"""
    results = []
    
    for i, url in enumerate(product_links):
        try:
            # Create filename from URL
            file_name = url.strip("/").split("/")[-1] + ".md"
            file_path = os.path.join(output_dir, file_name)
            
            # Skip if already exists
            if skip_existing and os.path.exists(file_path):
                result = f"⏭️ Skipped {file_name} (already exists)"
            else:
                # Simple scraping with requests
                response = requests.get(url, headers=HEADERS, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract main content
                    content = soup.get_text(separator='\n', strip=True)
                    
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(f"# {soup.title.string if soup.title else 'Product Page'}\n\n")
                        f.write(content)
                    
                    result = f"✅ Saved {file_name} (fallback mode)"
                else:
                    result = f"❌ Failed to fetch {file_name}: HTTP {response.status_code}"
        except Exception as e:
            result = f"❌ Error scraping {url}: {str(e)}"
        
        results.append(result)
        
        # Update progress
        progress = (i + 1) / len(product_links)
        st.session_state.progress_bar.progress(progress)
        st.session_state.status_text.text(f"Processing {i + 1}/{len(product_links)}: {result}")
    
    return results

def create_download_zip(output_dir):
    """Create a ZIP file of all scraped markdown files"""
    zip_buffer = BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_dir)
                    zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

# Main interface
st.markdown('<h2 class="sub-header flex" >🚀 Start Scraping</h2>', unsafe_allow_html=True)

if st.button("🔍 Get Product Links", type="primary", use_container_width=True):
    if not base_url:
        st.error("❌ Please enter a valid URL")
    else:
        with st.spinner("Fetching product links..."):
            links = get_product_links(base_url, max_products)
            st.session_state.product_links = links

# Display found links
if 'product_links' in st.session_state and st.session_state.product_links:
    st.markdown(f"### 📋 Found {len(st.session_state.product_links)} Product Links")
    
    # Show sample links
    with st.expander("View Sample Links", expanded=False):
        for i, link in enumerate(st.session_state.product_links[:5]):
            st.text(f"{i+1}. {link}")
        if len(st.session_state.product_links) > 5:
            st.text(f"... and {len(st.session_state.product_links) - 5} more")
    
    # Start scraping button
    if st.button("🕷️ Start Scraping", type="secondary", use_container_width=True):
        st.markdown('<div class="info-box">🚀 Starting scraping process...</div>', unsafe_allow_html=True)
        
        # Initialize progress tracking
        st.session_state.progress_bar = st.progress(0)
        st.session_state.status_text = st.empty()
        
        # Run scraping
        try:
            results = asyncio.run(scrape_all_products(
                st.session_state.product_links,
                output_folder,
                concurrent_scraping,
                skip_existing
            ))
            
            # Display results
            st.markdown("### 📊 Scraping Results")
            
            success_count = sum(1 for r in results if "✅" in str(r))
            error_count = sum(1 for r in results if "❌" in str(r))
            skip_count = sum(1 for r in results if "⏭️" in str(r))
            
            col_s, col_e, col_sk = st.columns(3)
            with col_s:
                st.metric("✅ Successful", success_count)
            with col_e:
                st.metric("❌ Errors", error_count)
            with col_sk:
                st.metric("⏭️ Skipped", skip_count)
            
            # Show detailed results
            with st.expander("View Detailed Results", expanded=False):
                for result in results:
                    st.text(result)
            
            # Download option
            if success_count > 0:
                st.markdown("### 📥 Download Results")
                zip_data = create_download_zip(output_folder)
                st.download_button(
                    label="📦 Download All Markdown Files (ZIP)",
                    data=zip_data,
                    file_name=f"bdstall_scraped_{int(time.time())}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            
            st.markdown('<div class="success-box">🎉 Scraping completed successfully!</div>', unsafe_allow_html=True)
            
        except Exception as e:
            st.markdown(f'<div class="error-box">❌ Scraping failed: {str(e)}</div>', unsafe_allow_html=True)


# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #666; font-size: 0.9rem;">'
    '🕷️ BdStall Web Scraper | Built with Streamlit & Crawl4AI'
    '</p>',
    unsafe_allow_html=True
)