#!/usr/bin/env python3
"""
Link scraper module for Rumah123
This module is responsible for extracting property listing links from the search pages.
"""
import os
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from utils import get_headers, request_with_backoff

def extract_links_from_page(url, base_url="https://www.rumah123.com"):
    """
    Extract property links from a listing page using simple fallback method.

    Args:
        url (str): The URL of the listing page
        base_url (str): The base URL for the website

    Returns:
        list: List of unique property links found on the page
    """
    try:
        logging.info(f"Retrieving listing page: {url}")
        res = request_with_backoff(
            url,
            headers=get_headers(),
            timeout=30
        )
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        property_links = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/properti/") and href.endswith("/"):
                full_url = base_url + href
                property_links.add(full_url)

        logging.info(f"Found {len(property_links)} unique property links on {url}")
        return list(property_links)

    except Exception as e:
        logging.error(f"Error extracting links from {url}: {str(e)}", exc_info=True)
        return []

def scrape_all_links(start_url, start_page=1, max_pages=1, min_delay=2, max_delay=5, output_file=None):
    """
    Scrape all property links from multiple listing pages
    
    Args:
        start_url (str): The starting URL for scraping
        start_page (int): Page number to start scraping from
        max_pages (int): Maximum number of pages to scrape
        min_delay (float): Minimum delay between requests in seconds
        max_delay (float): Maximum delay between requests in seconds
        output_file (str): Path to save the links to
        
    Returns:
        list: List of unique property links
    """
    all_links = []
    all_unique_links = set()  # Use a set to avoid duplicates
    
    base_url = f"{urlparse(start_url).scheme}://{urlparse(start_url).netloc}"
    
    # Calculate end page
    end_page = start_page + max_pages - 1
    
    for page in range(start_page, end_page + 1):
        logging.info(f"Scraping page {page} (page {page - start_page + 1} of {max_pages} requested)...")
        
        # Construct the URL for the current page
        if "?" in start_url:
            url = f"{start_url}&page={page}"
        else:
            url = f"{start_url}?page={page}"
            
        links = extract_links_from_page(url, base_url)
        
        # Add unique links to our set
        new_links_count = 0
        for link in links:
            if link not in all_unique_links:
                all_unique_links.add(link)
                all_links.append(link)
                new_links_count += 1
        
        logging.info(f"Added {new_links_count} new unique links from page {page}")
        
        # Add random delay between page requests
        if page < end_page:
            random_delay = random.uniform(min_delay, max_delay)
            logging.info(f"Waiting {random_delay:.2f} seconds before next page")
            time.sleep(random_delay)
    
    logging.info(f"Total unique links found: {len(all_unique_links)}")
    
    # Save links to file if specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for link in all_links:
                    f.write(f"{link}\n")
            logging.info(f"Saved {len(all_links)} links to {output_file}")
        except Exception as e:
            logging.error(f"Error saving links to file: {str(e)}")
    
    return all_links

if __name__ == "__main__":
    # This allows the module to be run independently for testing
    from utils import setup_logging
    setup_logging()
    
    BASE_URL = "https://www.rumah123.com/jual/dki-jakarta/rumah/"
    links = scrape_all_links(BASE_URL, start_page=1, max_pages=1)
    print(f"Found {len(links)} links")