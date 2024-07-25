#!/usr/bin/env python3
from factgenie.loaders.dataset import Dataset

import logging
import tinyhtml
import json2table
import datasets
import numpy as np

logger = logging.getLogger(__name__)


class HFDataset(Dataset):
    """
    Base class for HF datasets
    """

    def __init__(self, **kwargs):
        self.name = "summeval"
        self.hf_id = "mteb/summeval"
        # self.hf_id = kwargs.pop("hf_id")

        super().__init__(**kwargs, name="dummy")

    def load_data(self):
        dataset = datasets.load_dataset(
            self.hf_id,
        )
        splits = list(dataset.keys())
        examples = {split: [] for split in splits}

        for split in splits:
            examples[split] = dataset[split].to_pandas().to_dict(orient="records")
            # convert all the "ndarrays" to lists
            for example in examples[split]:
                for k, v in example.items():
                    if isinstance(v, np.ndarray):
                        example[k] = v.tolist()
        breakpoint()
        return examples

    def render(self, example):
        # default method, can be overwritten by dataset classes
        html = json2table.convert(
            example,
            build_direction="LEFT_TO_RIGHT",
            table_attributes={
                "class": "table table-sm caption-top meta-table table-responsive font-mono rounded-3 table-bordered"
            },
        )
        return html
