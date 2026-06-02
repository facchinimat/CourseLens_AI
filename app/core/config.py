from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = ""
    chroma_db_path: str = "data/chroma_db"
    upload_dir: str = "data/uploads"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_retrieval_docs: int = 5
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
