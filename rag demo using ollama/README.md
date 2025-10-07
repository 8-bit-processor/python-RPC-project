# Medical Note RAG and Parser

This project is a Flask application that provides a RAG (Retrieval-Augmented Generation) pipeline for answering questions about medical notes. It also includes a GUI for parsing medical notes into a structured format.

## Features

*   **RAG Pipeline:** Ask questions about a collection of medical notes and get answers based on their content.
*   **Medical Note Parser:** Parse unstructured medical notes into a structured JSON format using a large language model (Ollama).
*   **Web Interface:** A simple web interface for interacting with the RAG pipeline.
*   **GUI:** A desktop GUI for parsing medical notes.

## How it Works

The application is composed of several components:

*   **Flask App (`app.py`):** The main web application that serves the web interface and provides an API for the RAG pipeline.
*   **RAG Pipeline (`rag_pipeline.py`):** This module is responsible for:
    *   Loading medical notes from a directory.
    *   Splitting the notes into smaller chunks.
    *   Generating embeddings for the chunks using a sentence transformer model.
    *   Storing the embeddings in a FAISS vector store.
    *   Setting up a RAG chain with an Ollama language model to answer questions.
*   **LLM Parser (`llm_parser.py`):** This module uses an Ollama language model to parse unstructured medical notes and extract information into a structured JSON format.
*   **GUI (`ollama_gui.py`):** A Tkinter-based GUI that allows users to paste a medical note and have it parsed by the LLM parser.

## Getting Started

### Prerequisites

*   Python 3.7+
*   Docker
*   Ollama

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```
2.  Install the Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Start the Ollama service:
    ```bash
    docker-compose up -d
    ```

### Running the Application

1.  **Run the Flask App:**
    ```bash
    python app.py
    ```
    This will start the web server on `http://localhost:3000`.

2.  **Run the GUI Parser:**
    ```bash
    python ollama_gui.py
    ```
    This will open the desktop GUI for parsing medical notes.

## Usage

### Web Interface

1.  Open your web browser and go to `http://localhost:3000`.
2.  Enter a question about the medical notes in the input box and click "Ask".
3.  The answer and the source documents used to generate it will be displayed.

### GUI Parser

1.  Run the `ollama_gui.py` script.
2.  Paste an unstructured medical note into the input text box.
3.  Click the "Parse Note with Ollama" button.
4.  The parsed information will be displayed in the corresponding fields.
