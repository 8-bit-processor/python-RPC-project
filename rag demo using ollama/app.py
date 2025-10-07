from flask import Flask, render_template, request, jsonify
import os
import threading
import time

from rag_pipeline import load_documents, split_documents, create_vector_store, setup_rag_chain

app = Flask(__name__)

# Global list to store engine events/logs
engine_events = []

def log_event(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    engine_events.append(f"[{timestamp}] {message}")
    print(f"[ENGINE EVENT] {message}") # Also print to console for debugging

# Global RAG components
qa_chain = None
vectorstore = None
embeddings = None

def initialize_rag_pipeline():
    global qa_chain, vectorstore, embeddings
    log_event("Initializing RAG pipeline...")
    try:
        current_directory = r"C:\Users\FreeP\Desktop\Old and New Natural language processing\NLP tools"
        
        log_event("Loading documents...")
        documents = load_documents(current_directory)
        log_event(f"Loaded {len(documents)} documents.")

        log_event("Splitting documents...")
        texts = split_documents(documents)
        log_event(f"Split into {len(texts)} chunks.")

        log_event("Creating vector store...")
        vectorstore, embeddings = create_vector_store(texts)
        log_event("Vector store created.")

        log_event("Setting up RAG chain...")
        qa_chain = setup_rag_chain(vectorstore)
        log_event("RAG chain ready.")
        log_event("RAG pipeline initialization complete.")
    except Exception as e:
        log_event(f"Error during RAG pipeline initialization: {e}")

# Start RAG pipeline initialization in a separate thread
rag_thread = threading.Thread(target=initialize_rag_pipeline)
rag_thread.daemon = True
rag_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    user_query = request.json.get('query')
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400

    log_event(f"Received query: {user_query}")
    if qa_chain is None:
        log_event("RAG pipeline not yet initialized. Please wait.")
        return jsonify({'answer': 'RAG pipeline is still initializing. Please try again in a moment.'}), 202

    try:
        result = qa_chain.invoke({"query": user_query})
        answer = result["result"]
        source_documents = result["source_documents"]
        
        log_event(f"Answered query: {user_query}")
        return jsonify({
            'answer': answer,
            'source_documents': [{'source': os.path.basename(doc.metadata['source']), 'content': doc.page_content} for doc in source_documents]
        })
    except Exception as e:
        log_event(f"Error processing query: {e}")
        return jsonify({'error': f'Error processing query: {e}'}), 500

@app.route('/events')
def get_events():
    return jsonify({'events': engine_events})

if __name__ == '__main__':
    # Create a 'templates' directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(host='0.0.0.0', port=3000, debug=True)