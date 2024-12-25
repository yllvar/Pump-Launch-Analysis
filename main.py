import requests
import time
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import urllib.parse
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# API Configuration
API_CONFIG = {
    "pump_fun_coins": "",
    "pump_fun_sol_price": "",
    "twitter_api": "",
    "ai_detector_api": ""
}

def fetch_data(url: str, timeout: int = 5, headers: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
    """
    Generic function to fetch data from an API with error handling and timeout.
    """
    try:
        response = requests.get(url, timeout=timeout, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching data from {url}: {e}")
        return None

def validate_url(url: str) -> bool:
    """
    Validate URL format with improved error handling.
    """
    try:
        result = urllib.parse.urlparse(url)
        return bool(result.scheme and result.netloc)
    except ValueError:
        return False

def detect_ai_generated_website(website_url: str) -> Optional[float]:
    """
    Check if website content is AI-generated using the AI Content Detector API.
    Includes rate limit handling.
    """
    try:
        # Fetch website content
        response = requests.get(website_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        website_text = soup.get_text(separator=" ", strip=True)[:5000]  # Limit to 5000 chars
        
        if not website_text:
            logger.warning(f"No meaningful content found on: {website_url}")
            return None
            
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "ai-content-detector6.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        
        payload = {"text": website_text}
        
        api_response = requests.post(
            API_CONFIG["ai_detector_api"],
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if api_response.status_code == 200:
            result = api_response.json()
            score = result.get("confidenceScore", 0)
            logger.info(f"AI content detection score for {website_url}: {score}")
            return score
        elif api_response.status_code == 429:  # Rate limit exceeded
            logger.warning("AI detection API rate limit exceeded. Skipping analysis.")
            return None
        
        logger.error(f"AI detection API error: {api_response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error in AI content detection for {website_url}: {e}")
        return None

def analyze_twitter_account(twitter_url: str) -> Optional[Dict[str, Any]]:
    """
    Analyze Twitter account details using the Twitter API45.
    """
    try:
        twitter_handle = twitter_url.split("/")[-1].strip()
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
        }
        
        # Parameters for the Twitter API
        params = {
            "screenname": twitter_handle,
            "rest_id": ""  # Optional, can be left empty
        }
        
        response = requests.get(
            API_CONFIG["twitter_api"],
            headers=headers,
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            twitter_data = response.json()
            
            # Extract relevant information from the response
            user_info = {
                "creation_date": twitter_data.get("created_at"),
                "followers_count": twitter_data.get("followers_count"),
                "following_count": twitter_data.get("following_count"),
                "tweet_count": twitter_data.get("statuses_count"),
                "location": twitter_data.get("location"),
                "verified": twitter_data.get("verified", False),
                "account_age_days": None  # Will be calculated if creation_date exists
            }
            
            # Calculate account age if creation_date exists
            if user_info["creation_date"]:
                created_date = datetime.strptime(user_info["creation_date"], "%Y-%m-%d %H:%M:%S")
                account_age = datetime.now() - created_date
                user_info["account_age_days"] = account_age.days
            
            logger.info(f"Twitter analysis for @{twitter_handle}:")
            logger.info(f"Created: {user_info['creation_date']}")
            logger.info(f"Account age: {user_info['account_age_days']} days")
            logger.info(f"Followers: {user_info['followers_count']}")
            logger.info(f"Following: {user_info['following_count']}")
            logger.info(f"Tweets: {user_info['tweet_count']}")
            
            return user_info
        elif response.status_code == 429:  # Rate limit exceeded
            logger.warning("Twitter API rate limit exceeded. Skipping analysis.")
            return None
            
        logger.error(f"Twitter API error: {response.text}")
        return None
        
    except Exception as e:
        logger.error(f"Error analyzing Twitter account {twitter_url}: {e}")
        return None

def fetch_and_process_latest_data() -> None:
    """
    Combined function to fetch and process latest token data.
    """
    try:
        # Fetch coin data
        coin_data = fetch_data(API_CONFIG["pump_fun_coins"])
        if not coin_data:
            return

        website = coin_data.get('website')
        twitter = coin_data.get('twitter')
        symbol = coin_data.get('symbol')

        if not (validate_url(website) and validate_url(twitter)):
            logger.warning(f"Skipping token ({symbol}): Invalid website or Twitter URL.")
            return

        # Analyze website content for AI generation
        ai_content_score = detect_ai_generated_website(website)
        if ai_content_score and ai_content_score > 0.7:
            logger.warning(f"Website {website} appears to be AI-generated (score: {ai_content_score})")

        # Analyze Twitter account
        twitter_info = analyze_twitter_account(twitter)

        # Fetch additional data
        sol_price_data = fetch_data(API_CONFIG["pump_fun_sol_price"])
        trade_data = fetch_data(
            f"https://frontend-api.pump.fun/trades/latest?mint={coin_data.get('mint')}"
        )

        # Display results
        display_token_info(coin_data, sol_price_data, trade_data, twitter_info, ai_content_score)

    except Exception as e:
        logger.error(f"Error in data processing: {e}")

def display_token_info(
    coin_data: Dict, 
    sol_price_data: Dict, 
    trade_data: Dict, 
    twitter_info: Optional[Dict],
    ai_score: Optional[float]
) -> None:
    """
    Display formatted token information with improved Twitter info display.
    """
    print("\n" + "="*50)
    print("Latest Token Details")
    print("="*50)
    
    # Token basics
    print(f"Name: {coin_data.get('name')}")
    print(f"Symbol: {coin_data.get('symbol')}")
    print(f"Description: {coin_data.get('description')}")
    print(f"Market Cap: ${coin_data.get('market_cap', 0):,.2f}")
    print(f"Total Supply: {coin_data.get('total_supply', 0):,}")
    
    # Reserves and prices
    print(f"Virtual SOL Reserves: {coin_data.get('virtual_sol_reserves')}")
    print(f"Virtual Token Reserves: {coin_data.get('virtual_token_reserves')}")
    print(f"SOL Price: ${sol_price_data.get('solPrice', 0):,.2f}")
    
    # URLs and creator
    print(f"Website: {coin_data.get('website')}")
    print(f"Twitter: {coin_data.get('twitter')}")
    print(f"Creator: {coin_data.get('creator')}")
    
    # AI Content Analysis (if available)
    if ai_score is not None:
        print(f"\nWebsite AI Content Analysis:")
        print(f"AI Content Score: {ai_score:.2f}")
        if ai_score > 0.7:
            print("⚠️ WARNING: Website content appears to be AI-generated")
    else:
        print("\nWebsite AI Content Analysis: Not available (API rate limit reached)")
    
    # Twitter Analysis (if available)
    if twitter_info:
        print("\nTwitter Account Analysis:")
        print(f"  Creation Date: {twitter_info.get('creation_date')}")
        if twitter_info.get('account_age_days'):
            print(f"  Account Age: {twitter_info.get('account_age_days')} days")
        print(f"  Followers: {twitter_info.get('followers_count'):,}")
        print(f"  Following: {twitter_info.get('following_count'):,}")
        print(f"  Total Tweets: {twitter_info.get('tweet_count'):,}")
    else:
        print("\nTwitter Account Analysis: Not available")
    
    # Supply distribution
    print("\nSupply Distribution:")
    print(f"  Real SOL Reserves: {coin_data.get('real_sol_reserves', 0)}")
    print(f"  Real Token Reserves: {coin_data.get('real_token_reserves', 0)}")
    print(f"  Total Supply: {coin_data.get('total_supply', 0):,}")
    
    # Trade details
    if trade_data and trade_data.get('mint') == coin_data.get('mint'):
        print("\nLatest Trade Details:")
        print(f"Trade Signature: {trade_data.get('signature')}")
        print(f"SOL Amount: {trade_data.get('sol_amount')}")
        print(f"Token Amount: {trade_data.get('token_amount')}")
        print(f"Is Buy: {trade_data.get('is_buy')}")
        print(f"User: {trade_data.get('user')}")
    else:
        print("\nNo recent trades available")

def main():
    """
    Main execution loop with proper error handling.
    """
    logger.info("Starting token monitoring script...")
    try:
        while True:
            fetch_and_process_latest_data()
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        raise

if __name__ == "__main__":
    main()