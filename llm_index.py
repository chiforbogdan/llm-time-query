import os
import re
from datetime import datetime
from datetime import datetime
from chromadb import EphemeralClient
from sentence_transformers import SentenceTransformer

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

class LLMIndex:
    def __init__(self):
        client = EphemeralClient()
        self.collection = client.create_collection("logcat")
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')

    def _get_embedding(self, text):
        return self.model.encode(text).tolist()
    
    def load_users(self, file_path):
        with open(file_path, 'r') as file:
            self.users = file.read()

    def get_users(self):
        return self.users

    def _index_logcat(self, uid, start_date, end_date, file_name, file_content):
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        # TODO split into chunks
        embedding = self._get_embedding(file_content)
        self.collection.add(
            documents=[file_content],
            embeddings=[embedding],
            metadatas=[{"start_timestamp": start_timestamp, "end_timestamp": end_timestamp,  "user_id": uid}],
            ids=[file_name]
        )
        return

    def load_logcat(self, logcat_dir):
        entries = os.listdir(logcat_dir)
        files = [entry for entry in entries if os.path.isfile(os.path.join(logcat_dir, entry))]
        for file in files:
            file_path = os.path.join(logcat_dir, file)
            start_date, end_date = extract_dates_from_logcat(file_path)
            uid = file.split("_")[0]
            with open(file_path, 'r') as f:
                self._index_logcat(uid, start_date, end_date, file, f.read())
    
    def query_logcat(self, uid, start_date, end_date, query):
        start_timestamp = int(start_date.timestamp())
        end_timestamp = int(end_date.timestamp())
        embedding = self._get_embedding(query)

        results = self.collection.query(
            query_embeddings=[embedding],
            where={"$and": [{"start_timestamp": {"$gt": start_timestamp}}, {"end_timestamp": {"$lt": end_timestamp}}, {"user_id": uid}]}
        )

        return results['documents'][0][0]
            

