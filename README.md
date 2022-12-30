# Machine Translation: Viennese (and Surrounding Areas) to Standard German
This project is based on the bachelor's thesis of Tahel Singer (Technical University of Vienna | TU Wien): "Machine Translation: Viennese to Standard German. Focus on Handling Out-Of-Vocabulary Words", 2021. 

The full scope of the thesis is presented in the following paper: https://ojs.bibl.u-szeged.hu/index.php/wpcl/article/view/44201/43015 
(Ludwig Maximilian Breuer, Arnold Graf, Tahel Singer, and Markus Pluschkovits. 2022. “Transcribe: A Web-Based Linguistic Transcription Tool”. Working Papers in Corpus Linguistics and Digital Technologies: Analyses and Methodology 7 (September):8-24. https://doi.org/10.14232/wpcl.2022.7.1. )

In this project, a bigger dialectal area was covered, considering not only Vienna but also its surroundings, including Baden, Moedling, and other close parts located in Lower Austria. The single tokens, originally transcribed according to GAT2 conventions (see Selting et al. 2009. http://www.gespraechsforschung-ozs.de/heft2009/px-gat2.pdf) were processed into sentences and got automatically translated with a machine translation that is trained on Viennese data with extra features that allow it to be more flexible when it comes to Out-Of-Vocabulary. The results were then post-processed back into standardorthographically transcribed tokens and the PostgreSQL database was updated.

The main idea of translating the tokens within a structured sentence is avoiding the ambiguity of dialectal words and benefiting from the observation of those words within a context (bi- and trigrams). This approach has been shown to be very beneficial during the research for the bachelor's thesis.

In total, about **360000 tokens** were updated in the database, building about **45000 parallel sentences**.

Future work would include further analysis of the translation quality, especially for the tokens from the surroundings of Vienna as well as adapting the model to more dialectal areas (e.g. Graz in Styria).
