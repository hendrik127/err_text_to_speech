from fastapi.responses import StreamingResponse
import io
import json
from fastapi import Header
import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import parse_obj_as
from scrape import scrape_data
from typing import List, Dict, Optional, Tuple
from sqlmodel import Session, select
from database import Article, ArticleAudio, engine
# from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException


class TextToSpeech(BaseModel):
    text: str
    speaker: str
    speed: float


TEXT_TO_SPEECH_URL = "https://api.tartunlp.ai/text-to-speech/v2"


def scrape(all: bool) -> List[Article]:
    # Whether to seed empty database or to only get new articles.
    old_count = 0
    with Session(engine) as session:
        articles = select(Article)
        old_count = len(session.exec(articles).all())

    data = scrape_data(all)
    result = parse_obj_as(List[Article], data)
    session = Session(engine)
    for key, article in enumerate(result):
        session.add(article)
        for i in range(len(article.content)):
            session.add(ArticleAudio(
                article_id=key+1+old_count, index=i+old_count, audio=b''))
    session.commit()
    session.close()
    return result


app = FastAPI()

# origins = [
#     "*",
# ]

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.on_event("startup")
def on_startup():
    # Check whether the database is empty.
    # If empty, seed with all articles that can be found.
    # If not empty, add all articles that have not been added.
    with Session(engine) as session:
        articles = select(Article)
        result = session.exec(articles).first()
        if not result:
            scrape(True)
        else:
            scrape(False)


@app.get("/")
async def root() -> List[Article]:
    with Session(engine) as session:
        result = session.exec(select(Article)).all()
        return result


@app.get("/titles/")
async def titles_by_page(page: int = 1, page_size: int = 20) -> JSONResponse:
    # Returns titles of articles by page size.
    start = (page - 1) * page_size
    end = start + page_size

    with Session(engine) as session:
        result = session.exec(select(Article.id, Article.title).where(
            Article.id > start, Article.id <= end)).all()
        json_compatible = jsonable_encoder(result)
        return JSONResponse(status_code=200, content=json_compatible)


@app.get("/paragraphs/")
async def paragraphs(id: int) -> List[str]:
    # returns the paragraphs of an article by id.
    with Session(engine) as session:
        result = session.exec(select(Article.content).where(
            Article.id == id)).first()
        return result


@app.get("/sync")
async def sync():
    # Fetch new articles that are not in the database yet.
    # Add them to the database.
    scrape(False)
    return {"sync": "complete"}


@app.get("/sort")
async def sort() -> List[Article]:
    # Get all the articles from the database sorted by date.
    with Session(engine) as session:
        stmt = select(Article).order_by(Article.timestamp.desc())
        articles_by_date = session.exec(stmt).all()
        return articles_by_date


async def fetchAndSaveAudio(article_id: int, index: int, text: str = "",
                            speaker: str = "Mari", speed: float = 1.0):

    headers: Dict = {"Content-Type": "application/json"}
    with Session(engine) as session:
        stmt2 = select(ArticleAudio).where(ArticleAudio.article_id == article_id,
                                           ArticleAudio.index == index)
        result2 = session.exec(stmt2)
        audio = result2.first()
        audio_binary = audio.audio
        if not audio.audio and text:
            try:
                async with httpx.AsyncClient() as client:
                    body = TextToSpeech(text=text,
                                        speaker=speaker, speed=speed)
                    response = await client.post(TEXT_TO_SPEECH_URL, headers=headers, json=body.dict())
                    audio_binary = response.content
                    audio.audio = audio_binary
                    session.add(audio)
                    session.commit()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=e.response.status_code, detail=f"External API error: {e}")
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Internal Server Error: {e}")

        if audio_binary:
            return audio_binary
        else:
            return b''


@app.get("/audio/{article_id}/{index}")
async def audio(article_id: int, index: int,
                range: Optional[str] = Header(None),
                ) -> StreamingResponse:

    audio_binary = await fetchAndSaveAudio(article_id, index)
    text = ""
    if not audio_binary:
        with Session(engine) as session:
            stmt = select(Article).where(Article.id == article_id)
            result = session.exec(stmt)
            article = result.first()
            if not article:
                return b''
            text = article.content[index]
        audio_binary = await fetchAndSaveAudio(article_id, index, text)

    if range:
        start, end = parse_range_header(range)
        audio_binary = audio_binary[start:end]

    return StreamingResponse(io.BytesIO(audio_binary), media_type="audio/wav")


def parse_range_header(range_header: str) -> Tuple[int, int]:
    _, range_values = range_header.split('=')
    start, end = map(int, range_values.split('-'))
    return start, end + 1
