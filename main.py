#!/usr/bin/env python3 
""" 
Rumah123 Property Scraper - Main Script 
This script orchestrates the scraping process for Rumah123 property listings.
It supports two modes of operation:
1. Scrape links only (--mode links)
2. Scrape property details from previously scraped links (--mode details)
""" 
 
import os 
import logging 
import argparse 
from datetime import datetime 
 
from link_scraper import scrape_all_links 
from property_scraper import scrape_all_properties 
from utils import setup_logging, save_to_csv, save_specs_summary 
 
def main(): 
    """Main function to orchestrate the scraping process""" 
    parser = argparse.ArgumentParser(description='Scrape property data from Rumah123') 
    parser.add_argument('--mode', type=str, choices=['links', 'details', 'both'], default='both',
                        help='Scraping mode: links (only scrape and save links), details (scrape details from saved links), or both (default)')
    parser.add_argument('--pages', type=int, default=1, help='Number of pages to scrape (used in links mode)') 
    parser.add_argument('--delay-min', type=float, default=2, help='Minimum delay between requests (seconds)') 
    parser.add_argument('--delay-max', type=float, default=5, help='Maximum delay between requests (seconds)') 
    parser.add_argument('--url', type=str, default="https://www.rumah123.com/jual/dki-jakarta/rumah/",  
                        help='Base URL to start scraping from (used in links mode)') 
    parser.add_argument('--links-file', type=str, default=None,
                        help='File containing property links to scrape (used in details mode)') 
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Directory to save results (default: auto-generated timestamped directory)')
    args = parser.parse_args() 
     
    # Create results directory structure 
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S") 
    if args.output_dir:
        results_dir = args.output_dir
    else:
        results_dir = os.path.join("results", f"scraping_session_{timestamp}")
    
    os.makedirs(results_dir, exist_ok=True) 
     
    # Setup logging 
    log_file = os.path.join(results_dir, "scraping.log") 
    setup_logging(log_file) 
     
    logging.info("="*50) 
    logging.info("Rumah123 Property Scraper") 
    logging.info("="*50) 
    logging.info(f"Starting scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 
    logging.info(f"Mode: {args.mode}")
    logging.info(f"Results will be saved to: {results_dir}") 
    
    try: 
        # Variable to store links
        unique_links = []
        
        # Step 1: Scrape property links (if mode is 'links' or 'both')
        if args.mode in ['links', 'both']:
            logging.info(f"Will scrape up to {args.pages} pages from {args.url}")
            links_file = os.path.join(results_dir, "property_links.txt") 
            unique_links = scrape_all_links( 
                start_url=args.url, 
                max_pages=args.pages, 
                min_delay=args.delay_min, 
                max_delay=args.delay_max, 
                output_file=links_file 
            )
            logging.info(f"Saved {len(unique_links)} property links to {links_file}")
            
            # If mode is 'links' only, we're done
            if args.mode == 'links':
                logging.info("Link scraping completed successfully!")
                return
         
        # Step 2: Scrape property details (if mode is 'details' or 'both')
        if args.mode in ['details', 'both']:
            # If in details mode, load links from file if specified
            if args.mode == 'details' and args.links_file:
                links_file = args.links_file
                logging.info(f"Loading property links from {links_file}")
                try:
                    with open(links_file, 'r') as f:
                        unique_links = [line.strip() for line in f if line.strip()]
                    logging.info(f"Loaded {len(unique_links)} property links from file")
                except Exception as e:
                    logging.error(f"Failed to load links from file: {str(e)}")
                    return
            
            if not unique_links:
                logging.warning("No property links to scrape details from.")
                return
                
            properties = scrape_all_properties( 
                links=unique_links, 
                min_delay=args.delay_min, 
                max_delay=args.delay_max, 
                results_dir=results_dir 
            ) 
             
            # Step 3: Save final results 
            if properties: 
                # Save complete dataset 
                final_filename = os.path.join(results_dir, f"rumah123_properties_final.csv") 
                saved_file = save_to_csv(properties, final_filename) 
                 
                if saved_file: 
                    logging.info(f"Scraping completed successfully! Data saved to {saved_file}") 
                     
                    # Save a summary of all specification fields encountered 
                    specs_file = os.path.join(results_dir, "property_specifications_summary.csv") 
                    specs_summary = save_specs_summary(specs_file) 
                    if specs_summary: 
                        logging.info(f"Specification fields summary saved to {specs_summary}") 
                else: 
                    logging.error("Failed to save final CSV file.") 
            else: 
                logging.warning("No property details could be scraped.") 
             
    except KeyboardInterrupt: 
        logging.info("\nScraping interrupted by user.") 
    except Exception as e: 
        logging.error(f"An error occurred during scraping: {str(e)}", exc_info=True) 
     
    logging.info(f"Scraping session completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") 
 
if __name__ == "__main__": 
    main()