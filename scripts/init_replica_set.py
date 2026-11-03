"""Turns a local mongod started with --replSet rs0 into a one-node replica set. Safe to re-run."""
import sys

from pymongo import MongoClient
from pymongo.errors import OperationFailure

host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:27017"
client = MongoClient(f"mongodb://{host}/?directConnection=true", serverSelectionTimeoutMS=3000)
try:
    client.admin.command("replSetInitiate", {"_id": "rs0", "members": [{"_id": 0, "host": host}]})
    print("replica set rs0 created")
except OperationFailure as err:
    if err.code == 23:  # AlreadyInitialized
        print("replica set already exists")
    elif err.code == 76:  # NoReplicationEnabled
        sys.exit("mongod is not running with --replSet rs0. See the setup section of README.md.")
    else:
        raise
