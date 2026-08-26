const { Firestore } = require('@google-cloud/firestore');
const firestore = new Firestore();

async function check() {
  const chunksRef = firestore.collection('tenants').doc('default').collection('documents').doc('doc_006').collection('chunks');
  const snapshot = await chunksRef.where('page_number', '==', 7).get();
  snapshot.forEach(doc => {
    const data = doc.data();
    console.log(`Chunk ID: ${doc.id}`);
    console.log(`Text preview: ${data.text.substring(0, 100).replace(/\n/g, ' ')}`);
    console.log(`Bbox: ${JSON.stringify(data.bbox)}`);
    console.log('---');
  });
}
check().catch(console.error);
