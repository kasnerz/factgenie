#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

from factgenie.loaders.dataset import Dataset
from tinyhtml import h
import json
from pathlib import Path
from collections import defaultdict


class Dummy(Dataset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, name="dummy")

    def get_info(self):
        return """
        Example dataset.
        """

    def render(self, example):
        return example

    def get_generated_outputs(self, split, output_idx):
        outs_all = []

        for outs in self.outputs[split].values():
            for model_out in outs:
                out = {}

                out["setup"] = model_out["setup"]
                out["generated"] = model_out["generated"][output_idx]["out"]

                outs_all.append(out)

        return outs_all
