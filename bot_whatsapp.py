from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--remote-debugging-port=9222")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--no-sandbox")

service = Service(r"C:\WebDriver\chromedriver.exe")
driver = webdriver.Chrome(service=service, options=options)
