#!/usr/bin/env python3
import ast
import json
import logging
from datasets import load_dataset

logger = logging.getLogger(__name__)
from factgenie.loaders.dataset import Dataset
from tinyhtml import h


class LogicnlgBase(Dataset):
    def __init__(self, splits=['dev'], **kwargs):
        self.type = "table"
        self.splits = splits 
        super().__init__(**kwargs)

    def get_info(self):
        return f"""
        LogicNLG {self.split} split loaded from  <a href="https://huggingface.co/datasets/kasnerz/logicnlg">HuggingFace Dataset <i>kasnerz/logicnlg</i></a>.
        For details see the official <a href="https://github.com/wenhuchen/LogicNLG?tab=readme-ov-file">LogicNLG official release on GitHub</a>.
        """

    def load_data(self):
        """Overriding the default load_data function to load the data from HuggingFace datasets.
        Still calling the postprocess_data internally! 
        """
        assert set(self.splits) & set(["train", "dev", "test"]) == set(self.splits), f"Invalid splits {self.splits} for LogicNLG. Valid splits are ['train', 'dev', 'test']."
        d = {}
        for split in self.splits:
            
            raw_data = load_dataset("kasnerz/logicnlg", split=split if split != "dev" else "validation")
            d[split] = self.postprocess_data(raw_data, split)
        return d 

    def postprocess_data(self, hf_dataset, split):
        examples = []

        for example in hf_dataset:
            # List of rows (list).
            # The first list is the list of column names ie the header.
            # Hack how to convert almost json like data to list of list
            table = ast.literal_eval(example['table'])
            table_title = example['title']
            table_id = example['table_id']
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


class LogicnlgTest100Tables(LogicnlgBase):
    def __init__(self, **kwargs):
        # The name is used in the data loading and output loading
        # but also as the dataset is presented to the user
        super().__init__(**kwargs, splits=['test'], name="logicnlg")

    def get_info(self):
        return f"""
        A 100 subset of the LogicNLG {self.splits} split which is loaded from  <a href="https://huggingface.co/datasets/kasnerz/logicnlg">HuggingFace Dataset <i>kasnerz/logicnlg</i></a>.
        For details see the official <a href="https://github.com/wenhuchen/LogicNLG?tab=readme-ov-file">LogicNLG official release on GitHub</a>.
        """

    def postprocess_data(self, hf_dataset, split):
        # filter the data for the first 100 examples
        with open(f"{self.data_path}/{self.name}/{split}.json") as f:
            table_ids = json.load(f)
        filtered_dataset = hf_dataset.filter(lambda x: x["table_id"] in table_ids)
        return super().postprocess_data(filtered_dataset, split)


if __name__ == "__main__":
    # Testing the loader
    d = LogicnlgTest100Tables()
    print(len(d.examples['test']))