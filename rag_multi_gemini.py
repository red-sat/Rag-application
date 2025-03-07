import logging
import sys
import os
import time
import streamlit as st
from dataclasses import dataclass

import google.generativeai as genai
from llama_index.core import Settings, VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding

@dataclass
class AppConfig:
    """Configuration class for application settings"""
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5
    MAX_TOKENS: int = 1024
    DEFAULT_TEMPERATURE: float = 0.3
    LOG_FILE: str = 'app.log'
    EVAL_TEMPERATURE: float = 0.2  # Lower temperature for more consistent evaluations

    # Latest Gemini Models
    GEMINI_MODELS = {
        "Gemini 1.5 Pro": "gemini-1.5-pro-latest",
        "Gemini 2.0 Flash": "gemini-2.0-flash-exp"
    }

    # Evaluation criteria
    EVALUATION_CRITERIA = [
        "Relevance to the original query",
        "Accuracy of information",
        "Clarity and coherence",
        "Comprehensiveness",
        "Use of context from provided documents"
    ]

class DocumentChatApp:
    def __init__(self):
        """Initialize the Streamlit Document Chat Application"""
        self._setup_logging()
        self._validate_api_key()
        self._initialize_genai()
        
        self.documents = []  # Initialize documents list
        self.eval_model = None  # Evaluation model

    def _setup_logging(self):
        """Configure logging with file and stream handlers"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(AppConfig.LOG_FILE),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _validate_api_key(self):
        self.GOOGLE_API_KEY = 'AIzaSyBxwD2NrEx9lcaUKzFsDmXBgyiveAfnJR8' #AIzaSyBwVOCO3mhnYtsK--CZsdmjeXbcX2IkGPU

    def _initialize_genai(self):
        """Configure Google Generative AI"""
        try:
            genai.configure(api_key=self.GOOGLE_API_KEY)
        except Exception as e:
            self.logger.error(f"Failed to configure Generative AI: {e}")
            st.error(f"API Configuration Error: {e}")
            st.stop()

    def _initialize_models(self, selected_model):
        try:
            model_name = f"models/{AppConfig.GEMINI_MODELS.get(selected_model, 'gemini-2.0-flash-exp')}"
            
            self.llm = Gemini(
                model=model_name,
                api_key=self.GOOGLE_API_KEY,
                temperature=st.session_state.temperature,
                max_tokens=AppConfig.MAX_TOKENS
            )
            
            self.embed_model = GeminiEmbedding(
                api_key=self.GOOGLE_API_KEY,
                model_name="models/embedding-001"
            )
            
            # Initialize evaluation model
            self.eval_model = Gemini(
                model="models/gemini-2.0-flash-exp",
                api_key=self.GOOGLE_API_KEY,
                temperature=AppConfig.EVAL_TEMPERATURE,
                max_tokens=AppConfig.MAX_TOKENS
            )
        except Exception as e:
            self.logger.error(f"Model initialization error: {e}")
            st.error(f"Failed to initialize models: {e}")
            st.stop()

    def _evaluate_response(self, prompt, response, context_docs):
        """Evaluate the generated response using Gemini 2.0 Flash"""
        try:
            # Prepare context information
            context_text = "\n".join([doc.text for doc in context_docs]) if context_docs else "No context documents provided."
            
            # Construct evaluation prompt
            eval_prompt = f"""Evaluate the following response based on these criteria:
            {', '.join(AppConfig.EVALUATION_CRITERIA)}

            Original Query: {prompt}
            Context Documents: {context_text[:1000]}  # Limit context to prevent token overflow
            Response: {response}

            Please provide:
            1. A score (0-10) for each criterion
            2. A brief explanation for each score
            3. An overall assessment of the response quality
            4. Suggestions for improvement if applicable

            Format your response as:
            Criterion 1 Score: X/10 - Explanation
            Criterion 2 Score: X/10 - Explanation
            ...
            Overall Score: X/10
            Improvement Suggestions: [List]
            """

            # Generate evaluation
            evaluation = self.eval_model.complete(eval_prompt)
            return str(evaluation)
        except Exception as e:
            self.logger.error(f"Response evaluation error: {e}")
            return f"Evaluation failed: {e}"

    def _load_local_documents(self, selected_files):
        """Load documents directly from the txt_files directory based on user selection."""
        self.documents = []
        txt_dir = "txt_files"
        if not os.path.exists(txt_dir):
            st.error("Text directory not found. Please ensure txt_files directory is present.")
            return []
        
        input_files = [os.path.join(txt_dir, f) for f in selected_files]

        try:
            reader = SimpleDirectoryReader(input_files=input_files)
            self.documents = reader.load_data()

            if not self.documents:
                st.warning("No documents were loaded. Please check the selected files.")
            
            return self.documents
        except Exception as e:
            self.logger.error(f"Document loading error: {e}")
            st.error(f"Failed to load documents: {e}")
            return []

    def _create_vector_index(self):
        """Create vector index from loaded documents"""
        try:
            return VectorStoreIndex.from_documents(
                self.documents, 
                chunk_size=AppConfig.CHUNK_SIZE, 
                chunk_overlap=AppConfig.CHUNK_OVERLAP
            )
        except Exception as e:
            self.logger.error(f"Vector index creation error: {e}")
            st.error(f"Failed to create vector index: {e}")
            return None

    def _initialize_chat_engine(self, vector_index):
        """Initialize chat engine with vector index"""
        try:
            return vector_index.as_chat_engine(
                similarity_top_k=AppConfig.TOP_K_RESULTS
            )
        except Exception as e:
            self.logger.error(f"Chat engine initialization error: {e}")
            st.error(f"Failed to initialize chat engine: {e}")
            return None

    def run(self):
        """Run the Streamlit application"""
        st.set_page_config(page_title="Multi-Doc Gemini Chat", page_icon="📄")
        st.title('Chat with SFCR docs')
        self._setup_sidebar()
        self._initialize_session_state()
        self._process_local_documents()
        self._display_chat_history()
        self._process_user_input()

    def _setup_sidebar(self):
        """Configure sidebar with application settings"""
        st.sidebar.header('Chat Configuration')
        
        # Model selection 
        st.session_state.selected_model = st.sidebar.selectbox(
            'Select Gemini Model',
            list(AppConfig.GEMINI_MODELS.keys()),
            index=0
        )
        
        # Temperature slider
        st.session_state.temperature = st.sidebar.slider(
            'Temperature', 
            min_value=0.0, 
            max_value=1.0, 
            value=AppConfig.DEFAULT_TEMPERATURE,
            step=0.1
        )
        
        st.sidebar.write("Select between 1 and 4 documents from the image:")

        txt_dir = "txt_files"
        if os.path.exists(txt_dir):
            available_files = [f for f in os.listdir(txt_dir) if f.endswith(".txt")]
        else:
            available_files = []

        st.session_state.selected_files = st.sidebar.multiselect(
            "Select documents",
            options=available_files,
            help="Select between 1 and 4 documents."
        )

        # Add toggle for response evaluation
        st.session_state.enable_evaluation = st.sidebar.checkbox(
            'Enable Response Evaluation', 
            value=True,
            help="Automatically evaluate each response using Gemini 2.0 Flash"
        )

        # Clear conversation button
        if st.sidebar.button('Clear Conversation'):
            st.session_state.messages = []
            st.session_state.conversation_context = None
            st.session_state.vector_index = None

    def _initialize_session_state(self):
        """Initialize or reset session state variables"""
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "conversation_context" not in st.session_state:
            st.session_state.conversation_context = None
        if "vector_index" not in st.session_state:
            st.session_state.vector_index = None
        if "selected_model" not in st.session_state:
            st.session_state.selected_model = "Gemini Pro"
        if "temperature" not in st.session_state:
            st.session_state.temperature = AppConfig.DEFAULT_TEMPERATURE
        if "selected_files" not in st.session_state:
            st.session_state.selected_files = []
        if "enable_evaluation" not in st.session_state:
            st.session_state.enable_evaluation = True

    def _process_local_documents(self):
        """Process local documents based on user selection and create vector index"""
        selected_files = st.session_state.selected_files
        
        # Vérifier le nombre de fichiers sélectionnés
        if selected_files:
            if len(selected_files) > 4:
                st.warning("You selected more than 4 documents. Only the first 4 will be considered.")
                selected_files = selected_files[:4]
        else:
            st.info("Please select at least one document.")
            return
        
        documents = self._load_local_documents(selected_files)
        
        if documents:
            # Initialize models
            self._initialize_models(st.session_state.selected_model)
            
            # Configure settings
            Settings.llm = self.llm
            Settings.embed_model = self.embed_model
            Settings.chunk_size = AppConfig.CHUNK_SIZE
            Settings.chunk_overlap = AppConfig.CHUNK_OVERLAP
            
            # Create vector index
            st.session_state.vector_index = self._create_vector_index()
            
            # Initialize chat engine
            if st.session_state.vector_index:
                st.session_state.chat_engine = self._initialize_chat_engine(st.session_state.vector_index)
                st.sidebar.success(f"{len(documents)} documents loaded successfully!")
        else:
            st.sidebar.error("Failed to load the selected documents. Please try again.")

    def _display_chat_history(self):
        """Display previous chat messages"""
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display evaluation if available
                if message["role"] == "assistant" and "evaluation" in message:
                    with st.expander("Response Evaluation"):
                        st.markdown(message["evaluation"])

    def _process_user_input(self):
        """Process and respond to user input"""
        # Check if chat engine is ready
        if not hasattr(st.session_state, 'chat_engine') or not st.session_state.chat_engine:
            st.info("Please select and load documents to start chatting.")
            return

        if prompt := st.chat_input("Ask me anything about the selected documents!"):
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate and display assistant response
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                for word in self._response_generator(prompt):
                    full_response += word
                    response_placeholder.markdown(full_response)
                
                # Perform response evaluation if enabled
                evaluation = ""
                if st.session_state.enable_evaluation and self.eval_model:
                    with st.spinner("Evaluating response..."):
                        evaluation = self._evaluate_response(
                            prompt, 
                            full_response, 
                            self.documents
                        )
            
            # Add assistant response to chat history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": full_response,
                "evaluation": evaluation if st.session_state.enable_evaluation else None
            })

    def _response_generator(self, prompt):
        """Generate streaming response for the given prompt"""
        try:
            # Query chat engine
            response = st.session_state.chat_engine.query(prompt)
            
            # Check for empty response
            if not response or not str(response).strip():
                yield "I couldn't find a relevant response. Could you rephrase your question?"
                return
            
            # Stream response words
            for word in str(response).split():
                yield word + " "
                time.sleep(0.05)
        
        except Exception as e:
            self.logger.error(f"Response generation error: {e}")
            yield f"An error occurred: {e}"

def main():
    """Main application entry point"""
    try:
        app = DocumentChatApp()
        app.run()
    except Exception as e:
        st.error(f"Application initialization error: {e}")
        logging.error(f"Unhandled application error: {e}")

if __name__ == "__main__":
    main()
