# This class accesses the database for collecting the tokens 
# and after processing feeding the correct spacy taggs to it
from dotenv import load_dotenv
import psycopg2
import re
from pathlib import Path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
import os
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_NAME = os.getenv("DATABASE_NAME")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_USER = os.getenv("DATABASE_USER")


# Open connection to the database
def connectDB():
    print("Initializing connection to the database")
    try: 
        conn = psycopg2.connect(host=DATABASE_HOST,
                            database=DATABASE_NAME,
                            port=DATABASE_PORT,
                            user=DATABASE_USER,
                            password=DATABASE_PASSWORD)
        print("Connecting to the PostgreSQL database...")
        return conn
    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

# Close connection to the database
def closeConnectionDB(conn):  
    # closing connection to the database
    if conn:
        conn.cursor().close()
        conn.close()
        print("PostgreSQL connection is closed")

# Get all transcript ids from the database that are relevant to Vienna
def get_transcripts_IDs_Vienna(cursor):
    postgreSQL_get_transcript_ids = "SELECT id FROM transcript WHERE name LIKE '%_WIEW%'" # should be 8 transcripts

    cursor.execute(postgreSQL_get_transcript_ids)
    records = cursor.fetchall()
    transcript_ids = []
    for row in records:
        transcript_ids.append(row[0]) # only one entry per row, as we ask for one column

    transcript_ids.sort()
    print("transcript ids for Vienna: ", transcript_ids)
    return transcript_ids

# Get all transcript ids from the database that are relevant to Vienna surrounding area
def get_transcripts_IDs_ViennaNear(cursor):
    postgreSQL_get_transcript_ids = "SELECT id FROM transcript WHERE name LIKE '%_WIER%' OR name LIKE '%_WIENW%' OR name LIKE '%_GERAS%' OR name LIKE '%_BADEN%' OR name LIKE '%_MÖDL%'" # should be 46 transcripts

    cursor.execute(postgreSQL_get_transcript_ids)
    records = cursor.fetchall()
    transcript_ids = []
    for row in records:
        transcript_ids.append(row[0]) # only one entry per row, as we ask for one column

    transcript_ids.sort()
    print("transcript ids for Vienna surrounding area: ", transcript_ids)
    return transcript_ids

# return tokens as dict objects
def get_tokens_per_transcriptID(cursor, id):
    postGreSQL_select_query_from_transcript = "SELECT * FROM token t WHERE t.text != '⦿' AND t.transcript_id_id = " + str(id) + " ORDER BY token_reihung ASC"

    cursor.execute(postGreSQL_select_query_from_transcript)
    records = cursor.fetchall()
    fields_names = [i[0] for i in cursor.description]

    data = []
    for row in records:
        row_object = {}
        for i in range(len(row)):
            row_object[fields_names[i]] = row[i]
        data.append(row_object)  

    return data

def get_speakers_IDs(cursor, id):
    postGreSQL_select_speaker_ids = "SELECT DISTINCT t.\"ID_Inf_id\" FROM token t WHERE t.transcript_id_id = " + str(id)

    cursor.execute(postGreSQL_select_speaker_ids)
    records = cursor.fetchall()

    speaker_ids = []
    for row in records:
        speaker_ids.append(row[0]) # only one entry per row

    speaker_ids.sort()
    return speaker_ids

def get_tokens_for_transcript_and_speakerID(cursor, transcript_id, speaker_id):
    postGreSQL_select_query_from_transcript_for_user = "SELECT id, text, ortho, t.\"ID_Inf_id\", token_reihung FROM token t WHERE t.text != '⦿' AND t.transcript_id_id = " + str(transcript_id) + " AND t.\"ID_Inf_id\" = " + str(speaker_id) + " ORDER BY token_reihung ASC"

    cursor.execute(postGreSQL_select_query_from_transcript_for_user)
    records = cursor.fetchall()
    fields_names = [i[0] for i in cursor.description]

    data = []
    for row in records:
        row_object = {}
        for i in range(len(row)):
            row_object[fields_names[i]] = row[i]
        data.append(row_object)

    return data    

"""""
:param: the relevant trancript object, a dictionary accessed by speaker's id
:return: sentences dict:
sentences = {
    "speaker_id:token_reihung": {
        "items": [item1, item2, ...]
        "filtered_sentence": [word1, word2, word3]
    },
    ...
}
"""""
def create_sentences(transcript):
    sentences = {} # tokenreihung is generated automatically, therefore access can be easily done without a dictionary

    for speaker_id in transcript:
        sentence_item = []
        last_token_ = 1
        for item in transcript[speaker_id]: # go through all same speaker's items
            if item["text"] is not None: # if it is a None, then skip
                # if it has arrived to the point where the sentence ends, if the sentence is too long then split also on the comma
                if item["text"].strip() == "." or item["text"].strip() == "?" or item["text"].strip() == ";" or item["text"].strip() == "," or item["text"].strip() == "-": # end the sentence
                    if sentence_item:
                        id = str(speaker_id) + "_" + str(last_token_)
                        sentences[id] = {}
                        sentences[id]["items"] = clean_fregments(sentence_item) # update global dict
                        sentences[id]["output_sentence"] = clean_sentence(' '.join(item["text"] for item in sentences[id]["items"]))
                        sentence_item = []
                        last_token_ = item["token_reihung"]
                else:
                    if not re.findall(r"\(\([a-zäüöß]+", item["text"]) and not re.findall(r"[a-zäüöß]+\)\)", item["text"]):
                        if text_is_word(item["text"].replace("_", "").replace(":", "")) and item["text"] != ":" and item["text"] != "_":
                            sentence_item.append(item)

    return sentences 

def clean_sentence(s):
    s = filter_out_signs(s)
    s = deanonymize(s)
    return fix_gaps(s)

def filter_out_signs(s):
    return s.replace("=", "").replace(":", "").replace("_", "").replace("-", "").replace("(", "").replace(")", "").lower()

def fix_gaps(s):
    return re.sub(r"(  )( )*", " ", s)

"""""
clean all fregments that were created by the transcripting process
"""""
def clean_fregments(l):
    index = len(l) - 1
    while (index > 0) :
        if l[index - 1]["text"].endswith(l[index]["text"]) and len(l[index - 1]["text"]) > len(l[index]["text"]) and (l[index]["text"] != 'a' or l[index]["text"] != 'i'):
            l.pop(index)
        index -= 1

    return l

def deanonymize(s):
    if re.findall(r"\[[a-zA-ZÄÖÜäüöß\s]+\][sopnza]{1,2}", s):
        s = s.replace("[", "")
        s = re.sub(r"\][sozpna]{2}", "" ,s)
        s = re.sub(r"\][sopnaz]", "" ,s)
        return s
    return s

def text_is_word(txt):
    if txt == "m" or txt == "hm" or txt == "mh" or txt == "mhm" or txt == "ähm" or txt == "ahm" or txt == "öhm" or "#" in txt: return False

    if re.findall(r"\(\(?\d\.\d\)\)?", txt.strip()) or re.findall(r"\(\(?([-]+|[\.]+)\)\)?", txt.strip()) or re.findall(r"\(\(?[a-zA-ZäüößÄÜÖ\s]+\)\)?", txt.strip()): ## filter out words that are time stamps, (---), (.)
        return False
    return True

def get_settings():
    connection = connectDB()
    transcripts_ids = get_transcripts_IDs_ViennaNear(connection.cursor()) # get_transcripts_IDs_Vienna(connection.cursor())
    transcript_objects = {}

    for transcript_id in transcripts_ids:
        speaker_ids = get_speakers_IDs(connection.cursor(), transcript_id)
        transcript_objects[transcript_id] = {}
        for speaker_id in speaker_ids:
            tokens_per_speaker = get_tokens_for_transcript_and_speakerID(connection.cursor(), transcript_id=transcript_id, speaker_id=speaker_id)
            transcript_objects[transcript_id][speaker_id] = tokens_per_speaker

    sentence_objects = {}
    for id in transcripts_ids:
        sentence_objects[id] = create_sentences(transcript_objects[id]) # holds the sentence structure

    return transcripts_ids ,sentence_objects, connection