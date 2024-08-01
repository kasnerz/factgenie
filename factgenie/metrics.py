#!/usr/bin/env python3

import traceback
from openai import OpenAI
from textwrap import dedent
import argparse
import yaml
import json
import sys

from pathlib import Path
import os
import coloredlogs
import logging
import time
import requests
import copy

# logging.basicConfig(format="%(message)s", level=logging.INFO, datefmt="%H:%M:%S")
coloredlogs.install(level="INFO", fmt="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DIR_PATH = os.path.dirname(__file__)
LLM_ANNOTATION_DIR = os.path.join(DIR_PATH, "annotations")


class LLMMetricFactory:
    """Register any new metric here. The get_metric is the factory method based on the config"""

    @staticmethod
    def metric_classes():
        return {
            "openai": OpenAIMetric,
            "ollama": OllamaMetric,
        }

    @staticmethod
    def from_config(config):
        metric_type = config["type"]
        classes = LLMMetricFactory.metric_classes()

        if metric_type not in classes:
            raise ValueError(f"Metric type {metric_type} is not implemented.")

        return classes[metric_type](config)


class LLMMetric:
    def __init__(self, config):
        self.validate_config(config)
        self.config = config

        if "extra_args" in config:
            # the key in the model output that contains the annotations
            self.annotation_key = config["extra_args"].get("annotation_key", "annotations")

    def get_required_fields(self):
        return {
            "type": str,
            "annotation_span_categories": list,
            "prompt_template": str,
            "model": str,
            "model_args": dict,
        }

    def get_optional_fields(self):
        return {
            "system_msg": str,
            "api_url": str,
            "extra_args": dict,
        }

    def get_annotator_id(self):
        return "llm-" + self.config["type"] + "-" + self.config["model"]

    def get_config(self):
        return self.config

    def validate_config(self, config):
        for field in self.get_required_fields():
            assert field in config, f"Field `{field}` is missing in the config. Keys: {config.keys()}"

        for field, field_type in self.get_required_fields().items():
            assert isinstance(
                config[field], field_type
            ), f"Field `{field}` must be of type {field_type}, got {config[field]=}"

        for field, field_type in self.get_optional_fields().items():
            if field in config:
                assert isinstance(
                    config[field], field_type
                ), f"Field `{field}` must be of type {field_type}, got {config[field]=}"
            else:
                # set the default value for the data type
                config[field] = field_type()

        # warn if there are any extra fields
        for field in config:
            if field not in self.get_required_fields() and field not in self.get_optional_fields():
                logger.warning(f"Field `{field}` is not recognized in the config.")

    def postprocess_annotations(self, text, model_json):
        annotation_list = []
        current_pos = 0

        if self.annotation_key not in model_json:
            logger.error(f"Cannot find the key `{self.annotation_key}` in {model_json=}")
            return []

        for annotation in model_json[self.annotation_key]:
            # find the `start` index of the error in the text
            start_pos = text.lower().find(annotation["text"].lower(), current_pos)

            if current_pos != 0 and start_pos == -1:
                # try from the beginning
                start_pos = text.find(annotation["text"])

            if start_pos == -1:
                logger.warning(f"Cannot find {annotation=} in text {text}, skipping")
                continue

            annotation["start"] = start_pos
            annotation_list.append(copy.deepcopy(annotation))

            current_pos = start_pos + len(annotation["text"])

        return annotation_list

    def preprocess_data_for_prompt(self, data):
        """Override this method to change the format how the data is presented in the prompt. See self.prompt() method for usage."""
        return data

    def prompt(self, data, text):
        assert isinstance(text, str) and len(text) > 0, f"Text must be a non-empty string, got {text=}"
        data_for_prompt = self.preprocess_data_for_prompt(data)
        return self.config["prompt_template"].format(data=data_for_prompt, text=text)

    def annotate_example(self, data, text):
        raise NotImplementedError("Override this method in the subclass to call the LLM API")


class OpenAIMetric(LLMMetric):
    def __init__(self, config):
        super().__init__(config)
        self.client = OpenAI()
        self.parse_model_args()

    def get_required_fields(self):
        return {
            "type": str,
            "annotation_span_categories": list,
            "prompt_template": str,
            "model": str,
        }

    def get_optional_fields(self):
        return {
            "system_msg": str,
            "model_args": dict,
            "api_url": str,  # TODO we receive it from the UI, but can be removed
            "extra_args": dict,  # TODO we receive it from the UI, but can be removed
        }

    def parse_model_args(self):
        if "temperature" in self.config["model_args"]:
            self.config["model_args"]["temperature"] = float(self.config["model_args"]["temperature"])

    def annotate_example(self, data, text):
        try:
            prompt = self.prompt(data, text)

            logger.debug(f"Calling OpenAI API with prompt: {prompt}")
            response = self.client.chat.completions.create(
                model=self.config["model"],
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.config["system_msg"]},
                    {"role": "user", "content": prompt},
                ],
                **self.config.get("model_args", {}),
            )
            annotation_str = response.choices[0].message.content
            j = json.loads(annotation_str)
            logger.info(j)

            return self.postprocess_annotations(text=text, model_json=j)
        except Exception as e:
            logger.error(e)
            return {"error": str(e)}


class OllamaMetric(LLMMetric):
    def __init__(self, config):
        super().__init__(config)

    def postprocess_output(self, output):
        output = output.strip()
        j = json.loads(output)

        if self.config["model"].startswith("llama3"):
            # the model often tends to produce a nested list
            annotations = j[self.annotation_key]
            if isinstance(annotations, list) and len(annotations) >= 1 and isinstance(annotations[0], list):
                j[self.annotation_key] = j[self.annotation_key][0]

        return j

    def annotate_example(self, data, text):
        prompt = self.prompt(data=data, text=text)
        request_d = {
            "model": self.config["model"],
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": self.config,
        }
        msg = f"Ollama API {self.config['api_url']} with args:\n\t{request_d}"
        response, annotation_str, j = None, None, None
        try:
            logger.debug(f"Calling {msg}")
            response = requests.post(self.config["api_url"], json=request_d)
            response_json = response.json()

            if "error" in response_json:
                return response_json

            annotation_str = response_json["response"]

            j = self.postprocess_output(annotation_str)
            logger.info(j)
            return self.postprocess_annotations(text=text, model_json=j)
        except Exception as e:
            logger.error(
                f"Called {msg}\n\n and received\n\t{response=}\n\t{annotation_str=}\n\t{j=}\nbefore the error:{e}"
            )
            traceback.print_exc()
            return []


# class LogicNLGMarkdownOllamaMetric(OllamaMetric):
#     def __init__(self, config):
#         super().__init__(config)
#         self._table_str_f = self.config["extra_args"].get("table_str_f", "to_string")

#     def get_required_fields(self):
#         return {
#             "type": str,
#             "annotation_span_categories": list,
#             "prompt_template": str,
#             "model": str,
#             "model_args": dict,
#             "extra_args": dict,
#         }

#     def preprocess_data_for_prompt(self, example):
#         import pandas as pd  # requires tabulate

#         rowlist = example[0]
#         table_title = example[1]
#         table = pd.DataFrame(rowlist[1:], columns=rowlist[0])

#         if self._table_str_f == "to_markdown":
#             table_str = table.to_markdown()
#         elif self._table_str_f == "to_string":
#             table_str = table.to_string()
#         elif self._table_str_f == "to_json":
#             # List of rows
#             table_str = table.to_json(orient="records")
#         else:
#             raise ValueError(f"Unknown table string function {self._table_str_f}")

#         data2prompt = f"Table title: {table_title}\n{table_str}"

#         return data2prompt
