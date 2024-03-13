from dotenv import load_dotenv
import os
import streamlit as st
import requests

from langchain_openai import ChatOpenAI
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import ChatMessage

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 환경 변수를 사용하여 API 키를 불러옵니다.
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# OpenAI API 키가 없는 경우 오류 메시지 출력
if not OPENAI_API_KEY:
    st.error("Please add your OpenAI API key to continue.")
    st.stop()

# TMDb API 키가 없는 경우 오류 메시지 출력
if not TMDB_API_KEY:
    st.error("Please add your TMDb API key to continue.")
    st.stop()

# OpenAI 모델 및 챗봇 설정
MODEL = "gpt-4-0125-preview"
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model_name=MODEL)

class StreamHandler(BaseCallbackHandler):
    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.text += token
        self.container.markdown(self.text)

# 사용자가 입력한 텍스트에서 배우 이름을 추출하는 함수
def extract_actor_name(prompt):
    words = prompt.split()
    for word in words:
        if word.istitle():
            return word
    return None

# TMDb API를 사용하여 배우가 출연한 영화 목록을 가져오는 함수
def get_movies_with_actor(actor_name):
    base_url = 'https://api.themoviedb.org/3'
    search_actor_url = f'{base_url}/search/person'

    params = {
        'api_key': TMDB_API_KEY,
        'query': actor_name,
    }

    response = requests.get(search_actor_url, params=params)
    if response.status_code == 200:
        actor_data = response.json()
        movies_with_actor = []

        if 'results' in actor_data and actor_data['results']:
            actor_id = actor_data['results'][0]['id']
            actor_movies_url = f'{base_url}/person/{actor_id}/movie_credits'
            params = {'api_key': TMDB_API_KEY}
            response = requests.get(actor_movies_url, params=params)

            if response.status_code == 200:
                movies_data = response.json()
                for movie in movies_data.get('cast', []):
                    movies_with_actor.append(movie['title'])
                return movies_with_actor
            else:
                st.error("Failed to fetch movies with the actor. Please try again later.")
                st.stop()
        else:
            st.error("Actor not found. Please check the actor's name and try again.")
            st.stop()
    else:
        st.error("Failed to fetch actor information. Please try again later.")
        st.stop()

# Streamlit UI 시작
st.title("📺 MOVIE BOT")
st.info("좋아하는 배우 출연 영화를 추천해드리는 챗봇입니다.")
st.error("배우 이름을 영어로 기입해주세요. EX) Brad Pitt, Lee Byung-hun")

if "messages" not in st.session_state:
    st.session_state["messages"] = [ChatMessage(role="assistant", content="Hello! I'm MOVIE BOT.")]

# 사용자와 챗봇의 대화 표시
for msg in st.session_state.messages:
    st.chat_message(msg.role).write(msg.content)

# 사용자 입력 처리
if prompt := st.text_input("Enter the name of your favorite actor:"):
    st.session_state.messages.append(ChatMessage(role="user", content=prompt))

    # 챗봇 응답 생성
    with st.spinner("Fetching movie information..."):
        # 사용자가 입력한 배우 이름을 추출
        actor_name = extract_actor_name(prompt)
        
        # 배우가 출연한 영화 목록 가져오기
        movies_with_actor = get_movies_with_actor(actor_name)
        
        # 사용자에게 선택할 수 있는 영화 목록 제공
        assistant_response = f"Movies featuring {actor_name}:\n"
        for movie in movies_with_actor:
            assistant_response += f"- {movie}\n"
        st.session_state.messages.append(ChatMessage(role="assistant", content=assistant_response))

        # 사용자에게 다음 질문 표시
        st.session_state.messages.append(ChatMessage(role="assistant", content="What type of movie are you in the mood for?"))

    # OpenAI 모델을 사용하여 챗봇 응답 생성
    response = llm(st.session_state.messages)
    st.session_state.messages.append(ChatMessage(role="assistant", content=response.content))
