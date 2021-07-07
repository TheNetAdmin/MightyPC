from pymongo import MongoClient
import logging


def make_mongodb(dbcol: str):
    db, col = dbcol.split(":")
    return mongodb(db, col)


class mongodb:
    def __init__(self, database, collection):
        self.logger = logging.getLogger("mongo")
        # NOTE: fill with your MongoDB username, password and url
        #       if you are using Docker/mighty-pc.yaml to create MongoDB Docker
        #       you can find and set the default username and password in that file
        self.username = "your_mongodb_username"
        self.password = "your_mongodb_password"
        self.url = "your_mongodb_url:your_port"
        self.database = database
        self.collection = collection
        self.server = MongoClient(
            f"mongodb://{self.username}:{self.password}@{self.url}",
            serverSelectionTimeoutMS=2000,
        )
        self.server.server_info()
        self.client = self.server[database][collection]
