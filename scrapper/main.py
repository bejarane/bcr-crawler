import requests
import datetime
import logging
import configparser
import warnings
import json

class AppConfig:
    config : configparser.ConfigParser = None
    LICENSE_SERVICE_ID : int
    BASE_URL : str
    TOPIC_PATH : str
    BRANCH_PATH : str
    REGIONS : list
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        self.LICENSE_SERVICE_ID = self.config.getint('Settings', 'LICENSE_SERVICE_ID')
        self.BASE_URL = self.config.get('Settings', 'BASE_URL')
        self.TOPIC_PATH = self.config.get('Settings', 'TOPIC_PATH')
        self.PROCEDURE_PATH = self.config.get('Settings', 'PROCEDURE_PATH')
        self.BRANCH_PATH = self.config.get('Settings', 'BRANCH_PATH')
        regions = self.config.get('Settings', 'REGIONS')
        self.REGIONS = json.loads(regions)

class Appointment:
    date : datetime.date = None
    time : datetime.time = None
    id : int

    def __init__(self, _date: datetime.date ) -> None:
        self.date = _date

class Branch:
    id : int
    name : str
    address : str
    region_id : int
    topic_id : int
    config : AppConfig
    appointments : list[Appointment]

    def __init__(self, _id : int, _name : str, _address : str, _region_id : int, _topic_id : int, _config : AppConfig):
        self.id = _id
        self.name = _name
        self.address = _address
        self.region_id = _region_id
        self.topic_id = _topic_id
        self.config = _config
        self.appointments = []

    def add_appointment(self, _appointment : Appointment):
        self.appointments.append(_appointment)

    def __str__(self):
        return f"branchId: {self.id} branchName: {self.name}"
    
    def __repr__(self):
        return self.__str__()

class Region:
    id : int
    name : str
    branches : list[Branch]
    topic_id : int
    config : AppConfig

    def __init__(self, _id : int, _name : str, _topic_id : int, _config : AppConfig):
        self.id = _id
        self.name = _name
        self.topic_id = _topic_id
        self.config = _config
        self.branches = []

    def get_branches(self):
        logging.info(f"Downloading branches for topic {self.topic_id} in region {self.name}...")
        post_data = {"topicoId": self.topic_id, "provinciaId": self.id}
        url = self.config.BASE_URL + self.config.BRANCH_PATH
        response = Rest.post_uri(_uri= url, _data= post_data)
        available_branches = response.json()
        for unit in available_branches:
            branch = Branch(unit['pSucursalID'], unit['pNombre'], unit['pDireccion'], unit['numeroProvincia'], self.topic_id, self.config)
            self.branches.append(branch)
        logging.debug("Obtained branches: ")
        logging.debug(self.branches)
        logging.debug("\n\n")   

class Procedure:
    id : int
    name : str

    def __init__(self, _id : int, _name : str):
        self.id= _id
        self.name = _name
        self.branches = []

    def __str__(self):
        return f"procedureID: {self.id} procedureName: {self.name}"
    
    def __repr__(self):
        return self.__str__()

class Topic:
    id : int
    name : str
    procedures : list[Procedure]
    regions : list[Region]

    def __init__(self, _id : int, _name : str, _config : AppConfig):
        self.config = _config
        self.id = _id
        self.name = _name
        self.procedures = []
        self.regions = []
    
    def __str__(self):
        return f"topicID: {self.id} topicName: {self.name}"
    
    def __repr__(self):
        return self.__str__()
    
    def get_procedures(self):
        logging.info(f"Downloading procedures for topic {self.name}...")
        post_data = {"topicoId": self.id}
        url = self.config.BASE_URL + self.config.PROCEDURE_PATH
        response = Rest.post_uri(_uri= url, _data= post_data)
        available_procedures = response.json()
        for unit in available_procedures:
            procedure = Procedure(unit['TramiteId'],unit['Nombre'])
            self.procedures.append(procedure)
        logging.debug("Obtained procedures: ")
        logging.debug(self.procedures)
        logging.debug("\n\n")

    def generate_regions(self):
        logging.info(f"Generating regions for topic {self.name}...")
        for region in self.config.REGIONS:
            generated_region = Region(region[0], region[1], self.id, self.config)
            self.regions.append(generated_region)
        logging.debug("Completed regions")
        logging.debug("\n\n")     
    

class BCRScrapper:
    id : int
    date : datetime.date
    topics : list[Topic]
    
    def __init__(self, _id: int, _config : AppConfig):
        self.config = _config
        self.topics = []
        logging.info(f"Creating Scrap id {_id}")
        self.id = _id
        self.date = datetime.datetime.now()
        self.get_topics()
        logging.info(f"Created Scrap id {self.id} at {self.date}\n\n")

    def get_topics (self):
        logging.info("Downloading topics...")
        post_data = {"servicioId": self.config.LICENSE_SERVICE_ID}
        url = self.config.BASE_URL + self.config.TOPIC_PATH
        response = Rest.post_uri(url, post_data)
        available_topics = response.json()
        for unit in available_topics:
            topic = Topic(unit['pTopicoID'], unit['pNombre'], self.config)
            self.topics.append(topic)
        logging.debug("Obtained topics: ")
        logging.debug(self.topics)
        logging.debug("\n\n")

    def load_topics_procedures (self):
        logging.info(f"Starting procedures refresh at: {datetime.datetime.now()}")
        for topic in self.topics:
            topic.get_procedures()
        logging.info(f"Completed procedures refresh at: {datetime.datetime.now()}\n\n")

    def load_topics_branches (self):
        logging.info(f"Starting branches refresh at: {datetime.datetime.now()}")
        for topic in self.topics:
            topic.generate_regions()
            for region in topic.regions:
                region.get_branches()
        logging.info(f"Completed branches refresh at: {datetime.datetime.now()}\n\n")

class Rest:
    def get_uri(self):
        """
        Not sure if needed
        """
        pass

    @classmethod
    def post_uri(cls, _uri : str, _data : dict = {}, _verify : bool = False):
        try:
            response = requests.post(_uri, data=_data, verify=_verify)
            return response
        except requests.exceptions.HTTPError as http_error:
            logging.debug(f"Failed with HTTP error: {http_error}")
            return None
        except requests.exceptions.Timeout as timeout_error:
            logging.debug(f"Failed due to timeout. Error: {timeout_error}")
            return None
        except requests.exceptions.RequestException as request_error:
            logging.debug(f"Request failed with error: {request_error}")
            return None

def main():
    warnings.filterwarnings("ignore")
    logging.basicConfig(level=logging.INFO)
    app_config = AppConfig('config.ini')
    scrapped = BCRScrapper(1, app_config)
    scrapped.load_topics_procedures()
    scrapped.load_topics_branches()

if __name__ == '__main__':
    main()