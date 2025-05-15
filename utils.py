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

# Core fields to include in the CSV
CORE_PROPERTY_FIELDS = [
    "url", "title", "location", "price", "price_numeric", "original_price", 
    "original_price_numeric", "savings", "property_type", "building_size", 
    "land_size", "electricity", "floors", "updated_date", "posted_by",
    "description", "installment_info"
]

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
    ]
    
    return {
        "User-Agent": random.choice(user_agents),
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": "https://www.rumah123.com/",
        "Cache-Control": "max-age=0"
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
    Save data to CSV file with dynamic columns
    
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
    
    # Organize fields in a logical order:
    # 1. Core fields first
    ordered_fields = [field for field in CORE_PROPERTY_FIELDS if field in all_fields]
    
    # 2. Add specifications_text field that contains all specs in a single cell
    if "specifications_text" in all_fields:
        ordered_fields.append("specifications_text")
        all_fields.remove("specifications_text")
    
    # 3. Add individual specification fields (those starting with "spec_")
    spec_fields = sorted([field for field in all_fields if field.startswith("spec_")])
    ordered_fields.extend(spec_fields)
    for field in spec_fields:
        if field in all_fields:
            all_fields.remove(field)
    
    # 4. Add any remaining fields
    remaining_fields = sorted(list(all_fields))
    ordered_fields.extend(remaining_fields)
    
    # Remove 'all_specifications' field if it exists - we don't want this in the CSV
    if "all_specifications" in ordered_fields:
        ordered_fields.remove("all_specifications")
    
    # Remove 'error' field if it exists - we want to keep this in a separate column
    if "error" in ordered_fields:
        ordered_fields.remove("error")
        # Add it at the end
        ordered_fields.append("error")
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        
        with open(filename, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=ordered_fields, extrasaction='ignore')
            writer.writeheader()
            
            # Write data but ignore 'all_specifications' dictionary
            for property_item in data:
                # Create a copy without the 'all_specifications' key
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

if __name__ == "__main__":
    # This allows the module to be run independently for testing
    setup_logging()
    print("Utility functions imported successfully")