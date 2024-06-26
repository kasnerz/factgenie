#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
from factgenie.loaders.dataset import Dataset
from tinyhtml import h


class Wikidata(Dataset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, name="wikidata")
        self.type = "table"

    def get_info(self):
        return """
        Wikidata entities and their properties from the <u><a href="https://graphs.telecom-paris.fr/Home_page.html#wikidatasets-section">WikiDataSets</a></u> package.
        """

    def postprocess_data(self, data):
        examples = []

        for example in data:
            entity = example["entity"]
            properties = example["properties"]

            table = entity + "\n---\n"
            table += "\n".join([f"- {prop}: {subj}" for prop, subj in properties])
            examples.append(table)

        return examples

    def render(self, example):
        example = example.split("\n")
        title = example[0]

        trs = []
        for line in example[2:]:
            key, value = line.split(": ", 1)
            key = key.strip("- ")
            th_el = h("th")(key)
            td_el = h("td")(value)
            tr_el = h("tr")(th_el, td_el)
            trs.append(tr_el)

        tbody_el = h("tbody", id="main-table-body")(trs)
        table_el = h(
            "table",
            klass="table table-sm table-bordered caption-top main-table font-mono",
        )(tbody_el)

        header_el = h("div")(h("h4", klass="")(title))
        html_el = h("div")(header_el, table_el)

        return html_el.render()
