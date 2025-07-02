# BdStall Web Scraper - Streamlit UI

A user-friendly Streamlit interface for scraping BdStall product pages and converting them to markdown format.

## Features

- 🕷️ **Easy Web Scraping**: Extract product data from any BdStall category page
- 🎯 **Customizable URLs**: Input any BdStall category URL (laptops, mobiles, desktops, etc.)
- 📊 **Progress Tracking**: Real-time progress updates during scraping
- 📦 **Batch Download**: Download all scraped markdown files as a ZIP
- ⚡ **Concurrent Scraping**: Option for faster scraping (with rate limit considerations)
- 🔄 **Smart Skip**: Automatically skip already scraped files
- 📱 **Responsive UI**: Clean, modern interface that works on all devices

## Installation

1. **Navigate to the streamlit_app directory:**
   ```bash
   cd streamlit_app
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

4. **Open your browser** and go to `http://localhost:8501`

## Usage

### Step 1: Configure Settings
- **Base URL**: Enter a BdStall category URL (e.g., `https://www.bdstall.com/laptop/`)
- **Maximum Products**: Set the number of products to scrape (1-100)
- **Output Folder**: Choose where to save the markdown files
- **Advanced Options**: Enable concurrent scraping or skip existing files

### Step 2: Get Product Links
1. Click the "🔍 Get Product Links" button
2. The app will fetch and display all product links found on the page
3. Review the sample links in the expandable section

### Step 3: Start Scraping
1. Click the "🕷️ Start Scraping" button
2. Monitor the real-time progress bar and status updates
3. View the scraping results summary (successful, errors, skipped)

### Step 4: Download Results
1. Once scraping is complete, click "📦 Download All Markdown Files (ZIP)"
2. Save the ZIP file containing all scraped markdown files

## Supported URLs

The scraper works with any BdStall category page:
- `https://www.bdstall.com/laptop/`
- `https://www.bdstall.com/mobile/`
- `https://www.bdstall.com/desktop/`
- `https://www.bdstall.com/tablet/`
- Any other BdStall category page

## Configuration Options

### Basic Settings
- **Base URL**: The BdStall category page to scrape
- **Maximum Products**: Limit the number of products (default: 40)
- **Output Folder**: Directory name for saved files (default: "bdstall_markdown")

### Advanced Settings
- **Concurrent Scraping**: 
  - ✅ Faster scraping
  - ⚠️ May hit rate limits
  - 💡 Use for small batches or when server load is low

- **Skip Existing Files**:
  - ✅ Avoids re-scraping already processed products
  - 💡 Useful for resuming interrupted scraping sessions

## Output Format

Each scraped product page is saved as a markdown file:
- **Filename**: Based on the product URL slug (e.g., `laptop-dell-inspiron-15.md`)
- **Content**: Full page content converted to markdown format
- **Encoding**: UTF-8 for proper character support

## Troubleshooting

### Common Issues

1. **"No product links found"**
   - Check if the URL is a valid BdStall category page
   - Ensure the page contains product listings
   - Try a different category URL

2. **Scraping errors**
   - Check your internet connection
   - The target website might be temporarily unavailable
   - Try reducing the number of concurrent requests

3. **Installation issues**
   - Ensure you have Python 3.8+ installed
   - Try installing dependencies one by one
   - Use a virtual environment to avoid conflicts

### Performance Tips

- **For large batches**: Disable concurrent scraping to avoid rate limits
- **For speed**: Enable concurrent scraping for small batches (< 20 products)
- **For reliability**: Keep "Skip Existing Files" enabled

## Technical Details

### Dependencies
- **Streamlit**: Web interface framework
- **Crawl4AI**: Advanced web scraping with JavaScript support
- **BeautifulSoup4**: HTML parsing for link extraction
- **Requests**: HTTP requests for initial page fetching

### Architecture
- **Frontend**: Streamlit web interface
- **Backend**: Async scraping with Crawl4AI
- **Storage**: Local filesystem with markdown files
- **Export**: ZIP compression for batch downloads

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is part of the BdStall RAG ChatBot system developed by **Subodh Chandra Shil**.