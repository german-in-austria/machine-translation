from alignments import *
import re
from nltk.util import ngrams

"""
This class holds all relevant attributes per each input sentence instance
The translation task consists of a preprocessing step in which all unknown words to the system are found.
The unknown words are analysed and gained back by alternation of some charachters based on known language patterns.

"""
class InputSentence: 
    """Constructor for the InputSentence class.

    Parameters
    ----------
    inputSentence : str - The raw input that is inserted to the system and is to be translated
    corpus : Corpora - The corpus instance that conducts the translation
    """
    def __init__(self, inputSentence, corpus):
        self.original_input = inputSentence # the original input is kept for key look up reasons
        inputSentence = re.sub(r"(  )( )*", " ", inputSentence).strip().lower() 
        self.to_translate_input = inputSentence
        self.corpus = corpus 
        self.has_oov = False # boolean flag if the sentence contains unknown words
        self.oov_tagged = "" # empty string if has_oov is false, else value is inserted during translation
            
        self.oov = []
        self.in_target = []
        self.oov_or_in_target = []    

        self.stack_decoder_translation = self.translate_with_stack_decoder()

    """Translates the input sentence.
    First, the out of vocabulary words are found.
    If no OOV words appear in the sentence, translation is executed without any further processing.
    Otherwise, the OOV words are handled and if they are not gained back via the heuristic, they are replaced with the UNK tag. 
    This way, no PhraseTable error interrupts the translation.
    
    Returns
    -------
    final result
        str - contains the StackDecoder based translation
    """
    def translate_with_stack_decoder(self):

        # dealing with empty inputs
        if not self.to_translate_input or self.to_translate_input == 'N/A' or self.original_input == 'N/A':
            self.to_translate_input = 'N/A'
            return 'N/A'
        
        self.find_oov()

        if (not self.oov):
            return " ".join(self.corpus.translate_with_decoder(self.to_translate_input))

        # if holds OOV
        self.has_oov = True
        uknown_tagged_to_translate = self.to_translate_input.split()

        for entry in self.oov:
            uknown_tagged_to_translate[entry[1]] = self.corpus.unknown_tag
       
        self.oov_tagged = self.corpus.translate_with_decoder(" ".join(uknown_tagged_to_translate).replace("  ", " ").strip())
       
        joined_str = " ".join(self.oov_tagged)

        # inserting back the oov word, already sorted, replacing iterative each occurence of the unknown tag
        for entry in self.oov:
            if len(self.oov_tagged) != 0:
                joined_str = joined_str.replace(self.corpus.unknown_tag, entry[0], 1)

        return joined_str


    """Finds all unknown words to the system.
    This algoritm performs per word in the given sentence a lookup in the dictionary.
    It finds real OOV words and words that appear only in the target language.
    If the words belong only to the target domain, they are dynamically added to the corpus through its PhraseTable instance.
    Later, a vowel detector iterates over the OOV words and checks if the changed word appears in the lookup dictionary.

    Data changed
    ------------
    in_target : [(str , int)] - the string holds the word and integer holds the index of the word in the input sentence to ease orientation
    oov : [(str , int)] - the string holds the word and integer holds the index of the word in the input sentence to ease orientation
    oov_or_in_target : [(str , int)] - concatenated list of oov and in_target
    """
    def find_oov(self):
        input_list = self.to_translate_input.split()

        # iteration over each word in the input sentence
        index = 0
        for word in input_list:
            if word not in self.corpus.lookup_dict:
                # if the word appears in the target values (the orth form), it is observed as if it has the same meaning 
                # is added to the table_phrase to save a redundant <UNK> tag replacement
                if word in [x for v in self.corpus.lookup_dict.values() for x in v]: 
                    self.in_target.append((word, index))
                    
                    # casting the word into a unigram to match the search in the phrase table
                    item_gram = ngrams([word], 1)
                    unigram_item_list = [gram for gram in item_gram]
                    self.corpus.phrase_table.add(unigram_item_list[0], unigram_item_list[0], 1.0)
                    self.corpus.lookup_dict[word] = [(word, 1)]
                
                # if the word does not appear at all in our dictionary will be noticed
                else:
                    self.oov.append((word, index))

            index += 1

        self.oov_or_in_target = self.oov + self.in_target

        # if the word exists is in the dictionary without the special signs, filter out and change the original input
        # is checked only for non-punctuation entries
        # iterating only over self.oov because the self.in_traget list has already been handled
        index_oov = len(self.oov) - 1
        for item in reversed(self.oov):
            # rechecking if underscores prevent the system from finding the word in the dictionary, if so change the to be translated sentence 
            if re.sub(r"_", "", item[0]) in self.corpus.lookup_dict:
                if item in self.oov_or_in_target: self.oov_or_in_target.remove(item)
                self.oov.remove(item)
                self.to_translate_input = re.sub(item[0], re.sub(r"_", "", item[0]), self.to_translate_input)
                continue

            # rechecking if slashes prevent the system from finding the word in the dictionary, if so change the to be translated sentence 
            if re.sub(r"\\", "", item[0]) in self.corpus.lookup_dict:
                if item in self.oov_or_in_target: self.oov_or_in_target.remove(item)
                self.oov.remove(item)
                self.to_translate_input = re.sub(item[0], re.sub(r"\\", "", item[0]), self.to_translate_input)
                continue

            # training to regain OOV words based on the predefined vowel_table
            # if the changed word exists in the lookup dictionary, accept the change and rebuild with it the to be translated sentence
            changed_vowel = False
            for vowel in self.corpus.vowel_table:
                if not changed_vowel and re.search(vowel, item[0]):
                        for i in range(len(self.corpus.vowel_table[vowel])):
                            # if the word exists in the lookup dictionary as a key, update the oov and oov_or_in_target lists and the to_translate_input 
                            if item[0].replace(vowel, self.corpus.vowel_table[vowel][i]) in self.corpus.lookup_dict and not changed_vowel:
                                if item in self.oov_or_in_target: self.oov_or_in_target.remove(item)
                                if item in self.oov: self.oov.remove(item)
                                self.to_translate_input = self.to_translate_input.replace(item[0], item[0].replace(vowel, self.corpus.vowel_table[vowel][i]))
                                print('The word: ', item[0], ' was changed, new sentence: ', self.to_translate_input)
                                self.corpus.fixed_oov.append([item[0], item[0].replace(vowel, self.corpus.vowel_table[vowel][i])])
                                changed_vowel = True 
                            
                            # if the word exists in the target language - update phrase_table, oov and in_target lists and the to_translate_input
                            if item[0].replace(vowel, self.corpus.vowel_table[vowel][i]) in [x for v in self.corpus.lookup_dict.values() for x in v] and not changed_vowel:
                                self.in_target.append((item[0].replace(vowel, self.corpus.vowel_table[vowel][i]) ,item[1]))
                                
                                item_gram = ngrams([self.in_target[len(self.in_target) - 1]], 1)
                                unigram_item_list = [gram for gram in item_gram]
                                self.corpus.phrase_table.add(unigram_item_list[0], unigram_item_list[0], 1.0)
                                self.corpus.lookup_dict[self.in_target[len(self.in_target) - 1]] = [(self.in_target[len(self.in_target) - 1], 1)]
                                
                                if item in self.oov: self.oov.remove(item)
                                self.to_translate_input = self.to_translate_input.replace(item[0], item[0].replace(vowel, self.corpus.vowel_table[vowel][0]))
                                self.corpus.fixed_oov.append([item[0], item[0].replace(vowel, self.corpus.vowel_table[vowel][i])])
                                changed_vowel = True
                            
                            # if the word exists in its capitalized version in the target language - update phrase_table, oov and in_target lists and the to_translate_input
                            if item[0].replace(vowel, self.corpus.vowel_table[vowel][i]).capitalize() in [x for v in self.corpus.lookup_dict.values() for x in v] and not changed_vowel:
                                self.in_target.append((item[0].replace(vowel, self.corpus.vowel_table[vowel][i]) ,item[1]).capitalize())

                                item_gram = ngrams([self.in_target[len(self.in_target) - 1]], 1)
                                unigram_item_list = [gram for gram in item_gram]
                                self.corpus.phrase_table.add(unigram_item_list[0], unigram_item_list[0], 1.0)
                                self.corpus.lookup_dict[self.in_target[len(self.in_target) - 1]] = [(self.in_target[len(self.in_target) - 1], 1)]

                                if item in self.oov: self.oov.remove(item)
                                self.to_translate_input = self.to_translate_input.replace(item[0], item[0].replace(vowel, self.corpus.vowel_table[vowel][i]).capitalize())
                                self.corpus.fixed_oov.append([item[0], item[0].replace(vowel, self.corpus.vowel_table[vowel][i]).capitalize()])
                                changed_vowel = True
                            
                            # handling the special case of the past form where the word construction includes the letter g for compounding
                            # once the word is forced to replace the vowel to "ge" it stays tagged as OOV 
                            # because it is not part of the language model, thus return value would be an empty string
                            if vowel == "g" and not changed_vowel and not re.search("ge", item[0]):
                                # g at the beginning of the word
                                if item[0][0] == vowel:
                                    # if the part - word is dialect, rewrite the part with its translation (based on highest probability)
                                    if item[0][1:] in self.corpus.lookup_dict:
                                        item = (item[0].replace(item[0][1:], self.corpus.translate_single_input(item[0][1:])), item[1])
                                        self.oov[index_oov] = (item[0].replace("g", "ge").lower(), self.oov[index_oov][1])
                                        self.to_translate_input = self.to_translate_input.replace(item[0], item[0].replace("g", "ge").lower())
                                        self.corpus.fixed_oov.append([item[0], item[0].replace("g", "ge").lower()])
                                        changed_vowel = True  
                                    # if the part - word is in the target language - just commit the update to the OOV list
                                    elif item[0][1:] in [x for v in self.corpus.lookup_dict.values() for x in v]:
                                        self.oov[index_oov] = (item[0].replace("g", "ge").lower(), self.oov[index_oov][1])
                                        self.to_translate_input = self.to_translate_input.replace(item[0], item[0].replace("g", "ge").lower())
                                        self.corpus.fixed_oov.append([item[0], item[0].replace("g", "ge").lower()])
                                        changed_vowel = True  
                                        
                                # the word is built out of two words together connected with 'g'
                                else:
                                    parts = item[0].split(vowel, 1) # splits only on the first 'g' occurrence
                                    in_dict = []
                                    for part in parts:
                                        if len(part) > 1 and part in self.corpus.lookup_dict: 
                                            item = (item[0].replace(part, self.corpus.translate_single_input(part)), item[1]) 
                                            in_dict.append(True)
                                        elif len(part) > 1 and part in [x for v in self.corpus.lookup_dict.values() for x in v]:
                                            in_dict.append(True)

                                    # if both words appear in the dictionary - commit the update to the OOV list
                                    if len(in_dict) == 2:
                                        self.oov[index_oov] = (item[0].replace("g", "ge").lower(), self.oov[index_oov][1])
                                        self.to_translate_input = self.to_translate_input.replace(item[0], item[0].replace("g", "ge").lower())
                                        self.corpus.fixed_oov.append([item[0], item[0].replace("g", "ge").lower()])
                                        changed_vowel = True  
            
            index_oov -= 1                                
                                    
        
        self.corpus.oov += [item[0] for item in self.oov] # Keeping track of the main OOV list of the corpus