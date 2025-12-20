"""Graph data fixtures for graph exploration E2E tests.

This module provides fixtures for testing knowledge graph visualization and exploration:
- Documents that form interesting graph structures
- Entity-rich content for relationship extraction
- Community detection validation data
- Graph export test data
"""

from pathlib import Path

import pytest


@pytest.fixture
def stanford_ai_lab_document(tmp_path: Path) -> Path:
    """Create a document about Stanford AI Lab.

    This document contains many entities and relationships ideal for
    knowledge graph construction and exploration.

    Returns:
        Path to Stanford AI Lab document
    """
    content = """# Stanford Artificial Intelligence Laboratory

## History and Formation

The Stanford Artificial Intelligence Laboratory (SAIL) was founded in 1963 by John McCarthy,
who is widely recognized as one of the founding fathers of artificial intelligence. McCarthy
coined the term "artificial intelligence" in 1955 and organized the famous Dartmouth Conference
in 1956, which is considered the birthplace of AI as a field.

SAIL has been at the forefront of AI research for over six decades, contributing groundbreaking
work in machine learning, computer vision, natural language processing, and robotics.

## Key Faculty and Researchers

### Andrew Ng

Professor Andrew Ng is a prominent figure in modern AI and machine learning. He joined Stanford's
Computer Science Department in 2002 and became an Associate Professor in 2009. Ng founded the
Stanford AI Lab in its modern form and led pioneering research in deep learning.

In 2011, Andrew Ng founded Google Brain, Google's deep learning research project. Under his
leadership, Google Brain developed many of the fundamental deep learning technologies used today,
including TensorFlow's predecessor systems.

In 2012, Ng co-founded Coursera with Daphne Koller, making high-quality education accessible
to millions worldwide. His Machine Learning course on Coursera has been taken by over 5 million
students, making it one of the most popular online courses ever created.

From 2014 to 2017, Ng served as Chief Scientist at Baidu, where he led the company's AI Group
and drove innovations in speech recognition, natural language processing, and autonomous driving.

In 2017, Andrew Ng founded deeplearning.ai, focusing on AI education and research. He also
founded Landing AI, which applies AI to manufacturing and industrial applications.

### Fei-Fei Li

Professor Fei-Fei Li is the Sequoia Professor of Computer Science at Stanford University and
Co-Director of Stanford's Human-Centered AI Institute. She served as Director of the Stanford
AI Lab from 2013 to 2018.

Li is best known for creating ImageNet, a massive visual database that revolutionized computer
vision research. The annual ImageNet Large Scale Visual Recognition Challenge (ILSVRC), which
ran from 2010 to 2017, drove tremendous advances in deep learning and convolutional neural
networks.

Her research focuses on computer vision, machine learning, cognitive neuroscience, and AI ethics.
Li has published over 200 scientific papers in top-tier conferences like CVPR, ICCV, NeurIPS,
and Nature.

From 2017 to 2018, Li took a leave from Stanford to serve as Chief Scientist of AI/ML at
Google Cloud, where she led the development of Google Cloud AI products and services.

### Christopher Manning

Professor Christopher Manning is the Thomas M. Siebel Professor in Machine Learning at Stanford
and Director of the Stanford Artificial Intelligence Laboratory. His research focuses on natural
language processing, computational linguistics, and deep learning.

Manning is the co-author of several influential textbooks, including "Foundations of Statistical
Natural Language Processing" with Hinrich Schütze. He has made fundamental contributions to
dependency parsing, sentiment analysis, and neural network architectures for NLP.

He co-developed the Stanford CoreNLP toolkit, widely used in NLP research and industry applications.
Manning has received numerous awards, including the ACL Lifetime Achievement Award.

### Percy Liang

Professor Percy Liang is an Associate Professor of Computer Science at Stanford, specializing
in machine learning and natural language processing. He leads research on interpretable AI,
robustness, and machine learning systems.

Liang created the Stanford Question Answering Dataset (SQuAD), which has become a standard
benchmark for reading comprehension and question answering systems. His work on semantic parsing
and program synthesis has influenced how machines understand structured knowledge.

## Research Areas and Projects

### Computer Vision

SAIL researchers have made seminal contributions to computer vision, including:

- **ImageNet**: Created by Fei-Fei Li and collaborators, ImageNet contains over 14 million
  labeled images and has driven advances in object recognition and scene understanding.

- **Convolutional Neural Networks**: SAIL researchers contributed to the development and
  refinement of CNNs, particularly through the ImageNet challenge which demonstrated the
  power of deep learning for visual recognition.

- **3D Scene Understanding**: Research on understanding 3D structure from 2D images, including
  work on depth estimation, 3D reconstruction, and spatial reasoning.

### Natural Language Processing

SAIL's NLP research spans multiple areas:

- **Stanford CoreNLP**: A suite of natural language analysis tools providing tokenization,
  part-of-speech tagging, named entity recognition, parsing, and sentiment analysis.

- **Question Answering**: Development of SQuAD and other benchmarks for machine reading
  comprehension, driving progress in language understanding.

- **Neural Language Models**: Research on transformer architectures, attention mechanisms,
  and large language models.

### Machine Learning Theory

SAIL conducts fundamental research in machine learning:

- **Deep Learning**: Theoretical and practical advances in neural network architectures,
  training methods, and optimization techniques.

- **Reinforcement Learning**: Research on policy gradient methods, inverse reinforcement
  learning, and human-robot interaction.

- **Interpretable AI**: Work on understanding and explaining AI decision-making processes.

### Robotics

SAIL has a strong robotics program:

- **Autonomous Systems**: Research on self-driving vehicles, including perception, planning,
  and control systems.

- **Manipulation**: Work on robotic grasping, object manipulation, and dexterous control.

- **Human-Robot Interaction**: Research on collaborative robots that work safely alongside humans.

## Industry Partnerships and Impact

SAIL maintains strong connections with industry through:

- **Google**: Multiple SAIL faculty and alumni have contributed to Google's AI initiatives,
  including Google Brain, Google Cloud AI, and Google Research.

- **Baidu**: Collaborations on speech recognition, natural language understanding, and
  autonomous driving technologies.

- **Coursera**: Founded by Andrew Ng and Daphne Koller, bringing Stanford-quality education
  to millions of learners worldwide.

- **Toyota**: Partnership through the Toyota Research Institute, focusing on autonomous
  vehicles and human-centered AI.

## Notable Alumni

SAIL has produced numerous influential AI researchers and entrepreneurs:

- **Daphne Koller**: Co-founder of Coursera, Professor at Stanford (now at Insitro)
- **Sebastian Thrun**: Founded Google X, creator of the self-driving car project
- **Pieter Abbeel**: Professor at UC Berkeley, co-founder of Covariant
- **Andrej Karpathy**: Former Director of AI at Tesla, OpenAI researcher
- **Ian Goodfellow**: Inventor of Generative Adversarial Networks (GANs)

## Educational Programs

SAIL contributes to Stanford's educational mission through:

- **CS221**: Artificial Intelligence: Principles and Techniques
- **CS229**: Machine Learning (taught by Andrew Ng)
- **CS231n**: Convolutional Neural Networks for Visual Recognition
- **CS224n**: Natural Language Processing with Deep Learning
- **CS330**: Deep Multi-Task and Meta Learning

These courses are among the most popular at Stanford and have influenced AI education globally.

## Research Publications and Impact

SAIL researchers regularly publish in top-tier venues:

- **NeurIPS** (Conference on Neural Information Processing Systems)
- **ICML** (International Conference on Machine Learning)
- **CVPR** (Conference on Computer Vision and Pattern Recognition)
- **ACL** (Association for Computational Linguistics)
- **Nature**, **Science**, and other prestigious journals

The lab's research has accumulated hundreds of thousands of citations, reflecting its profound
impact on the field of artificial intelligence.

## Future Directions

SAIL continues to push the boundaries of AI research in several directions:

- **Human-Centered AI**: Developing AI systems that augment human capabilities and align with
  human values, led by the Stanford Human-Centered AI Institute (HAI).

- **Robust and Trustworthy AI**: Research on AI safety, fairness, interpretability, and robustness
  to ensure AI systems are reliable and beneficial.

- **Multimodal Learning**: Integrating vision, language, and other modalities for more
  comprehensive AI understanding.

- **Embodied Intelligence**: Advancing robotics and physical AI systems that interact with
  the real world.

The Stanford Artificial Intelligence Laboratory remains one of the world's premier AI research
institutions, driving innovation and training the next generation of AI leaders.
"""

    doc_path = tmp_path / "stanford_ai_lab.txt"
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


@pytest.fixture
def google_brain_document(tmp_path: Path) -> Path:
    """Create a document about Google Brain.

    This document shares entities with Stanford AI Lab document,
    creating interesting cross-document relationships.

    Returns:
        Path to Google Brain document
    """
    content = """# Google Brain: Deep Learning Research at Google

## Origins and Formation

Google Brain is Google's artificial intelligence research team focused on deep learning and
machine learning. It was founded in 2011 by Andrew Ng, Greg Corrado, and Jeff Dean as an
exploratory project within Google X, Google's semi-secret research and development facility.

The project was initiated with the goal of building large-scale neural networks and exploring
the potential of deep learning, which at the time was still a relatively nascent field in
machine learning research.

## Founding Team

### Andrew Ng

Andrew Ng, who joined Google Brain from Stanford University, was instrumental in establishing
the project. At Stanford, Ng had been conducting groundbreaking research in machine learning
and had founded the Stanford Artificial Intelligence Laboratory.

Ng brought his expertise in deep learning and neural networks to Google, where he led the
initial experiments that would prove the viability of large-scale deep learning systems.

### Jeff Dean

Jeff Dean is a Google Senior Fellow and has been a key figure in Google Brain since its
inception. Dean is one of Google's most accomplished engineers, having previously led the
development of fundamental Google technologies including MapReduce, BigTable, and Spanner.

Dean's expertise in distributed systems and scalable computing infrastructure was crucial for
building the large-scale neural network training systems that became Google Brain's hallmark.

### Greg Corrado

Greg Corrado, a neuroscientist and machine learning researcher, co-founded Google Brain with
Ng and Dean. His background in neuroscience informed the team's approach to building
brain-inspired computing systems.

## Key Research and Achievements

### The Cat Paper (2012)

One of Google Brain's first major breakthroughs came in 2012 with the famous "cat paper."
The team trained a massive neural network with 16,000 CPU cores on 10 million unlabeled
YouTube video frames. The network learned to recognize cats without being explicitly
programmed to do so, demonstrating the power of unsupervised learning.

This work, published at ICML 2012, captured public imagination and helped catalyze the deep
learning revolution. The paper was authored by Quoc Le, Marc'Aurelio Ranzato, Rajat Monga,
Matthieu Devin, Kai Chen, Greg Corrado, Jeff Dean, and Andrew Ng.

### TensorFlow

In 2015, Google Brain released TensorFlow, an open-source machine learning framework that
has become one of the most widely used tools for building and training neural networks.

TensorFlow was designed to be flexible, efficient, and scalable, supporting everything from
research prototyping to production deployment. Key contributors included Rajat Monga,
Jeff Dean, Matthieu Devin, and many others from the Google Brain team.

The release of TensorFlow democratized deep learning, enabling researchers and developers
worldwide to build sophisticated AI applications. By 2020, TensorFlow had been downloaded
over 100 million times and used in countless products and research projects.

### Transformer Architecture

In 2017, Google Brain researchers introduced the Transformer architecture in the landmark
paper "Attention Is All You Need" (Vaswani et al., NeurIPS 2017). This architecture replaced
recurrent neural networks with attention mechanisms, dramatically improving performance on
natural language processing tasks.

The Transformer became the foundation for modern large language models, including BERT, GPT,
T5, and countless other systems. Authors included Ashish Vaswani, Noam Shazeer, Niki Parmar,
Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, and Illia Polosukhin.

### BERT (2018)

Building on the Transformer architecture, Google Brain developed BERT (Bidirectional Encoder
Representations from Transformers), a breakthrough in natural language understanding. BERT
achieved state-of-the-art results on 11 NLP tasks, including question answering (SQuAD),
named entity recognition, and sentiment analysis.

BERT was developed by Jacob Devlin, Ming-Wei Chang, Kenton Lee, and Kristina Toutanova.
The pre-training approach introduced by BERT became the standard paradigm for NLP research.

### AlphaGo and AlphaZero

While technically developed by DeepMind, Google Brain collaborated closely on reinforcement
learning research. The success of AlphaGo in defeating world champion Go player Lee Sedol in
2016 demonstrated the potential of deep reinforcement learning combined with Monte Carlo tree
search.

## Research Areas

### Computer Vision

Google Brain has made significant contributions to computer vision:

- **Image Classification**: Developing models that achieve human-level performance on ImageNet
  and other benchmarks.

- **Object Detection**: Creating efficient architectures like MobileNets for real-time object
  detection on mobile devices.

- **Image Generation**: Research on generative models including GANs and diffusion models for
  creating realistic images.

### Natural Language Processing

NLP is a major focus area for Google Brain:

- **Language Understanding**: BERT, T5, and other models for comprehending natural language.

- **Machine Translation**: Neural machine translation systems that power Google Translate,
  supporting over 100 languages.

- **Question Answering**: Systems that can read documents and answer questions about their
  content, used in Google Search.

### Speech Recognition

Google Brain has advanced speech recognition technology:

- **End-to-End Models**: Deep learning systems that directly map audio to text without
  intermediate representations.

- **Multilingual Recognition**: Supporting hundreds of languages and dialects in Google Assistant
  and other products.

- **Real-Time Processing**: Efficient models enabling low-latency speech recognition on devices.

### Reinforcement Learning

Research on learning through interaction with environments:

- **Game Playing**: Agents that master complex games through self-play.

- **Robotics**: Control policies for robotic manipulation and navigation.

- **Resource Optimization**: Using RL to optimize data center cooling, chip placement, and
  other real-world problems.

## Industry Applications

Google Brain's research directly impacts Google products:

- **Google Search**: NLP models improve query understanding and result relevance.

- **Google Assistant**: Speech recognition and natural language understanding power the
  virtual assistant.

- **Google Photos**: Computer vision enables automatic organization, search, and enhancement.

- **Gmail**: Smart Compose and Smart Reply use language models to help users write emails.

- **Google Translate**: Neural machine translation provides accurate translations across
  100+ languages.

- **YouTube**: Recommendation systems and content moderation use deep learning extensively.

## Notable Researchers

Google Brain has attracted world-class researchers:

- **Geoffrey Hinton**: Turing Award winner, godfather of deep learning (part-time advisor)
- **Quoc Le**: Co-inventor of sequence-to-sequence learning and AutoML
- **Ilya Sutskever**: Co-creator of AlexNet, later co-founded OpenAI
- **Ian Goodfellow**: Inventor of Generative Adversarial Networks (GANs)
- **Dario Amodei**: Research on AI safety, later co-founded Anthropic
- **Samy Bengio**: Long-time researcher, now at Apple

## Relationship with Academic Community

Google Brain maintains strong ties with academia:

- **Publications**: Regularly publishes in top conferences (NeurIPS, ICML, ICLR, ACL, CVPR)
- **Open Source**: Releases tools, datasets, and models to the research community
- **Residency Program**: Hosts researchers for 1-year positions to work on cutting-edge projects
- **Collaborations**: Partners with universities including Stanford, MIT, and Berkeley

## Evolution and Integration

In 2023, Google announced the merger of Google Brain and DeepMind into a single organization
called Google DeepMind. This consolidation aimed to accelerate AI research and development by
combining the strengths of both teams.

Google Brain's legacy continues through its contributions to:

- Open-source frameworks (TensorFlow, JAX)
- Fundamental research (Transformers, BERT, AutoML)
- Product innovations (search, translation, photos, assistant)
- Educational resources (courses, tutorials, papers)

The team's impact on the field of artificial intelligence is immeasurable, having trained
numerous researchers who have gone on to lead AI efforts at other companies and institutions.

## Future Directions

Before the merger with DeepMind, Google Brain was pursuing several research directions:

- **Efficient AI**: Making models smaller, faster, and more energy-efficient
- **Multimodal Learning**: Integrating vision, language, and other modalities
- **Federated Learning**: Training models while preserving user privacy
- **Neural Architecture Search**: Automatically discovering optimal model architectures
- **AI Safety and Alignment**: Ensuring AI systems are beneficial and controllable

Google Brain's pioneering work has shaped modern AI and will continue to influence the field
for years to come through its alumni, open-source contributions, and published research.
"""

    doc_path = tmp_path / "google_brain.txt"
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


@pytest.fixture
def deep_learning_pioneers_document(tmp_path: Path) -> Path:
    """Create a document about deep learning pioneers.

    This document creates additional connections between entities
    mentioned in other documents.

    Returns:
        Path to deep learning pioneers document
    """
    content = """# Pioneers of Deep Learning

## Geoffrey Hinton: The Godfather of Deep Learning

Geoffrey Hinton is widely regarded as one of the most influential figures in artificial
intelligence and deep learning. Born in London in 1947, Hinton earned his PhD from the
University of Edinburgh in 1978 under the supervision of Christopher Longuet-Higgins.

### Key Contributions

Hinton's contributions to neural networks and deep learning are foundational:

- **Backpropagation** (1986): Along with David Rumelhart and Ronald Williams, Hinton
  popularized the backpropagation algorithm, which remains the primary method for training
  neural networks today.

- **Boltzmann Machines** (1983): Hinton co-invented Boltzmann machines with Terry Sejnowski,
  introducing probabilistic models with hidden units.

- **Deep Belief Networks** (2006): Hinton introduced deep belief networks and layer-wise
  pre-training, helping to revive interest in deep learning after the "AI winter."

- **Dropout** (2012): With his students, Hinton developed dropout regularization, a simple
  but effective technique for preventing overfitting in neural networks.

- **Capsule Networks** (2017): Hinton proposed capsule networks as an alternative to
  convolutional neural networks, aiming to better preserve spatial hierarchies.

### Academic Career

Hinton has held positions at Carnegie Mellon University, University of Toronto, and University
College London. Since 1987, he has been a professor at the University of Toronto, where he
founded the machine learning group in the Computer Science Department.

His students and collaborators include many of today's leading AI researchers, including
Ilya Sutskever (co-founder of OpenAI), Alex Krizhevsky (creator of AlexNet), and Yann LeCun.

### Industry Impact

In 2013, Google acquired Hinton's startup DNNresearch, and Hinton joined Google as a
Distinguished Researcher, dividing his time between Google Brain and the University of Toronto.

In 2018, Hinton received the Turing Award (often called the "Nobel Prize of Computing")
together with Yann LeCun and Yoshua Bengio for their work on deep learning.

## Yann LeCun: Convolutional Neural Networks Pioneer

Yann LeCun is a French computer scientist best known for his work on convolutional neural
networks (CNNs) and their application to computer vision.

### Convolutional Neural Networks

In the late 1980s and early 1990s, LeCun developed convolutional neural networks while working
at AT&T Bell Labs. His LeNet architecture, demonstrated on handwritten digit recognition,
became the foundation for modern computer vision systems.

LeCun's CNN architecture introduced several key innovations:

- **Local connectivity**: Neurons connected to local regions of the input
- **Shared weights**: Same filter applied across the entire image
- **Pooling**: Downsampling to achieve spatial invariance

### Academic and Industry Career

LeCun earned his PhD from Pierre and Marie Curie University in 1987. He spent time at AT&T
Bell Labs (later AT&T Labs) from 1988 to 2003, where he led research on machine learning,
pattern recognition, and neural networks.

In 2003, LeCun joined New York University as a professor of computer science and neural science.
He founded the NYU Center for Data Science in 2012, serving as its inaugural director.

In 2013, Facebook (now Meta) recruited LeCun to establish and lead the Facebook AI Research
(FAIR) lab. As Chief AI Scientist at Meta, LeCun has overseen research on computer vision,
natural language processing, and reinforcement learning.

### Awards and Recognition

LeCun received the Turing Award in 2018 together with Geoffrey Hinton and Yoshua Bengio.
He has published over 200 papers and is one of the most cited computer scientists in the world.

## Yoshua Bengio: Deep Learning Theorist

Yoshua Bengio is a Canadian computer scientist and one of the three "godfathers" of deep learning,
alongside Hinton and LeCun.

### Research Contributions

Bengio's research has focused on the theoretical foundations of deep learning:

- **Neural Language Models** (2003): Bengio pioneered neural network approaches to language
  modeling, introducing the idea of learning distributed representations of words.

- **Long Short-Term Memory**: Contributed to understanding and improving LSTM networks for
  sequence modeling.

- **Generative Models**: Research on variational autoencoders, GANs, and other generative
  approaches.

- **Attention Mechanisms**: Early work on attention mechanisms that later became central to
  Transformer architectures.

### Academic Leadership

Bengio is a professor at the University of Montreal (Université de Montréal) and founder of
the Montreal Institute for Learning Algorithms (MILA). Under his leadership, MILA has become
one of the world's leading AI research institutes.

His students include many prominent researchers, including Ian Goodfellow (inventor of GANs),
Aaron Courville, and Pascal Vincent.

### AI for Humanity

Bengio is deeply concerned about the societal implications of AI. He co-founded Element AI
(acquired by ServiceNow in 2020) and has been vocal about the need for responsible AI
development, AI safety research, and policies to ensure AI benefits humanity.

In 2018, he received the Turing Award with Hinton and LeCun. He has also received the
prestigious Killam Prize and been made an Officer of the Order of Canada.

## Other Influential Figures

### Andrew Ng

Andrew Ng is a Stanford professor who founded Google Brain and co-founded Coursera. His
contributions to online education have democratized AI learning, with his Machine Learning
course taken by over 5 million students.

Ng has also served as Chief Scientist at Baidu and founded deeplearning.ai and Landing AI,
continuing to advance both AI research and education.

### Fei-Fei Li

Fei-Fei Li created ImageNet, the dataset that catalyzed the deep learning revolution in
computer vision. The ImageNet Large Scale Visual Recognition Challenge (ILSVRC) drove rapid
advances in CNNs and established deep learning as the dominant paradigm in computer vision.

Li served as Director of Stanford's AI Lab and Chief Scientist of AI/ML at Google Cloud.
She co-founded AI4ALL, a nonprofit working to increase diversity and inclusion in AI.

### Ian Goodfellow

Ian Goodfellow, a student of Yoshua Bengio and Andrew Ng, invented Generative Adversarial
Networks (GANs) in 2014. GANs revolutionized generative modeling and have been applied to
image generation, style transfer, and many other applications.

Goodfellow worked at Google Brain, OpenAI, and Apple, making significant contributions to
adversarial machine learning and deep learning security.

### Ilya Sutskever

Ilya Sutskever studied under Geoffrey Hinton at the University of Toronto. He co-created
AlexNet, the CNN that won the 2012 ImageNet competition and sparked the modern deep learning
era.

Sutskever worked at Google Brain before co-founding OpenAI in 2015, where he served as
Chief Scientist. His research on sequence-to-sequence learning and language models has been
instrumental in the development of large language models.

## The Deep Learning Revolution

The work of these pioneers has transformed artificial intelligence from a niche academic
field to a technology that powers countless applications:

- **Computer Vision**: Face recognition, autonomous vehicles, medical imaging
- **Natural Language Processing**: Machine translation, chatbots, search engines
- **Speech Recognition**: Virtual assistants, transcription services
- **Recommendation Systems**: Content discovery on social media, streaming platforms
- **Healthcare**: Disease diagnosis, drug discovery, personalized medicine
- **Science**: Protein folding prediction, climate modeling, particle physics

The deep learning community they built is characterized by open collaboration, with researchers
freely sharing papers, code, and ideas. Major conferences like NeurIPS, ICML, ICLR, and CVPR
have grown from small academic gatherings to massive international events attended by
thousands of researchers from academia and industry.

## Challenges and Future Directions

Despite tremendous progress, the pioneers acknowledge significant challenges remain:

- **Data Efficiency**: Current models require massive amounts of labeled data
- **Interpretability**: Deep learning models remain largely "black boxes"
- **Robustness**: Models can be fooled by adversarial examples
- **Energy Consumption**: Training large models requires enormous computational resources
- **Bias and Fairness**: Models can amplify societal biases present in training data
- **Safety and Alignment**: Ensuring powerful AI systems remain beneficial and controllable

The next generation of researchers, trained by these pioneers, is working to address these
challenges and push the boundaries of what's possible with artificial intelligence.
"""

    doc_path = tmp_path / "deep_learning_pioneers.txt"
    doc_path.write_text(content, encoding="utf-8")
    return doc_path


@pytest.fixture
def indexed_graph_documents(
    stanford_ai_lab_document: Path,
    google_brain_document: Path,
    deep_learning_pioneers_document: Path,
) -> list[Path]:
    """Get all graph-rich documents for knowledge graph testing.

    These documents form an interesting knowledge graph with:
    - Shared entities (Andrew Ng, Geoffrey Hinton, etc.)
    - Various relationship types (FOUNDED, WORKED_AT, STUDIED_UNDER)
    - Multiple communities (Stanford, Google, University of Toronto)

    Returns:
        List of Paths to graph-rich documents
    """
    return [
        stanford_ai_lab_document,
        google_brain_document,
        deep_learning_pioneers_document,
    ]
