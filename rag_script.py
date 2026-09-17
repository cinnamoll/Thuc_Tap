import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

import frontmatter
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma  
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_deepseek import ChatDeepSeek  
from dotenv import load_dotenv

load_dotenv()

def parse_structured_json(content: str) -> Optional[Dict]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None

def flatten_metadata(metadata: dict) -> dict:
    flat = {}
    for key, value in metadata.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat_key = f"{key}.{sub_key}"
                if isinstance(sub_value, (str, int, float, bool)) or sub_value is None:
                    flat[flat_key] = sub_value
                else:
                    flat[flat_key] = str(sub_value)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            flat[key] = value
        elif isinstance(value, list):
            flat[key] = value
        else:
            flat[key] = str(value)
    return flat

def load_rag_optimized_md(file_path: str) -> List[Document]:
    with open(file_path, "r", encoding="utf-8") as f:
        post = frontmatter.load(f)

    base_metadata = flatten_metadata(dict(post.metadata))
    base_metadata["source"] = str(file_path)
    content = post.content

    documents = []

    structured_data = parse_structured_json(content)
    if structured_data:
        documents.append(
            Document(
                page_content=json.dumps(structured_data, ensure_ascii=False, indent=2),
                metadata={**base_metadata, "chunk_type": "structured_json", "section": "0. Structured Data"}
            )
        )

    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    header_splits = md_splitter.split_text(content)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""]
    )

    for split in header_splits:
        section_meta = {
            **base_metadata,
            "chunk_type": "narrative",
            "section": split.metadata.get("h2") or split.metadata.get("h1") or "unknown"
        }

        if len(split.page_content) < 1500:
            documents.append(Document(page_content=split.page_content, metadata=section_meta))
        else:
            sub_chunks = text_splitter.split_text(split.page_content)
            for i, chunk in enumerate(sub_chunks):
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={**section_meta, "sub_chunk": i}
                    )
                )

    tags_match = re.search(r"## Retrieval Tags.*?(```yaml.*?```)", content, re.DOTALL)
    if tags_match:
        documents.append(
            Document(
                page_content=tags_match.group(1),
                metadata={**base_metadata, "chunk_type": "retrieval_tags", "section": "Retrieval Tags"}
            )
        )

    return documents

def load_directory(path: str, pattern: str = "**/*.md", name_filter: Optional[str] = "RAG") -> List[Document]:
    all_docs = []
    root = Path(path)

    for file_path in list(root.rglob(pattern)):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() != ".md":
            continue
        if name_filter and name_filter.upper() not in file_path.name.upper():
            continue

        try:
            docs = load_rag_optimized_md(str(file_path))
            all_docs.extend(docs)
            print(f"Loaded {len(docs):>3} chunks ← {file_path.relative_to(root)}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    return all_docs


def build_vectorstore(documents: List[Document], persist_directory: str):
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2-preview")

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory,
        collection_name="financial_reports_rag"
    )
    return vectorstore

def get_retriever(vectorstore, period_key: Optional[str] = None, company_name: Optional[str] = None, k: int = 6, entity_id: Optional[str] = None,
    scope: Optional[str] = None):
    search_kwargs = {"k": k}

    filter_dict = {}
    if period_key:
        filter_dict["period_key"] = period_key
    if company_name:
        filter_dict["company_name"] = company_name
    if entity_id:
        filter_dict["entity_id"] = entity_id
    if scope:
        filter_dict["scope"] = scope

    if filter_dict:
        search_kwargs["filter"] = filter_dict

    return vectorstore.as_retriever(search_type="similarity", search_kwargs=search_kwargs)

PROMPT_TEMPLATE = """Bạn là trợ lý phân tích tài chính nghiêm ngặt, chỉ được trả lời dựa trên Context.

QUY TẮC BẮT BUỘC:
1. Ưu tiên số liệu từ khối "structured_json" nếu có.
2. Luôn trích dẫn nguồn theo format: (company_name | period_key | section)
3. Nếu không tìm thấy thông tin → trả lời đúng câu: "I don't know based on the provided documents."
4. Không suy đoán, không dùng kiến thức bên ngoài.
5. Khi trả lời số liệu, giữ nguyên đơn vị (tỷ VND, %, ...).

Context:
{context}

Câu hỏi: {question}
"""

prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

def format_docs(docs: List[Document]) -> str:
    formatted = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        header = f"[{i}] ({meta.get('company_name', 'N/A')} | {meta.get('period_key', 'N/A')} | {meta.get('section', 'N/A')})"
        formatted.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(formatted)

def build_rag_chain(retriever):
    llm = ChatDeepSeek(model="deepseek-v4-flash", temperature=0)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

if __name__ == "__main__":
    print("Loading documents...")
    documents = load_directory("./example_output", pattern="**/*.md")
    print(f"Total chunks: {len(documents)}")

    print("Building vector store...")
    vectorstore = build_vectorstore(documents, persist_directory="./chroma_db_financial")

    retriever = get_retriever(vectorstore)
    rag_chain = build_rag_chain(retriever)

    while True:
        question = input("\nEnter question or 'exit': ").strip()
        if question.lower() == "exit":
            break
        answer = rag_chain.invoke(question)
        print(answer)