
class Params:
    DELAY = 8
    DAYS = 7
    timeout = 15
    xpath_cookies = '//*[@id="yDmH0d"]/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[1]/div/div/button/span'
    xpath_tabla_button = "//div[contains(@class,'OHJaU')]"
    xpath_tabla_precios_elem = "//div[contains(@class,'OHJaU')]"
    xpath_celdas_tabla_precio = "//div[contains(@class,'NFIRFd')]"
    date_format = '%Y-%m-%d'
    month_mapping = {
                "jan": 1,
                "ene": 1,
                "feb": 2,
                "mar": 3,
                "apr": 4,
                "abr": 4,
                "may": 5,
                "jun": 6,
                "jul": 7,
                "aug": 8,
                "ago": 8,
                "sep": 9,
                "set": 9,
                "oct": 10,
                "nov": 11,
                "dec": 12,
                "dic": 12
            }