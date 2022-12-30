from nltk import bigrams, trigrams

"""This class provides some helping functions to create alignments based on bi- and trigrams perspective. 
The start and end tags are also appended here.

"""

start_tag = '<s> ' # built-in post tag space 
end_tag = ' </s>' # built-in pre tag space

"""adding opening and closing tags (<s> </s>) for each sentence
   
Parameters
----------
case : int - 0 or 1
sentence_list : list of lists or list of tuples: 
case 0: [[orig, orth], [orig, orth], ...] - parallel sentences sturcture 
case 1: [(word1, word2, word3), (word1, word2, word3), ...] - orth. sentence divided in tupels each
"""
def add_start_end_tags(sentence_list, case):
    tagged_sentence_list = []

    if (case == 0):
        for item in sentence_list:
        # for now I want to deal only with same length sentences
            if (len(item[0].split()) == len(item[1].split()) and len(item[0].split()) > 0):
                tagged_sentence_list.append([start_tag + item[0] + end_tag, start_tag + item[1] + end_tag])

    # for a list of strings without the parallel sentence
    elif (case == 1):
        count = 0
        for item in sentence_list:
            if (isinstance(item, tuple)): 
                count += 1
                tagged_sentence_list.append(tuple([start_tag.strip()]) + item + tuple([end_tag]))
        
    return tagged_sentence_list       

"""Conducts the word alignment.

Parameters
----------
sentence_list : [[str, str]] 
    
Returns
-------
algined_words_list : list 
    contains the concatenated strings in the following data structure: ["Word1 alignedWord", "des das"]
This way it would be possible to easily create bi- and trigrams containing both source and target languages in one representation 
"""
def align_words(sentence_list):
    aligned_words_list = [] 
    for sentence in sentence_list:
        orig = sentence[0].split()
        orth = sentence[1].split()

        if (len(orig) != len(orth)):
            print("shouldn't happen at this point")
            continue # moving forward to the next sentence
        
        tmp_list = []
        for i in range(len(orig)):
            aligned_pair = orig[i] + " " + orth[i]
            aligned_words_list.append(aligned_pair)

            tmp_list.append(aligned_pair)

    return aligned_words_list    

"""Conducts bigrams alignment.
Each parallel sentence is be transformed into bigrams and then aligned based on the sentence position 

Parameters
----------
sentences_list : [[str, str]] - holds all tagged parallel sentences


Returns
-------    
[
    [(bigram1orig), (bigram1orth)],
    [(bigram2orig), (bigram2orth)],
    [(bigram3orig), (bigram3orth)],
    ...
    [(bigram_n_orig), (bigram_n_orth)],
]
"""
def align_bigrams(sentences_list):
    aligned_bigrams_list = []
    for sentence in sentences_list:
        orig = sentence[0].split()
        orth = sentence[1].split()

        orig_bigrams = bigrams(orig)
        orth_bigrams = bigrams(orth)

        orig_birgams_list = [item for item in orig_bigrams]
        orth_birgams_list = [item for item in orth_bigrams]

        counter = 0

        while (counter < len(orig_birgams_list)):
            aligned_bigrams_list.append([(orig_birgams_list[counter], orth_birgams_list[counter])])
            counter += 1
    
    return aligned_bigrams_list

"""Conducts bigrams alignment.

Each parallel sentence is be transformed into trigrams and then aligned based on the sentence position 

Parameters
----------
sentences_list : [[str, str]] - holds all tagged parallel sentences

Returns
-------
[
    [(trigram1orig), (trigram1orth)],
    [(trigram2orig), (trigram2orth)],
    [(trigram3orig), (trigram3orth)],
    ...
    [(trigram_n_orig), (trigram_n_orth)],
]
"""
def align_trigrams(sentences_list):
    aligned_trigrams_list = []
    for sentence in sentences_list:
        orig = sentence[0].split()
        orth = sentence[1].split()

        orig_trigrams = trigrams(orig)
        orth_trigrams = trigrams(orth)

        orig_trirgams_list = [item for item in orig_trigrams]
        orth_trirgams_list = [item for item in orth_trigrams]

        counter = 0

        while (counter < len(orig_trirgams_list)):
            aligned_trigrams_list.append([(orig_trirgams_list[counter], orth_trirgams_list[counter])])
            counter += 1
    
    return aligned_trigrams_list