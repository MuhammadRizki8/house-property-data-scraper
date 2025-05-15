#!/usr/bin/env python3
"""
Property scraper module for Rumah123
This module is responsible for extracting detailed property information from property pages.
"""

import os
import re
import json
import time
import random
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from utils import get_headers, clean_price, save_to_csv

# Set of all specification fields encountered across all properties
ALL_SPEC_FIELDS = set()

def extract_property_details(url):
    """
    Extract details from a property page
    
    Args:
        url (str): URL of the property page
        
    Returns:
        dict: Dictionary containing property details
    """
    global ALL_SPEC_FIELDS
    
    try:
        # Parse URL to check if it's a valid property URL
        parsed_url = urlparse(url)
        if not parsed_url.path.startswith("/properti/"):
            logging.warning(f"Invalid property URL format: {url}")
        
        # Make the request with increased timeout
        res = requests.get(url, headers=get_headers(), timeout=30)
        res.raise_for_status()
        
        # Log response size for debugging
        logging.info(f"Received response from {url} - Size: {len(res.content)} bytes")
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Initialize property data with core fields
        property_data = {
            "url": url,
            "title": None,
            "location": None,
            "price": None,
            "price_numeric": None,
            "original_price": None,
            "original_price_numeric": None,
            "savings": None,
            "property_type": None,
            "updated_date": None,
            "posted_by": None,
            "description": None,
            "installment_info": None,
            "specifications_text": "",
            "interior_exterior": None,
            "facilities": None,
            "surroundings": None,
        }
        
        # Extract title
        title_element = soup.select_one("h1.text-gray-800")
        if title_element:
            property_data["title"] = title_element.text.strip()
        
        # Extract location
        location_element = soup.select_one("p.text-xs.text-gray-500")
        if location_element:
            property_data["location"] = location_element.text.strip()
        
        # Extract price
        price_element = soup.select_one("span.text-primary.font-bold")
        if price_element:
            price_text = price_element.text.strip()
            property_data["price"] = price_text
            property_data["price_numeric"] = clean_price(price_text)
        
        # Extract original price if discounted
        original_price_element = soup.select_one("span.text-greyText.font-medium.line-through")
        if original_price_element:
            original_price = original_price_element.text.strip()
            property_data["original_price"] = original_price
            property_data["original_price_numeric"] = clean_price(original_price)
        
        # Extract savings
        savings_element = soup.select_one("span.text-accent.mr-1.font-medium")
        if savings_element:
            savings_text = savings_element.text.strip()
            if "HEMAT" in savings_text:
                savings = savings_text.replace("HEMAT", "").strip()
                property_data["savings"] = savings
        
        # Extract property type - using more generic selector
        property_type_elements = soup.select("div.rounded-full")
        if property_type_elements:
            for elem in property_type_elements:
                text = elem.text.strip()
                if text in ["Rumah", "Apartemen", "Tanah", "Ruko", "Kost"]:
                    property_data["property_type"] = text
                    break
        
        # Extract update date and poster
        date_by_element = soup.select_one("p.text-3xs.text-gray-400")
        if date_by_element:
            date_by_text = date_by_element.text.strip()
            date_match = re.search(r'Diperbarui\s+(\d+\s+\w+\s+\d+)', date_by_text)
            if date_match:
                property_data["updated_date"] = date_match.group(1)
            
            poster_match = re.search(r'oleh\s+(.+)$', date_by_text)
            if poster_match:
                property_data["posted_by"] = poster_match.group(1).strip()
        
        # Extract installment info - using a more generic selector to avoid parsing issues
        installment_elements = soup.select("div.installmets-container div")
        for element in installment_elements:
            if "Cicilan" in element.text:
                property_data["installment_info"] = element.text.strip()
                break
        
        # Collect specifications
        all_specs = {}
        
        # Look for all specification items on the page using multiple selectors
        selectors = [
            "div#property-information div.mb-4.flex.items-center.gap-4.text-sm",
            "div.mb-4.flex.items-center.gap-4.text-sm",  # More generic selector
            "div.flex.items-center.gap-4.text-sm",       # Even more generic
            "div.flex.items-center"                     # Most generic selector
        ]
        
        for selector in selectors:
            spec_items = soup.select(selector)
            for item in spec_items:
                # Look for label and value pairs in various formats
                label_elem = item.select_one("p.w-32.text-xs.font-light.text-gray-500, span.text-xs.text-gray-500, span.text-sm.text-gray-500")
                value_elem = item.select_one("p:not(.w-32), span.text-xs.font-medium, span.text-sm.font-medium")
                
                if label_elem and value_elem:
                    label = label_elem.text.strip().lower()
                    value = value_elem.text.strip()
                    
                    # Skip if this is clearly not a property specification
                    if len(label) < 2 or len(value) < 1:
                        continue
                    
                    # Standardize some common labels
                    clean_label = label.replace(":", "").strip()
                    
                    # Add to all specifications
                    all_specs[clean_label] = value
                    
                    # Track all specification fields encountered
                    ALL_SPEC_FIELDS.add(clean_label)
        
        # Create specification columns with spec_ prefix
        for key, value in all_specs.items():
            # Create a sanitized column name to avoid CSV issues
            column_name = f"spec_{key.replace(' ', '_').replace(':', '').replace(',', '').replace(';', '')}"
            property_data[column_name] = value
            
        # Store specifications as a single text field for easy viewing
        if all_specs:
            spec_strings = [f"{k}: {v}" for k, v in all_specs.items()]
            property_data["specifications_text"] = "; ".join(spec_strings)
        
        # Look for description
        description_selectors = [
            "div#property-information p.text-sm.font-light.mb-6.whitespace-pre-wrap",
            "div.text-sm.text-gray-800.whitespace-pre-line",
            "div.whitespace-pre-line",
            "div[data-testid='description']"
        ]
        
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem and desc_elem.text.strip():
                property_data["description"] = desc_elem.text.strip()
                break
        
        # Try to extract structured data from JSON-LD as a fallback
        for script in soup.find_all("script", {"type": "application/ld+json"}):
            try:
                json_data = json.loads(script.string)
                
                # Extract data from structured JSON if available and not already found
                if isinstance(json_data, dict):
                    if "name" in json_data and not property_data["title"]:
                        property_data["title"] = json_data["name"]
                    
                    if "address" in json_data and isinstance(json_data["address"], dict):
                        address_parts = []
                        for field in ["streetAddress", "addressLocality", "addressRegion"]:
                            if field in json_data["address"] and json_data["address"][field]:
                                address_parts.append(json_data["address"][field])
                        
                        if address_parts and not property_data["location"]:
                            property_data["location"] = ", ".join(address_parts)
                    
                    if "offers" in json_data and isinstance(json_data["offers"], dict):
                        if "price" in json_data["offers"] and not property_data.get("price_numeric"):
                            try:
                                property_data["price_numeric"] = float(json_data["offers"]["price"])
                                if not property_data["price"]:
                                    property_data["price"] = json_data["offers"]["price"]
                            except:
                                pass
            except:
                # If JSON parsing fails, continue to the next script tag
                continue
                
        # Extract collapsible sections (like Interior & Exterior)
        # These sections may be hidden but should still be in the HTML
        collapsible_sections = {
            "Interior & Exterior": "interior_exterior",
            "Fasilitas": "facilities",
            "Sekitar Properti": "surroundings"
        }
        
        # First approach - find sections by button text
        for section_name, field_name in collapsible_sections.items():
            section_items = []
            
            # Find all button elements that might contain section headers
            section_buttons = soup.find_all("button", class_=lambda x: x and "flex" in x and "items-center" in x and "justify-between" in x)
            
            for button in section_buttons:
                # Find the div containing the section name
                title_div = button.find("div", class_="text-sm font-bold")
                
                if title_div and section_name in title_div.text:
                    # Found the section button, now find the parent element
                    parent_element = button.parent
                    
                    # The content div should be the next sibling to the button
                    content_div = None
                    
                    # First, check if there's a div directly inside the parent after the button
                    if parent_element:
                        # Look for all divs inside this parent
                        inner_divs = parent_element.find_all("div", recursive=False)
                        for div in inner_divs:
                            # Skip the div that contains the button
                            if not div.find("button"):
                                content_div = div
                                break
                    
                    # If we found the content div, extract the items
                    if content_div:
                        # Find all item divs
                        item_divs = content_div.find_all("div", class_=lambda x: x and "mb-4" in x and "flex" in x and "items-center" in x)
                        
                        for item_div in item_divs:
                            # Find label and value
                            label_elem = item_div.find("p", class_=lambda x: x and "w-32" in x)
                            value_elem = item_div.find("p", class_=lambda x: x is None or "w-32" not in x)
                            
                            if label_elem and value_elem:
                                label = label_elem.text.strip()
                                value = value_elem.text.strip()
                                section_items.append(f"{label}: {value}")
            
            # Add to property data if we found any items
            if section_items:
                property_data[field_name] = "; ".join(section_items)
                
        # Second approach - more generic search for collapsed content
        # This is a fallback in case the first approach didn't find anything
        for section_name, field_name in collapsible_sections.items():
            # Skip if we already found data for this field
            if property_data[field_name]:
                continue
                
            section_items = []
            
            # Find all divs that might be collapsible sections
            all_possible_sections = soup.find_all("div", class_=lambda x: x and "border-b" in x)
            
            for section in all_possible_sections:
                # Look for the section title
                title_text = section.get_text()
                if section_name in title_text:
                    # Now look for all items in this section
                    item_divs = section.find_all("div", class_=lambda x: x and "mb-4" in x and "flex" in x)
                    
                    for item_div in item_divs:
                        # Try different selectors for label and value
                        label_elem = item_div.find(["p", "span"], class_=lambda x: x and ("w-32" in x or "text-gray-500" in x))
                        
                        # Value might be in any p or span that's not the label
                        if label_elem:
                            # Find the next sibling that's a p or span
                            value_elem = label_elem.find_next_sibling(["p", "span"])
                            
                            if not value_elem:
                                # Try looking for any other p or span in this div
                                all_p_spans = item_div.find_all(["p", "span"])
                                if len(all_p_spans) > 1:
                                    # Use the one that's not the label
                                    for elem in all_p_spans:
                                        if elem != label_elem:
                                            value_elem = elem
                                            break
                            
                            if value_elem:
                                label = label_elem.text.strip()
                                value = value_elem.text.strip()
                                section_items.append(f"{label}: {value}")
            
            # Add to property data if we found any items
            if section_items:
                property_data[field_name] = "; ".join(section_items)
        
        return property_data
    
    except Exception as e:
        logging.error(f"Error extracting details from {url}: {str(e)}", exc_info=True)
        # Return at least the URL so we know which property had an error
        return {"url": url, "error": str(e)}

def scrape_all_properties(links, min_delay=2, max_delay=5, results_dir=None):
    """
    Scrape all property details from the provided links
    
    Args:
        links (list): List of property links to scrape
        min_delay (float): Minimum delay between requests in seconds
        max_delay (float): Maximum delay between requests in seconds
        results_dir (str): Directory to save interim results
        
    Returns:
        list: List of dictionaries containing property details
    """
    global ALL_SPEC_FIELDS
    
    # Track URLs we've already scraped to avoid duplicates
    scraped_urls = set()
    all_properties = []
    
    for i, link in enumerate(links):
        # Skip if we've already scraped this URL
        if link in scraped_urls:
            logging.info(f"Skipping already scraped URL: {link}")
            continue
        
        # Log progress
        logging.info(f"Scraping property {i+1}/{len(links)}: {link}")
        
        # Add random delay before each request
        if i > 0:  # No need to delay before the first request
            random_delay = random.uniform(min_delay, max_delay)
            logging.info(f"Waiting {random_delay:.2f} seconds before next property")
            time.sleep(random_delay)
            
        # Extract property details
        property_data = extract_property_details(link)
        
        # Add to our collection if we got data
        if property_data:
            all_properties.append(property_data)
            scraped_urls.add(link)
            
            # Periodically save data to avoid losing everything if the script crashes
            if (i + 1) % 5 == 0 or (i + 1) == len(links):
                if results_dir:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    interim_filename = os.path.join(results_dir, f"interim_results_{timestamp}.csv")
                    save_to_csv(all_properties, interim_filename)
                    logging.info(f"Saved interim results to {interim_filename}")
    
    logging.info(f"Successfully scraped {len(all_properties)} unique properties")
    return all_properties

if __name__ == "__main__":
    # This allows the module to be run independently for testing
    from utils import setup_logging
    setup_logging()
    
    # Test scraping a single property
    test_url = "https://www.rumah123.com/properti/example-property/"
    property_data = extract_property_details(test_url)
    print(json.dumps(property_data, indent=2, ensure_ascii=False))