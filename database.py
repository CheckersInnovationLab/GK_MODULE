import os
import mysql.connector
from mysql.connector import Error
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DB_HOST = os.getenv("DB_HOST", "193.203.162.224")
DB_USER = os.getenv("DB_USER", "cil-db-user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "rK32_5t@fM#")
DB_NAME = os.getenv("DB_NAME", "checkers_lms")
DB_PORT = os.getenv("DB_PORT", "3306")

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
        return conn
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {e}")
