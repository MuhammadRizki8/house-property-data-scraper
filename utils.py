#!/usr/bin/env python3
"""
Utility functions for the Rumah123 scraper
"""

import os
import re
import csv
import random
import logging
from datetime import datetime
import time
import requests
# Global set to track all specification fields encountered across all properties
ALL_SPEC_FIELDS = set()

def setup_logging(log_file=None):
    """
    Set up logging configuration
    
    Args:
        log_file (str): Path to log file
    """
    handlers = []
    
    # Always log to console
    handlers.append(logging.StreamHandler())
    
    # Log to file if specified
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def get_headers():
    """
    Get randomized headers for HTTP requests
    
    Returns:
        dict: Headers dictionary
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",  
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.rumah123.com/",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

def clean_price(price_text):
    """
    Clean price text and convert to numeric value
    
    Args:
        price_text (str): Price text to clean
        
    Returns:
        float: Numeric price value, or original text if conversion fails
    """
    if not price_text:
        return None
    
    # Remove non-numeric characters except decimal point
    clean = re.sub(r'[^\d,.]', '', price_text)
    
    # Handle different formats (Miliar, Juta, etc.)
    multiplier = 1
    if "miliar" in price_text.lower() or "m" in price_text.lower():
        multiplier = 1000000000
    elif "juta" in price_text.lower():
        multiplier = 1000000
    elif "ribu" in price_text.lower() or "rb" in price_text.lower():
        multiplier = 1000
        
    # Convert to float if possible
    try:
        # Replace comma with dot for decimal parsing
        clean = clean.replace(',', '.')
        value = float(clean) * multiplier
        return value
    except ValueError:
        return price_text

def save_to_csv(data, filename=None):
    """
    Save data to CSV file with all columns present in the data
    
    Args:
        data (list): List of property data dictionaries
        filename (str): Output filename
        
    Returns:
        str: Path to the saved file, or None if failed
    """
    global ALL_SPEC_FIELDS
    
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rumah123_properties_{timestamp}.csv"
    
    if not data:
        logging.warning("No data to save")
        return None
    
    # Get all fields across all records
    all_fields = set()
    for record in data:
        all_fields.update(record.keys())
    
    # Remove internal tracking fields
    if "all_specifications" in all_fields:
        all_fields.remove("all_specifications")
    
    # Move error field to the end if it exists
    ordered_fields = sorted(list(all_fields))
    if "error" in ordered_fields:
        ordered_fields.remove("error")
        ordered_fields.append("error")
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields, extrasaction='ignore')
            writer.writeheader()
            
            # Write data but ignore internal tracking fields
            for property_item in data:
                # Create a copy without the tracking keys
                clean_item = {k: v for k, v in property_item.items() if k != "all_specifications"}
                writer.writerow(clean_item)
        
        logging.info(f"Saved {len(data)} unique property records to {filename}")
        logging.info(f"CSV includes {len(ordered_fields)} columns")
        return filename
    except Exception as e:
        logging.error(f"Error saving data to CSV: {str(e)}", exc_info=True)
        # Try to save to a different filename if there was an error
        if not filename.startswith("backup_"):
            backup_filename = f"backup_{filename}"
            logging.info(f"Trying to save to backup file: {backup_filename}")
            return save_to_csv(data, backup_filename)
        return None

def save_specs_summary(filename="property_specifications_summary.csv"):
    """
    Save a summary of all specification fields encountered
    
    Args:
        filename (str): Output filename
        
    Returns:
        str: Path to the saved file, or None if failed
    """
    global ALL_SPEC_FIELDS
    spec_fields = sorted(list(ALL_SPEC_FIELDS))
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Specification Field"])
            for field in spec_fields:
                writer.writerow([field])
        
        logging.info(f"Saved {len(spec_fields)} specification fields to {filename}")
        return filename
    except Exception as e:
        logging.error(f"Error saving specification summary: {str(e)}", exc_info=True)
        return None

def deduplicate_properties(properties, key="url"):
    """
    Remove duplicate properties from a list based on a key
    
    Args:
        properties (list): List of property dictionaries
        key (str): Key to use for deduplication
        
    Returns:
        list: Deduplicated list of properties
    """
    seen = set()
    unique_properties = []
    
    for prop in properties:
        if key in prop and prop[key] not in seen:
            seen.add(prop[key])
            unique_properties.append(prop)
    
    duplicate_count = len(properties) - len(unique_properties)
    if duplicate_count > 0:
        logging.info(f"Removed {duplicate_count} duplicate properties")
    
    return unique_properties

def request_with_backoff(url, headers=None, params=None, status_forcelist=(429, 500, 502, 503, 504), **kwargs):
    if "timeout" not in kwargs:
        kwargs["timeout"] = 10
    
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.get(url, headers=headers, params=params, **kwargs)
            if resp.status_code not in status_forcelist:
                return resp
            logging.warning(f"[{resp.status_code}] Server responded with retryable status on {url}. Attempt {attempt}")
        except requests.RequestException as e:
            logging.warning(f"Request error on attempt {attempt} for {url}: {e}")
        
        wait = min(60, 2 ** attempt) + random.uniform(0, 1)  # max delay 60s (bisa disesuaikan)
        logging.info(f"Waiting {wait:.1f}s before retrying...")
        time.sleep(wait)

def load_links_from_file(file_path):
    """
    Load property links from a text file
    
    Args:
        file_path (str): Path to the file containing links
        
    Returns:
        list: List of property links
    """
    if not os.path.exists(file_path):
        logging.error(f"Links file not found: {file_path}")
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
        
        logging.info(f"Loaded {len(links)} property links from {file_path}")
        return links
    except Exception as e:
        logging.error(f"Error loading links from file: {str(e)}")
        return []

if __name__ == "__main__":
    # This allows the module to be run independently for testing
    setup_logging()
    print("Utility functions imported successfully")