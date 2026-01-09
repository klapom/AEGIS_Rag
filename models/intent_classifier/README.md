---
tags:
- setfit
- sentence-transformers
- text-classification
- generated_from_setfit_trainer
widget:
- text: Was ist die aktuelle Versionsnummer von JIRA?
- text: How do I migrate my database to Amazon RDS manually?
- text: How to integrate Google Workspace with Microsoft Teams?
- text: What is the recommended logging and monitoring solution for a Dockerized application?
- text: Wie füge ich eine PostgreSQL-Datenbank auf einer Docker-Vorlage hinzu?
metrics:
- accuracy
pipeline_tag: text-classification
library_name: setfit
inference: true
base_model: sentence-transformers/paraphrase-mpnet-base-v2
---

# SetFit with sentence-transformers/paraphrase-mpnet-base-v2

This is a [SetFit](https://github.com/huggingface/setfit) model that can be used for Text Classification. This SetFit model uses [sentence-transformers/paraphrase-mpnet-base-v2](https://huggingface.co/sentence-transformers/paraphrase-mpnet-base-v2) as the Sentence Transformer embedding model. A [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance is used for classification.

The model has been trained using an efficient few-shot learning technique that involves:

1. Fine-tuning a [Sentence Transformer](https://www.sbert.net) with contrastive learning.
2. Training a classification head with features from the fine-tuned Sentence Transformer.

## Model Details

### Model Description
- **Model Type:** SetFit
- **Sentence Transformer body:** [sentence-transformers/paraphrase-mpnet-base-v2](https://huggingface.co/sentence-transformers/paraphrase-mpnet-base-v2)
- **Classification head:** a [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance
- **Maximum Sequence Length:** 512 tokens
- **Number of Classes:** 5 classes
<!-- - **Training Dataset:** [Unknown](https://huggingface.co/datasets/unknown) -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Repository:** [SetFit on GitHub](https://github.com/huggingface/setfit)
- **Paper:** [Efficient Few-Shot Learning Without Prompts](https://arxiv.org/abs/2209.11055)
- **Blogpost:** [SetFit: Efficient Few-Shot Learning Without Prompts](https://huggingface.co/blog/setfit)

### Model Labels
| Label          | Examples                                                                                                                                                                                                                                                                                                                                                  |
|:---------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| navigation     | <ul><li>'What section holds the user permission management tools?'</li><li>'Where can we access quarterly earnings reports in Microsoft SharePoint?'</li><li>'How can I access the security policies section?'</li></ul>                                                                                                                                  |
| factual        | <ul><li>'What is the atomic number of carbon?'</li><li>"What is the main data storage system used in IBM's Watson AI?"</li><li>'Welche Sprache verwendet Spring Boot?'</li></ul>                                                                                                                                                                          |
| procedural     | <ul><li>'Steps to perform principal component analysis (PCA) in R'</li><li>'Wie erstelle ich einen Workflow in ServiceNow für Incident Management?'</li><li>'Was sind die Schritte zur Konfiguration eines LDAP-Verbindens in Active Directory?'</li></ul>                                                                                                |
| comparison     | <ul><li>'Vergleiche die Leistungsfähigkeit und Skalierbarkeit von Redis gegenüber Cassandra in Bezug auf Datenbankanwendungen.'</li><li>'Vergleichen Sie die Genauigkeit von CNNs und Transformers für die Bilderkennung.'</li><li>'Welche Ansätze zur Continuous Integration unterscheiden sich in Bezug auf Geschwindigkeit und Komplexität?'</li></ul> |
| recommendation | <ul><li>'Kann man empfehlen, Kubernetes für die Containerisierung unserer Webanwendungen zu nutzen?'</li><li>'Was ist der optimale Workflow für Kundensupport-Tickets?'</li><li>'Welche Dokumentationstools sind am besten geeignet für tech-Spezialisten?'</li></ul>                                                                                     |

## Uses

### Direct Use for Inference

First install the SetFit library:

```bash
pip install setfit
```

Then you can load this model and run inference.

```python
from setfit import SetFitModel

# Download from the 🤗 Hub
model = SetFitModel.from_pretrained("setfit_model_id")
# Run inference
preds = model("Was ist die aktuelle Versionsnummer von JIRA?")
```

<!--
### Downstream Use

*List how someone could finetune this model on their own dataset.*
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Set Metrics
| Training set | Min | Median  | Max |
|:-------------|:----|:--------|:----|
| Word count   | 1   | 10.0803 | 24  |

| Label          | Training Sample Count |
|:---------------|:----------------------|
| factual        | 168                   |
| procedural     | 167                   |
| comparison     | 167                   |
| recommendation | 166                   |
| navigation     | 166                   |

### Training Hyperparameters
- batch_size: (32, 32)
- num_epochs: (1, 1)
- max_steps: -1
- sampling_strategy: oversampling
- body_learning_rate: (2e-05, 2e-05)
- head_learning_rate: 0.01
- loss: CosineSimilarityLoss
- distance_metric: cosine_distance
- margin: 0.25
- end_to_end: False
- use_amp: False
- warmup_proportion: 0.1
- l2_weight: 0.01
- seed: 42
- eval_max_steps: -1
- load_best_model_at_end: False

### Training Results
| Epoch  | Step  | Training Loss | Validation Loss |
|:------:|:-----:|:-------------:|:---------------:|
| 0.0001 | 1     | 0.3519        | -               |
| 0.0029 | 50    | 0.3337        | -               |
| 0.0058 | 100   | 0.2724        | -               |
| 0.0086 | 150   | 0.2451        | -               |
| 0.0115 | 200   | 0.2375        | -               |
| 0.0144 | 250   | 0.225         | -               |
| 0.0173 | 300   | 0.1819        | -               |
| 0.0201 | 350   | 0.1486        | -               |
| 0.0230 | 400   | 0.1182        | -               |
| 0.0259 | 450   | 0.0923        | -               |
| 0.0288 | 500   | 0.0592        | -               |
| 0.0316 | 550   | 0.0428        | -               |
| 0.0345 | 600   | 0.0267        | -               |
| 0.0374 | 650   | 0.0171        | -               |
| 0.0403 | 700   | 0.0126        | -               |
| 0.0431 | 750   | 0.0069        | -               |
| 0.0460 | 800   | 0.0054        | -               |
| 0.0489 | 850   | 0.0034        | -               |
| 0.0518 | 900   | 0.002         | -               |
| 0.0546 | 950   | 0.0015        | -               |
| 0.0575 | 1000  | 0.0019        | -               |
| 0.0604 | 1050  | 0.0033        | -               |
| 0.0633 | 1100  | 0.0057        | -               |
| 0.0661 | 1150  | 0.0016        | -               |
| 0.0690 | 1200  | 0.0021        | -               |
| 0.0719 | 1250  | 0.0005        | -               |
| 0.0748 | 1300  | 0.001         | -               |
| 0.0776 | 1350  | 0.0018        | -               |
| 0.0805 | 1400  | 0.0016        | -               |
| 0.0834 | 1450  | 0.0009        | -               |
| 0.0863 | 1500  | 0.0019        | -               |
| 0.0891 | 1550  | 0.0033        | -               |
| 0.0920 | 1600  | 0.0016        | -               |
| 0.0949 | 1650  | 0.0021        | -               |
| 0.0978 | 1700  | 0.0011        | -               |
| 0.1006 | 1750  | 0.0019        | -               |
| 0.1035 | 1800  | 0.0018        | -               |
| 0.1064 | 1850  | 0.0033        | -               |
| 0.1093 | 1900  | 0.0065        | -               |
| 0.1121 | 1950  | 0.0014        | -               |
| 0.1150 | 2000  | 0.0027        | -               |
| 0.1179 | 2050  | 0.002         | -               |
| 0.1208 | 2100  | 0.0019        | -               |
| 0.1236 | 2150  | 0.0014        | -               |
| 0.1265 | 2200  | 0.0035        | -               |
| 0.1294 | 2250  | 0.0002        | -               |
| 0.1323 | 2300  | 0.0004        | -               |
| 0.1351 | 2350  | 0.0001        | -               |
| 0.1380 | 2400  | 0.0014        | -               |
| 0.1409 | 2450  | 0.0001        | -               |
| 0.1438 | 2500  | 0.0001        | -               |
| 0.1466 | 2550  | 0.0001        | -               |
| 0.1495 | 2600  | 0.0004        | -               |
| 0.1524 | 2650  | 0.0001        | -               |
| 0.1553 | 2700  | 0.0003        | -               |
| 0.1581 | 2750  | 0.0004        | -               |
| 0.1610 | 2800  | 0.0007        | -               |
| 0.1639 | 2850  | 0.0002        | -               |
| 0.1668 | 2900  | 0.0002        | -               |
| 0.1696 | 2950  | 0.0001        | -               |
| 0.1725 | 3000  | 0.0001        | -               |
| 0.1754 | 3050  | 0.0007        | -               |
| 0.1783 | 3100  | 0.0007        | -               |
| 0.1811 | 3150  | 0.0001        | -               |
| 0.1840 | 3200  | 0.0001        | -               |
| 0.1869 | 3250  | 0.0001        | -               |
| 0.1898 | 3300  | 0.0001        | -               |
| 0.1927 | 3350  | 0.0001        | -               |
| 0.1955 | 3400  | 0.0           | -               |
| 0.1984 | 3450  | 0.0012        | -               |
| 0.2013 | 3500  | 0.0034        | -               |
| 0.2042 | 3550  | 0.0065        | -               |
| 0.2070 | 3600  | 0.0024        | -               |
| 0.2099 | 3650  | 0.0032        | -               |
| 0.2128 | 3700  | 0.0018        | -               |
| 0.2157 | 3750  | 0.0013        | -               |
| 0.2185 | 3800  | 0.0001        | -               |
| 0.2214 | 3850  | 0.0           | -               |
| 0.2243 | 3900  | 0.0001        | -               |
| 0.2272 | 3950  | 0.0066        | -               |
| 0.2300 | 4000  | 0.0018        | -               |
| 0.2329 | 4050  | 0.0001        | -               |
| 0.2358 | 4100  | 0.0007        | -               |
| 0.2387 | 4150  | 0.0           | -               |
| 0.2415 | 4200  | 0.0           | -               |
| 0.2444 | 4250  | 0.0           | -               |
| 0.2473 | 4300  | 0.0           | -               |
| 0.2502 | 4350  | 0.0           | -               |
| 0.2530 | 4400  | 0.0           | -               |
| 0.2559 | 4450  | 0.0007        | -               |
| 0.2588 | 4500  | 0.0018        | -               |
| 0.2617 | 4550  | 0.0006        | -               |
| 0.2645 | 4600  | 0.0           | -               |
| 0.2674 | 4650  | 0.0           | -               |
| 0.2703 | 4700  | 0.0           | -               |
| 0.2732 | 4750  | 0.0           | -               |
| 0.2760 | 4800  | 0.0           | -               |
| 0.2789 | 4850  | 0.0           | -               |
| 0.2818 | 4900  | 0.0           | -               |
| 0.2847 | 4950  | 0.0           | -               |
| 0.2875 | 5000  | 0.0           | -               |
| 0.2904 | 5050  | 0.0           | -               |
| 0.2933 | 5100  | 0.0           | -               |
| 0.2962 | 5150  | 0.0           | -               |
| 0.2990 | 5200  | 0.0           | -               |
| 0.3019 | 5250  | 0.0           | -               |
| 0.3048 | 5300  | 0.0           | -               |
| 0.3077 | 5350  | 0.0           | -               |
| 0.3105 | 5400  | 0.0           | -               |
| 0.3134 | 5450  | 0.0           | -               |
| 0.3163 | 5500  | 0.0           | -               |
| 0.3192 | 5550  | 0.0           | -               |
| 0.3220 | 5600  | 0.0           | -               |
| 0.3249 | 5650  | 0.0           | -               |
| 0.3278 | 5700  | 0.0           | -               |
| 0.3307 | 5750  | 0.0           | -               |
| 0.3335 | 5800  | 0.0           | -               |
| 0.3364 | 5850  | 0.0           | -               |
| 0.3393 | 5900  | 0.0           | -               |
| 0.3422 | 5950  | 0.0           | -               |
| 0.3450 | 6000  | 0.0           | -               |
| 0.3479 | 6050  | 0.0           | -               |
| 0.3508 | 6100  | 0.0           | -               |
| 0.3537 | 6150  | 0.0           | -               |
| 0.3565 | 6200  | 0.0           | -               |
| 0.3594 | 6250  | 0.0           | -               |
| 0.3623 | 6300  | 0.0           | -               |
| 0.3652 | 6350  | 0.0           | -               |
| 0.3680 | 6400  | 0.0           | -               |
| 0.3709 | 6450  | 0.0           | -               |
| 0.3738 | 6500  | 0.0           | -               |
| 0.3767 | 6550  | 0.0           | -               |
| 0.3796 | 6600  | 0.0           | -               |
| 0.3824 | 6650  | 0.0           | -               |
| 0.3853 | 6700  | 0.0           | -               |
| 0.3882 | 6750  | 0.0           | -               |
| 0.3911 | 6800  | 0.0           | -               |
| 0.3939 | 6850  | 0.0           | -               |
| 0.3968 | 6900  | 0.0           | -               |
| 0.3997 | 6950  | 0.0           | -               |
| 0.4026 | 7000  | 0.0           | -               |
| 0.4054 | 7050  | 0.0           | -               |
| 0.4083 | 7100  | 0.0           | -               |
| 0.4112 | 7150  | 0.0           | -               |
| 0.4141 | 7200  | 0.0           | -               |
| 0.4169 | 7250  | 0.0           | -               |
| 0.4198 | 7300  | 0.0           | -               |
| 0.4227 | 7350  | 0.0           | -               |
| 0.4256 | 7400  | 0.0           | -               |
| 0.4284 | 7450  | 0.0           | -               |
| 0.4313 | 7500  | 0.0           | -               |
| 0.4342 | 7550  | 0.0           | -               |
| 0.4371 | 7600  | 0.0           | -               |
| 0.4399 | 7650  | 0.0           | -               |
| 0.4428 | 7700  | 0.0           | -               |
| 0.4457 | 7750  | 0.0           | -               |
| 0.4486 | 7800  | 0.0           | -               |
| 0.4514 | 7850  | 0.0           | -               |
| 0.4543 | 7900  | 0.0           | -               |
| 0.4572 | 7950  | 0.0           | -               |
| 0.4601 | 8000  | 0.0           | -               |
| 0.4629 | 8050  | 0.0           | -               |
| 0.4658 | 8100  | 0.0           | -               |
| 0.4687 | 8150  | 0.0           | -               |
| 0.4716 | 8200  | 0.0           | -               |
| 0.4744 | 8250  | 0.0           | -               |
| 0.4773 | 8300  | 0.0           | -               |
| 0.4802 | 8350  | 0.0           | -               |
| 0.4831 | 8400  | 0.0           | -               |
| 0.4859 | 8450  | 0.0           | -               |
| 0.4888 | 8500  | 0.0           | -               |
| 0.4917 | 8550  | 0.0           | -               |
| 0.4946 | 8600  | 0.0007        | -               |
| 0.4974 | 8650  | 0.0064        | -               |
| 0.5003 | 8700  | 0.0038        | -               |
| 0.5032 | 8750  | 0.0052        | -               |
| 0.5061 | 8800  | 0.0014        | -               |
| 0.5089 | 8850  | 0.0004        | -               |
| 0.5118 | 8900  | 0.001         | -               |
| 0.5147 | 8950  | 0.0016        | -               |
| 0.5176 | 9000  | 0.0026        | -               |
| 0.5204 | 9050  | 0.0009        | -               |
| 0.5233 | 9100  | 0.0002        | -               |
| 0.5262 | 9150  | 0.0           | -               |
| 0.5291 | 9200  | 0.0006        | -               |
| 0.5319 | 9250  | 0.0002        | -               |
| 0.5348 | 9300  | 0.0           | -               |
| 0.5377 | 9350  | 0.0           | -               |
| 0.5406 | 9400  | 0.0           | -               |
| 0.5434 | 9450  | 0.0           | -               |
| 0.5463 | 9500  | 0.0004        | -               |
| 0.5492 | 9550  | 0.0006        | -               |
| 0.5521 | 9600  | 0.0007        | -               |
| 0.5549 | 9650  | 0.0           | -               |
| 0.5578 | 9700  | 0.0           | -               |
| 0.5607 | 9750  | 0.0           | -               |
| 0.5636 | 9800  | 0.0           | -               |
| 0.5665 | 9850  | 0.0           | -               |
| 0.5693 | 9900  | 0.0           | -               |
| 0.5722 | 9950  | 0.0001        | -               |
| 0.5751 | 10000 | 0.0           | -               |
| 0.5780 | 10050 | 0.0           | -               |
| 0.5808 | 10100 | 0.0           | -               |
| 0.5837 | 10150 | 0.0           | -               |
| 0.5866 | 10200 | 0.0           | -               |
| 0.5895 | 10250 | 0.0           | -               |
| 0.5923 | 10300 | 0.0           | -               |
| 0.5952 | 10350 | 0.0           | -               |
| 0.5981 | 10400 | 0.0           | -               |
| 0.6010 | 10450 | 0.0           | -               |
| 0.6038 | 10500 | 0.0           | -               |
| 0.6067 | 10550 | 0.0           | -               |
| 0.6096 | 10600 | 0.0           | -               |
| 0.6125 | 10650 | 0.0           | -               |
| 0.6153 | 10700 | 0.0           | -               |
| 0.6182 | 10750 | 0.0           | -               |
| 0.6211 | 10800 | 0.0           | -               |
| 0.6240 | 10850 | 0.0           | -               |
| 0.6268 | 10900 | 0.0           | -               |
| 0.6297 | 10950 | 0.0           | -               |
| 0.6326 | 11000 | 0.0           | -               |
| 0.6355 | 11050 | 0.0           | -               |
| 0.6383 | 11100 | 0.0007        | -               |
| 0.6412 | 11150 | 0.0           | -               |
| 0.6441 | 11200 | 0.0           | -               |
| 0.6470 | 11250 | 0.0           | -               |
| 0.6498 | 11300 | 0.0           | -               |
| 0.6527 | 11350 | 0.0           | -               |
| 0.6556 | 11400 | 0.0           | -               |
| 0.6585 | 11450 | 0.0           | -               |
| 0.6613 | 11500 | 0.0           | -               |
| 0.6642 | 11550 | 0.0           | -               |
| 0.6671 | 11600 | 0.0           | -               |
| 0.6700 | 11650 | 0.0           | -               |
| 0.6728 | 11700 | 0.0           | -               |
| 0.6757 | 11750 | 0.0           | -               |
| 0.6786 | 11800 | 0.0           | -               |
| 0.6815 | 11850 | 0.0           | -               |
| 0.6843 | 11900 | 0.0           | -               |
| 0.6872 | 11950 | 0.0           | -               |
| 0.6901 | 12000 | 0.0           | -               |
| 0.6930 | 12050 | 0.0004        | -               |
| 0.6958 | 12100 | 0.0007        | -               |
| 0.6987 | 12150 | 0.0           | -               |
| 0.7016 | 12200 | 0.0           | -               |
| 0.7045 | 12250 | 0.0           | -               |
| 0.7073 | 12300 | 0.0           | -               |
| 0.7102 | 12350 | 0.0           | -               |
| 0.7131 | 12400 | 0.0           | -               |
| 0.7160 | 12450 | 0.0           | -               |
| 0.7188 | 12500 | 0.0           | -               |
| 0.7217 | 12550 | 0.0           | -               |
| 0.7246 | 12600 | 0.0           | -               |
| 0.7275 | 12650 | 0.0           | -               |
| 0.7303 | 12700 | 0.0           | -               |
| 0.7332 | 12750 | 0.0           | -               |
| 0.7361 | 12800 | 0.0           | -               |
| 0.7390 | 12850 | 0.0           | -               |
| 0.7418 | 12900 | 0.0           | -               |
| 0.7447 | 12950 | 0.0           | -               |
| 0.7476 | 13000 | 0.0           | -               |
| 0.7505 | 13050 | 0.0           | -               |
| 0.7533 | 13100 | 0.0           | -               |
| 0.7562 | 13150 | 0.0           | -               |
| 0.7591 | 13200 | 0.0           | -               |
| 0.7620 | 13250 | 0.0           | -               |
| 0.7649 | 13300 | 0.0           | -               |
| 0.7677 | 13350 | 0.0           | -               |
| 0.7706 | 13400 | 0.0           | -               |
| 0.7735 | 13450 | 0.0           | -               |
| 0.7764 | 13500 | 0.0           | -               |
| 0.7792 | 13550 | 0.0           | -               |
| 0.7821 | 13600 | 0.0           | -               |
| 0.7850 | 13650 | 0.0           | -               |
| 0.7879 | 13700 | 0.0           | -               |
| 0.7907 | 13750 | 0.0           | -               |
| 0.7936 | 13800 | 0.0           | -               |
| 0.7965 | 13850 | 0.0           | -               |
| 0.7994 | 13900 | 0.0           | -               |
| 0.8022 | 13950 | 0.0           | -               |
| 0.8051 | 14000 | 0.0           | -               |
| 0.8080 | 14050 | 0.0           | -               |
| 0.8109 | 14100 | 0.0           | -               |
| 0.8137 | 14150 | 0.0           | -               |
| 0.8166 | 14200 | 0.0           | -               |
| 0.8195 | 14250 | 0.0           | -               |
| 0.8224 | 14300 | 0.0           | -               |
| 0.8252 | 14350 | 0.0           | -               |
| 0.8281 | 14400 | 0.0           | -               |
| 0.8310 | 14450 | 0.0           | -               |
| 0.8339 | 14500 | 0.0           | -               |
| 0.8367 | 14550 | 0.0           | -               |
| 0.8396 | 14600 | 0.0           | -               |
| 0.8425 | 14650 | 0.0           | -               |
| 0.8454 | 14700 | 0.0           | -               |
| 0.8482 | 14750 | 0.0           | -               |
| 0.8511 | 14800 | 0.0           | -               |
| 0.8540 | 14850 | 0.0           | -               |
| 0.8569 | 14900 | 0.0           | -               |
| 0.8597 | 14950 | 0.0           | -               |
| 0.8626 | 15000 | 0.0           | -               |
| 0.8655 | 15050 | 0.0           | -               |
| 0.8684 | 15100 | 0.0           | -               |
| 0.8712 | 15150 | 0.0           | -               |
| 0.8741 | 15200 | 0.0           | -               |
| 0.8770 | 15250 | 0.0           | -               |
| 0.8799 | 15300 | 0.0           | -               |
| 0.8827 | 15350 | 0.0           | -               |
| 0.8856 | 15400 | 0.0           | -               |
| 0.8885 | 15450 | 0.0           | -               |
| 0.8914 | 15500 | 0.0           | -               |
| 0.8942 | 15550 | 0.0           | -               |
| 0.8971 | 15600 | 0.0           | -               |
| 0.9000 | 15650 | 0.0           | -               |
| 0.9029 | 15700 | 0.0           | -               |
| 0.9057 | 15750 | 0.0           | -               |
| 0.9086 | 15800 | 0.0           | -               |
| 0.9115 | 15850 | 0.0           | -               |
| 0.9144 | 15900 | 0.0           | -               |
| 0.9172 | 15950 | 0.0           | -               |
| 0.9201 | 16000 | 0.0           | -               |
| 0.9230 | 16050 | 0.0           | -               |
| 0.9259 | 16100 | 0.0           | -               |
| 0.9287 | 16150 | 0.0           | -               |
| 0.9316 | 16200 | 0.0           | -               |
| 0.9345 | 16250 | 0.0           | -               |
| 0.9374 | 16300 | 0.0           | -               |
| 0.9402 | 16350 | 0.0           | -               |
| 0.9431 | 16400 | 0.0           | -               |
| 0.9460 | 16450 | 0.0           | -               |
| 0.9489 | 16500 | 0.0           | -               |
| 0.9518 | 16550 | 0.0           | -               |
| 0.9546 | 16600 | 0.0           | -               |
| 0.9575 | 16650 | 0.0           | -               |
| 0.9604 | 16700 | 0.0003        | -               |
| 0.9633 | 16750 | 0.0           | -               |
| 0.9661 | 16800 | 0.0           | -               |
| 0.9690 | 16850 | 0.0           | -               |
| 0.9719 | 16900 | 0.0           | -               |
| 0.9748 | 16950 | 0.0           | -               |
| 0.9776 | 17000 | 0.0           | -               |
| 0.9805 | 17050 | 0.0           | -               |
| 0.9834 | 17100 | 0.0           | -               |
| 0.9863 | 17150 | 0.0           | -               |
| 0.9891 | 17200 | 0.0           | -               |
| 0.9920 | 17250 | 0.0           | -               |
| 0.9949 | 17300 | 0.0           | -               |
| 0.9978 | 17350 | 0.0           | -               |

### Framework Versions
- Python: 3.12.3
- SetFit: 1.1.3
- Sentence Transformers: 5.2.0
- Transformers: 4.57.3
- PyTorch: 2.9.0a0+50eac811a6.nv25.09
- Datasets: 4.4.2
- Tokenizers: 0.22.2

## Citation

### BibTeX
```bibtex
@article{https://doi.org/10.48550/arxiv.2209.11055,
    doi = {10.48550/ARXIV.2209.11055},
    url = {https://arxiv.org/abs/2209.11055},
    author = {Tunstall, Lewis and Reimers, Nils and Jo, Unso Eun Seo and Bates, Luke and Korat, Daniel and Wasserblat, Moshe and Pereg, Oren},
    keywords = {Computation and Language (cs.CL), FOS: Computer and information sciences, FOS: Computer and information sciences},
    title = {Efficient Few-Shot Learning Without Prompts},
    publisher = {arXiv},
    year = {2022},
    copyright = {Creative Commons Attribution 4.0 International}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->