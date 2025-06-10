# import streamlit as st
# import os
# import json
# from pathlib import Path
# from datetime import datetime
# from typing import Dict, List

# # Import the PDFParserSystem from the main script
# from llama_parse import LlamaParse
# from llama_index.core import Document, VectorStoreIndex, Settings, load_index_from_storage
# from llama_index.core.storage.storage_context import StorageContext
# from llama_index.embeddings.openai import OpenAIEmbedding
# from llama_index.llms.openai import OpenAI
# from llama_index.core.prompts import PromptTemplate

# class StreamlitPDFChatbot:
#     """
#     Streamlit chatbot interface for querying parsed PDF documents
#     """
    
#     def __init__(self, 
#                  llama_api_key: str,
#                  openai_api_key: str,
#                  index_dir: str = "./vector_index"):
#         """
#         Initialize the chatbot
        
#         Args:
#             llama_api_key: Your LlamaCloud API key
#             openai_api_key: Your OpenAI API key
#             index_dir: Directory containing the vector index
#         """
#         self.llama_api_key = llama_api_key
#         self.index_dir = Path(index_dir)
        
#         # Set up LlamaIndex settings
#         Settings.embed_model = OpenAIEmbedding(api_key= st.secrets["OPENAI_API_KEY"])
#         Settings.llm = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        
#         self.index = None
#         self.parsed_files_log = self.index_dir / "parsed_files.json"
        
#     def load_vector_index(self) -> bool:
#         """
#         Load the existing vector index - FIXED VERSION
        
#         Returns:
#             True if index was loaded successfully, False otherwise
#         """
#         try:
#             if not self.index_dir.exists():
#                 return False
            
#             # Check if minimum required files exist
#             required_files = [
#                 self.index_dir / "docstore.json",
#                 self.index_dir / "index_store.json"
#             ]
            
#             # Vector store file might have different names in different versions
#             vector_store_files = [
#                 self.index_dir / "vector_store.json",
#                 self.index_dir / "default__vector_store.json",
#                 self.index_dir / "vector_index.json"
#             ]
            
#             vector_store_exists = any(f.exists() for f in vector_store_files)
            
#             if not all(f.exists() for f in required_files):
#                 st.error("Required index files not found")
#                 return False
            
#             if not vector_store_exists:
#                 st.error("⚠️ Vector store file missing - this will cause empty query responses")
#                 st.info("Available files: " + ", ".join([f.name for f in self.index_dir.iterdir() if f.is_file()]))
#                 return False
            
#             # Load the storage context and index
#             storage_context = StorageContext.from_defaults(persist_dir=str(self.index_dir))
            
#             # CRITICAL FIX: Use load_index_from_storage instead of from_documents
#             self.index = load_index_from_storage(storage_context)
            
#             return True
            
#         except Exception as e:
#             st.error(f"Error loading index: {str(e)}")
#             return False
    
#     def get_document_summary(self) -> Dict:
#         """
#         Get summary of parsed documents
        
#         Returns:
#             Dictionary with document statistics
#         """
#         if not self.parsed_files_log.exists():
#             return {"message": "No documents found"}
        
#         try:
#             with open(self.parsed_files_log, 'r') as f:
#                 history = json.load(f)
            
#             if not history.get("parsed_files", []):
#                 return {"message": "No documents parsed yet"}
            
#             file_names = [Path(f).name for f in history["parsed_files"]]
            
#             return {
#                 "total_files": len(history["parsed_files"]),
#                 "parse_sessions": len(history.get("parse_sessions", [])),
#                 "files": file_names,
#                 "last_updated": history.get("parse_sessions", [{}])[-1].get("timestamp", "Unknown") if history.get("parse_sessions") else "Unknown"
#             }
#         except Exception as e:
#             return {"message": f"Error reading document summary: {str(e)}"}
    
#     def query_documents(self, question: str, similarity_top_k: int = 5) -> str:
#         """
#         Query the parsed documents - IMPROVED VERSION
        
#         Args:
#             question: The question to ask
#             similarity_top_k: Number of similar chunks to retrieve
            
#         Returns:
#             Answer string
#         """
#         if not self.index:
#             if not self.load_vector_index():
#                 return "❌ No vector index found. Please run the PDF parser first to create an index."
        
#         try:
            
#             # Debug: Check if retriever returns results
#             retriever = self.index.as_retriever(similarity_top_k=similarity_top_k)
#             retrieved_nodes = retriever.retrieve(question)
            
#             if not retrieved_nodes:
#                 return "❌ No relevant documents found. The index might be empty or the query didn't match any content."
            
#             # Show number of relevant chunks found
#             # st.info(f"🔍 Found {len(retrieved_nodes)} relevant document chunks")
            
#             custom_prompt = PromptTemplate(
#                 "Context information is provided below.\n"
#                 "---------------------\n"
#                 "{context_str}\n"
#                 "---------------------\n"
#                 "Using only the context above (no outside knowledge), answer the query in the following structured format:\n\n"
#                 "**🔍 Answer:**\n"
#                 "- [Provide a concise, direct answer in one line. Use a bullet if applicable.]\n\n"
#                 "**📌 Explanation:**\n"
#                 "- Use 2–3 brief bullet points explaining how the answer was derived.\n"
#                 "- Refer to key terms, properties, or section numbers if available.\n\n"
#                 "**📊 Table (if applicable):**\n"
#                 "IMPORTANT: If creating a table, use proper markdown table format with pipes (|) and ensure:\n"
#                 "- Header row with column names\n"
#                 "- Separator row with dashes\n"
#                 "- Data rows with consistent column alignment\n"
#                 "- No extra spaces or formatting issues\n\n"
#                 "Example table format:\n"
#                 "| Property | Value | Unit/Notes |\n"
#                 "|----------|-------|-----------|\n"
#                 "| Tensile Strength | 3000 | psi (minimum per ASTM D-412) |\n"
#                 "| Hardness | 90±5 | Durometer A (ASTM D-2240) |\n\n"
#                 "*If no table is needed, you may omit this section.*\n\n"
#                 "Query: {query_str}\n"
#                 "Answer:"
#             )
            
            
#             query_engine = self.index.as_query_engine(similarity_top_k=similarity_top_k,text_qa_template=custom_prompt)
#             response = query_engine.query(question)
            
            
#             response = query_engine.query(question)
            
#             if not response or str(response).strip() == "":
#                 return "❌ Empty response generated. This might indicate an issue with the LLM or query processing."
            
#             return str(response)
            
#         except Exception as e:
#             return f"❌ Error querying documents: {str(e)}"

# def main():
#     """
#     Main Streamlit application
#     """
#     st.set_page_config(
#         page_title="Material Specifications Insights",
#         page_icon="📚",
#         layout="centered"
#     )
    
#     # Configuration - Set your API keys here
#     LLAMA_API_KEY = st.secrets["LLAMA_API_KEY"]
#     OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]  # Make sure to set this environment variable
#     SIMILARITY_TOP_K = 5  # Number of relevant chunks to retrieve
    
#     # Custom CSS for better appearance
#     st.markdown("""
#     <style>
#     .main-header {
#         font-size: 2.5rem;
#         color: #1f77b4;
#         text-align: center;
#         margin-bottom: 1rem;
#     }
#     .subtitle {
#         text-align: center;
#         color: #666;
#         margin-bottom: 2rem;
#     }
#     .status-info {
#         background-color: #f8f9fa;
#         padding: 1rem;
#         border-radius: 8px;
#         margin: 1rem 0;
#         text-align: center;
#         border: 1px solid #e9ecef;
#     }
#     </style>
#     """, unsafe_allow_html=True)
    
#     # Header
#     st.markdown('<h1 class="main-header">Material Specifications Insights</h1>', unsafe_allow_html=True)
#     st.markdown('<p class="subtitle">Ask questions about your material specific documents</p>', unsafe_allow_html=True)
    
#     # Check API keys
#     if not OPENAI_API_KEY:
#         st.error("⚠️ OpenAI API key not found! Please set the OPENAI_API_KEY environment variable.")
#         st.info("""
#         **To set your OpenAI API key:**
#         - Windows: `set OPENAI_API_KEY=your_key_here`
#         - Mac/Linux: `export OPENAI_API_KEY=your_key_here`
#         - Or add it to your .env file
#         """)
#         return
    
#     # Initialize chatbot
#     if "chatbot" not in st.session_state:
#         st.session_state.chatbot = StreamlitPDFChatbot(
#             llama_api_key=LLAMA_API_KEY,
#             openai_api_key=OPENAI_API_KEY
#         )
    
#     # Initialize index status check (without displaying status)
#     if "index_status_checked" not in st.session_state:
#         st.session_state.index_status_checked = False
#         st.session_state.index_loaded = st.session_state.chatbot.load_vector_index()
    
#     # Initialize chat history
#     if "messages" not in st.session_state:
#         st.session_state.messages = [
#             {"role": "assistant", "content": "Hello! I'm here to help you explore your PDF documents. What would you like to know?"}
#         ]
    
#     # Display chat history
#     for message in st.session_state.messages:
#         with st.chat_message(message["role"]):
#             st.markdown(message["content"])
    
#     # Chat input - only enable if index is loaded
#     if st.session_state.index_loaded:
#         if prompt := st.chat_input("Ask me anything about your documents..."):
#             # Add user message to chat history
#             st.session_state.messages.append({"role": "user", "content": prompt})
#             with st.chat_message("user"):
#                 st.markdown(prompt)
            
#             # Generate and display assistant response
#             with st.chat_message("assistant"):
#                 with st.spinner("Searching through your documents..."):
#                     response = st.session_state.chatbot.query_documents(
#                         prompt, 
#                         similarity_top_k=SIMILARITY_TOP_K
#                     )
#                 st.markdown(response)
            
#             # Add assistant response to chat history
#             st.session_state.messages.append({"role": "assistant", "content": response})
#     else:
#         st.text_input("Ask me anything about your documents...", 
#                      disabled=True, 
#                      placeholder="Please fix the index issues above before querying")
    
#     # # Footer with instructions
#     # st.divider()
#     # st.markdown("""
#     # <div style="text-align: center; color: #666; font-size: 0.9rem; margin-top: 2rem;">
#     #     <strong>💡 How to use:</strong><br>
#     #     • Ask specific questions about your documents<br>
#     #     • Try asking for summaries, key points, or specific information<br>
#     #     • To add more documents, run the PDF parser script<br>
#     #     • Make sure your OpenAI API key is set as an environment variable
#     # </div>
#     # """, unsafe_allow_html=True)

# if __name__ == "__main__":
#     main()


import streamlit as st
import os
import json
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Import the PDFParserSystem from the main script
from llama_parse import LlamaParse
from llama_index.core import Document, VectorStoreIndex, Settings, load_index_from_storage
from llama_index.core.storage.storage_context import StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

class StreamlitPDFChatbot:
    """
    Streamlit chatbot interface for querying parsed PDF documents with enhanced table generation
    """
    
    def __init__(self, 
                 llama_api_key: str,
                 openai_api_key: str,
                 index_dir: str = "./vector_index"):
        """
        Initialize the chatbot
        """
        self.llama_api_key = llama_api_key
        self.index_dir = Path(index_dir)
        
        # Set up LlamaIndex settings with more explicit configuration
        Settings.embed_model = OpenAIEmbedding(api_key=openai_api_key)
        Settings.llm = OpenAI(
            api_key=openai_api_key,
            model="gpt-4",  # Using GPT-4 for better table generation
            temperature=0.1,  # Lower temperature for more consistent formatting
            max_tokens=1500   # Ensure enough tokens for complete responses
        )
        
        self.index = None
        self.parsed_files_log = self.index_dir / "parsed_files.json"
    
    def load_vector_index(self) -> bool:
        """Load the existing vector index"""
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
                st.error("⚠️ Vector store file missing")
                return False
            
            # Load the storage context and index
            storage_context = StorageContext.from_defaults(persist_dir=str(self.index_dir))
            self.index = load_index_from_storage(storage_context)
            
            return True
            
        except Exception as e:
            st.error(f"Error loading index: {str(e)}")
            return False
    
    def create_enhanced_table_prompt(self, query_type: str = "general") -> str:
        """
        Create different prompt templates based on query type
        """
        if "specification" in query_type.lower() or "properties" in query_type.lower() or "table" in query_type.lower():
            return """Context information is provided below.
            ---------------------
            {context_str}
            ---------------------
            
            CRITICAL INSTRUCTIONS FOR TABLE GENERATION:
            - If the context contains tabular data, specifications, or properties, you MUST format them as a markdown table
            - Use this EXACT format with proper spacing and alignment:
            
            | Property | Value | Unit/Standard |
            |----------|-------|---------------|
            | Tensile Strength | 3500 | psi |
            | Hardness | 85±5 | Durometer A |
            
            RESPONSE FORMAT:
            **🔍 Answer:**
            - [Provide a concise, direct answer in one line. Use a bullet if applicable.]
            
            **📊 Table:**
            [MANDATORY: Create table if ANY numerical data, properties, or specifications are mentioned]
            
            **📌 Additional Notes:**
            - Use 2–3 brief bullet points explaining how the answer was derived.
            - Refer to key terms, properties, or section numbers if available.
            
            Query: {query_str}
            
            Remember: 
            - Always create tables for specifications, properties, or numerical data
            - Use consistent pipe (|) alignment 
            - Include units and standards where available
            - Don't skip the table even if data seems incomplete
            
            Answer:"""
        else:
            return """Context information is provided below.
            ---------------------
            {context_str}
            ---------------------
            
            Using the context above, provide a comprehensive answer to the query.
            If the context contains any specifications, properties, measurements, or tabular data, format them as a markdown table using this structure:
            
            | Property | Value | Notes |
            |----------|-------|-------|
            | [Property Name] | [Value] | [Unit/Standard] |
            
            Query: {query_str}
            Answer:"""
    
    def query_documents_with_debug(self, question: str, similarity_top_k: int = 5) -> tuple:
        """
        Query documents with debugging capabilities
        
        Returns:
            tuple: (response_text, raw_response, retrieved_context)
        """
        if not self.index:
            if not self.load_vector_index():
                return "❌ No vector index found.", None, None
        
        try:
            # Get retrieved context
            retriever = self.index.as_retriever(similarity_top_k=similarity_top_k)
            retrieved_nodes = retriever.retrieve(question)
            
            if not retrieved_nodes:
                return "❌ No relevant documents found.", None, None
            
            # Determine query type for appropriate prompting
            query_type = "specification" if any(word in question.lower() for word in 
                                             ["specification", "properties", "table", "values", "data", "compare"]) else "general"
            
            from llama_index.core.prompts import PromptTemplate
            
            # Use enhanced prompt based on query type
            custom_prompt = PromptTemplate(self.create_enhanced_table_prompt(query_type))
            
            # Create query engine with custom prompt
            query_engine = self.index.as_query_engine(
                similarity_top_k=similarity_top_k,
                text_qa_template=custom_prompt,
                response_mode="compact"  # This can help with more structured responses
            )
            
            # Get response
            response = query_engine.query(question)
            response_text = str(response)
            
            # Debug information
            context_info = {
                'retrieved_chunks': len(retrieved_nodes),
                'query_type': query_type,
                'chunks_preview': [node.text[:200] + "..." for node in retrieved_nodes[:2]]
            }
            
            return response_text, response, context_info
            
        except Exception as e:
            return f"❌ Error querying documents: {str(e)}", None, None
    
    def extract_and_display_tables(self, response_text: str) -> str:
        """Extract and format tables from response"""
        # Look for markdown table patterns
        table_pattern = r'\|[^\n]*\|(?:\n\|[^\n]*\|)+'
        tables = re.findall(table_pattern, response_text, re.MULTILINE)
        
        if not tables:
            return response_text
        
        modified_response = response_text
        
        for i, table_match in enumerate(tables):
            try:
                lines = [line.strip() for line in table_match.split('\n') if line.strip()]
                
                if len(lines) < 2:
                    continue
                
                # Parse header
                headers = [cell.strip() for cell in lines[0].split('|') if cell.strip()]
                
                # Find data rows (skip separator lines with dashes)
                data_rows = []
                for line in lines[1:]:
                    if not re.match(r'^[\|\-\s]+$', line):  # Skip separator lines
                        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                        if len(cells) == len(headers):
                            data_rows.append(cells)
                
                if data_rows and headers:
                    # Create DataFrame
                    df = pd.DataFrame(data_rows, columns=headers)
                    
                    # Replace with placeholder
                    placeholder = f"[TABLE_{i}]"
                    modified_response = modified_response.replace(table_match, placeholder)
                    
                    # Store for display
                    if not hasattr(st.session_state, 'current_tables'):
                        st.session_state.current_tables = {}
                    st.session_state.current_tables[placeholder] = df
                    
            except Exception as e:
                st.warning(f"Table parsing error: {str(e)}")
        
        return modified_response
    
    def display_response_with_tables(self, response_text: str):
        """Display response with proper table formatting"""
        # Check for table placeholders
        table_placeholders = re.findall(r'\[TABLE_\d+\]', response_text)
        
        if not table_placeholders:
            st.markdown(response_text)
            return
        
        # Display parts with tables
        parts = re.split(r'\[TABLE_\d+\]', response_text)
        
        for i, part in enumerate(parts):
            if part.strip():
                st.markdown(part)
            
            if i < len(table_placeholders):
                placeholder = table_placeholders[i]
                if hasattr(st.session_state, 'current_tables') and placeholder in st.session_state.current_tables:
                    df = st.session_state.current_tables[placeholder]
                    st.dataframe(df, use_container_width=True)

def main():
    """Main Streamlit application"""
    
    st.set_page_config(
        page_title="Material Specifications Insights",
        page_icon="📚",
        layout="centered"
    )
    
    # Configuration
    LLAMA_API_KEY = "llx-s1tvfbKSb68NQ6ZDXhDZunJeWzFDYkk65M5gK0x4pSbd2FBJ"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
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
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">Material Specifications Insights</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Ask questions about your material specific documents</p>', unsafe_allow_html=True)
    
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
            openai_api_key=OPENAI_API_KEY
        )
    
    # Load index
    if "index_loaded" not in st.session_state:
        st.session_state.index_loaded = st.session_state.chatbot.load_vector_index()
    
    if not st.session_state.index_loaded:
        st.error("❌ Vector index not loaded. Please check your index files.")
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm here to help you explore your PDF documents. What would you like to know?"}
        ]
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                processed_response = st.session_state.chatbot.extract_and_display_tables(message["content"])
                st.session_state.chatbot.display_response_with_tables(processed_response)
            else:
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your documents..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching through your documents..."):
                response_text, raw_response, context_info = st.session_state.chatbot.query_documents_with_debug(
                    prompt, 
                    similarity_top_k=5
                )
            
            # Process and display response
            if hasattr(st.session_state, 'current_tables'):
                st.session_state.current_tables = {}
            
            processed_response = st.session_state.chatbot.extract_and_display_tables(response_text)
            st.session_state.chatbot.display_response_with_tables(processed_response)
        
        # Add to chat history
        st.session_state.messages.append({"role": "assistant", "content": response_text})

if __name__ == "__main__":
    main()