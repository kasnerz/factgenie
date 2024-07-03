from factgenie.loaders.ice_hockey import IceHockey
from factgenie.loaders.gsmarena import GSMArena
from factgenie.loaders.openweather import OpenWeather
from factgenie.loaders.owid import OurWorldInData
from factgenie.loaders.wikidata import Wikidata
from factgenie.loaders.logicnlg import LogicnlgTest100Tables
from factgenie.loaders.dummy import Dummy
from factgenie.loaders.practicald2t_st24 import ST24GSMArena, ST24IceHockey, ST24OpenWeather, ST24OurWorldInData

DATASET_CLASSES = {
    "ice_hockey": IceHockey,
    "gsmarena": GSMArena,
    "openweather": OpenWeather,
    "owid": OurWorldInData,
    "wikidata": Wikidata,
    "logicnlg": LogicnlgTest100Tables,
    "dummy": Dummy,
    "st24-ice_hockey": ST24IceHockey,
    "st24-gsmarena": ST24GSMArena,
    "st24-openweather": ST24OpenWeather,
    "st24-owid": ST24OurWorldInData,
}
