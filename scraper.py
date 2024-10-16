from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
import os
import time
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Function to initialize WebDriver
def initialize_driver():
    firefox_options = Options()  # Create Firefox Options object
    firefox_options.add_argument("--headless")  # Run in headless mode
    firefox_options.binary_location = "/usr/bin/firefox"  # Set Firefox binary location
    
    # Initialize and run Firefox WebDriver
    driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=firefox_options)
    return driver

# Function to clear the screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Function to print the header
def print_header():
    clear_screen()
    print(Style.BRIGHT + Fore.CYAN + "=" * 50)
    print(Style.BRIGHT + Fore.MAGENTA + " " * 10 + "🌟 Booking.com Hotel Scraper 🌟")
    print(Style.BRIGHT + Fore.CYAN + "=" * 50 + "\n")

# Function to scroll down the page until the end or for a set number of scrolls
def scroll_to_bottom(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(10)  # Wait for more hotels to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

# Function to click the 'Load more results' button if it exists
def click_load_more_results_button(driver):
    try:
        load_more_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Load more results')]"))
        )
        load_more_button.click()
        print(Fore.CYAN + "'Load more results' button clicked.")
        time.sleep(5)  # Wait for the new results to load
        return True
    except Exception as e:
        print(Fore.RED + f"Error clicking 'Load more results' button: {e}")
        return False


# Function to scrape hotel information from the page
def scrape_page(driver, scraped_names):
    hotels = []
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    for hotel in soup.find_all('div', attrs={'data-testid': 'property-card'}):
        try:
            name = hotel.find('div', attrs={'data-testid': 'title'}).text.strip()
        except AttributeError:
            name = 'N/A'
        
        try:
            # Extract the hotel detail page URL (relative path)
            url = hotel.find('a', attrs={'data-testid': 'title-link'})['href']
            # Convert relative path to absolute path if not already absolute
            if not url.startswith("http"):
                url = "https://www.booking.com" + url  # URL 절대 경로로 변환
        except TypeError:
            url = 'N/A'
        
        if name in scraped_names:
            continue  # Skip duplicates
        
        hotels.append({'Name': name, 'URL': url})
        scraped_names.add(name)
    
    return hotels

# Function to estimate remaining time
def estimate_remaining_time(start_time, total_scraped, total_needed):
    elapsed_time = datetime.now() - start_time
    time_per_hotel = elapsed_time.total_seconds() / total_scraped if total_scraped > 0 else 0
    remaining_hotels = total_needed - total_scraped
    remaining_time = remaining_hotels * time_per_hotel
    return remaining_time

# Function to scrape all pages
def scrape_all_pages(driver, base_url, max_hotels):
    all_hotels = []
    scraped_names = set()
    cooldown_attempts = 0
    start_time = datetime.now()

    while True:
        print_header()
        print(Fore.YELLOW + "Scraping page...")
        try:
            scroll_to_bottom(driver)
            hotels = scrape_page(driver, scraped_names)
        except Exception as e:
            print(Fore.RED + f"Error during scraping: {e}")
            time.sleep(30)
            continue
        
        if not hotels:
            if cooldown_attempts == 0:
                print(Fore.RED + "No more hotels found, starting 1-minute cooldown.")
                for i in range(60, 0, -1):
                    print(Fore.YELLOW + f"Cooldown: {i} seconds remaining...", end='\r')
                    time.sleep(1)
                cooldown_attempts += 1
                continue  # Retry scraping the same page after cooldown
            else:
                print(Fore.RED + "No more hotels found after cooldown, stopping scrape.")
                break
        
        all_hotels.extend(hotels)
        total_hotels = len(all_hotels)
        
        print(Fore.GREEN + f"Total unique hotels collected so far: {total_hotels}")
        
        remaining_time = estimate_remaining_time(start_time, total_hotels, max_hotels)
        print(Fore.BLUE + f"Estimated remaining time: {time.strftime('%H:%M:%S', time.gmtime(remaining_time))}")
        
        if total_hotels >= max_hotels:
            print(Fore.GREEN + f"Reached the maximum limit of {max_hotels} unique hotels. Stopping scrape.")
            break

        retry_count = 0
        max_retries = 5
        while retry_count < max_retries:
            try:
                # Check if the "Load more results" button exists
                if len(driver.find_elements(By.XPATH, "//button[contains(text(), 'Load more results')]")) == 0:
                    print(Fore.RED + "No 'Load more results' button found. Ending scrape.")
                    return all_hotels
                
                # Re-find the "Load more results" button before each click
                load_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Load more results')]"))
                )
                load_more_button.click()
                print(Fore.CYAN + "Load more button clicked.")
                time.sleep(5)  # Give time for the next set of results to load
                break  # Exit the retry loop if successful
            except Exception as e:
                retry_count += 1
                print(Fore.RED + f"Error while trying to click 'Load more results' button: {e}")
                if retry_count < max_retries:
                    print(Fore.YELLOW + f"Retrying... ({retry_count}/{max_retries})")
                    time.sleep(30)  # Wait for 30 seconds before retrying
                else:
                    print(Fore.RED + "Stopping scrape.")
                    return all_hotels
        
        cooldown_attempts = 0  # Reset cooldown attempts after successful scrape
        time.sleep(1)  # A bit of delay to avoid overloading the server

    return all_hotels

# Main function
def main():
    print_header()
    base_url = input(Fore.YELLOW + "Enter the Booking.com search results URL: ")
    max_hotels = int(input(Fore.YELLOW + "Enter the maximum number of hotels to scrape: "))

    driver = initialize_driver()
    driver.get(base_url)

    all_hotels = scrape_all_pages(driver, base_url, max_hotels)

    # Save hotel information to an Excel file
    if all_hotels:
        df = pd.DataFrame(all_hotels)
        df.to_excel('hotels.xlsx', index=False)
        print(Fore.GREEN + "\nData successfully saved in hotels.xlsx")
    else:
        print(Fore.RED + "\nNo hotels found. Check the HTML structure of the page.")

    driver.quit()

if __name__ == "__main__":
    main()