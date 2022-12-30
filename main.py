from Corpora import Corpora
from InputSentence import InputSentence
from process_tokens import get_settings, closeConnectionDB
import logging

def main():
    print("griaß di")
    corpus = Corpora("./Training_data.xlsx")

    # creating logger
    root_logger= logging.getLogger()
    root_logger.setLevel(logging.DEBUG) 
    handler = logging.FileHandler('Queries.log', 'w', 'utf-8') 
    formatter = logging.Formatter('%(message)s') 
    handler.setFormatter(formatter) 
    root_logger.addHandler(handler)
 
    transcripts_ids ,sentence_objects, connection = get_settings()

    queries = {} # per transcript, all queries are stored as an array

    for id in transcripts_ids:
        queries[id] = []
        for key in sentence_objects[id].keys():
            o = sentence_objects[id][key]
            sntc = InputSentence(o["output_sentence"], corpus)
            sentence_objects[id][key]["translation"] = sntc.stack_decoder_translation
            queries[id].extend(process_into_queries(sentence_objects[id][key]))
        logging.debug(queries[id])

    closeConnectionDB(connection)

# Input: sentence object with .items and .translation
def process_into_queries(obj):
    queries = []
    orthos = obj["translation"].split(" ")
    index = 0
    if len(obj["items"]) != len(orthos):
        print("Lengths do not correspond! This sentence needs further processing")
        print(obj)
        return []
    for item in obj["items"]:
        queries.append(createQuery(item["id"], orthos[index]))
        index += 1
    return queries

def createQuery(id, ortho):
    return "UPDATE token SET ortho = '" + ortho  + "', updated = CURRENT_TIMESTAMP WHERE id = " + str(id) + ";"

if __name__ == "__main__":
    main()