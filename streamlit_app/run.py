#!/usr/bin/env python3
"""
Simple script to run the BdStall Web Scraper Streamlit app
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ['streamlit', 'requests', 'beautifulsoup4', 'crawl4ai']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install them with: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def run_streamlit():
    """Run the Streamlit application"""
    try:
        print("🚀 Starting BdStall Web Scraper...")
        print("📱 The app will open in your default browser")
        print("🔗 URL: http://localhost:8501")
        print("\n⏹️  Press Ctrl+C to stop the application\n")
        
        # Run streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=True)
        
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running Streamlit: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def main():
    """Main function"""
    print("🕷️ BdStall Web Scraper - Streamlit UI")
    print("=" * 40)
    
    # Check if we're in the right directory
    if not os.path.exists("app.py"):
        print("❌ app.py not found in current directory")
        print("💡 Make sure you're in the streamlit_app folder")
        return
    
    # Check dependencies
    if not check_dependencies():
        return
    
    # Run the app
    run_streamlit()

if __name__ == "__main__":
    main()