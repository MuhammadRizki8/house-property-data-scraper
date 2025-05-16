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

from utils import get_headers, clean_price, save_to_csv, request_with_backoff

# Set of all specification fields encountered across all properties
ALL_SPEC_FIELDS = set()


def extract_property_details(url, split_details=True):
    """
    Extract details from a property page

    Args:
        url (str): URL of the property page
        split_details (bool): If True, split specifications/facilities/POI into multiple columns. If False, only keep *_text fields.

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
        # res = requests.get(url, headers=get_headers(), timeout=30)
        res = request_with_backoff(
            url,
            headers=get_headers(),
            timeout=30
        )
        res.raise_for_status() 
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
            "facilities_text": "",  # New field for facilities as text
            "poi_text": "",  # New field for Points of Interest as text
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
        if split_details:
            for key, value in all_specs.items():
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
        
        # Extract facilities data by category
        all_facilities = []
        facility_categories = [
            "Fasilitas Rumah",
            "Fasilitas Perumahan", 
            "Perabotan"
        ]
        
        # Initialize category text fields in property_data
        for category in facility_categories:
            sanitized_category = category.lower().replace(" ", "_")
            property_data[f"{sanitized_category}_text"] = ""
        
        # Process each facility category
        for category in facility_categories:
            # Prepare the ID selector with escaped spaces
            category_id = category.replace(" ", "\\ ")
            category_selector = f"div#property-facility-{category_id}"
            
            try:
                # Find the category element
                category_elem = soup.select_one(category_selector)
                
                if category_elem:
                    # Look for facilities in this category
                    facility_items = category_elem.select("div.flex.flex-wrap p")
                    category_facilities = []
                    
                    for item in facility_items:
                        # Extract facility name from span
                        span_elem = item.select_one("span.text-sm.font-light")
                        if span_elem and span_elem.text.strip():
                            facility_name = span_elem.text.strip()
                            
                            # Add to category-specific list
                            category_facilities.append(facility_name)
                            
                            # Add to all facilities list
                            all_facilities.append(facility_name)
                            
                            # Create individual boolean field
                            if split_details:
                                column_name = f"facility_{facility_name.lower().replace(' ', '_').replace('-', '_').replace('.', '').replace(',', '')}"
                                property_data[column_name] = True
                    
                    # Store category facilities as text
                    if category_facilities:
                        sanitized_category = category.lower().replace(" ", "_")
                        property_data[f"{sanitized_category}_text"] = ", ".join(category_facilities)
            except Exception as e:
                logging.warning(f"Error extracting facilities for category {category}: {str(e)}")
        
        # Store all facilities as a single text field
        if all_facilities:
            property_data["facilities_text"] = ", ".join(all_facilities)
            
        # Fallback extraction method in case category-based extraction missed some facilities
        if not all_facilities:
            try:
                # Try a more generic selector to find facilities
                generic_facility_items = soup.select("div[id^='property-facility'] div.flex.flex-wrap p span.text-sm.font-light")
                if generic_facility_items:
                    generic_facilities = [item.text.strip() for item in generic_facility_items if item.text.strip()]
                    
                    # Add these to property_data
                    for facility in generic_facilities:
                        column_name = f"facility_{facility.lower().replace(' ', '_').replace('-', '_').replace('.', '').replace(',', '')}"
                        property_data[column_name] = True
                    
                    # Update the text field
                    property_data["facilities_text"] = ", ".join(generic_facilities)
            except Exception as e:
                logging.warning(f"Error in fallback facility extraction: {str(e)}")

        # NEW CODE: Extract Points of Interest (POI) by category
        try:
            # Select the entire POI section
            poi_section = soup.select_one("div#property-poi")
            
            if poi_section:
                all_poi_categories = {}
                all_pois = []
                
                # Find all category sections
                poi_categories = poi_section.select("div.mb-4.pb-2.border-0.border-b.border-solid.border-gray-200")
                
                for category_section in poi_categories:
                    # Extract category name from the SVG title or p tag
                    category_elem = category_section.select_one("p.flex.items-center.gap-2.mb-2.text-sm")
                    
                    if category_elem:
                        # Extract the category name (remove the SVG icon from consideration)
                        svg_elem = category_elem.select_one("svg")
                        if svg_elem:
                            svg_elem.extract()  # Remove SVG temporarily to get clean text
                        
                        category_name = category_elem.text.strip()
                        
                        # Find all POIs in this category
                        poi_items = category_section.select("p.text-xs.font-light.mb-2")
                        category_pois = [item.text.strip() for item in poi_items if item.text.strip()]
                        
                        if category_pois:
                            # Store category POIs
                            sanitized_category = f"poi_{category_name.lower().replace(' ', '_').replace('-', '_').replace('.', '').replace(',', '')}"
                            property_data[sanitized_category + "_text"] = ", ".join(category_pois)
                            
                            # Add to category dictionary
                            all_poi_categories[category_name] = category_pois
                            
                            # Add to overall POI list
                            all_pois.extend(category_pois)
                            
                            # Create individual POI fields
                            if split_details:
                                for poi in category_pois:
                                    sanitized_poi = f"poi_{category_name.lower()}_{poi.lower().replace(' ', '_').replace('-', '_').replace('.', '').replace(',', '')}"
                                    property_data[sanitized_poi] = True
                
                # Store all POIs as a single text field
                if all_pois:
                    property_data["poi_text"] = ", ".join(all_pois)
                
                # Store structured POI data
                if all_poi_categories:
                    poi_strings = []
                    for category, items in all_poi_categories.items():
                        poi_strings.append(f"{category}: {', '.join(items)}")
                    
                    property_data["poi_structured_text"] = "; ".join(poi_strings)
        
        except Exception as e:
            logging.warning(f"Error extracting POI data: {str(e)}")

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
        property_data = extract_property_details(link, False)
        
        # Add to our collection if we got data
        if property_data:
            all_properties.append(property_data)
            scraped_urls.add(link)
            
            # Periodically save data to avoid losing everything if the script crashes
            if (i + 1) % 100 == 0 or (i + 1) == len(links):
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