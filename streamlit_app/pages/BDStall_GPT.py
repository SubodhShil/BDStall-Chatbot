import streamlit as st 
from dotenv import load_dotenv
import os 
import shelve

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

load_dotenv()

st.title("BDStall GPT")

USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

# Pinecone Configuration
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "bdstall-products-768"

@st.cache_resource
def get_vector_store():
    """Initializes and returns the Pinecone vector store."""
    if not PINECONE_API_KEY:
        st.error("PINECONE_API_KEY not found in environment variables.")
        return None
    
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        vector_store = PineconeVectorStore.from_existing_index(PINECONE_INDEX_NAME, embeddings)
        return vector_store
    except Exception as e:
        st.error(f"Error connecting to Pinecone: {e}")
        return None

@st.cache_resource
def get_conversational_chain(_vector_store):
    """Creates and returns a conversational RAG chain."""
    prompt_template = """
    You are a helpful assistant for BDStall. Answer the user's question based on the context provided.
    If the information is not in the context, say you don't have that information.

    Context:
    {context}

    Question:
    {question}

    Answer:
    """
    
    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.3,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    
    chain = RetrievalQA.from_chain_type(
        llm=model,
        chain_type="stuff",
        retriever=_vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 5, "fetch_k": 20}),
        chain_type_kwargs={"prompt": prompt},
        return_source_documents=True
    )
    return chain

vector_store = get_vector_store()

# Ensure gemini_model is initialized in session state
if "gemini_model" not in st.session_state:
    st.session_state["gemini_model"] = "gemini-2.0-flash"


# Load chat history from shelve file
def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("messages", [])


# Save chat history to shelve file
def save_chat_history(messages):
    with shelve.open("chat_history") as db:
        db["messages"] = messages


# Initialize or load chat history
if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

# Sidebar with a button to delete chat history
with st.sidebar:
    if st.button("Delete Chat History"):
        st.session_state.messages = []
        save_chat_history([])

# Display chat messages
for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# Main chat interface
if prompt := st.chat_input("How can I help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    if vector_store:
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            message_placeholder = st.empty()
            
            with st.spinner("Thinking..."):
                chain = get_conversational_chain(vector_store)
                response = chain.invoke({"query": prompt})
                full_response = response.get("result", "Sorry, I could not find an answer.")

                # Display source documents for debugging
                if "source_documents" in response:
                    with st.expander("Source Documents"):
                        for doc in response["source_documents"]:
                            st.write(doc.page_content)
            
            message_placeholder.markdown(full_response)
    else:
        st.error("Vector store is not available. Please check your configuration.")
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Save chat history after each interaction
save_chat_history(st.session_state.messages)