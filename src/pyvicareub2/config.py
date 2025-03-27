from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    client_id: str = ""
    email: str = ""
    password: str = ""
    local_mode: bool = False
    timezone: str = "Europe/Amsterdam"
    data_file: str = "burner_data.csv"
    data_file_json: str = "burner_data.jsonl"
    token_file: str = "token.save"
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    background_task_interval: int = 300  # 5 minutes in seconds

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
