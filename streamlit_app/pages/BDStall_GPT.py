import streamlit as st 
import base64
from dotenv import load_dotenv
import os 
import getpass
import shelve

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAI
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate

from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores.faiss import FAISS
from langchain.chains import RetrievalQA

# pinecone 
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore


from datetime import datetime 

load_dotenv()
st.title("BDStall GPT")

USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

# Initialize Gemini Flash 2.0 model
client = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",
    google_api_key=os.getenv("GEMINI_API_KEY"),
    temperature=0.7
)

# Ensure gemini_model is initialized in session state
if "gemini_model" not in st.session_state:
    st.session_state["gemini_model"] = "gemini-2.0-flash-exp"


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

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        message_placeholder = st.empty()
        full_response = ""
        
        # Convert messages to LangChain format
        from langchain_core.messages import HumanMessage, AIMessage
        langchain_messages = []
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        # Stream response from Gemini
        try:
            response = client.stream(langchain_messages)
            for chunk in response:
                if hasattr(chunk, 'content'):
                    full_response += chunk.content
                    message_placeholder.markdown(full_response + "|")
        except Exception as e:
            # Fallback to non-streaming if streaming fails
            response = client.invoke(langchain_messages)
            full_response = response.content
            
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Save chat history after each interaction
save_chat_history(st.session_state.messages)