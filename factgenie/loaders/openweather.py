#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

import json
from factgenie.loaders.dataset import Dataset
import dateutil.parser
from datetime import datetime


class OpenWeather(Dataset):
    def __init__(self, name=None, **kwargs):
        name = "openweather" if name is None else name
        super().__init__(name=name, **kwargs)
        self.type = "json"

    def get_info(self):
        return """
        Weather forecasts from <u><a href="https://openweathermap.org/forecast5">OpenWeather</a></u>.
        """

    def postprocess_data(self, data):
        forecasts = data["forecasts"]
        data = []

        # https://openweathermap.org/api/hourly-forecast, using metric system
        units = {
            "temp": "°C",
            "wind": "m/s",
            "pressure": "hPa",
            "rain": "mm",
            "snow": "mm",
        }

        for forecast in forecasts:
            city = forecast["city"]
            lst_filtered = []
            timezone_shift_sec = city["timezone"]

            for key in ["sunrise", "sunset", "population", "timezone"]:
                city.pop(key, None)

            for i, f in enumerate(forecast["list"]):
                # 6-hour intervals
                if i % 2 != 0:
                    continue
                f = {k: v for k, v in f.items() if k not in ["dt", "pop", "sys", "visibility"]}

                # remove the main -> temp_kf key
                f["main"] = {
                    k: v for k, v in f["main"].items() if k not in ["temp_kf", "humidity", "sea_level", "grnd_level"]
                }

                # convert "dt_txt" to timestamp
                local_datetime = dateutil.parser.parse(f["dt_txt"])
                local_datetime = local_datetime.timestamp()
                # shift timezone
                local_datetime += timezone_shift_sec
                # convert back to "2023-11-28 09:00:00"
                local_datetime = datetime.fromtimestamp(local_datetime).strftime("%Y-%m-%d %H:%M:%S")
                f["dt_txt"] = local_datetime

                lst_filtered.append(f)

            data.append({"city": city, "units": units, "list": lst_filtered})

        return data

    def render(self, example):
        html = ""

        return (
            """<div id="meteogram"></div><div class="root" style="margin-top: 40px">"""
            + html
            + """</div>
        <script>
            if (typeof forecast === 'undefined') {
                var forecast = """
            + json.dumps(example)
            + """;
                // var tree = jsonview.create(forecast);
            } else {
                forecast = """
            + json.dumps(example)
            + """;
               // tree = jsonview.create(forecast);
            }
            
            // jsonview.render(tree, document.querySelector('.root'));
            // jsonview.expand(tree);
            window.meteogram = new Meteogram(forecast, 'meteogram');
        </script>"""
        )
