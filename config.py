# config.py


class Config:
    SECRET_KEY = 'dummy_secret'
    DEBUG = False
    TESTING = False
    DB_USER = None
    DB_PASSWORD = None
    BOLT_URL = 'bolt://localhost:7687'
    DB_CONNECTION_ENCRYPTED = 'ENCRYPTION_OFF'
    UPLOAD_FOLDER = 'uploads'


class TestingConfig(Config):
    TESTING = True


class DevelopmentConfig(Config):
    DEBUG = True
    DB_USER = 'neo4j'  # Set your local neo4j db user
    DB_PASSWORD = '123456'  # Set your local neo4j db password


class ProductionConfig(Config):
    pass
