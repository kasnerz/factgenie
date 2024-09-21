# factgenie

![GitHub](https://img.shields.io/github/license/kasnerz/factgenie)
![GitHub issues](https://img.shields.io/github/issues/kasnerz/factgenie)
![Github stars](https://img.shields.io/github/stars/kasnerz/factgenie?style=social)
<!-- ![PyPI](https://img.shields.io/pypi/v/factgenie) -->
<!-- ![PyPI downloads](https://img.shields.io/pypi/dm/factgenie) -->

Annotate LLM outputs with a lightweight, self-hosted web application 🌈

<img src="factgenie/static/img/github/browse.png" width="100%" alt="Main screen" />

## 📢  News
- **19/09/2024** - On the Analytics page, you can now see detailed statistics about annotations and compute inter-annotator agreement 📈
- **16/09/2024** - You can now collect extra inputs from the annotators for each example using sliders and selectboxes. 
- **16/09/2024** - We added an option to generate outputs for the inputs with LLMs directly within factgenie! 🦾
- **10/09/2024** - We improved UX for the annotation and browsing interfaces. See the summary of changes [here](https://github.com/ufal/factgenie/pull/71).
- **09/08/2024** - Instructions for the annotators can be now configured directly in the web interace and in the configuration file – no need for coding HTML!
- **31/07/2024** - We updated and expanded the README into a set of tutorials. The tutorials are available on our [Github wiki](../../wiki/).
- **31/07/2024** - We substantially improved the data management. You can now manage the datasets both through the configuration file and the web interface.
- **25/07/2024** - We published an [arXiv pre-print](https://arxiv.org/abs/2407.17863) about factgenie. The paper is accepted to the INLG 2024 System Demonstrations track.

## 👉️ How can factgenie help you?
Outputs from large language models (LLMs) may contain errors: semantic, factual, and lexical. 

With factgenie, you can have the error spans annotated:
- From LLMs through an API.
- From humans through a crowdsourcing service.

Factgenie can provide you:
1. **A user-friendly website** for collecting annotations from human crowdworkers.
2. **API calls** for collecting equivalent annotations from LLM-based evaluators.
3. **A visualization interface** for visualizing the data and inspecting the annotated outputs.

---
*What does factgenie **not help with** is collecting the data (we assume that you already have these), starting the crowdsourcing campaign (for that, you need to use a service such as [Prolific.com](https://prolific.com)) or running the LLM evaluators (for that, you need a local framework such as [Ollama](https://ollama.com) or a proprietary API).*

## 🏃 Quickstart
Make sure you have Python 3 installed (the project is tested with Python 3.10).

After cloning the repository, the following commands install the package and start the web server:
```
pip install -e .
factgenie run --host=127.0.0.1 --port 5000
```

## 💡 Usage guide


See the following **wiki pages** that that will guide you through various use-cases of factgenie:

| Topic                                                                  | Description                                        |
| ---------------------------------------------------------------------- | -------------------------------------------------- |
| 🔧 [Setup](../../wiki/01-Setup)                                         | How to install factgenie.                          |
| 🗂️ [Data Management](../../wiki/02-Data-Management)                     | How to manage datasets and model outputs.          |
| 🤖 [LLM Annotations](../../wiki/03-LLM-Annotations)                     | How to annotate outputs using LLMs.                |
| 👥 [Crowdsourcing Annotations](../../wiki/04-Crowdsourcing-Annotations) | How to annotate outputs using human crowdworkers.  |
| ✍️  [Generating Outputs](../../wiki/05-Generating-Outputs)              | How to generate outputs using LLMs.                |
| 📊 [Analyzing Annotations](../../wiki/06-Analyzing-Annotations)         | How to obtain statistics on collected annotations. |
| 🧑‍💻 [Developer Notes](../../wiki/07-Developer-Notes)                     | How to contribute to the framework.                |

 
We provide multiple examples for you to get inspired when preparing your own experiments. In simple cases, you can even get without writing Python code completely!

## 💬 Cite us

[Our paper](https://aclanthology.org/2024.inlg-demos.5/) is accepted for INLG 2024 System Demonstrations!

You can also find it on [arXiv](https://arxiv.org/abs/2407.17863).

For citing us, please use the following BibTeX entry:
```bibtex
@inproceedings{kasner2024factgenie,
    title = "factgenie: A Framework for Span-based Evaluation of Generated Texts",
    author = "Kasner, Zden{\v{e}}k  and
      Platek, Ondrej  and
      Schmidtova, Patricia  and
      Balloccu, Simone  and
      Dusek, Ondrej",
    editor = "Mahamood, Saad  and
      Minh, Nguyen Le  and
      Ippolito, Daphne",
    booktitle = "Proceedings of the 17th International Natural Language Generation Conference: System Demonstrations",
    year = "2024",
    address = "Tokyo, Japan",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2024.inlg-demos.5",
    pages = "13--15",
}
```

## Acknowledgements
This work was co-funded by the European Union (ERC, NG-NLG, 101039303).

<img src="img/LOGO_ERC-FLAG_FP.png" alt="erc-logo" height="150"/> 