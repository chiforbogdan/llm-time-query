import os
import re
from datetime import datetime
from datetime import datetime
from chromadb import EphemeralClient
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter


from openai import OpenAI

logcat_date_format = "%m-%d %H:%M:%S.%f"
log_entry_pattern = re.compile(r"(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})")
def extract_dates_from_logcat(file_path):
    current_year = datetime.now().year
    earliest_date = None
    latest_date = None

    with open(file_path, 'r') as file:
        for line in file:
            match = log_entry_pattern.search(line)
            if match:
                log_date_str = match.group(1)
                try:
                    log_date = datetime.strptime(log_date_str, logcat_date_format)
                    log_date = log_date.replace(year=current_year)
                except ValueError:
                    continue

                if earliest_date is None or log_date < earliest_date:
                    earliest_date = log_date
                if latest_date is None or log_date > latest_date:
                    latest_date = log_date
    return earliest_date, latest_date


def extract_process_info(text):
    # Define the regex pattern with capturing groups
    pattern = r'(?P<process_info>.+?)\[(?P<process_id>\d+)\]'

    # Search for the pattern in the text
    match = re.search(pattern, text)

    if match:
        # Extract groups from the match object
        process = match.group('process_info')
        process_id = match.group('process_id')
        return {
            'process': process,
            'pid': process_id
        }
    else:
        return {
            'process': text,
            'pid': '1'
        }


def extract_metadata_from_linux_log(log_line):
    # Define regex pattern to extract metadata
    pattern = (
        r'(?P<timestamp>\w+ \s*\d+ \d+:\d+:\d+) '
        r'(?P<level>\w+) '  # level
        r'(?P<text>.*)'  # Text of the log message
    )

    match = re.match(pattern, log_line)

    if match:
        # Extract groups with defaults if not found
        timestamp = match.group('timestamp') or 'unknown'
        level = match.group('level') or 'unknown'
        text = match.group('text') or 'unknown'
        text = text.split(':')
        proc_info = extract_process_info(text[0])
        timestamp = datetime.strptime(timestamp, '%b %d %H:%M:%S')
        timestamp = timestamp.replace(year = datetime.now().year)
        metadata = {
            'timestamp': int(timestamp.timestamp()),
            'level': level,
            'process': proc_info['process'],
            'pid': proc_info['pid'],
        }

        return metadata, text[1]
    else:
        return None, None

class LLMIndex:
    def __init__(self):
        client = EphemeralClient()
        self.collection = client.create_collection("logcat")
        # self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')
        self.model = OpenAI()
        self.ids = 0

    def _get_embedding(self, text):
        # return self.model.encode(text).tolist()
        return self.model.embeddings.create(input = [text], model="text-embedding-3-small").data[0].embedding
    
    def load_users(self, file_path):
        with open(file_path, 'r') as file:
            self.users = file.read()

    def get_android_users(self):
        return self.users
    
    def get_linux_users(self):
        with open("/etc/passwd", "r") as file:
            return file.read()

    def _index_logcat(self, uid, start_date, end_date, file_name, file_content):
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        print(f"Index logcat file {file_name} for uid: {uid} with start date: {start_timestamp} and end date: {end_timestamp}")

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_text(file_content)

        for chunk in chunks:
            embedding = self._get_embedding(chunk)
            self.collection.add(
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{"start_timestamp": start_timestamp, "end_timestamp": end_timestamp,  "user_id": uid}],
                ids=[str(self.ids)]
            )
            self.ids = self.ids + 1

    def load_logcat(self, logcat_dir):
        entries = os.listdir(logcat_dir)
        files = [entry for entry in entries if os.path.isfile(os.path.join(logcat_dir, entry))]
        for file in files:
            file_path = os.path.join(logcat_dir, file)
            if not file_path.endswith(".logcat"):
                continue
            start_date, end_date = extract_dates_from_logcat(file_path)
            uid = file.split("_")[0]
            with open(file_path, 'r') as f:
                self._index_logcat(uid, start_date, end_date, file, f.read())
    
    def query_logcat(self, uid, start_date, end_date, query):
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        print(f"Query logcat uid: {uid} start_date: {start_timestamp} end_date: {end_timestamp} query: {query}")
        embedding = self._get_embedding(query)

        results = self.collection.query(
            query_embeddings=[embedding],
            where={"$and": [{"start_timestamp": {"$gt": start_timestamp}}, {"end_timestamp": {"$lt": end_timestamp}}, {"user_id": uid}]}
            # where={"user_id": uid}
        )
        
        if len(results['documents']) == 0 or len(results['documents'][0]) == 0:
            return f"There are no logcat entries for user with ID {uid} at the specified time interval. Please tell human that you don't know the answer."

        result = results['documents'][0][0]
        print(f"Query logcat result: {result}")

        return result

    def load_linux_log(self, linux_log_dir):
        entries = os.listdir(linux_log_dir)
        files = [entry for entry in entries if os.path.isfile(os.path.join(linux_log_dir, entry))]
        for file in files:
            file_path = os.path.join(linux_log_dir, file)
            with open(file_path, 'r') as fd:
                for line in fd:
                    metadata, log = extract_metadata_from_linux_log(file)
                    if metadata is None:
                        continue
                    embedding = self._get_embedding(log)
                    #print("Adding:", metadata, ids, log)
                    self.collection.add(
                        documents=[log],
                        embeddings=[embedding],
                        metadatas=[metadata],
                        ids=[str(self.ids)]
                    )
                    self.ids = self.ids + 1
