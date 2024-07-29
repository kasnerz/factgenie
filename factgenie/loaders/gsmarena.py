#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

from factgenie.loaders.base import JSONDataset
from tinyhtml import h


class GSMArena(JSONDataset):
    def render(self, example):
        details = example["details"]

        quick_trs = []

        for spec in details["quickSpec"]:
            th_name = h("th")(spec["name"])
            td_val = h("td")(spec["value"])
            tr = h("tr")(th_name, td_val)
            quick_trs.append(tr)

        trs = []
        for category in details["detailSpec"]:
            category_name = category["category"]
            specs = category["specifications"]
            th_el = h("th", rowspan=len(specs) + 1)(category_name)
            tds = [th_el]

            for spec in specs:
                th_name = h("th")(spec["name"])
                td_val = h("td")(spec["value"])
                tr = h("tr")(th_name, td_val)
                tds.append(tr)

            tr_el = h("tr")(tds)
            trs.append(tr_el)

        product_info = "name: " + example["name"] + ", id: " + example["id"]

        quick_tbody_el = h("tbody")(quick_trs)
        quick_table_el = h(
            "table",
            klass="table table-sm table-bordered caption-top subtable font-mono",
        )(h("caption")("quick specifications"), h("tbody")(quick_tbody_el))

        tbody_el = h("tbody", id="main-table-body")(trs)
        table_el = h(
            "table",
            klass="table table-sm table-bordered caption-top main-table font-mono",
        )(h("caption")("detailed specifications"), tbody_el)

        header_el = h("div")(h("h4", klass="")(details["name"]), h("p", klass="")(product_info))
        html_el = h("div")(header_el, quick_table_el, table_el)

        return html_el.render()
