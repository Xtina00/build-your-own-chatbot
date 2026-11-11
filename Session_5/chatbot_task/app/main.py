import streamlit as st
import asyncio
import logging
from dataclasses import dataclass

@dataclass
class ChatMessage:
    role: str
    content: str
from src.chatbot import CustomChatBot
import os

INDEX_DATA = os.environ.get("INDEX_DATA", "0")
PULL_EMBEDDING_MODEL = os.environ.get("PULL_EMBEDDING_MODEL", "0")

# Configure logger
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console logs
    ],
)

logger = logging.getLogger(__name__)

# Initialize chatbot instance (avoid reloading)
if "bot" not in st.session_state:
    st.session_state["bot"] = CustomChatBot(index_data=bool(int(INDEX_DATA)), pull_embedding_model=bool(int(PULL_EMBEDDING_MODEL)))

# Streamlit UI setup
st.set_page_config(page_title="ChatDoc", page_icon="📄")
st.header("Chat with your Document")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(role="assistant", content="How can I help you?")]

if len(st.session_state["messages"]) == 0 or st.sidebar.button("Clear message history"):
    st.session_state["messages"].clear()
    st.session_state["messages"] = [ChatMessage(role="assistant", content="How can I help you?")]

# Display chat messages
for msg in st.session_state.messages:
    st.chat_message(msg.role).write(msg.content)

# Handle user input
st.sidebar.header("Search Settings")

retrieval_count = st.sidebar.slider(
    "Number of retrieved chunks",
    min_value=1,
    max_value=10,
    value=3,
    step=1
)

st.session_state["bot"].set_retrieval_count(retrieval_count)

# Export chat history as a TXT file
if st.session_state.messages:
    chat_history = "\n\n".join(
        f"{message.role.upper()}: {message.content}"
        for message in st.session_state.messages
    )

    st.sidebar.download_button(
        label="Download Chat History",
        data=chat_history,
        file_name="chat_history.txt",
        mime="text/plain"
    )
    
if user_query := st.chat_input(placeholder="Ask me anything!"):
    st.session_state.messages.append(ChatMessage(role="user", content=user_query))
    logger.info(f"Write user message in session state {user_query}")
    st.chat_message("user").write(user_query)

    async def handle_user_query(user_query):
        container = st.empty()
        answer = ""
        try:
            async for chunk in st.session_state["bot"].astream(user_query):
                if chunk:
                    answer+=chunk
                    container.markdown(answer)
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            container.error("An error occurred while processing your request.")

        # Store assistant response in session state
        if answer:
            logger.info(f"Write assistant message in session state {user_query}")
            st.session_state.messages.append(ChatMessage(role="assistant", content=answer))

    sources = st.session_state["bot"].get_sources(user_query)

    with st.expander("View retrieved sources"):
        for i, source in enumerate(sources, start=1):
            st.write(f"Source {i}: {source['source']}")
            st.write(f"Page: {source['page']}")
            st.write(source["content"])
            st.divider()

    with st.chat_message("assistant"):
        with st.spinner("Searching for information in your documents and generation response..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(handle_user_query(user_query))