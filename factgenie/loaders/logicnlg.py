#!/usr/bin/env python3
import ast
import json
import logging
from datasets import load_dataset

logger = logging.getLogger(__name__)
from factgenie.loaders.dataset import Dataset
from tinyhtml import h
from collections import defaultdict
from pathlib import Path
from slugify import slugify


class LogicNLG(Dataset):
    def load_examples(self, split, data_path):
        # loading only 100 examples for the sample
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

    def load_generated_outputs(self, output_path):
        outputs = defaultdict(dict)

        for split in self.get_splits():
            outs = Path.glob(Path(output_path) / split, "*.json")
            outputs[split] = defaultdict(dict)

            for out in outs:
                with open(out) as f:
                    j = json.load(f)
                setup_id = slugify(j["setup"]["id"])
                outputs[split][setup_id]["generated"] = []

                all_claims = []
                current_table_id = j["generated"][0]["table_id"]
                for table_out in j["generated"]:
                    if table_out["table_id"] != current_table_id:
                        current_table_id = table_out["table_id"]
                        outputs[split][setup_id]["generated"].append({"out": "\\n\\n".join(all_claims)})
                        all_claims = []

                    all_claims.append(table_out["out"])

        return outputs
