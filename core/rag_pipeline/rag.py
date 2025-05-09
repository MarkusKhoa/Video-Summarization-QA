import weaviate
import os
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)

from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.memory import ConversationBufferMemory
from langchain.chains import conversational_retrieval, retrieval_qa
from langchain.agents import initialize_agent
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langchain_core.tools import tool

from langchain_community.document_loaders import TextLoader
from langchain_weaviate.vectorstores import WeaviateVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from contextlib import contextmanager
from loguru import logger
from pyvi import ViTokenizer
from weaviate.classes.init import Auth
from dotenv import load_dotenv

load_dotenv()

weaviate_url = os.getenv('WEAVIATE_URL')
weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# @contextmanager
def weaviate_client_context(url, api_key):
    """Context manager for Weaviate client."""
    client = None
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=url,
        auth_credentials=Auth.api_key(api_key),
    )
    logger.info(f"Is ready?: {client.is_ready()}")
    yield client
    
def load_and_process_text(file_path):
    """Load and process text file."""
    try:
        with open(file_path) as file:
            transcript = file.read()
        return ViTokenizer.tokenize(transcript)
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

@tool(response_format = "content_and_artifact")
def retrieve(query: str, vector_store):
    """Retrieve information related to a query."""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\n" f"Content: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs



def main():
    # Load environment variables
    load_dotenv()
    weaviate_url = os.getenv('WEAVIATE_URL')
    weaviate_api_key = os.getenv('WEAVIATE_API_KEY')
    os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

    # Process text
    # with open("../../data/transcription_Tra_An.txt") as f:
    #     transcription = f.read()

    loader = TextLoader("../../data/transcription_Tra_An.txt")
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=200, chunk_overlap=0)
    texts = text_splitter.split_documents(docs)

    logger.info(f"Documents: {texts}")

    # Initialize embedding model
    embedding_model_name = "sentence-transformers/all-mpnet-base-v2"
    embeddings = HuggingFaceEmbeddings(
        model_name = embedding_model_name
    )

    # Create vector store
    weaviate_client = weaviate.connect_to_weaviate_cloud(
        cluster_url = weaviate_url,
        auth_credentials = Auth.api_key(weaviate_api_key),
    )

    docsearch = WeaviateVectorStore.from_documents(
        documents = texts,
        embedding = embeddings,
        client = weaviate_client,
        index_name = "Transcription_db",
        metadatas=[{"source": f"{i}-pl"} for i in range(len(texts))],
        text_key = "page_content"
    )

    retriever = docsearch.as_retriever()

    # Initialize LLM
    llm_model = ChatGroq(
        model = "llama-3.2-3b-preview",
        temperature = 0,
        max_tokens = 1024
    )

    # Create prompt template
    template = """You are an assistant for question-answering tasks. Use the following pieces of retrieved context to answer the question.
    Keep the context under 500 characters. You are also proficient in Vietnamese context.
    Question: {question}
    Context: {context}
    Answer:"""
    prompt = ChatPromptTemplate.from_template(template)

    # Create RAG chain
    rag_chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm_model
        | StrOutputParser()
    )


    # Process question
    try:
        question = "Vụ án xảy ra ở đâu?"
        # segmented_question = ViTokenizer.tokenize(question)
        answer = rag_chain.invoke(question)
        logger.info(f"Question: {question}")
        logger.info(f"Answer: {answer}")
    except Exception as e:
        logger.error(f"Error during RAG chain execution: {e}")
    
    weaviate_client.close()


if __name__ == "__main__":
    main()