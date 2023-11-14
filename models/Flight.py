import os
import json
from datetime import datetime
from typing import List, Any
from dataclasses import dataclass, field, asdict

def load_itinerarios_from_json(json_file_path):
    with open(json_file_path, 'r') as file:
        json_data = json.load(file)

    itinerarios = [Itinerario(**itinerary) for itinerary in json_data]
    return itinerarios
    

@dataclass(frozen=True)
class Itinerario:
    origin: str
    destination: str
    departure_date: str
    return_date: str | None = None

    @property
    def file_name(self):
        now = datetime.now()
        s = f"{now.month}-{now.day}_{self.origin}_{self.destination}_{self.departure_date}_{self.return_date}.json"
        return s
    

@dataclass(frozen=True)
class FlightOption:
    departure: str
    carrier: str
    escalas: str
    price: float
    link: str = field(repr=False)


@dataclass(frozen=True)
class FlightAlternative:
    departure_date: str
    return_date: str
    price: float


@dataclass
class FlightRoute:
    itinerario: Itinerario
    options: List[FlightOption] = field(default_factory=list)
    alternatives: List[FlightAlternative] = field(default_factory=list)

    def get_best_alterantive(self) -> FlightAlternative:
        return min(self.alternatives, key=lambda x: x.price)
    
    def save_to_json(self, workpath: str) -> str:
        dir_path = os.path.join(workpath, 'fligths_data')
        os.makedirs(dir_path, exist_ok=True)
        outpath = os.path.join(dir_path, self.itinerario.file_name)
        with open(outpath, 'w') as json_file:
            json.dump(asdict(self), json_file, indent=4)
                