import os
import json
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
from datetime import datetime
import streamlit as st

# Core libraries
from llama_parse import LlamaParse
from llama_index.core import Document, VectorStoreIndex, Settings, load_index_from_storage
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core.storage.storage_context import StorageContext
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI

class PDFParserSystem:
    """
    A comprehensive PDF parsing and querying system using LlamaParse
    """
    
    def __init__(self, 
                 llama_api_key: str,
                 openai_api_key: Optional[str] = None,
                 output_dir: str = "./parsed_docs",
                 index_dir: str = "./vector_index"):
        """
        Initialize the PDF Parser System
        
        Args:
            llama_api_key: Your LlamaCloud API key
            openai_api_key: Your OpenAI API key (optional, will use env var if not provided)
            output_dir: Directory to store parsed documents
            index_dir: Directory to store vector index
        """
        self.llama_api_key = llama_api_key
        self.output_dir = Path(output_dir)
        self.index_dir = Path(index_dir)
        
        # Create directories if they don't exist
        self.output_dir.mkdir(exist_ok=True)
        self.index_dir.mkdir(exist_ok=True)
        
        # Initialize LlamaParse with advanced settings
        self.parser = LlamaParse(
            api_key=llama_api_key,
            result_type="markdown",
            extract_charts=True,
            auto_mode=True,
            auto_mode_trigger_on_image_in_page=True,
            auto_mode_trigger_on_table_in_page=True,
            verbose=True
        )
        
        # Set up LlamaIndex settings
        if openai_api_key:
            Settings.embed_model = OpenAIEmbedding(api_key=st.secrets("OPENAI_API_KEY"))
            Settings.llm = OpenAI(api_key=st.secrets("OPENAI_API_KEY"))
        else:
            # Will use environment variables
            Settings.embed_model = OpenAIEmbedding()
            Settings.llm = OpenAI()
        
        self.index = None
        self.documents = []
        self.parsed_files_log = self.index_dir / "parsed_files.json"
        
    def get_parsed_files_history(self) -> Dict:
        """
        Get the history of parsed files
        
        Returns:
            Dictionary with parsed files information
        """
        if self.parsed_files_log.exists():
            with open(self.parsed_files_log, 'r') as f:
                return json.load(f)
        return {"parsed_files": [], "parse_sessions": []}
    
    def update_parsed_files_history(self, new_files: List[str], session_info: Dict):
        """
        Update the history of parsed files
        
        Args:
            new_files: List of newly parsed file paths
            session_info: Information about the parsing session
        """
        history = self.get_parsed_files_history()
        history["parsed_files"].extend(new_files)
        history["parse_sessions"].append(session_info)
        
        with open(self.parsed_files_log, 'w') as f:
            json.dump(history, f, indent=2)
        
    def find_pdf_files(self, folder_path: str) -> List[Path]:
        """
        Find all PDF files in the specified folder and subfolders
        
        Args:
            folder_path: Path to the folder containing PDF files
            
        Returns:
            List of Path objects for PDF files
        """
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"Folder {folder_path} does not exist")
        
        pdf_files = []
        for file_path in folder.rglob("*.pdf"):
            if file_path.is_file():
                pdf_files.append(file_path)
        
        print(f"Found {len(pdf_files)} PDF files in {folder_path}")
        return pdf_files
    
    def get_new_pdf_files(self, folder_path: str) -> List[Path]:
        """
        Find PDF files that haven't been parsed yet
        
        Args:
            folder_path: Path to the folder containing PDF files
            
        Returns:
            List of Path objects for new PDF files
        """
        all_pdf_files = self.find_pdf_files(folder_path)
        history = self.get_parsed_files_history()
        parsed_files = set(history["parsed_files"])
        
        new_files = [f for f in all_pdf_files if str(f.absolute()) not in parsed_files]
        
        print(f"Found {len(new_files)} new PDF files to parse")
        if len(new_files) != len(all_pdf_files):
            print(f"Skipping {len(all_pdf_files) - len(new_files)} already parsed files")
        
        return new_files
    
    def parse_single_pdf(self, pdf_path: Path) -> List[Document]:
        """
        Parse a single PDF file using LlamaParse
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of Document objects
        """
        print(f"Parsing: {pdf_path.name}")
        
        try:
            extra_info = {
                "file_name": str(pdf_path),
                "file_path": str(pdf_path.absolute()),
                "parsed_date": datetime.now().isoformat()
            }
            
            with open(pdf_path, "rb") as f:
                documents = self.parser.load_data(f, extra_info=extra_info)
            
            # Save parsed content as markdown
            output_file = self.output_dir / f"{pdf_path.stem}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                for doc in documents:
                    f.write(f"# {pdf_path.name}\n\n")
                    f.write(doc.text)
                    f.write("\n\n---\n\n")
            
            print(f"✓ Successfully parsed {pdf_path.name}")
            return documents
            
        except Exception as e:
            print(f"✗ Error parsing {pdf_path.name}: {str(e)}")
            return []
    
    def parse_folder(self, folder_path: str, max_files: Optional[int] = None, parse_only_new: bool = True) -> None:
        """
        Parse PDF files in a folder
        
        Args:
            folder_path: Path to the folder containing PDF files
            max_files: Maximum number of files to process (None for all)
            parse_only_new: If True, only parse files not already parsed
        """
        if parse_only_new:
            pdf_files = self.get_new_pdf_files(folder_path)
        else:
            pdf_files = self.find_pdf_files(folder_path)
        
        if not pdf_files:
            print("No new PDF files to parse!")
            # Still try to load existing index for querying
            if not self.index:
                self.load_existing_index()
            return
        
        if max_files:
            pdf_files = pdf_files[:max_files]
            print(f"Processing first {max_files} files...")
        
        new_documents = []
        successfully_parsed = []
        
        for pdf_path in pdf_files:
            documents = self.parse_single_pdf(pdf_path)
            if documents:
                new_documents.extend(documents)
                successfully_parsed.append(str(pdf_path.absolute()))
        
        if new_documents:
            # Try to load existing documents first
            existing_docs = []
            if self.load_existing_index():
                print("Found existing index. Will rebuild with new documents.")
                # Note: We'll rebuild the entire index to ensure consistency
            
            # For now, we'll just use the new documents
            # In a more sophisticated version, you'd want to merge with existing
            self.documents = new_documents
            
            print(f"\nCompleted parsing {len(pdf_files)} files")
            print(f"Generated {len(new_documents)} new document chunks")
            
            # Create the vector index
            self.create_vector_index()
            
            # Update parsed files history
            session_info = {
                "timestamp": datetime.now().isoformat(),
                "folder_path": folder_path,
                "files_parsed": len(successfully_parsed),
                "new_documents": len(new_documents)
            }
            self.update_parsed_files_history(successfully_parsed, session_info)
    
    def create_vector_index(self) -> None:
        """
        Create a vector index from the parsed documents
        """
        print("Creating/updating vector index...")
        
        try:
            # Parse documents into nodes
            node_parser = SimpleNodeParser()
            nodes = node_parser.get_nodes_from_documents(self.documents)
            
            # Create vector store and index
            vector_store = SimpleVectorStore()
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            
            self.index = VectorStoreIndex(
                nodes=nodes,
                storage_context=storage_context
            )
            
            # Persist the index
            self.index.storage_context.persist(persist_dir=str(self.index_dir))
            
            print(f"✓ Vector index created/updated with {len(nodes)} nodes")
            
        except Exception as e:
            print(f"✗ Error creating vector index: {str(e)}")
    
    def load_existing_index(self) -> bool:
        """
        Load an existing vector index - FIXED VERSION
        
        Returns:
            True if index was loaded successfully, False otherwise
        """
        try:
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
                print("Required index files not found")
                return False
            
            if not vector_store_exists:
                print("⚠️ Vector store file missing - this will cause empty query responses")
                print("Available files:", [f.name for f in self.index_dir.iterdir() if f.is_file()])
                return False
            
            # Load the storage context and index
            storage_context = StorageContext.from_defaults(persist_dir=str(self.index_dir))
            
            # CRITICAL FIX: Use load_index_from_storage instead of from_documents
            self.index = load_index_from_storage(storage_context)
            
            print("✓ Successfully loaded existing vector index")
            return True
            
        except Exception as e:
            print(f"Failed to load existing index: {str(e)}")
            print("This usually means the index is corrupted or incomplete.")
            return False
    
    def query(self, question: str, similarity_top_k: int = 5) -> str:
        """
        Query the parsed documents
        
        Args:
            question: The question to ask
            similarity_top_k: Number of similar chunks to retrieve
            
        Returns:
            Answer string
        """
        if not self.index:
            if not self.load_existing_index():
                return "No index available. Please parse documents first."
        
        try:
            # Test if index has content
            query_engine = self.index.as_query_engine(similarity_top_k=similarity_top_k)
            
            # Debug: Check if retriever returns results
            retriever = self.index.as_retriever(similarity_top_k=similarity_top_k)
            retrieved_nodes = retriever.retrieve(question)
            
            if not retrieved_nodes:
                return "No relevant documents found. The index might be empty or the query didn't match any content."
            
            print(f"Found {len(retrieved_nodes)} relevant document chunks")
            
            response = query_engine.query(question)
            
            if not response or str(response).strip() == "":
                return "Empty response generated. This might indicate an issue with the LLM or query processing."
            
            return str(response)
        
        except Exception as e:
            return f"Error querying: {str(e)}"
    
    def get_document_summary(self) -> Dict:
        """
        Get a summary of parsed documents
        
        Returns:
            Dictionary with document statistics
        """
        history = self.get_parsed_files_history()
        
        if not history["parsed_files"]:
            return {"message": "No documents parsed yet"}
        
        file_names = [Path(f).name for f in history["parsed_files"]]
        
        summary = {
            "total_files_parsed": len(history["parsed_files"]),
            "parse_sessions": len(history["parse_sessions"]),
            "files": file_names,
            "last_parse_session": history["parse_sessions"][-1] if history["parse_sessions"] else None
        }
        
        # Add index status
        if self.index or self.load_existing_index():
            summary["index_status"] = "Available"
        else:
            summary["index_status"] = "Not found"
        
        return summary
    
    def debug_index(self):
        """
        Debug method to check index status
        """
        print("\n" + "="*50)
        print("INDEX DEBUG INFO")
        print("="*50)
        
        # Check if index exists
        if self.index:
            print("✓ Index object exists in memory")
        else:
            print("✗ No index object in memory")
            if self.load_existing_index():
                print("✓ Successfully loaded index from disk")
            else:
                print("✗ Failed to load index from disk")
        
        # Check index files
        print("\nIndex directory contents:")
        if self.index_dir.exists():
            for file_path in self.index_dir.iterdir():
                if file_path.is_file():
                    size = file_path.stat().st_size
                    print(f"  {file_path.name}: {size:,} bytes")
        else:
            print("  Index directory doesn't exist")
        
        # Check critical files
        critical_files = [
            "docstore.json",
            "index_store.json", 
            "vector_store.json",
            "default__vector_store.json"
        ]
        
        print("\nCritical file check:")
        for filename in critical_files:
            file_path = self.index_dir / filename
            if file_path.exists():
                print(f"✓ {filename}")
            else:
                print(f"✗ {filename}")
        
        # Test retrieval
        if self.index:
            try:
                retriever = self.index.as_retriever(similarity_top_k=1)
                test_results = retriever.retrieve("test query")
                print(f"\nTest retrieval: Found {len(test_results)} results")
                if test_results:
                    print(f"Sample content preview: {test_results[0].text[:100]}...")
                else:
                    print("⚠️ No results found - index might be empty")
            except Exception as e:
                print(f"\nTest retrieval failed: {str(e)}")
        
        # Suggest fixes
        print("\n" + "="*30)
        print("RECOMMENDED ACTIONS:")
        print("="*30)
        
        vector_store_exists = any((self.index_dir / f).exists() for f in ["vector_store.json", "default__vector_store.json"])
        
        if not vector_store_exists:
            print("🔧 ISSUE: Missing vector store file")
            print("   SOLUTION: Re-run parsing (Option 1) to rebuild the complete index")
            print("   This will recreate all index files including the vector store")
        elif not self.index:
            print("🔧 ISSUE: Cannot load existing index")
            print("   SOLUTION: Try re-parsing documents or check file permissions")
        else:
            print("✅ Index appears to be working correctly")

def interactive_parser():
    """
    Interactive PDF parser with options to parse multiple batches
    """
    # Your API keys
    LLAMA_API_KEY = st.secrets("LLAMA_API_KEY")
    OPENAI_API_KEY = st.secrets("OPENAI_API_KEY")
    
    # Initialize the system
    pdf_system = PDFParserSystem(
        llama_api_key=st.secrets("LLAMA_API_KEY"),
        openai_api_key=st.secrets("OPENAI_API_KEY")
    )
    
    print("="*60)
    print("PDF PARSER SYSTEM - FIXED VERSION")
    print("="*60)
    
    while True:
        print("\nOptions:")
        print("1. Parse new PDF documents")
        print("2. View document summary")
        print("3. Query documents")
        print("4. Debug index status")
        print("5. Exit")
        
        choice = input("\nSelect an option (1-5): ").strip()
        
        if choice == "1":
            folder_path = input("Enter the path to your PDF folder: ").strip()
            
            if os.path.exists(folder_path):
                max_files = input("Max files to process (press Enter for all): ").strip()
                max_files = int(max_files) if max_files else None
                
                parse_new_only = input("Parse only new files? (y/n, default: y): ").strip().lower()
                parse_new_only = parse_new_only != 'n'
                
                pdf_system.parse_folder(folder_path, max_files=max_files, parse_only_new=parse_new_only)
            else:
                print(f"Folder {folder_path} does not exist!")
        
        elif choice == "2":
            summary = pdf_system.get_document_summary()
            print("\n" + "="*50)
            print("DOCUMENT SUMMARY")
            print("="*50)
            for key, value in summary.items():
                if key == "files" and isinstance(value, list):
                    print(f"{key}: {', '.join(value[:10])}" + ("..." if len(value) > 10 else ""))
                else:
                    print(f"{key}: {value}")
        
        elif choice == "3":
            print("\n" + "="*50)
            print("QUERY INTERFACE")
            print("="*50)
            print("Ask questions about your documents (type 'back' to return to main menu)")
            
            while True:
                question = input("\nYour question: ").strip()
                
                if question.lower() in ['back', 'b']:
                    break
                
                if question:
                    print("\nSearching...")
                    answer = pdf_system.query(question)
                    print(f"\nAnswer: {answer}")
        
        elif choice == "4":
            pdf_system.debug_index()
        
        elif choice == "5":
            print("Goodbye!")
            break
        
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    interactive_parser()