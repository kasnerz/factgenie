#!/usr/bin/env python3
import ast
import json
import logging
from datasets import load_dataset

logger = logging.getLogger(__name__)
from factgenie.loaders.dataset import Dataset
from tinyhtml import h


class LogicNLG(Dataset):
    def load_examples(self, split, data_path):
        # loading only 100 examples as an example
        hf_dataset = load_dataset("kasnerz/logicnlg", split=split + "[:100]")
        examples = []

        for example in hf_dataset:
            table = ast.literal_eval(example["table"])
            table_title = example["title"]
            table_id = example["table_id"]
            examples.append((table, table_title, table_id))

        return examples

    def render(self, example):
        table_title = f"{example[1]}"
        table_id = f"[{example[2]}]"
        header_el = h("div")(h("i")(table_id), h("h4", klass="")(table_title))

        rows = example[0]
        trs = [h("tr")([h("th")(c) for c in rows[0]])]
        for row in rows[1:]:
            cells = [h("td")(v) for v in row]
            tr_el = h("tr")(cells)
            trs.append(tr_el)

        tbody_el = h("tbody", id="main-table-body")(trs)
        table_el = h(
            "table",
            klass="table table-sm table-bordered caption-top main-table font-mono",
        )(tbody_el)

        html_el = h("div")(header_el, table_el)

        return html_el.render()
