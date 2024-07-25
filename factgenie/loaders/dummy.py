#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)

from factgenie.loaders.dataset import Dataset


class Dummy(Dataset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs, name="dummy")

    def get_info(self):
        return """
        Example dataset.
        """

    def render(self, example):
        return example
