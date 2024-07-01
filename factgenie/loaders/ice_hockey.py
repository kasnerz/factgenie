#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

from datetime import datetime
from tinyhtml import h
from factgenie.loaders.dataset import Dataset
import json
from pathlib import Path


class IceHockey(Dataset):
    def __init__(self, name=None, **kwargs):
        name = "ice_hockey" if name is None else name
        super().__init__(name=name, **kwargs)
        self.type = "json"

    def get_info(self):
        return """
        Ice hockey game summaries from <u><a href="https://rapidapi.com/fluis.lacasse/api/icehockeyapi">RapidAPI</a></u>.
        """

    def postprocess_data(self, data):
        # recursively remove any references to images: `logo` and `flag` keys
        def recursive_remove_key(data, key_to_remove):
            if isinstance(data, dict):
                # Remove the key if it exists
                data.pop(key_to_remove, None)

                # Recursively call the function for nested dictionaries
                for key, value in data.items():
                    data[key] = recursive_remove_key(value, key_to_remove)

            elif isinstance(data, list):
                # Recursively call the function for elements in the list
                data = [recursive_remove_key(item, key_to_remove) for item in data]

            return data

        for game in data:
            start_timestamp = game["startTimestamp"]

            for key in [
                "changes",
                "crowdsourcingDataDisplayEnabled",
                "crowdsourcingEnabled",
                "customId",
                "finalResultOnly",
                "hasEventPlayerStatistics",
                "hasGlobalHighlights",
                "isEditor",
                "periods",
                "status",
                "time",
                "roundInfo",
                "tournament",
                "winnerCode",
            ]:
                if key in game:
                    game.pop(key)

            game["season"].pop("editor", None)

            for key in [
                "current",
                "slug",
                "sport",
                "teamColors",
                "subTeams",
                "userCount",
                "type",
                "disabled",
                "national",
            ]:
                recursive_remove_key(game, key)

            for key in ["homeTeam", "awayTeam"]:
                if type(game[key]["country"]) is dict and "name" in game[key]["country"]:
                    country_name = game[key]["country"]["name"]
                    game[key].pop("country")
                    game[key]["country"] = country_name

            # convert timestamp to date
            game["startDatetime"] = datetime.fromtimestamp(start_timestamp).strftime("%Y-%m-%d %H:%M:%S")

        return data

    def render(self, example):
        # metadata table
        metadata_columns = [
            "id",
            "startDatetime",
            "startTimestamp",
        ]
        metadata_trs = []

        home_team = example["homeTeam"]["name"]
        away_team = example["awayTeam"]["name"]
        match_info = f"{home_team} – {away_team}"

        for col in metadata_columns:
            th_name = h("th")(col)
            td_val = h("td")(example[col])
            tr = h("tr")(th_name, td_val)
            metadata_trs.append(tr)

        metadata_table_el = h(
            "table",
            klass="table table-sm table-bordered caption-top meta-table font-mono",
        )(h("caption")("metadata"), h("tbody")(metadata_trs))

        simple_table_names = [
            "season",
            "homeTeam",
            "homeScore",
            "awayScore",
            "awayTeam",
        ]
        simple_tables = []

        for table_name in simple_table_names:
            simple_trs = []
            for name, value in example[table_name].items():
                th_name = h("th")(name)
                td_val = h("td")(value)
                tr = h("tr")(th_name, td_val)
                simple_trs.append(tr)

            simple_table_el = h(
                "table",
                klass="table table-sm table-bordered caption-top meta-table font-mono",
            )(h("caption")(table_name), h("tbody")(simple_trs))
            simple_tables.append(simple_table_el)

        header_el = h("div")(h("h4", klass="")(match_info))
        col_1 = h("div", klass="col-5 ")(metadata_table_el, *simple_tables[:-2])
        col_2 = h("div", klass="col-7 ")(*simple_tables[-2:])
        cols = h("div", klass="row")(col_1, col_2)
        html_el = h("div")(header_el, cols)

        return html_el.render()
