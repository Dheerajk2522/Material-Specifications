import streamlit as st
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Import the PDFParserSystem from the main script
from llama_parse import LlamaParse
from llama_index.core import Document, VectorStoreIndex, Settings, load_index_from_storage
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

class StreamlitPDFChatbot:
    """
    Streamlit chatbot interface for querying parsed PDF documents
    """
    
    def __init__(self, 
                 llama_api_key: str,
                 openai_api_key: str,
                 index_dir: str = "./vector_index"):
        """
        Initialize the chatbot
        
        Args:
            llama_api_key: Your LlamaCloud API key
            openai_api_key: Your OpenAI API key
            index_dir: Directory containing the vector index
        """
        self.llama_api_key = llama_api_key
        self.index_dir = Path(index_dir)
        
        # Set up LlamaIndex settings
        Settings.embed_model = OpenAIEmbedding(api_key= st.secrets["OPENAI_API_KEY"])
        Settings.llm = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        
        self.index = None
        self.parsed_files_log = self.index_dir / "parsed_files.json"
        
    def load_vector_index(self) -> bool:
        """
        Load the existing vector index - FIXED VERSION
        
        Returns:
            True if index was loaded successfully, False otherwise
        """
        try:
            if not self.index_dir.exists():
                return False
            
            # Check if minimum required files exist
            required_files = [
                self.index_dir / "docstore.json",
                self.index_dir / "index_store.json"
            ]
            
            # Vector store file might have different names in different versions
            vector_store_files = [
                self.index_dir / "vector_store.json",
                self.index_dir / "default__vector_store.json",
                self.index_dir / "vector_index.json"
            ]
            
            vector_store_exists = any(f.exists() for f in vector_store_files)
            
            if not all(f.exists() for f in required_files):
                st.error("Required index files not found")
                return False
            
            if not vector_store_exists:
                st.error("⚠️ Vector store file missing - this will cause empty query responses")
                st.info("Available files: " + ", ".join([f.name for f in self.index_dir.iterdir() if f.is_file()]))
                return False
            
            # Load the storage context and index
            storage_context = StorageContext.from_defaults(persist_dir=str(self.index_dir))
            
            # CRITICAL FIX: Use load_index_from_storage instead of from_documents
            self.index = load_index_from_storage(storage_context)
            
            return True
            
        except Exception as e:
            st.error(f"Error loading index: {str(e)}")
            return False
    
    def get_document_summary(self) -> Dict:
        """
        Get summary of parsed documents
        
        Returns:
            Dictionary with document statistics
        """
        if not self.parsed_files_log.exists():
            return {"message": "No documents found"}
        
        try:
            with open(self.parsed_files_log, 'r') as f:
                history = json.load(f)
            
            if not history.get("parsed_files", []):
                return {"message": "No documents parsed yet"}
            
            file_names = [Path(f).name for f in history["parsed_files"]]
            
            return {
                "total_files": len(history["parsed_files"]),
                "parse_sessions": len(history.get("parse_sessions", [])),
                "files": file_names,
                "last_updated": history.get("parse_sessions", [{}])[-1].get("timestamp", "Unknown") if history.get("parse_sessions") else "Unknown"
            }
        except Exception as e:
            return {"message": f"Error reading document summary: {str(e)}"}
    
    def query_documents(self, question: str, similarity_top_k: int = 5) -> str:
        """
        Query the parsed documents - IMPROVED VERSION
        
        Args:
            question: The question to ask
            similarity_top_k: Number of similar chunks to retrieve
            
        Returns:
            Answer string
        """
        if not self.index:
            if not self.load_vector_index():
                return "❌ No vector index found. Please run the PDF parser first to create an index."
        
        try:
            # Test if index has content
            query_engine = self.index.as_query_engine(similarity_top_k=similarity_top_k)
            
            # Debug: Check if retriever returns results
            retriever = self.index.as_retriever(similarity_top_k=similarity_top_k)
            retrieved_nodes = retriever.retrieve(question)
            
            if not retrieved_nodes:
                return "❌ No relevant documents found. The index might be empty or the query didn't match any content."
            
            # Show number of relevant chunks found
            # st.info(f"🔍 Found {len(retrieved_nodes)} relevant document chunks")
            
            response = query_engine.query(question)
            
            if not response or str(response).strip() == "":
                return "❌ Empty response generated. This might indicate an issue with the LLM or query processing."
            
            return str(response)
            
        except Exception as e:
            return f"❌ Error querying documents: {str(e)}"

def main():
    """
    Main Streamlit application
    """
    st.set_page_config(
        page_title="Material Specifications Insights",
        page_icon="📚",
        layout="centered"
    )
    
    # Configuration - Set your API keys here
    LLAMA_API_KEY = st.secrets["LLAMA_API_KEY"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]  # Make sure to set this environment variable
    SIMILARITY_TOP_K = 5  # Number of relevant chunks to retrieve
    
    # Custom CSS for better appearance
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .status-info {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">Material Specifications Insights</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Ask questions about your material specific documents</p>', unsafe_allow_html=True)
    
    # Check API keys
    if not OPENAI_API_KEY:
        st.error("⚠️ OpenAI API key not found! Please set the OPENAI_API_KEY environment variable.")
        st.info("""
        **To set your OpenAI API key:**
        - Windows: `set OPENAI_API_KEY=your_key_here`
        - Mac/Linux: `export OPENAI_API_KEY=your_key_here`
        - Or add it to your .env file
        """)
        return
    
    # Initialize chatbot
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = StreamlitPDFChatbot(
            llama_api_key=LLAMA_API_KEY,
            OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
        )
    
    # Initialize index status check (without displaying status)
    if "index_status_checked" not in st.session_state:
        st.session_state.index_status_checked = False
        st.session_state.index_loaded = st.session_state.chatbot.load_vector_index()
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm here to help you explore your PDF documents. What would you like to know?"}
        ]
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input - only enable if index is loaded
    if st.session_state.index_loaded:
        if prompt := st.chat_input("Ask me anything about your documents..."):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate and display assistant response
            with st.chat_message("assistant"):
                with st.spinner("Searching through your documents..."):
                    response = st.session_state.chatbot.query_documents(
                        prompt, 
                        similarity_top_k=SIMILARITY_TOP_K
                    )
                st.markdown(response)
            
            # Add assistant response to chat history
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.text_input("Ask me anything about your documents...", 
                     disabled=True, 
                     placeholder="Please fix the index issues above before querying")
    
    # # Footer with instructions
    # st.divider()
    # st.markdown("""
    # <div style="text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;">
    #     <strong>💡 How to use:</strong><br>
    #     • Ask specific questions about your documents<br>
    #     • Try asking for summaries, key points, or specific information<br>
    #     • To add more documents, run the PDF parser script<br>
    #     • Make sure your OpenAI API key is set as an environment variable
    # </div>
    # """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()