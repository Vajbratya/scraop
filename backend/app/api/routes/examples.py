from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/examples", tags=["examples"])


class PubMedSearchIn(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=10, ge=1, le=50)


class PubMedArticle(BaseModel):
    pmid: str
    title: str | None = None
    journal: str | None = None
    pubdate: str | None = None
    authors: list[str] = []


class PubMedSearchOut(BaseModel):
    items: list[PubMedArticle]


@router.post("/pubmed/search", response_model=PubMedSearchOut)
async def pubmed_search(payload: PubMedSearchIn) -> PubMedSearchOut:
    # E-utilities esearch -> pmids, then esummary -> article meta
    params = {
        "db": "pubmed",
        "term": payload.query,
        "retmode": "json",
        "retmax": str(payload.max_results),
        "sort": "relevance",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        esearch = await client.get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi", params=params)
        esearch.raise_for_status()
        data = esearch.json()
        idlist: list[str] = data.get("esearchresult", {}).get("idlist", [])
        if not idlist:
            return PubMedSearchOut(items=[])
        esummary = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(idlist),
                "retmode": "json",
            },
        )
        esummary.raise_for_status()
        sdata = esummary.json()
        result = sdata.get("result", {})
        items: list[PubMedArticle] = []
        for pmid in idlist:
            r = result.get(pmid, {})
            title = r.get("title")
            journal = (r.get("fulljournalname") or r.get("source"))
            pubdate = r.get("pubdate")
            authors = [a.get("name") for a in r.get("authors", []) if a.get("name")]
            items.append(PubMedArticle(pmid=pmid, title=title, journal=journal, pubdate=pubdate, authors=authors))
        return PubMedSearchOut(items=items)


class PubMedSummarizeIn(BaseModel):
    pmid: str
    language: str | None = None


class SummaryOut(BaseModel):
    summary: str


async def _openai_chat(messages: list[dict[str, str]], model: str = "gpt-4o-mini") -> str:
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="Missing OPENAI_API_KEY")
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
    body = {"model": model, "messages": messages, "temperature": 0.2}
    async with httpx.AsyncClient(timeout=40) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=await resp.text())
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        return content


def _extract_abstract(xml_text: str) -> str:
    try:
        root = ET.fromstring(xml_text)
        abstracts: list[str] = []
        for ab in root.iter():
            if ab.tag.endswith("AbstractText") and (ab.text or "").strip():
                abstracts.append(ab.text.strip())
        return "\n\n".join(abstracts).strip()
    except ET.ParseError:
        return ""


@router.post("/pubmed/summarize", response_model=SummaryOut)
async def pubmed_summarize(payload: PubMedSummarizeIn) -> SummaryOut:
    # Fetch abstract XML then summarize with GPT
    async with httpx.AsyncClient(timeout=30) as client:
        efetch = await client.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "pubmed", "id": payload.pmid, "retmode": "xml"},
        )
        efetch.raise_for_status()
        abstract = _extract_abstract(efetch.text)
    if not abstract:
        raise HTTPException(status_code=404, detail="Abstract not found")
    lang_note = f" in {payload.language}" if payload.language else ""
    prompt = (
        "Summarize the following PubMed abstract as concise bullet points" + lang_note + ":\n\n" + abstract
    )
    summary = await _openai_chat(
        messages=[{"role": "system", "content": "You are a helpful medical research summarizer."}, {"role": "user", "content": prompt}]
    )
    return SummaryOut(summary=summary)


class AskIn(BaseModel):
    question: str = Field(min_length=4)
    urls: list[str] = Field(default_factory=list, description="Optional URLs to ground the answer")
    max_chars_per_page: int = Field(default=8000, ge=1000, le=20000)


class AskOut(BaseModel):
    answer: str
    citations: list[str] = []


def _strip_html(text: str) -> str:
    # naive removal of tags
    out: list[str] = []
    skip = False
    for ch in text:
        if ch == "<":
            skip = True
            continue
        if ch == ">":
            skip = False
            out.append(" ")
            continue
        if not skip:
            out.append(ch)
    return "".join(out)


@router.post("/ask", response_model=AskOut)
async def ask(payload: AskIn) -> AskOut:
    if not payload.urls:
        raise HTTPException(status_code=400, detail="Provide one or more URLs in 'urls' to ground the answer")
    pages: list[str] = []
    async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "scraper-playground/1.0"}) as client:
        for u in payload.urls[:5]:
            try:
                r = await client.get(u, follow_redirects=True)
                if r.status_code < 400 and r.text:
                    txt = _strip_html(r.text)
                    pages.append(txt[: payload.max_chars_per_page])
            except Exception:
                continue
    if not pages:
        raise HTTPException(status_code=400, detail="Failed to fetch any URL content")
    prompt = (
        "Use the provided web content to answer the question with citations like [1], [2].\n\n"
        + "Question: "
        + payload.question
        + "\n\nWeb content:\n"
        + "\n\n".join([f"[Source {i+1}]\n" + p for i, p in enumerate(pages)])
    )
    answer = await _openai_chat(
        messages=[{"role": "system", "content": "You are a precise research assistant that cites sources."}, {"role": "user", "content": prompt}],
        model="gpt-4o-mini",
    )
    return AskOut(answer=answer, citations=payload.urls[: len(pages)])
