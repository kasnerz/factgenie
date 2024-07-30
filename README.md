# factgenie

![GitHub](https://img.shields.io/github/license/kasnerz/factgenie)
![GitHub issues](https://img.shields.io/github/issues/kasnerz/factgenie)
![Github stars](https://img.shields.io/github/stars/kasnerz/factgenie?style=social)
<!-- ![PyPI](https://img.shields.io/pypi/v/factgenie) -->
<!-- ![PyPI downloads](https://img.shields.io/pypi/dm/factgenie) -->

Visualize and annotate LLM outputs.

<img src="factgenie/static/img/github/browse.png" width="100%" alt="Main screen" />

## Intro
Outputs from large language models (LLMs) may contain errors: semantic, factual, and lexical. 

With **factgenie**, you can have the errors highlighted 🌈:
- From humans through a crowdsourcing service.
- From LLMs through an API.

How does **factgenie** help with that?
1. It helps you **create a user-friendly website** for collecting annotations from human crowdworkers.
2. It helps you with **LLM API calls** for collecting equivalent annotations from LLM-based evaluators.
3. It provides you with **visualization interface** for inspecting the annotated outputs.

What does factgenie **not help with** is collecting the data or model outputs (we assume that you already have these), starting the crowdsourcing campaign (for that, you need to use a service such as [Prolific.com](https://prolific.com)) or running the LLM evaluators (for that, you need a local framework such as [Ollama](https://ollama.com) or a proprietary API).

## Quickstart
Make sure you have Python 3 installed (the project is tested with Python 3.10).

The following commands install the package and start the web server:
```
pip install -e .
factgenie run --host=127.0.0.1 --port 5000
```

## How to
See the following wiki pages that that will guide you through various use-cases of factgenie:

| Topic                                                   | Description                                     |
| ------------------------------------------------------- | ----------------------------------------------- |
| [Annotation](../../wiki/Annotation)                     | Learn how to annotate LLM outputs.              |
| [Adding datasets](../../wiki/Adding-datasets)           | Instructions for adding datasets to factgenie.  |
| [Adding model outputs](../../wiki/Adding-model-outputs) | Guide on how to add model outputs to factgenie. |
