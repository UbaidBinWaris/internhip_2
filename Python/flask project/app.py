from flask import Flask, render_template
from datetime import datetime
from bs4 import BeautifulSoup
import requests, time, re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def get_oil_and_coal():
    url = "https://markets.businessinsider.com/commodities"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        brent = wti = coal = "Not found"
        for tr in soup.select("table tbody tr"):
            cols = tr.find_all("td")
            if len(cols) >= 4:
                name = cols[0].get_text(strip=True)
                price = cols[1].get_text(strip=True)
                if "Oil (Brent)" in name:
                    brent = price
                elif "Oil (WTI)" in name:
                    wti = price
                elif name.strip().lower() == "coal":
                    coal = price
        return brent, wti, coal
    except Exception as e:
        print("Error fetching oil and coal:", e)
        return "Error", "Error", "Error"

def get_bunker_price():
    url = "https://shipandbunker.com/prices/av/global/av-glb-global-average-bunker-price"
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-software-rasterizer")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        for tr in soup.find_all("tr"):
            cols = tr.find_all("td")
            if cols and "Global Average Bunker Price" in cols[0].get_text(strip=True):
                return cols[1].get_text(strip=True)
        return "Not found"
    except Exception as e:
        print("Error fetching bunker price:", e)
        return "Error"

def get_usd_to_pkr():
    try:
        response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        data = response.json()
        rate = data["rates"]["PKR"]
        return f"{rate:.2f}"
    except Exception as e:
        print("Error fetching exchange rate:", e)
        return "Error"

# ✅ Fixed version of get_kibor()
def get_kibor():
    url = "https://www.sbp.org.pk/ecodata/kibor_index.asp"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        kibor_section = soup.find(string=lambda t: t and "KIBOR" in t)
        if not kibor_section:
            return "KIBOR data not found"
        table = kibor_section.find_parent().find_next('table')
        data = {}
        current_date = None
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            if len(cols) == 1:
                text = cols[0].get_text(strip=True)
                match = re.search(r"As on\s*(.+)", text, re.IGNORECASE)
                if match:
                    current_date = match.group(1).strip()
            elif len(cols) >= 3:
                tenor = cols[0].get_text(strip=True)
                bid = cols[1].get_text(strip=True)
                offer = cols[2].get_text(strip=True)
                data[tenor] = {"bid": bid, "offer": offer}
        return {"date": current_date, "rates": data}
    except Exception as e:
        print("Error fetching KIBOR:", e)
        return "Error"

def get_charter_rates():
    url = "https://www.handybulk.com/ship-charter-rates/"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        content = soup.get_text(separator="\n")
        lines = [line.strip() for line in content.splitlines() if '$' in line]
        return lines[:10]
    except Exception as e:
        print("Error fetching charter rates:", e)
        return ["Error fetching data"]

@app.route("/")
def index():
    brent, wti, coal = get_oil_and_coal()
    bunker = get_bunker_price()
    usd_to_pkr = get_usd_to_pkr()
    kibor = get_kibor()
    charter_rates = get_charter_rates()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template("index.html", brent=brent, wti=wti, coal=coal, bunker=bunker,
                           usd_to_pkr=usd_to_pkr, kibor=kibor, charter_rates=charter_rates,
                           timestamp=timestamp)

if __name__ == "__main__":
    app.run(debug=True)
