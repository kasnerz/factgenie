from factgenie.loaders.ice_hockey import IceHockey
from factgenie.loaders.gsmarena import GSMArena
from factgenie.loaders.openweather import OpenWeather
from factgenie.loaders.owid import OurWorldInData
from factgenie.loaders.wikidata import Wikidata
from factgenie.loaders.logicnlg import LogicnlgTest100Tables
from factgenie.loaders.dummy import Dummy

DATASET_CLASSES = {
    "ice_hockey": IceHockey,
    "gsmarena": GSMArena,
    "openweather": OpenWeather,
    "owid": OurWorldInData,
    "wikidata": Wikidata,
    "logicnlg": LogicnlgTest100Tables,
    "dummy": Dummy,
    "st24-ice_hockey": IceHockey,
    "st24-gsmarena": GSMArena,
    "st24-openweather": OpenWeather,
    "st24-owid": OurWorldInData,
}
