from factgenie.loaders.gsmarena import GSMArena
from factgenie.loaders.ice_hockey import IceHockey
from factgenie.loaders.openweather import OpenWeather
from factgenie.loaders.owid import OurWorldInData


class ST24GSMArena(GSMArena):
    def __init__(self, name=None, **kwargs):
        name = "st24-gsmarena"
        super().__init__(name=name, **kwargs)


class ST24IceHockey(IceHockey):
    def __init__(self, name=None, **kwargs):
        name = "st24-ice_hockey"
        super().__init__(name=name, **kwargs)


class ST24OpenWeather(OpenWeather):
    def __init__(self, **kwargs):
        name = "st24-openweather"
        super().__init__(name=name, **kwargs)


class ST24OurWorldInData(OurWorldInData):
    def __init__(self, **kwargs):
        name = "st24-owid"
        super().__init__(name=name, **kwargs)