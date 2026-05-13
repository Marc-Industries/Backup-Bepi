from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    matlab_path: str = ""
    octave_path: str = "octave"
    debug: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
