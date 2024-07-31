# factgenie

![GitHub](https://img.shields.io/github/license/kasnerz/factgenie)
![GitHub issues](https://img.shields.io/github/issues/kasnerz/factgenie)
![Github stars](https://img.shields.io/github/stars/kasnerz/factgenie?style=social)
<!-- ![PyPI](https://img.shields.io/pypi/v/factgenie) -->
<!-- ![PyPI downloads](https://img.shields.io/pypi/dm/factgenie) -->

Visualize and annotate LLM outputs 🌈

<img src="factgenie/static/img/github/browse.png" width="100%" alt="Main screen" />

## 📢  News
- **31/07/2024** - We released a set of tutorials for using factgenie on our [Github wiki](../../wiki/) page. Come and have a look!
- **25/07/2024** - We published an [arXiv pre-print](https://arxiv.org/abs/2407.17863) about factgenie. The paper is also accepted to INLG 2024 System Demonstrations track.

## 👉️ How can factgenie help you?
Outputs from large language models (LLMs) may contain errors: semantic, factual, and lexical. 

With **factgenie**, you can have the error spans annotated:
- From humans through a crowdsourcing service.
- From LLMs through an API.

How does **factgenie** help with that?
1. It helps you **create a user-friendly website** for collecting annotations from human crowdworkers.
2. It helps you with **LLM API calls** for collecting equivalent annotations from LLM-based evaluators.
3. It provides you with **visualization interface** for inspecting the annotated outputs.

What does factgenie **not help with** is collecting the data or model outputs (we assume that you already have these), starting the crowdsourcing campaign (for that, you need to use a service such as [Prolific.com](https://prolific.com)) or running the LLM evaluators (for that, you need a local framework such as [Ollama](https://ollama.com) or a proprietary API).

## 🏃 Quickstart
Make sure you have Python 3 installed (the project is tested with Python 3.10).

The following commands install the package and start the web server:
```
pip install -e .
factgenie run --host=127.0.0.1 --port 5000
```

## 💡 Tutorials

Each project is unique. That is why this **framework is partially DIY**: we assume that it will be customized for a particular use case.

See the following **wiki pages** that that will guide you through various use-cases of factgenie:

| Topic                                              | Description                            |
| -------------------------------------------------- | -------------------------------------- |
| [Setup](../../wiki/01-Setup)                       | How to install factgenie.              |
| [Data Management](../../wiki/02-Data-Management)   | How to add datasets and model outputs. |
| [Example Datasets](../../wiki/03-Example-Datasets) | Datasets included in factgenie.        |

## 🔗 Cite us
You can find our paper on [arXiv](https://arxiv.org/abs/2407.17863).

The paper is also accepted for INLG 2024 System Demonstrations.

For citing us, please use the following BibTeX entry:
```bibtex
@misc{kasner2024factgenie,
      title     = {factgenie: A Framework for Span-based Evaluation of Generated Texts}, 
      author    = {Zdeněk Kasner and Ondřej Plátek and Patrícia Schmidtová and Simone Balloccu and Ondřej Dušek},
      year      = {2024},
      booktitle = {Proceedings of the 17th International Natural Language Generation Conference (System Demonstrations)},
      note      = {To appear},
      url       = {https://arxiv.org/abs/2407.17863}, 
}
```