import re, collections
from nltk.util import ngrams
from nltk import bigrams, trigrams
from nltk.translate import PhraseTable, StackDecoder 
import pandas as pd
from collections import Counter, defaultdict
from itertools import chain
from operator import itemgetter
from math import *
from alignments import *
import logging
from nltk.tokenize import word_tokenize

"""
This class contains the corpus with all relevant parallel sentences and methods towards creating an N-gram based machine translation 

"""
class Corpora:
    """Constructor for the Corpora class

    Parameters
    ----------
    path : str 
        The file location for the parallel data
    """  
    def __init__(self, path):
        self.orig_orth = [] # contains the parallel data
        self.orig = [] # contains the source language data
        self.orth = [] # will be further anlayzed via language model
        
        # will be used in for the target language modelling 
        self.unigrams_orth = []
        self.bigrams_orth = []
        self.trigrams_orth = []

        self.not_same_len_gram = []
        self.refactored = []
        self.capital_letter_correction_gram = []

        self.slash_list = []
        self.hashtag_list = []
        self.error_list = []

        self.word_dict = [] # single word alignment based on equivalent index position of each sentence
        self.tupel_word_dict = []
        self.lookup_dict = {} # lookup dict consists of unigrams probability per key (= orig word in the source language)
        self.lookup_bigrams = {} # lookup dict consists of bigrams probability per key (= bigram in the source language)
        self.lookup_trigrams = {} # lookup dict consists of trigrams probability per key (= trigram in the source language

        self.general_bigrams = []
        self.general_trigrams = []
        self.slash_list = []

        self.tagged_sentences = []

        self.align_words_list = []

        self.fixed_oov = []
        self.oov = []

        self.unknown_tag = '<UNK>'
        self.punctuation_regex = re.compile('(\.|\,|!|\?)')
        
        # creating logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG) 
        handler = logging.FileHandler('corpora.log', 'w', 'utf-8') 
        formatter = logging.Formatter('%(message)s') 
        handler.setFormatter(formatter) 
        root_logger.addHandler(handler)
        
        self.phrase_table = PhraseTable()
        self.automatize_calls(path)
        self.language_model = self.create_language_model() 
        self.create_stack_decoder()
  
        self.references_general = [item.split() for item in self.orth] # creating the references list consisting of the whole corpus for the BLEU score

        # vowel_table for the heuristic method
        self.vowel_table = {}
        self.create_vowel_table()
            
 

    """This function calls all the needed functions for creating the

    Parameters
    ----------
    path : str 
        The file location for the parallel data
    """
    def automatize_calls(self, path):
        self.read_data_pandas(path)
        self.mainlist_statistics()
        self.handle_diff_lengths()
        self.create_word_dict()
        self.occurence_word_list = self.create_tupeldic()
        self.create_lookup_dict()
        self.info_printer()
        
        # bigrams
        self.create_bigrams()

        # trigrams
        self.create_trigrams()

        # create phrase table for further use in the StackDecoder
        self.create_phrase_table()
        

    """Reading the data from the xlsx (UTF-8 supported) file using pandas and save it into local data structures for training purposes.
    Each entry includes a pair of original <-> orthographic sentence that is appended to a global list.
    The data is then divided into:

    error_list : [[str, str]] - if it includes in the orig some \(sth.) and in the orth the '#' sign, will be handeled later
    orig_orth : [[str, str]] - the complementary list for the error_list
    slash | hashtag_list : [[str, str]] - added to the orig_orth list and is a subject for further processing   
    
    Parameters
    ----------
    path : str 
        The file location for the parallel data
    """
    def read_data_pandas(self, path):
        data = pd.read_excel(path)
        data.head() # defining the first (index 0) row as our head

        for first_row, second_row in zip(data.sentorig, data.sentorth):
            row = [first_row, second_row]
            ### filtering out the timer signs, scene descriptions - [lachen] and (?) ###
            row = [re.sub(r"\[\d+((,|\.)\d+)?s\]|\[[a-zA-ZäöüÄÖÜß]+\]|\(\?\)", "", word) for word in row]
            row = [re.sub(r"(  )( )*", " ", word) for word in row]
                
            if ((re.search(r"\\", row[0]) or not re.search(r"#", row[0])) and re.search(r"#", row[1])): 
                self.error_list.append(row)
            else:
                self.orig_orth.append(row)

            if (re.search(r"(\d)*/", row[0]) or re.search(r"(\d)*/", row[1])):
                self.slash_list.append(row)
                
            if (re.search(r"#", row[0]) or re.search(r"#", row[1])):
                self.hashtag_list.append(row)

    
    """Prints out statistical information about the data:
    - How many pairs have the same length? Sentences not of the same length are handled later in another function and are removed from the dictionary 
    - How many pairs are just capital letter correction?  

    Data changed
    ------------
    not_same_len_gram : [[str, str]] - a list containing the parallel sentences that do not posses the same length
    captial_letter_correction_gram : [[str, str]] - a list containing the parallel sentences that are identical lowered case 


    """
    def mainlist_statistics(self):
        counter = 0
        for item in self.orig_orth:
            # spliting each sentence into single words
            orig = item[0].split()
            orth = item[1].split()

            # not of the same length 
            if (len(orig) != len(orth)):
                self.not_same_len_gram.append(item)
               
            # capital letter correction 
            if (item[0] == item[1].lower()):
                self.capital_letter_correction_gram.append(item)
               
        logging.debug('Not of the same length: %d', len(self.not_same_len_gram))
        logging.debug('Capital letter correction: %d', len(self.capital_letter_correction_gram))

    """With this algorithm more than 5% of the usable input data can be gained back.
    The main reason for having parallel sentences of different lengths is due to the fragments created during transcribing.
    Fragments of the previous word were inserted in random positions in the source sentence.
    After cleaning the fragments from the {origsent}, if the length is then equal to {sentorig}, 
    the fixed parallel set will be added to the main working list.
    the produced parallel set drops also () and [] signs

    Data changed
    ------------
    refactored : [[str, str]] - keeps track of the gained back parallel sentences set
    orig_orth : [[str, str]] - the refactored list is appended to the orig_orth list
    not_same_len_gram : [[str, str]] - the items of the refactored list are removed 
    """
    def handle_diff_lengths(self):
        logging.debug('{} not same length before refactoring.'.format(len(self.not_same_len_gram)))
        logging.debug('{} same length before refactoring.'.format(len(self.orig_orth)))
        print(len(self.not_same_len_gram), ' parallel sets are now in the not_same_len_gram list\n' , len(self.orig_orth) ,' parallel sets are now in the main list')

        for parallel_set in reversed(self.not_same_len_gram):
            if (parallel_set not in self.error_list):
                orig = re.sub(r"\(|\)|\[|\]", "", parallel_set[0]).split()
                orth = re.sub(r"\(|\)|\[|\]", "", parallel_set[1]).split() # for checking if the end result is indeed of equal length
                
                handled = False
                index = len(orig) - 1
                
                while (len(orig) > len(orth) and len(orig) > 1 and not handled and index > 0):
                    if (orig[index] != '.' and orig[index] != ',' and orig[index] != '?' and orig[index] != '!'):
                        if (re.findall(orig[index] + '$', orig[index - 1])): 
                            orig.pop(index)
                            if (len(orig) == len(orth)):
                                self.refactored.append([' '.join(orig), parallel_set[1]]) # adding to the refactored list
                                self.orig_orth.append([' '.join(orig), ' '.join(orth)]) # adding to the main list
                                self.not_same_len_gram.remove(parallel_set) # removing from the not_same_len_gram list
                                handled = True
                   
                    index -= 1 # increment for the next iteration round

                    # if the iteration over the whole list has been completed and the length is still not equal, the handled boolean flag turns true 
                    if (index == 0 and len(orig) != len(orth)):
                        handled = True
   
        logging.debug('{} not same length after refactoring.'.format(len(self.not_same_len_gram)))
        logging.debug('{} same length after refactoring.'.format(len(self.orig_orth)))

    """Prints out additional information regarding the input data
    """
    def info_printer(self): 
        self.orig = [item[0] for item in self.orig_orth]
        self.orth = [item[1] for item in self.orig_orth]

        dialect_words_counter = collections.Counter([word for sentence in self.orig for word in sentence.split()])
        high_german_words_counter = collections.Counter([word for sentence in self.orth for word in sentence.split()])

        logging.debug('=========================\n{} Dialect words.'.format(len([word for sentence in self.orig for word in sentence.split()])))
        logging.debug('{} unique Dialect words.'.format(len(dialect_words_counter)))
        logging.debug('=========================')
        logging.debug('{} High-German words.'.format(len([word for sentence in self.orth for word in sentence.split()])))
        logging.debug('{} unique High-German words.'.format(len(high_german_words_counter)))
       
    """Creating a global word dictionary for a quick lookup.
    Sentences not of the same length are excluded.
    This data structure serves as a middle step towards creating a machine translation.
    The word alignment happens here based on the similar index in the sentence.

    Data changed
    ------------
    word_dict : [[str, str]] - holds the word in the source and target language
    """
    def create_word_dict(self):
        for item in self.orig_orth:
            orig = item[0].split()
            orth = item[1].split()

            index = 0
            for i in range(len(orig) - 1):
                if (len(orig) == len(orth) and len(orig[i]) > 0):   
                    self.word_dict.append([orig[i], orth[i]])

    """Creates unigrams tupels
       
    Returns
    -------
    Counter collection
            { (orig, orth): number of occurences }     
            
    """
    def create_tupeldic(self):
        for entry in self.word_dict:
            self.tupel_word_dict.append([(entry[0], entry[1])])
        
        return Counter(chain(*self.tupel_word_dict))
        
    """Creates a dictionary that is optimal for a look up
        
    Data changed
    -------
    lookup_dict : dict
        {
            "word1": [("translation1", occurence), ("translation2", occurence), ...]
            .
            .
            .
            "wordn": [("translation1", occurence), ("translation2", occurence), ...]

        }
    """
    def create_lookup_dict(self):
        for entry in self.occurence_word_list:
            if entry[0] in self.lookup_dict.keys():
                self.lookup_dict[entry[0]].append((entry[1], self.occurence_word_list[entry]))
            else:
                self.lookup_dict[entry[0]] = [(entry[1], self.occurence_word_list[entry])]
        
    """Creates bigrams for the whole corpus.
    Occurence entry in the lookup_bigram is referred to the global occurence and not the relative one per bigram.
    Relative occurence will be later calculated, once added to the PhrasTable under the log input value.

    Data changed
    ------------
    general_bigrams_list : [bigrams] - includes also empty entries which are eliminated in the new general_bigrams list
    general_bigrams : [(str, str)] 
                [('orig1 orth1', 'orig2 orth2'), ('orig2 orth2', 'orig3 orth3')...] ... word alignment is already integrated in the tupel
    lookup_bigrams : dict 
        {
            "bigram1": [("translationbigram1", occurence), ("translationbigram2", occurence), ...]
                .
                .
                .
            "bigramn": [("translationbigram1", occurence), ("translationbigram2", occurence), ...]
        }

    """
    def create_bigrams(self):
        self.tagged_sentences = add_start_end_tags(self.orig_orth, 0)
        self.align_words_list = align_words(self.tagged_sentences)
        self.general_bigrams_list = list(bigrams(self.align_words_list))

        for item in self.general_bigrams_list:
            if (item[0] != ' ' and item[1] != ' '):
                self.general_bigrams.append(item)

        self.par_bigrams_list = align_bigrams(self.tagged_sentences)        
        occurence_bigrams = Counter(chain(*self.par_bigrams_list))
        
        for entry in occurence_bigrams:
            if entry[0] in self.lookup_bigrams.keys():
                self.lookup_bigrams[entry[0]].append((entry[1], occurence_bigrams[entry]))
            else:
                self.lookup_bigrams[entry[0]] = [(entry[1], occurence_bigrams[entry])]
        
    """Creating trigrams for the whole corpus
    Occurence entry in the lookup_trigram is referred to the global occurence and not the relative one per trigram.
    Relative occurence will be later calculated, once added to the PhrasTable under the log input value.

    general_trigrams_list : [trigrams] - includes also empty entries which are eliminated in the new general_trigrams list
    general_trigrams : [(str, str)] 
                    [('orig1 orth1', 'orig2 orth2', 'orig3 orig3'), ('orig2 orth2', 'orig3 orth3', 'orig4 orig4')...] ... word alignment is already integrated in the tupel
    lookup_trigrams : dict 
            {
                "trigram1": [("translationtrigram1", occurence), ("translationtrigram2", occurence), ...]
                    ...
                "trigramn": [("translationtrigram1", occurence), ("translationtrigram2", occurence), ...]

            }
    """
    def create_trigrams(self):
        self.general_trigrams_list = list(trigrams(self.align_words_list))

        for item in self.general_trigrams_list:
            if (item[0] != ' ' and item[1] != ' '):
                self.general_trigrams.append(item)

        self.par_trigrams_list = align_trigrams(self.tagged_sentences)        
        occurence_trigrams = Counter(chain(*self.par_trigrams_list))

        for entry in occurence_trigrams:
            if entry[0] in self.lookup_trigrams.keys():
                self.lookup_trigrams[entry[0]].append((entry[1], occurence_trigrams[entry]))
            else:
                self.lookup_trigrams[entry[0]] = [(entry[1], occurence_trigrams[entry])]        

    """Creates a PhraseTable with opening and closing tags.
    The phrase table includes uni-, bi- and trigrams.

    Parameters used for the PhraseTable
    ----------
    log_prob : float - Log probability that given src_phrase, trg_phrase is its translation. Is calculated via conditional probability.       
    """
    def create_phrase_table(self):
        tracking_dataphrase = []

        # adding the tags to the phrase table as unigrams
        tags = ['<s>', '</s>', self.unknown_tag]
        to_grams = ngrams(tags, 1)
        tags_grams_array = [gram for gram in to_grams]
        for tag in tags_grams_array:
            self.phrase_table.add(tag, tag, 1)
        
        # adding unigrams to the PhraseTable
        for item in self.lookup_dict:
            overall_item = sum(n for _, n in self.lookup_dict[item]) # computing per key the total number of occurences for the relative probabilty 
            
            # casting the object to the right type -> a single unigram item
            item_gram = ngrams([item], 1)
            unigram_item_list = [gram for gram in item_gram] 

            for option in self.lookup_dict[item]:
                # casting the object to the right type -> a single unigram item
                option_gram = ngrams([option[0]], 1)
                option_single_list = [gram for gram in option_gram]
                self.phrase_table.add(unigram_item_list[0], option_single_list[0], option[1] / overall_item) # Python's '/' division is a "floor/true division", therefore not casting is needed 
                tracking_dataphrase.append((unigram_item_list[0], option_single_list[0], option[1] / overall_item)) # DataPhrase is not iterable
                
        # adding bigrams to the PhraseTable
        for item in self.lookup_bigrams:
            overall_item_bigram = sum(n for _, n in self.lookup_bigrams[item]) # computing per key the total number of occurences for the relative probabilty 

            # each entry is already in the needed bigram form, therefore no extra casting as for unigram
            for option in self.lookup_bigrams[item]:
                self.phrase_table.add(item, option[0], option[1] / overall_item_bigram)
                tracking_dataphrase.append((item, option[0], option[1] / overall_item_bigram))
                
        # adding trigrams to the PhraseTable
        for item in self.lookup_trigrams:
            overall_item_trigram = sum(n for _, n in self.lookup_trigrams[item]) # computing per key the total number of occurences for the relative probabilty 

            # each entry is already in the needed trigram form, therefore no extra casting as for unigram
            for option in self.lookup_trigrams[item]:
                self.phrase_table.add(item, option[0], option[1] / overall_item_trigram)
                tracking_dataphrase.append((item, option[0], option[1] / overall_item_trigram))
                

    """Creates a language model for the source language.
    The probabilities inserted are extracted from orth list.
    Returns
    -------
    object
        language_model of the target language
    """
    def create_language_model(self):
        
        # handling unigrams 
        for item in self.orth:
            tagged_sentence = '<s> <s> ' + item + ' </s> </s>'
            tmp_bigram = [gram for gram in bigrams(tagged_sentence.split())]            
            for gram in tmp_bigram:
                self.bigrams_orth.append(gram)

            tmp_trigram = [gram for gram in trigrams(tagged_sentence.split())]
            for gram in tmp_trigram:
                self.trigrams_orth.append(gram)

        language_prob = defaultdict(lambda: -50.0)

        # handling bigrams
        overall_bigrams_entries = len(self.bigrams_orth) 
        logging.debug('overall_entries_bigrams for orth: %d', overall_bigrams_entries)

        # handling trigrams
        overall_trigrams_entries = len(self.trigrams_orth)
        logging.debug('overall_entries_trigrams for orth: %d', overall_trigrams_entries)
        orth_occurences_trigrams = Counter(self.trigrams_orth)

        
        for gram in orth_occurences_trigrams:
            language_prob[gram] = log(orth_occurences_trigrams[gram] / overall_trigrams_entries)

        return type('',(object,),{'probability_change': lambda self, context, phrase: language_prob[phrase], 'probability': lambda self, phrase: language_prob[phrase]})()

    """Initializing the StackDecoder instance with the created phrase_table and language_model.
    Distortion factor is set on 0 since no reordering is needed.
    """
    def create_stack_decoder(self):
        self.stack_decoder = StackDecoder(self.phrase_table, self.language_model)
        self.stack_decoder.distortion_factor = 0.0
        
    """Translates a full input sentence
    
    Parameters
    ----------
    sentence : str - input sentence to be translated  
    
    Returns
    -------
    sentence : str - the output sentence returned from the stack_decoder instance
    """
    def translate_with_decoder(self, sentence):
        return self.stack_decoder.translate(sentence.split())
   
    """Translates an input of one word
    
    Parameters
    ----------
    sentence : str - input word to be translated, might contain one extra character that is filtered out for the translation
    
    Returns
    -------
    sentence
        The word with the highest probability from the lookup dictionary
    """
    def translate_single_input(self, sentence):
        if sentence.strip() != '.' and sentence.strip() != ',' and sentence.strip() != '?' and sentence.strip() != '!': 
            return max(self.lookup_dict[sentence.strip()], key = itemgetter(1))[0]
        return sentence

    """Prints information regarding the gained back (fixed) out-of-vocabulary words (OOV).
    These words were gained back during translation by the individual InputSentence instance.
    """
    def print_fixed_oov(self):
        logging.debug('=== OOV Statistics ===\n* Overall original OOV: %d\n* Gained back OOV: %d\n* %f percent was gained back', len(self.fixed_oov) + len(self.oov), len(self.fixed_oov), 100 * len(self.fixed_oov) / (len(self.fixed_oov) + len(self.oov)))
        logging.debug('=== CHANGED OOV: ===')
        for item in self.fixed_oov:
            logging.debug('The word: %s was changed to: %s', item[0], item[1])
        
        logging.debug('=== OOV WORDS: ===')
        for item in self.oov:
            if item != ',' and item != '.' and item != '!' and item != '?':
                logging.debug('* %s', item)

    """Filter the references for computing the BLEU score.
    Based on an input sentence, all sentences in the orthographic list will be collected if there is an intersection

    Parameters
    ----------
    sentence : str - the output sentence from the stack decoder 

    Returns
    -------
    [str]
        returns all sentences as reference for which one of the words in the input sentence appear

    """
    def filter_references(self, sentence):
        mid_result = [any([word in sntc for word in sentence.split()]) for sntc in self.orth]
        return [self.orth[i] for i in range(0, len(mid_result)) if mid_result[i]] if len([self.orth[i] for i in range(0, len(mid_result)) if mid_result[i]]) > 0 else [s.split() for s in self.orth]

    """Initializes the vowel_table (: dict) with values based on internal information about the language patterns. 
    These combinations of letters saved as keys are typical in the positions of their related values. 
    This change is based on the research of the varieties and this information could be used in case of OOV words, 
    while trying to gain back some words that are not recognized by the system.
    """
    def create_vowel_table(self):
        self.vowel_table = {
            'ää': ('ei', 'ai'),
            'aa': ('ei', 'ai'),
            'oo': ('au'),
            'öö': ('el', 'eil'),
            'oi': ('all', 'oll'),
            'ue': ('u'),
            'o': ('a'), 
            'g': ('ge'), # special case, will be handled more deeply
            'w': ('b'),
        }