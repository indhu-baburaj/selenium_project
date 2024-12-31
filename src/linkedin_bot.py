import logging
import json
from datetime import datetime
import os
import time
import csv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# XPaths used
XPATHS = {
        'send_note_button': "//button[contains(@aria-label, 'Add a note')]",
        'send_without_note_button': "//button[contains(@aria-label, 'Send without a note')]",
        'connect_to_invite': "(//main//button[contains(@aria-label, 'Invite')])[1]",
        'note_text_box': "//textarea[contains(@name, 'message')]",
        'send_invitation_confirmation_button': "//button[contains(@aria-label, 'Send invitation')]",
        'more_options': "//main//button[contains(@aria-label, 'More actions')]",
        'invite_options': "//main//div[contains(@aria-label, 'to connect')]",
        'message_option': "//span[text()='1st']",
        'already_connected_indicator': "//span[text()='1st']"
    }
class LinkedInBot:

    
    def __init__(self):
        self.logger = self.setup_logging()
        self.browser = None

    def setup_logging(self):
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('linkedin_automation.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

    def setup_browser(self, headless=False):
        """Initialize the WebDriver with Chrome options"""
        self.logger.info("Setting up Chrome browser...")
        try:
            options = Options()
            options.add_argument("--disable-gpu")
            options.add_argument("--start-maximized")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            service = Service(ChromeDriverManager().install())
            self.browser = webdriver.Chrome(service=service, options=options)
            self.logger.info("Chrome browser setup successful")
            return self.browser
        except Exception as e:
            self.logger.error(f"Failed to setup browser: {str(e)}")
            raise

    def get_processed_urls_filename(self, username):
        """Generate a unique processed URLs filename for each account"""
        safe_username = "".join(x for x in username if x.isalnum())
        return f'processed_urls_{safe_username}.json'

    def load_processed_urls(self, username):
        self.logger.info(f"Loading previously processed URLs for account: {username}")
        filename = self.get_processed_urls_filename(username)
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded {len(data)} previously processed URLs for {username}")
                    return data
            else:
                return {}
        except Exception as e:
            self.logger.error(f"Error loading processed URLs for {username}: {str(e)}")
        self.logger.info(f"No previous processed URLs found for {username}, starting fresh")
        return {}

    def save_processed_url(self, url, status, username):
        self.logger.debug(f"Saving URL status for {username} - URL: {url}, Status: {status}")
        try:
            filename = self.get_processed_urls_filename(username)
            processed_urls = self.load_processed_urls(username)
            processed_urls[url] = {
                'status': status,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(filename, 'w') as f:
                json.dump(processed_urls, f)
            self.logger.info(f"Successfully saved status for URL: {url} for account: {username}")
        except Exception as e:
            self.logger.error(f"Error saving processed URL {url} for {username}: {str(e)}")

    def is_already_connected(self):
        self.logger.debug("Checking if already connected...")
        try:
            element = self.safe_find_element(By.XPATH, XPATHS['already_connected_indicator'])
            is_connected = element is not None and element.is_displayed()
            self.logger.info(f"Connection status check result: {'Connected' if is_connected else 'Not connected'}")
            return is_connected
        except Exception as e:
            self.logger.error(f"Error checking connection status: {str(e)}")
            return False

    def safe_find_element(self, by, value):
        self.logger.debug(f"Searching for element: {by}={value}")
        try:
            element = self.browser.find_element(by, value)
            self.logger.debug(f"Element found: {by}={value}")
            return element
        except NoSuchElementException:
            self.logger.debug(f"Element not found: {by}={value}")
            return None

    def login_to_linkedin(self, username, password):
        self.logger.info("Starting LinkedIn login process...")
        try:
            self.browser.get("https://www.linkedin.com/login")
            self.logger.info("Navigated to LinkedIn login page")
            
            wait = WebDriverWait(self.browser, 10)
            wait.until(EC.presence_of_element_located((By.ID, "username")))
            
            username_input = self.safe_find_element(By.ID, "username")
            password_input = self.safe_find_element(By.ID, "password")
            sign_in_button = self.safe_find_element(By.CSS_SELECTOR, "button[aria-label='Sign in']")

            if all([username_input, password_input, sign_in_button]):
                username_input.send_keys(username)
                self.logger.info("Username entered")
                password_input.send_keys(password)
                self.logger.info("Password entered")
                if sign_in_button:
                    sign_in_button.click()
                    self.logger.info("Clicked sign-in button.")
                else:
                    self.logger.error("Sign in button not found, cannot proceed with login.")
                    return False
                
                try:
                    otp_element = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located((By.ID, "input__phone_verification_pin")))
                    otp_code = input("Enter the OTP sent to your phone: ")
                    otp_element.send_keys(otp_code)
                    self.browser.find_element(By.XPATH, "//button[@type='submit']").click()
                    self.logger.info("Entered OTP and submitted.")
                except TimeoutException:
                    self.logger.info("No OTP verification required.")
            
                # Verify successful login
                WebDriverWait(self.browser, 120).until(EC.presence_of_element_located((By.ID, "global-nav-search")))
                self.logger.info("Logged in to LinkedIn successfully.")
                return True
        except TimeoutException:
            self.logger.error("Login failed: Timeout while waiting for elements.")
            return False
        except NoSuchElementException:
            self.logger.error("Login failed: Element not found.")
            return False
        except Exception as e:
            self.logger.error(f"Login failed: {str(e)}")
            return False

    def send_invitation(self, note, with_note=True):
        self.logger.info("Attempting to send invitation...")
        if with_note:
            self.logger.info("Sending invitation with note")
            send_note = self.safe_find_element(By.XPATH, XPATHS['send_note_button'])
            if send_note:
                try:
                    send_note.click()
                    self.logger.info("Clicked 'Add a note' button")
                    time.sleep(2)
                    
                    note_box = self.safe_find_element(By.XPATH, XPATHS['note_text_box'])
                    if note_box:
                        note_box.send_keys(note)
                        self.logger.info("Note text entered successfully")
                        time.sleep(2)
                        
                        confirm_button = self.safe_find_element(By.XPATH, XPATHS['send_invitation_confirmation_button'])
                        if confirm_button:
                            confirm_button.click()
                            self.logger.info("Invitation with note sent successfully")
                            time.sleep(2)
                            return True
                except Exception as e:
                    self.logger.error(f"Error sending invitation with note: {str(e)}")
        else:
            self.logger.info("Sending invitation without note")
            send_without_note = self.safe_find_element(By.XPATH, XPATHS['send_without_note_button'])
            if send_without_note:
                try:
                    send_without_note.click()
                    self.logger.info("Invitation without note sent successfully")
                    time.sleep(2)
                    return True
                except Exception as e:
                    self.logger.error(f"Error sending invitation without note: {str(e)}")
        
        self.logger.error("Failed to send invitation")
        return False

    def pre_scan_profiles(self, csv_path, username):
        """Pre-scan profiles from CSV to determine connection status"""
        self.logger.info("Starting pre-scan of profiles...")
        try:
            processed_urls = self.load_processed_urls(username)
            total_profiles = 0
            already_connected_profiles = 0
            new_profiles = 0
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    profile_url = row['Profile_URL']
                    total_profiles += 1
                    if profile_url in processed_urls and processed_urls[profile_url]['status'] in ["Connected", "Already Connected"]:
                        self.logger.info(f"Skipping already connected profile: {profile_url}")
                        already_connected_profiles += 1
                        continue
                    
                    self.logger.info(f"Scanning profile {total_profiles}: {profile_url}")
                    new_profiles += 1
                    
                    self.browser.get(profile_url)
                    time.sleep(3)
                    
                    if self.is_already_connected():
                        self.logger.info(f"Profile already connected: {profile_url}")
                        self.save_processed_url(profile_url, "Already Connected", username)
                        already_connected_profiles += 1
                    else:
                        self.logger.info(f"Profile not connected: {profile_url}")
                        self.save_processed_url(profile_url, "Not Connected", username)
            
            self.logger.info(f"Pre-scan completed. Total profiles: {total_profiles}, Already connected: {already_connected_profiles}, New profiles: {new_profiles}")
        except Exception as e:
            self.logger.error(f"Error in pre_scan_profiles: {str(e)}")

    def connect_with_remaining(self, csv_path, note, username):
        """Connect with remaining profiles from CSV"""
        self.logger.info("Starting to connect with remaining profiles...")
        try:
            processed_urls = self.load_processed_urls(username)
            connection_attempts = 0
            successful_connections = 0
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    profile_url = row['Profile_URL']
                    if profile_url in processed_urls and processed_urls[profile_url]['status'] in ["Connected", "Already Connected"]:
                        self.logger.info(f"Skipping already connected profile: {profile_url}")
                        continue
                    
                    self.logger.info(f"Processing URL: {profile_url}")
                    connection_attempts += 1
                    
                    self.browser.get(profile_url)
                    time.sleep(3)
                    
                    if self.is_already_connected():
                        self.logger.info(f"Found already connected profile: {profile_url}")
                        self.save_processed_url(profile_url, "Already Connected", username)
                        continue

                    connect_button = self.safe_find_element(By.XPATH, XPATHS['connect_to_invite'])
                    if connect_button and connect_button.is_displayed():
                        self.logger.info("Found direct connect button")
                        connect_button.click()
                        time.sleep(2)
                        # Ask user whether to send with or without note
                        with_note = input("Do you want to send the invitation with a note? (yes/no): ").strip().lower() == 'yes'
                        
                        if self.send_invitation(note, with_note):
                            self.save_processed_url(profile_url, "Connection Sent", username)
                            successful_connections += 1
                        continue
                    else:
                        self.logger.warning(f"No connect option found for {profile_url}")
                        self.save_processed_url(profile_url, "No Connect Option", username)
            
            self.logger.info(f"Connection process completed. Attempts: {connection_attempts}, Successful: {successful_connections}")
        except Exception as e:
            self.logger.error(f"Error in connect_with_remaining: {str(e)}")

# Main execution
if __name__ == "__main__":
    bot = LinkedInBot()
    bot.logger.info("=== LinkedIn Automation Script Started ===")
    start_time = datetime.now()
    
    try:
        csv_path = "C:/Users/Indhu/Downloads/inputs.csv"
        bot.logger.info(f"Using CSV file: {csv_path}")
        
        username = input("Enter your username: ")
        password = input("Enter your password: ")
        
        bot.setup_browser(headless=False)
        
        if not bot.login_to_linkedin(username, password):
            bot.logger.error("Login failed, exiting script")
            bot.browser.quit()
            exit()
        
        # Pre-scan phase
        bot.pre_scan_profiles(csv_path, username)

        # Connect with remaining profiles
        note = "Hey,\n\n It's always great connecting with classmates! Let's stay in touch and explore any opportunities to collaborate in the future. \n\nCheers,\nIndhu"
        bot.connect_with_remaining(csv_path, note, username)
        
    except WebDriverException as e:
        bot.logger.error(f"Critical WebDriver error in main execution: {str(e)}")
    except Exception as e:
        bot.logger.error(f"Critical error in main execution: {str(e)}")
    finally:
        try:
            bot.browser.quit()
        except Exception as e:
            bot.logger.error(f"Error while quitting the browser: {str(e)}")
        end_time = datetime.now()
        duration = end_time - start_time
        bot.logger.info(f"=== Script completed in {duration} ===")