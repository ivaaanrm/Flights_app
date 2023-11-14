import re
import time
import logging

from rich import print
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from bs4.element import PageElement
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webelement import WebElement
from webdriver_manager.chrome import ChromeDriverManager

from config.params import Params
from models.Flight import Itinerario, FlightRoute, FlightOption, FlightAlternative
from models.Flight import load_itinerarios_from_json


logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)


class GoogleFligthsScraper:
    def __init__(self):
        self.options = Options()
        # self.options.add_experimental_option("detach", True)
        self.options.add_argument("--headless")
        self.options.add_argument("'--no-sandbox'")
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=self.options
        )

    def scrape_fligths(self, itinerario: Itinerario, best_day: bool = False) -> FlightRoute:
        logging.info(f"Scraping flights for {itinerario.origin} to {itinerario.destination}")
        
        url = self._make_url(itinerario)
        self.driver.get(url)
        self.__handle_cookies()

        route = FlightRoute(itinerario)
        route.alternatives = self.find_flights_alternatives()
        
        # Return the FlightRoute for the best day found
        if best_day:
            return self.scrape_best_day_found(route)
        else:
            route.options = self.get_results(num_res=3)
            return route

    def find_flights_alternatives(self) -> List[FlightAlternative]:
        self.find_element(By.XPATH, Params.xpath_tabla_button).click()
        table_element = self.find_element(By.XPATH, Params.xpath_tabla_precios_elem)
        time.sleep(Params.DELAY)
        cells = table_element.find_elements(By.XPATH, Params.xpath_celdas_tabla_precio)
        return self.__parse_tabla_precios(cells)

    def get_results(self, num_res: int = 1) -> List[FlightOption]:
        # Devolver los datos de cada opcion
        time.sleep(Params.DELAY)

        html = self.driver.page_source
        self.link = self.driver.current_url
        soup = BeautifulSoup(html, "html.parser")

        flights_options = soup.find_all("div", {"class": "OgQvJf nKlB3b"})

        options = [self.__parse_flight_data(raw_option) for raw_option in flights_options[:num_res]]
        return options


    def scrape_best_day_found(self, route: FlightRoute) -> FlightRoute:
        best = route.get_best_alterantive()

        new_itinerario = Itinerario(         
            route.itinerario.origin,
            route.itinerario.destination,
            best.departure_date,
            best.return_date
        )
        newRoute = FlightRoute(new_itinerario)

        url = self._make_url(new_itinerario)
        self.driver.get(url)

        # All flights for the date
        newRoute.options = self.get_results(num_res=3)
        newRoute.alternatives = self.find_flights_alternatives()

        return newRoute


    def _make_url(self, iti: Itinerario) -> str:
        if iti.return_date:
            url = "https://www.google.com/travel/flights?q=Flights%20to%20{dst}%20from%20{org}%20on%20{d_init}%20through%20{d_return}".format(
                dst=iti.destination,
                org=iti.origin,
                d_init=iti.departure_date,
                d_return=iti.return_date,
            )
        else:
            url = "https://www.google.com/travel/flights?q=Flights%20to%20{dst}%20from%20{org}%20on%20{d_init}".format(
                dst=iti.destination, org=iti.origin, d_init=iti.departure_date
            )

        return url

    def __handle_cookies(self):
        try:
            cookies = self.find_element(By.XPATH, Params.xpath_cookies)
            cookies.click()
        except Exception as e:
            logging.warning(f"! Failed to handle cookies pop-up")
            pass

    def __parse_tabla_precios(self, cells: List[WebElement]) -> List[FlightAlternative]:
        fechas = []
        prices = []

        for cell in cells:
            linea = cell.text
            
            dateES = re.search(r"\d{1,2} [a-z]{3}", linea)
            dateENG = re.search(
                r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{1,2}\b",
                linea,
            )
            if dateES:
                fechas.append(dateES.group())
            elif dateENG:
                fechas.append(dateENG.group())
            elif re.match(r"\d+ €", linea) or re.match(r"€\d+", linea):
                price = float("".join(x for x in linea if x.isdigit()))
                prices.append(price)

        departure_date = fechas[:Params.DAYS]
        return_date = fechas[Params.DAYS:]
        
        results = []
        for i, price in enumerate(prices):
            try:
                init_day = self.__parse_month_day_to_date(departure_date[i % Params.DAYS])
                return_day = self.__parse_month_day_to_date(return_date[i // Params.DAYS])
                results.append(FlightAlternative(init_day, return_day, price))
            except:
                continue
            
        return results

    def __parse_month_day_to_date(self, month_day_string: str) -> str:
        try:
            year = datetime.now().year
            month, day = month_day_string.split()            
            month_number = Params.month_mapping.get(month.lower(), None)
            
            if month_number < datetime.now().month:
                year += 1
            
            date = datetime(year, month_number, int(day))

            return date.strftime("%Y-%m-%d")
        
        except Exception as e:
            import traceback
            logging.warning(f"Error parseando fecha de la tabla de precios {day=}, {month=}")
            logging.warning(traceback.format_exc())
            

    def __parse_datetime(self, input_string) -> str:
        try:
            # Define the format of the input string
            input_format = "%I:%M %p on %a, %b %d"

            # Parse the string into a datetime object
            parsed_datetime = datetime.strptime(input_string, input_format)
            return parsed_datetime.strftime("%d/%M %H:%M")
        except ValueError:
            logging.error("Invalid datetime")
            return ""

    def __parse_flight_data(self, data: PageElement) -> FlightOption:
        departure_info = data.find_next("div", {"class": "Ir0Voe"}).find_all("div")
        departure = " -> ".join(
            [self.__parse_datetime(x.text) for x in departure_info[1:3]]
        )
        carrier = departure_info[-1].text
        escalas = data.find_next("div", {"class": "BbR8Ec"}).find_all("div")[0].text
        price = self.__parse_price(data.find_next("div", {"class": "U3gSDe"}).text)
        return FlightOption(departure, carrier, escalas, price, self.link)

    def __parse_price(self, cellText: str) -> float:
        if "€" in cellText:
            return float("".join(x for x in cellText if x.isdigit()))
        else:
            return -1

    def __go_to_cheapest_day(self, cells: List):
        prices = [
            (cell_element, self.__parse_price(cell_element.text))
            for cell_element in cells
            if self.__parse_price(cell_element.text) > 0
        ]
        min_price_element = min(prices, key=lambda x: x[1])
        actions = ActionChains(self.driver)
        actions.move_to_element(min_price_element[0]).click().perform()
        self.driver.find_element(
            By.XPATH,
            '//*[@id="yDmH0d"]/div[5]/div[1]/div[3]/div[2]/div[2]/div[2]/div/button/span',
        ).click()


    def find_element(self, by: str, value: str, timeout: int=15) -> WebElement:
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            print(f"Element with {by}={value} not found within {timeout} seconds.")
            return None
        
    def find_elements(self, by: str, value: str, timeout: int=15) -> WebElement:
        try:
            elements = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_all_elements_located((by, value))
            )
            return elements
        except TimeoutException:
            print(f"Element with {by}={value} not found within {timeout} seconds.")
            return None
    
    def close(self):
        self.driver.quit()






def main():
    WORKPATH = "/Users/ivan/Desktop/Projects-dev/Flights_app/data"
    JSON_ITIMERARIOS_PATH = "/Users/ivan/Desktop/Projects-dev/Flights_app/data/itinerarios.json"
    
    s = GoogleFligthsScraper()

    itinerarios = load_itinerarios_from_json(JSON_ITIMERARIOS_PATH)
    
    try:
        for itinerario in itinerarios:
            flight_route = s.scrape_fligths(itinerario, best_day=True)
            flight_route.save_to_json(WORKPATH)

    except Exception as e:
        logging.exception(e)
    finally:
        s.close()


if __name__ == "__main__":
    main()
