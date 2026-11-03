"""Creates the four MongoDB collections, their validators and indexes. Safe to re-run."""
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid

VALIDATORS = {
    "shopping_carts": {"bsonType": "object", "required": ["userId", "items"], "properties": {
        "userId": {"bsonType": "int"},
        "items": {"bsonType": "array", "items": {
            "bsonType": "object", "required": ["productId", "quantity", "price"],
            "properties": {"quantity": {"bsonType": "int", "minimum": 1}}}}}},
    "product_reviews": {"bsonType": "object", "required": ["productId", "userId", "rating", "comment"],
                        "properties": {"rating": {"bsonType": "int", "minimum": 1, "maximum": 5}}},
    "user_notifications": {"bsonType": "object", "required": ["userId", "title", "message", "isRead"]},
    "user_activity_logs": {"bsonType": "object", "required": ["action_type", "timestamp"]},
}


def setup(db):
    for name, schema in VALIDATORS.items():
        try:
            db.create_collection(name, validator={"$jsonSchema": schema})
        except CollectionInvalid:
            db.command("collMod", name, validator={"$jsonSchema": schema})
    db.shopping_carts.create_index("userId", unique=True)
    db.product_reviews.create_index([("productId", ASCENDING), ("userId", ASCENDING)], unique=True)
    db.product_reviews.create_index([("productId", ASCENDING), ("createdAt", DESCENDING)])
    db.user_notifications.create_index([("userId", ASCENDING), ("sentAt", DESCENDING)])
    # Idempotency key: replaying an outbox event cannot notify the customer twice.
    db.user_notifications.create_index("eventKey", unique=True, sparse=True)
    db.user_activity_logs.create_index("eventKey", unique=True, sparse=True)
    db.user_activity_logs.create_index([("userId", ASCENDING), ("timestamp", DESCENDING)])
    # Telemetry is short-lived: MongoDB expires it automatically after 180 days.
    db.user_activity_logs.create_index("timestamp", expireAfterSeconds=180 * 24 * 3600)
