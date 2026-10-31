# LinkedIn caption and recording plan

## Caption draft

Organisations have more documentation than time to search it. For my seKer AI internship project, I built **Quillseek**, a document search application that retrieves passages by meaning and shows the source pages behind its results.

The system ingests PDF, DOCX, and TXT documents, indexes them locally with MiniLM embeddings and ChromaDB, and exposes search and question-answering through a FastAPI backend and Gradio interface. For answer generation, Gemini receives the question and retrieved passages and returns a cited response when the evidence supports one.

I learned how document extraction, chunking, vector retrieval, source metadata, API design, and honest evaluation fit together. The current evaluation shows why ranking metrics need careful labels: matching a document page does not always mean the retrieved chunk contains the answer. Next I would validate answer grounding with live Gemini usage, improve chunk-level relevance labels, and complete browser screenshots and responsive checks.

Project: Quillseek — AI-powered document intelligence and semantic search.

#seKerAI #SemanticSearch #RAG #Python #MachineLearning

## Recording script (about 3 minutes)

| Time | What to show | Narration cue |
|---|---|---|
| 0:00–0:15 | **UI:** open Quillseek and show the Documents tab | “This is Quillseek, a local-first document search demo.” |
| 0:15–0:35 | **Upload:** choose a small sample PDF, DOCX, or TXT | “The app accepts common office and text formats.” |
| 0:35–0:55 | **Indexing:** start indexing and show the progress/status | “The backend extracts text, chunks it, embeds it, and stores it locally.” |
| 0:55–1:20 | **Semantic search:** enter a query and show ranked results with similarity scores | “Search is based on meaning and returns source pages.” |
| 1:20–1:40 | **Natural-language question:** ask a question grounded in the sample document | “The question goes through the same embedding model as the indexed text.” |
| 1:40–2:00 | **Retrieved context:** expand the source cards and show passages/pages | “These are the passages the answer is allowed to use.” |
| 2:00–2:30 | **AI answer:** show the answer card after a successful Gemini response | “Gemini generates a concise response from the supplied context.” |
| 2:30–2:45 | **Sources:** highlight labels and document/page citations | “The source labels map back to retrieved passages.” |
| 2:45–3:00 | Close on project name and one evaluation limitation | “I also measured retrieval and documented where page-level relevance can mislead.” |

Record answer and source scenes only after a working Gemini key/quota is available. Use public sample documents and avoid showing API keys, `.env`, or private material.
