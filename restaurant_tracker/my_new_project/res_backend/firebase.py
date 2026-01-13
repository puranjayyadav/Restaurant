import firebase_admin
from firebase_admin import credentials, firestore

# Path to your service account key JSON file
SERVICE_ACCOUNT_PATH = '../creds/restaurant-47dab-firebase-adminsdk-fbsvc-a2225a7d82.json'

# Initialize Firebase app (if not already initialized)
if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred)

# Get a Firestore client
db = firestore.client()

# Now you can use "db" to interact with your Cloud Firestore
# Example data to push to Firestore.
