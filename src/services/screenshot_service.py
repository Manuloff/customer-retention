from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class DashboardScreenshotService:
    def __init__(self, dashboard_url: str):
        self.dashboard_url = dashboard_url

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        self.driver = webdriver.Chrome(options=chrome_options)

    async def screenshot_graph(self, class_name: str, output_path: str):
        self.driver.get(self.dashboard_url)

        element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, class_name))
        )

        element.screenshot(output_path)

    def close(self):
        self.driver.quit()
