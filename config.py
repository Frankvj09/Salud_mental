import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-temporal'

    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # Fix obligatorio: Render entrega 'postgres://' pero psycopg2 necesita 'postgresql://'
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)