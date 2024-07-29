#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
from factgenie.loaders.base import JSONDataset
from tinyhtml import h


class Wikidata(JSONDataset):
    def postprocess_data(self, examples):
        examples = []

        for example in examples:
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
