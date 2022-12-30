from dotenv import load_dotenv
import psycopg2
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
        conn = psycopg2.connect(host="dioedb.dioe.at",
                            database="dioedb",
                            port="54323",
                            user="dioeuser",
                            password=DATABASE_PASSWORD)
        print("Connecting to the PostgreSQL database...")
        return conn
    except (Exception, psycopg2.Error) as error:
        print("Error while fetching data from PostgreSQL", error)

# Close connection to the database
def closeConnectionDB(conn):  
    if conn:
        conn.cursor().close()
        conn.close()
        print("PostgreSQL connection is closed")

def readQueriesFromLog():
    queries_file = open(".\Queries.log", "r", encoding="utf-8")
    lines = queries_file.readlines()
    queries = []
    count = 1
    for line in lines:
        single_queries = line.replace('[\"', "").replace('\"]', "")
        single_queries = single_queries.split('\", \"')
        queries.extend(single_queries)
        count += 1

    print("Number of tokens updated: ", len(queries))
    return queries

def commitSingleQuery(query, connection):
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()

def updateDB(queries, connection):
    count = 1
    for query in queries:
        commitSingleQuery(query, connection)
        count = count + 1
        if count % 10000 == 0:
            print(count, " tokens got updated so far")

def main():
    print("seas")

    connection = connectDB()
    queries = readQueriesFromLog()
    updateDB(queries, connection)
    closeConnectionDB(connection)

if __name__ == '__main__':
    main()