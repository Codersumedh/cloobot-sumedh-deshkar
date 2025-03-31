import os
import psycopg2
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_NAME = os.getenv("DB_NAME", "contract_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sumedh")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def fix_database():
    """
    Directly fix the database schema by recreating the embeddings table
    """
    print("Starting database fix...")
    
    # Connect to the database
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    
    try:
        with conn.cursor() as cursor:
            # Backup existing data if needed
            print("Creating backup of embeddings table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings_backup AS 
                SELECT * FROM embeddings
            """)
            conn.commit()
            
            # Drop existing tables that might cause conflicts
            print("Dropping conflicting tables...")
            cursor.execute("DROP TABLE IF EXISTS embeddings_new")
            cursor.execute("DROP TABLE IF EXISTS embeddings")
            conn.commit()
            
            # Create fresh embeddings table with float array type
            print("Creating new embeddings table...")
            cursor.execute("""
                CREATE TABLE embeddings (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id),
                    chunk_text TEXT NOT NULL,
                    embedding_vector FLOAT[] NOT NULL,
                    chunk_type TEXT,
                    risk_score FLOAT
                )
            """)
            conn.commit()
            
            print("Database schema fixed successfully!")
            print("Note: Previous embeddings data has been backed up to embeddings_backup table.")
            print("You will need to regenerate embeddings for existing documents.")
            
    except Exception as e:
        conn.rollback()
        print(f"Error fixing database: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()