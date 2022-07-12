from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException

import requests
from requests_html import HTMLSession
import pandas as pd
import time
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor
from random import randint

__config_dict =  {
    "projekt_name":"full_stepstone_DS_crawl",
    "hub_session" : False, #Attach to current Selenium Grid Session by ID 
    "max_pages": 380, 
    "job": "'Data Science'",
    "hub_url" : "http://127.0.0.1:4444/wd/hub",
    "url" : "https://www.stepstone.de/",
    "search_x_path": "/html/body/div[2]/div[1]/div[3]/div/div/div/div/div[1]/div[1]/div[1]/div/div[2]/input", 
    "cookie_disclamer_xpath" : "//div[@id = 'ccmgt_explicit_accept']",
    "headline_xpath" : "//h2[@class='sc-pJurq hXakmZ']",
    "city_xpath" : "//li[@class='sc-qQMSE gzFHUw sc-pBzUF eUumVw']",
    "links_xpath" : "//a[@class='sc-pAZqv cyGFEN']",
    "text_xpath" : "//div[@itemprop='description']//p|//div[@itemprop='description']//b|//div[@itemprop='description']//li",
    "next_page_xpath" : '//a[@data-at="pagination-next"]',
    "prod": False # If prod = True, content will saved to inline json
}


def attach_to_session(executor_url, session_id):
    '''
    If a Webdriver in the Selenium Grid is already allocated to a Session ID.
    Takes a Session ID and returns a Webdriver.
    '''
    original_execute = WebDriver.execute
    def new_command_execute(self, command, params=None):
        if command == "newSession":
            # Mock the response
            return {'success': 0, 'value': None, 'sessionId': session_id}
        else:
            return original_execute(self, command, params)
    # Patch the function before creating the driver object
    WebDriver.execute = new_command_execute
    
    opt = webdriver.ChromeOptions()
    opt.add_argument('ignore-certificate-errors')
    opt.add_argument("--incognito")
    opt.add_argument('--disable-blink-features=AutomationControlled')

    driver = webdriver.Remote(command_executor=executor_url, options=opt)
    driver.session_id = session_id
    print(session_id)
    # Replace the patched function with original function
    WebDriver.execute = original_execute
    return driver

class scraper:
    def __init__(self, driver, projekt_name,hub_url, job, url, search_x_path, cookie_disclamer_xpath, headline_xpath, city_xpath, links_xpath, text_xpath, next_page_xpath, max_pages):
        self.session = HTMLSession()
        self.driver = driver
        self.projekt_name = projekt_name
        self.hub_url = hub_url
        self.url = url
        self.job = job
        self.search_x_path = search_x_path
        self.cookie_disclamer_xpath = cookie_disclamer_xpath
        self.headline_xpath = headline_xpath
        self.city_xpath = city_xpath
        self.links_xpath = links_xpath
        self.text_xpath = text_xpath
        self.next_page_xpath = next_page_xpath
        self.max_pages = max_pages

        self.driver.delete_all_cookies
        self.driver.delete_cookie
        self.driver.maximize_window()
        self.driver.get(url)

        #Create Empty Dataframe
        self.df = pd.DataFrame(columns = ["headline","stadt","links","text"])

    def _check_presence(self, x_path, time = 1):
        '''
        Check if an X-Path-Element can be located at current page.
        Takes an X-Path-Element and returns the Driver if the Element is present. 
        '''
        try: 
            #check if element is visible
            good_driver = WebDriverWait(self.driver, time).until(EC.presence_of_element_located((By.XPATH, x_path)))
            return good_driver
        except TimeoutException as t:
            return False


    def _job_bot(self,url, session):
        '''
        Takes a HTML-Websession and returns requested element from page.
        '''
        try:
            #get random user agend
            time.sleep(randint(0,1))
            ua = UserAgent()
            headers = requests.utils.default_headers()
            #update header with user agend
            headers.update({'User-Agent': ua.chrome,})
            #send request
            response = session.get(url, headers=headers, timeout=10)
            print(f"          ---> DONE U............L: {url}")
            return " ".join([i.text for i in response.html.xpath(self.text_xpath)])
        except Exception as e:
            print(f"          ---> Skip URL: {url}")
            return ""
    
    def _save_data(self):
        '''
        Safe the dataframe to inline Json.
        '''
        if __config_dict["prod"]:
            self.df.to_json(f"./{self.projekt_name}.json", orient="records", lines = True)
            print(f"          ---> Saved Data to: ./{self.projekt_name}.json")

    def main_bot(self):
        '''
        Navigate through Stepstone and scrape job descriptions. 
        '''
        cookie_disclaimer = self._check_presence(x_path =  self.cookie_disclamer_xpath)
        if cookie_disclaimer:
            cookie_disclaimer.click()

        search_field = self._check_presence(x_path = self.search_x_path)
        if search_field:
            search_field.send_keys(self.job)
            search_field.send_keys(Keys.ENTER)

        for page in range(0,self.max_pages):
            try:
                next_page = self.driver.find_element(By.XPATH,self.next_page_xpath).get_attribute('href')
                print(f"\n Page {page+1} / {self.max_pages}: {next_page} \n")

                page_links = [i.get_attribute('href') for i in driver.find_elements(By.XPATH, self.links_xpath)]

                with ThreadPoolExecutor(max_workers=min(50, len(page_links))) as pool:
                    text_results = pool.map(self._job_bot, page_links, [self.session for _ in range(len(page_links))])

                current_page_data = pd.DataFrame({
                    "headline" : [i.text for i in driver.find_elements(By.XPATH, self.headline_xpath)],
                    "stadt" : [i.text for i in driver.find_elements(By.XPATH, self.city_xpath)],
                    "links" : page_links,
                    "text" : [i for i in text_results]})

                self.df = pd.concat([self.df, current_page_data])
                
                self._save_data()
                driver.get(next_page)
            except:
                pass
        if not self.df.empty:
            self._save_data()
        else:
            print("No Data Available. Check your Config")


if __name__ == "__main__":

    #Start Driver-Session
    if __config_dict["hub_session"]:
        print(f"Use Session {__config_dict['hub_session']}")
        driver = attach_to_session(executor_url = __config_dict["hub_url"],session_id = __config_dict["hub_session"])
    else:
        opt = webdriver.ChromeOptions()
        opt.add_argument('ignore-certificate-errors')
        opt.add_argument("--incognito")
        opt.add_argument('--disable-blink-features=AutomationControlled')

        driver = webdriver.Remote(command_executor=__config_dict["hub_url"],options=opt)
        print(f"Create new Session {driver.session_id}")

    try:
        scraper_instance = scraper(
            driver = driver, 
            projekt_name = __config_dict["projekt_name"],
            hub_url = __config_dict["hub_url"],
            job = __config_dict["job"],
            url = __config_dict["url"],
            search_x_path = __config_dict["search_x_path"],
            cookie_disclamer_xpath = __config_dict["cookie_disclamer_xpath"],
            headline_xpath = __config_dict["headline_xpath"],
            city_xpath = __config_dict["city_xpath"],
            links_xpath = __config_dict["links_xpath"],
            text_xpath = __config_dict["text_xpath"],
            next_page_xpath = __config_dict["next_page_xpath"],
            max_pages = __config_dict["max_pages"]
        )
        scraper_instance.main_bot()
        print(scraper_instance.df)
    except Exception as e:
        print(f"Delete session {driver.session_id} because of Error: {e}")
        requests.delete("{}/session/{}".format(__config_dict["hub_url"],driver.session_id))
    finally:
        driver.quit()





    





    