from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


load_dotenv()  # Load environment variables from .env file

class SpotifySong(BaseModel):
    title: str
    artist: str
    album: str
    release_year: int

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
parser = PydanticOutputParser(pydantic_object=SpotifySong)

