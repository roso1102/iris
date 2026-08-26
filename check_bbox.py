import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {'projectId': 'stitch-dev-3'})
db = firestore.client()

chunks_ref = db.collection('tenants').document('default').collection('documents').document('doc_006').collection('chunks')
docs = chunks_ref.where('page_number', '==', 7).get()

for doc in docs:
    data = doc.to_dict()
    text = data.get('text', '')[:100].replace('\n', ' ')
    print(f"Chunk ID: {doc.id}")
    print(f"Text preview: {text}")
    print(f"Bbox: {data.get('bbox')}")
    print('---')
