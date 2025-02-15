from selenium import webdriver
from shutil import which


class BCRAScraper:
    """
    Clase que representa un Scraper que funciona para las distintas
    publicaciones del BCRA (Banco Central de la República Argentina).


    Attributes
    ----------
    url : str
        Una cadena que representa una url válida, usada para obtener
        el contenido a ser scrapeado
    use_intermediate_panel : bool
        Flag para indicar si se debe generar o leer un archivo intermedio
        con formato panel

    Methods
    -------
    fetch_contents(start_date, end_date)
        Obtiene los contenidos a ser parseados

    parse_contents(start_date, end_date)
        Recibe un iterable de contenidos y devuelve un iterable con la
        información scrapeada

    run(start_date, end_date)
        Llama a los métodos que obtienen y scrapean los contenidos
        y los devuelve en un iterable
    """

    def __init__(self, url, use_intermediate_panel, *args, **kwargs):
        """
        Parameters
        ----------
        url : str
            Una cadena que representa una url válida, usada para obtener
            el contenido a ser scrapeado. Una URL se considera válida cuando su
            contenido no está vacio.
        use_intermediate_panel : bool
            Flag para indicar si se debe generar o leer un archivo intermedio
            con formato panel
        """
        self.browser_driver = None
        self.url = url
        self.timeout = kwargs.get('timeout', None)
        self.tries = kwargs.get('tries', 1)
        self.use_intermediate_panel = use_intermediate_panel

    def _create_browser_driver(self):
        """
        Método que crea el navegador y le pasa una opción
        para esconder la visualización del mismo.
        """
        if which("chromedriver"):
            options = webdriver.ChromeOptions()
            options.headless = True

            browser_driver = webdriver.Chrome(options=options)
            if self.timeout:
                browser_driver.set_page_load_timeout(self.timeout)

            return browser_driver
        else:
            print("El driver del navegador no se encuentra en el PATH")

    def get_browser_driver(self):
        """
        Método que verifica la existencia del navegador, en caso
        de que no exista llama a la función que lo crea.
        """
        if not self.browser_driver:
            self.browser_driver = self._create_browser_driver()

        return self.browser_driver

    def fetch_contents(self, start_date, end_date):
        """
        Retorna un iterable donde cada elemento es un String, o una lista
        vacía si no hay contenidos.

        Parameters
        ----------
        start_date : date
            fecha de inicio que va a tomar como referencia el scraper
        end_date: date
            fecha de fin que va a tomar como referencia el scraper
        Raises
        ------
        NotImplementedError
            si no se encuentra la función o sus parámetros dentro de la clase
        """

        raise NotImplementedError

    def parse_contents(self, start_date, end_date):
        """
        Retorna un iterable donde cada elemento es un String, o una lista
            vacía si no hay contenidos.

        Parameters
        ----------
        start_date : date
            fecha de inicio que va a tomar como referencia el scraper
        end_date: date
            fecha de fin que va a tomar como referencia el scraper
        Raises
        ------
        NotImplementedError
            si no se encuentra la función o sus parámetros dentro de la clase
        """

        raise NotImplementedError

    def preprocess_start_date(self, start_date):
        return start_date

    def preprocess_end_date(self, end_date):
        return end_date

    def run(self, start_date, end_date):
        """
        Inicializa un iterable. Llama a los métodos para obtener y scrapear
        los contenidos, y los ingresa en el iterable.
        Retorna un diccionario que tiene como clave cada moneda
        y como valor una lista con un diccionario que tiene los
        contenidos parseados.

        Parameters
        ----------
        start_date: date
            fecha de inicio que toma como referencia el scraper

        end_date : date
            fecha de fin que va a tomar como referencia el scraper
        """
        parsed = []
        start_date = self.preprocess_start_date(start_date)
        end_date = self.preprocess_end_date(end_date)

        if self.use_intermediate_panel:
            first_date = start_date.strftime("%Y-%m-%d")
            last_date = end_date.strftime("%Y-%m-%d")

            parsed = self.parse_from_intermediate_panel(first_date, last_date)
        else:
            contents = self.fetch_contents(start_date, end_date)
            _parsed = self.parse_contents(contents, start_date, end_date)

            parsed = self._preprocess_rows(_parsed)

            self.save_intermediate_panel(parsed)
        return parsed
