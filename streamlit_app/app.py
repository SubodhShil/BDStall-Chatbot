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
from PIL import Image

# RAG Embeddings imports
from pinecone import Pinecone, ServerlessSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    output_folder = st.text_input("Output Folder Name", value="") # required
    
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

# RAG Embeddings Functions
def get_markdown_text(markdown_dir):
    """Extract text from markdown files in the specified directory."""
    text = ""
    if not os.path.exists(markdown_dir):
        st.error(f"❌ Directory not found: {markdown_dir}")
        return text
    
    markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')]
    if not markdown_files:
        st.warning(f"⚠️ No markdown files found in {markdown_dir}")
        return text
    
    total_files = len(markdown_files)
    processed_files = 0
    skipped_files = 0
    max_file_size = 1024 * 1024  # 1MB per file limit
    
    for filename in markdown_files:
        file_path = os.path.join(markdown_dir, filename)
        try:
            # Check file size before reading
            file_size = os.path.getsize(file_path)
            if file_size > max_file_size:
                st.warning(f"⚠️ Skipping {filename} (too large: {file_size/1024/1024:.1f}MB)")
                skipped_files += 1
                continue
                
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Limit content length per file
                if len(content) > 50000:  # 50k characters per file
                    content = content[:50000] + "\n\n[Content truncated due to size limits]"
                    st.info(f"📄 Truncated {filename} to 50k characters")
                
                text += f"\n\n--- File: {filename} ---\n\n{content}"
                processed_files += 1
        except Exception as e:
            st.warning(f"⚠️ Could not read {filename}: {str(e)}")
            skipped_files += 1
    
    st.info(f"📊 Processed {processed_files}/{total_files} files (skipped {skipped_files})")
    return text

def get_text_chunks(text, model_name="Google AI"):
    """Convert the retrieved text into chunks or tokens."""
    if model_name == 'Google AI':
        # Reduced chunk size to handle large datasets better
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks, model_name="Google AI", api_key=None):
    """Store vector embeddings in Pinecone."""
    try:
        # API key configuration
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        if not pinecone_api_key:
            st.error("❌ PINECONE_API_KEY not found in environment variables")
            return None
        
        pc = Pinecone(api_key=pinecone_api_key)
        
        if model_name == "Google AI":
            google_api_key = api_key or os.environ.get("GOOGLE_API_KEY")
            if not google_api_key:
                st.error("❌ GOOGLE_API_KEY not found in environment variables")
                return None
            
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001", 
                google_api_key=google_api_key
            )
        
        # Pinecone vector store
        # Get actual embedding dimension
        try:
            test_embedding = embeddings.embed_query("test")
            embedding_dimension = len(test_embedding)
        except Exception:
            embedding_dimension = 768  # fallback to expected dimension
            
        index_name = f"bdstall-products-{embedding_dimension}"
        
        # Check if index exists and has correct dimensions
        if pc.has_index(index_name):
            index_info = pc.describe_index(index_name)
            if index_info.dimension != embedding_dimension:
                st.warning(f"⚠️ Existing index has dimension {index_info.dimension}, but we need {embedding_dimension}. Deleting old index...")
                pc.delete_index(index_name)
                
        if not pc.has_index(index_name):
            st.info(f"🔧 Creating new Pinecone index with {embedding_dimension} dimensions...")
            pc.create_index(
                name=index_name,
                dimension=embedding_dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            st.success("✅ Pinecone index created successfully!")
        
        index = pc.Index(index_name)
        vector_store = PineconeVectorStore(index=index, embedding=embeddings)
        
        # Add documents to Pinecone in batches to avoid size limits
        batch_size = 50  # Process chunks in smaller batches
        total_chunks = len(text_chunks)
        
        for i in range(0, total_chunks, batch_size):
            batch = text_chunks[i:i + batch_size]
            try:
                vector_store.add_texts(batch)
                st.info(f"📊 Processed batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size} ({len(batch)} chunks)")
            except Exception as batch_error:
                st.warning(f"⚠️ Error processing batch {i//batch_size + 1}: {str(batch_error)}")
                # Try with even smaller batch size
                smaller_batch_size = 10
                for j in range(i, min(i + batch_size, total_chunks), smaller_batch_size):
                    smaller_batch = text_chunks[j:j + smaller_batch_size]
                    try:
                        vector_store.add_texts(smaller_batch)
                        st.info(f"📊 Processed smaller batch ({len(smaller_batch)} chunks)")
                    except Exception as small_batch_error:
                        st.error(f"❌ Failed to process small batch: {str(small_batch_error)}")
        
        return vector_store
    
    except Exception as e:
        st.error(f"❌ Error creating vector store: {str(e)}")
        return None


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

# RAG Embeddings Section
st.markdown("---")
st.markdown('<h2 class="sub-header">🧠 Create RAG Embeddings</h2>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">Create vector embeddings from scraped markdown data for enhanced search and retrieval</p>', unsafe_allow_html=True)

# Default markdown directory
markdown_dir = r"f:\GitHub\Projects\BdStall Chatbot\Dataset\Web scraping\bdstall_markdown"

# Display current directory info
if os.path.exists(markdown_dir):
    markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('.md')]
    st.info(f"📁 Found {len(markdown_files)} markdown files in: `{markdown_dir}`")
else:
    st.warning(f"⚠️ Directory not found: `{markdown_dir}`")

# Create embeddings button
if st.button("🚀 Create RAG Embeddings", type="primary", use_container_width=True):
    if not os.path.exists(markdown_dir):
        st.error(f"❌ Directory not found: {markdown_dir}")
    else:
        with st.spinner("Creating RAG embeddings..."):
            try:
                # Step 1: Extract text from markdown files
                st.info("📖 Reading markdown files...")
                text = get_markdown_text(markdown_dir)
                
                if not text.strip():
                    st.error("❌ No text content found in markdown files")
                else:
                    # Step 2: Create text chunks
                    st.info("✂️ Creating text chunks...")
                    text_chunks = get_text_chunks(text)
                    st.success(f"✅ Created {len(text_chunks)} text chunks")
                    
                    # Step 3: Create vector store
                    st.info("🔗 Creating vector embeddings and storing in Pinecone...")
                    vector_store = get_vector_store(text_chunks)
                    
                    if vector_store:
                        st.success("✅ RAG embeddings created successfully!")
                        st.markdown('<div class="success-box">🎉 Vector embeddings have been created and stored in Pinecone. You can now use the BdStall GPT chatbot for enhanced question answering!</div>', unsafe_allow_html=True)
                        
                        # Display some statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("📄 Files Processed", len([f for f in os.listdir(markdown_dir) if f.endswith('.md')]))
                        with col2:
                            st.metric("🧩 Text Chunks", len(text_chunks))
                        with col3:
                            st.metric("📊 Characters", len(text))
                    else:
                        st.error("❌ Failed to create vector embeddings")
                        
            except Exception as e:
                st.error(f"❌ Error creating embeddings: {str(e)}")
                st.info("💡 Make sure you have set the required environment variables: PINECONE_API_KEY and GOOGLE_API_KEY")

# Footer
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #666; font-size: 0.9rem;">'
    '🕷️ BdStall Web Scraper | Built with Streamlit & Crawl4AI'
    '</p>',
    unsafe_allow_html=True
)