import os
import cv2
import numpy as np
import pytesseract
import PyPDF2
import re
from PIL import Image
import psycopg2
import json
from datetime import datetime
from sentence_transformers import SentenceTransformer
import torch
from typing import Dict, List, Tuple, Any, Optional
import argparse
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from dotenv import load_dotenv
from together import Together  # Import Together AI client

# Load environment variables
load_dotenv()

# Database connection parameters (from environment variables)
DB_NAME = os.getenv("DB_NAME", "contract_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "sumedh")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# Initialize Together AI client
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "99119015c00e5e948acff2763710ed0cd93b9dad1b3bbe4b794c120f5d01675f")
together_client = Together(api_key=TOGETHER_API_KEY)
TOGETHER_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

# Initialize embedding model - we'll keep using sentence-transformers for embeddings
# as they're optimized for this purpose
model = SentenceTransformer('all-MiniLM-L6-v2')  # Free and lightweight model from HuggingFace

# Risk score thresholds
RISK_THRESHOLDS = {
    "high": 0.7,
    "medium": 0.4,
    "low": 0.1
}

# Important clause types to look for
IMPORTANT_CLAUSES = [
    "payment_terms", 
    "termination", 
    "liability", 
    "confidentiality", 
    "intellectual_property",
    "data_protection", 
    "warranty", 
    "indemnification",
    "force_majeure",
    "non_compete",
    "governing_law"
]

class DatabaseManager:
    def __init__(self):
        """Initialize database connection and create tables if they don't exist."""
        self.conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        self.create_tables()
    
    def create_tables(self):
        """Create necessary tables if they don't exist."""
        with self.conn.cursor() as cursor:
            # Documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    upload_date TIMESTAMP NOT NULL,
                    full_text TEXT NOT NULL,
                    metadata JSONB
                )
            ''')
            
            # Check if embeddings table exists
            cursor.execute('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'embeddings'
                )
            ''')
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create the table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS embeddings (
                        id SERIAL PRIMARY KEY,
                        document_id INTEGER REFERENCES documents(id),
                        chunk_text TEXT NOT NULL,
                        embedding_vector FLOAT[] NOT NULL,
                        chunk_type TEXT,
                        risk_score FLOAT
                    )
                ''')
                self.conn.commit()
            else:
                # Check column type if table exists
                cursor.execute('''
                    SELECT data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'embeddings' AND column_name = 'embedding_vector'
                ''')
                
                column_type = cursor.fetchone()
                
                if column_type and column_type[0] == 'bytea':
                    print("Warning: Found embeddings table with bytea type. Migration needed.")
                    print("Please run the migration script separately.")
                    # We don't automatically migrate here to avoid data loss

            # Risk analysis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_analysis (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER REFERENCES documents(id),
                    clause_type TEXT NOT NULL,
                    clause_text TEXT NOT NULL,
                    risk_score FLOAT NOT NULL,
                    risk_explanation TEXT,
                    analysis_date TIMESTAMP NOT NULL
                )
            ''')
            
            self.conn.commit()
    
    def insert_document(self, filename: str, doc_type: str, full_text: str, metadata: Dict = None) -> int:
        """Insert document data and return document id."""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO documents (filename, doc_type, upload_date, full_text, metadata) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (filename, doc_type, datetime.now(), full_text, json.dumps(metadata or {}))
            )
            document_id = cursor.fetchone()[0]
            self.conn.commit()
            return document_id
    
    def insert_embeddings(self, document_id: int, chunks_with_embeddings: List[Dict]) -> None:
        """Insert text chunks and their embeddings as float arrays."""
        # Count for reporting
        successful = 0
        skipped = 0
        
        for chunk in chunks_with_embeddings:
            try:
                # Skip chunks without identified types
                if not chunk.get('type'):
                    skipped += 1
                    continue
                    
                # Convert numpy array to Python list
                if isinstance(chunk['embedding'], np.ndarray):
                    embedding_list = chunk['embedding'].tolist()
                else:
                    embedding_list = chunk['embedding']
                
                # Use a transaction for each insertion to prevent entire batch failure
                with self.conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO embeddings 
                        (document_id, chunk_text, embedding_vector, chunk_type, risk_score) 
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            document_id, 
                            chunk['text'], 
                            embedding_list,
                            chunk.get('type'), 
                            chunk.get('risk_score', 0.0)
                        )
                    )
                    self.conn.commit()
                    successful += 1
                    
            except Exception as e:
                # Log the error but continue processing other chunks
                self.conn.rollback()
                print(f"Error inserting embedding: {str(e)}")
                skipped += 1
        
        print(f"Embeddings inserted: {successful}, skipped: {skipped}")
    
    def insert_risk_analysis(self, document_id: int, analyses: List[Dict]) -> None:
        """Insert risk analysis results."""
        with self.conn.cursor() as cursor:
            for analysis in analyses:
                cursor.execute(
                    "INSERT INTO risk_analysis (document_id, clause_type, clause_text, risk_score, risk_explanation, analysis_date) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        document_id,
                        analysis['clause_type'],
                        analysis['clause_text'],
                        analysis['risk_score'],
                        analysis.get('risk_explanation', ''),
                        datetime.now()
                    )
                )
            self.conn.commit()
    
    def get_similar_clauses(self, embedding: np.ndarray, clause_type: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """Retrieve similar clauses based on embedding similarity."""
        with self.conn.cursor() as cursor:
            if clause_type:
                cursor.execute(
                    """
                    SELECT e.chunk_text, e.risk_score, d.doc_type, d.filename, e.embedding_vector
                    FROM embeddings e
                    JOIN documents d ON e.document_id = d.id
                    WHERE e.chunk_type = %s
                    """,
                    (clause_type,)
                )
            else:
                cursor.execute(
                    """
                    SELECT e.chunk_text, e.risk_score, e.chunk_type, d.doc_type, d.filename, e.embedding_vector
                    FROM embeddings e
                    JOIN documents d ON e.document_id = d.id
                    """
                )
            
            results = cursor.fetchall()
            
            if not results:
                return []
            
            # Get all embeddings and compute similarity
            similar_clauses = []
            for result in results:
                # Unpack the result based on whether a clause_type was provided
                if clause_type:
                    chunk_text, risk_score, doc_type, filename, db_embedding_array = result
                    chunk_type = clause_type
                else:
                    chunk_text, risk_score, chunk_type, doc_type, filename, db_embedding_array = result
                
                # Convert PostgreSQL array to numpy array
                db_embedding = np.array(db_embedding_array, dtype=np.float32)
                
                # Calculate similarity
                similarity = cosine_similarity([embedding], [db_embedding])[0][0]
                
                similar_clauses.append({
                    'text': chunk_text,
                    'similarity': similarity,
                    'risk_score': risk_score,
                    'type': chunk_type,
                    'doc_type': doc_type,
                    'filename': filename
                })
            
            # Sort by similarity and return top matches
            similar_clauses.sort(key=lambda x: x['similarity'], reverse=True)
            return similar_clauses[:limit]
    
    def get_average_risk_scores(self) -> Dict[str, float]:
        """Retrieve average risk scores by clause type from historical data."""
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT clause_type, AVG(risk_score) as avg_score
                FROM risk_analysis
                GROUP BY clause_type
                """
            )
            results = cursor.fetchall()
            return {clause_type: avg_score for clause_type, avg_score in results}
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()


class ContractAnalyzer:
    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize the contract analyzer with database manager."""
        self.db_manager = db_manager or DatabaseManager()
        
    def generate_document_summary(self, full_text: str, doc_type: str, important_clauses: List[Dict]) -> str:
        """
        Generate a concise summary of the document using Together AI's LLM.
        Falls back to rule-based summary if AI fails.
        """
        try:
            # Prepare the important clauses information
            clauses_info = ""
            if important_clauses:
                clauses_info = "Important clauses identified:\n"
                for clause in important_clauses[:5]:  # Limit to avoid token limits
                    clauses_info += f"- {clause['type'].replace('_', ' ')} (risk: {clause['risk_level']}): {clause['text'][:100]}...\n"
            
            # Calculate overall risk score
            overall_risk = sum(c['risk_score'] for c in important_clauses) / len(important_clauses) if important_clauses else 0
            
            # Count risk levels
            risk_counts = {"high": 0, "medium": 0, "low": 0, "negligible": 0}
            for clause in important_clauses:
                risk_level = clause.get('risk_level', 'low')
                risk_counts[risk_level] += 1
            
            # Prepare prompt for Together AI
            prompt = f"""You're a legal document analyzer. Summarize the following legal document concisely.
Document type: {doc_type}
Risk assessment: Overall risk score {overall_risk:.2f}, with {risk_counts['high']} high risk, {risk_counts['medium']} medium risk, and {risk_counts['low']} low risk clauses.

{clauses_info}

First 3000 characters of document:
{full_text[:3000]}

Generate a professional summary in 3-4 sentences. Mention document type, purpose, and major risk areas if any exist.
"""
            
            # Call Together AI
            response = together_client.chat.completions.create(
                model=TOGETHER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            
            summary_text = response.choices[0].message.content.strip()
            
            # Format the final summary with risk information
            if risk_counts['high'] > 0 or risk_counts['medium'] > 0:
                high_risk_clauses = [c for c in important_clauses if c.get('risk_level') in ['high', 'medium']]
                clause_types = ", ".join(set(c['type'].replace('_', ' ') for c in high_risk_clauses[:3]))
                
                final_summary = (
                    f"{summary_text}\n\n"
                    f"Key areas of concern include {clause_types}. "
                    f"The document has an overall risk score of {overall_risk:.2f} "
                    f"with {risk_counts['high']} high-risk clauses identified."
                )
            else:
                final_summary = (
                    f"{summary_text}\n\n"
                    f"No high-risk clauses were identified. The document has an overall risk score of {overall_risk:.2f}."
                )
            
            return final_summary
            
        except Exception as e:
            print(f"AI-based summary generation failed: {str(e)}")
            
            # Fall back to rule-based summary
            doc_descriptions = {
                "CONTRACT": "a sales contract that outlines terms and conditions between parties",
                "INVOICE": "an invoice document requesting payment for goods or services",
                "NDA": "a non-disclosure agreement protecting confidential information"
            }
            
            # Count clauses by risk level
            risk_counts = {"high": 0, "medium": 0, "low": 0, "negligible": 0}
            for clause in important_clauses:
                risk_level = clause.get('risk_level', 'low')
                risk_counts[risk_level] += 1
            
            # Generate simple summary
            fallback_summary = (
                f"This document is {doc_descriptions.get(doc_type, 'a legal document')}. "
                f"Analysis identified {len(important_clauses)} important clauses, including "
                f"{risk_counts['high']} high-risk, {risk_counts['medium']} medium-risk, and {risk_counts['low']} low-risk items. "
            )
            
            # Add information about high risk clauses if present
            if risk_counts['high'] > 0:
                high_risk_types = [c['type'].replace('_', ' ') for c in important_clauses if c.get('risk_level') == 'high']
                if high_risk_types:
                    fallback_summary += f"High-risk areas include {', '.join(high_risk_types[:3])}."
            
            return fallback_summary
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR."""
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Cannot read image file: {image_path}")
        
        # Preprocessing for better OCR
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Apply OCR
        text = pytesseract.image_to_string(gray)
        return text
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF."""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text()
        # print(text)   
        return text
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from a document based on file type."""
        _, file_ext = os.path.splitext(file_path)
        file_ext = file_ext.lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png']:
            return self.extract_text_from_image(file_path)
        elif file_ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    def detect_document_type(self, text: str) -> str:
        """
        Detect document type using Together AI instead of simple regex.
        Falls back to regex-based detection if AI fails.
        """
        try:
            # Prepare prompt for Together AI
            prompt = f"""You are an expert in document classification. Classify the following document text into one of these categories:
1. NDA (Non-disclosure agreement)
2. INVOICE (Invoice document)
3. CONTRACT (General contract)

Response must be ONLY one word: NDA, INVOICE, or CONTRACT.

Document text excerpt (first 1000 characters):
{text[:1000]}

Classification:"""
            
            # Call Together AI
            response = together_client.chat.completions.create(
                model=TOGETHER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10
            )
            
            classification = response.choices[0].message.content.strip().upper()
            
            # Validate response
            if classification in ["NDA", "INVOICE", "CONTRACT"]:
                return classification
            else:
                # Fall back to regex if AI returns invalid type
                print(f"AI returned invalid document type: {classification}. Falling back to regex.")
                return self._detect_document_type_regex(text)
                
        except Exception as e:
            print(f"AI-based document detection failed: {str(e)}. Falling back to regex.")
            return self._detect_document_type_regex(text)
    
    def _detect_document_type_regex(self, text: str) -> str:
        """Detect document type based on content using regex (fallback method)."""
        text_lower = text.lower()
        
        # Simple heuristics to detect document type
        if re.search(r'non-disclosure|nda|confidential\s+information', text_lower):
            return "NDA"
        elif re.search(r'invoice|payment\s+due|bill\s+to', text_lower):
            return "INVOICE"
        else:
            return "CONTRACT"  # Default type
    
    def split_into_chunks(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunks.append(text[start:end])
            start += chunk_size - overlap
        
        return chunks
    
    def identify_clause_type(self, text: str) -> Optional[str]:
        """
        Identify the type of clause using Together AI.
        Falls back to regex for reliability and performance.
        """
        # For efficiency, we'll keep the regex approach since clause identification
        # happens numerous times and making an API call for each would be expensive
        text_lower = text.lower()
        
        clause_patterns = {
            "payment_terms": r"payment\s+terms|pay\s+within|invoice\s+due|price|fee",
            "termination": r"terminat(e|ion)|cancel|end\s+of\s+contract",
            "liability": r"liab(le|ility)|responsible|obligation",
            "confidentiality": r"confidential|non-disclosure|secret|proprietary",
            "intellectual_property": r"intellectual\s+property|copyright|patent|trademark",
            "data_protection": r"data\s+protection|privacy|personal\s+data|gdpr",
            "warranty": r"warrant(y|ies)|guarantee",
            "indemnification": r"indemnif(y|ication)|hold\s+harmless",
            "force_majeure": r"force\s+majeure|act\s+of\s+god|unforeseen",
            "non_compete": r"non-compete|competition|restraint\s+of\s+trade",
            "governing_law": r"governing\s+law|jurisdiction|applicable\s+law"
        }
        
        for clause_type, pattern in clause_patterns.items():
            if re.search(pattern, text_lower):
                return clause_type
        
        return None  # Unknown clause type
    
    def generate_embeddings(self, chunks: List[str]) -> List[Dict]:
        """Generate embeddings for text chunks and identify clause types."""
        result = []
        
        for chunk in chunks:
            # Generate embedding
            embedding = model.encode(chunk, convert_to_tensor=True).detach().numpy()
            
            # Identify clause type
            clause_type = self.identify_clause_type(chunk)
            
            chunk_data = {
                'text': chunk,
                'embedding': embedding,
                'type': clause_type
            }

            result.append(chunk_data)
        
        return result
    
    def calculate_risk_score(self, clause_text: str, clause_type: str, similar_clauses: List[Dict]) -> Dict:
        """Calculate risk score for a clause based on similar past clauses."""
        # If we have similar clauses, use weighted average of their risk scores
        if similar_clauses:
            weighted_scores = []
            total_weight = 0
            
            for clause in similar_clauses:
                similarity = clause.get('similarity', 0)
                weight = similarity  # Use similarity as weight
                risk_score = clause.get('risk_score', 0)
                
                weighted_scores.append(weight * risk_score)
                total_weight += weight
            
            if total_weight > 0:
                final_score = sum(weighted_scores) / total_weight
            else:
                final_score = 0.5  # Default mid-level risk if no weights
        else:
            # Default risk assessment based on clause type if no similar clauses
            default_risks = {
                "payment_terms": 0.6,
                "termination": 0.7,
                "liability": 0.8,
                "confidentiality": 0.7,
                "intellectual_property": 0.7,
                "data_protection": 0.8,
                "warranty": 0.6,
                "indemnification": 0.7,
                "force_majeure": 0.5,
                "non_compete": 0.6,
                "governing_law": 0.4
            }
            final_score = default_risks.get(clause_type, 0.5)
        
        # Determine risk level
        if final_score >= RISK_THRESHOLDS["high"]:
            risk_level = "high"
        elif final_score >= RISK_THRESHOLDS["medium"]:
            risk_level = "medium"
        elif final_score >= RISK_THRESHOLDS["low"]:
            risk_level = "low"
        else:
            risk_level = "negligible"
        
        return {
            "clause_type": clause_type,
            "clause_text": clause_text,
            "risk_score": final_score,
            "risk_level": risk_level,
            "risk_explanation": self.generate_risk_explanation(clause_type, final_score)
        }
    
    def generate_risk_explanation(self, clause_type: str, risk_score: float) -> str:
        """
        Generate explanation for risk score using Together AI.
        Falls back to predefined explanations for efficiency and reliability.
        """
        # For consistency and efficiency, we'll keep using the predefined explanations
        # as they provide reliable and standardized responses
        explanations = {
            "payment_terms": {
                "high": "Payment terms are unfavorable and may lead to cash flow issues.",
                "medium": "Payment terms have some concerns that should be reviewed.",
                "low": "Payment terms are generally acceptable with minor concerns.",
                "negligible": "Payment terms are standard and favorable."
            },
            "termination": {
                "high": "Termination clause heavily favors the other party and may restrict your options.",
                "medium": "Termination provisions have some imbalance that should be addressed.",
                "low": "Termination terms are generally fair with some minor issues.",
                "negligible": "Termination terms are balanced and protect your interests."
            },
            "liability": {
                "high": "Liability clauses expose you to significant risk without adequate protection.",
                "medium": "Liability provisions have some concerning terms that should be negotiated.",
                "low": "Liability clauses have minor issues but are largely acceptable.",
                "negligible": "Liability provisions are well-balanced and provide adequate protection."
            },
            "confidentiality": {
                "high": "Confidentiality provisions may not adequately protect sensitive information.",
                "medium": "Confidentiality terms have gaps that should be addressed.",
                "low": "Confidentiality provisions are generally adequate with minor concerns.",
                "negligible": "Confidentiality terms are comprehensive and protective."
            },
            "intellectual_property": {
                "high": "IP provisions may compromise ownership rights or grant excessive licenses.",
                "medium": "IP terms have some concerning elements that should be reviewed.",
                "low": "IP clauses are generally favorable with minor concerns.",
                "negligible": "IP provisions properly protect your intellectual property."
            },
            "data_protection": {
                "high": "Data protection provisions don't meet compliance requirements or create liability.",
                "medium": "Data protection terms need strengthening to ensure proper compliance.",
                "low": "Data protection clauses are generally adequate with minor gaps.",
                "negligible": "Data protection provisions are comprehensive and compliant."
            },
            "warranty": {
                "high": "Warranty provisions create extensive obligations with limited protection.",
                "medium": "Warranty terms should be negotiated to improve balance.",
                "low": "Warranty clauses are generally acceptable with minor concerns.",
                "negligible": "Warranty provisions are reasonable and well-balanced."
            },
            "indemnification": {
                "high": "Indemnification clauses create significant one-sided obligations.",
                "medium": "Indemnification terms are imbalanced and should be negotiated.",
                "low": "Indemnification provisions have minor concerns but are generally fair.",
                "negligible": "Indemnification clauses are fair and provide mutual protection."
            },
            "force_majeure": {
                "high": "Force majeure provisions are inadequate or missing critical scenarios.",
                "medium": "Force majeure terms should be expanded to cover additional scenarios.",
                "low": "Force majeure clauses are generally adequate with minor gaps.",
                "negligible": "Force majeure provisions are comprehensive and well-balanced."
            },
            "non_compete": {
                "high": "Non-compete provisions are overly restrictive and may be unenforceable.",
                "medium": "Non-compete terms are broadly drafted and should be narrowed.",
                "low": "Non-compete clauses are generally reasonable with minor concerns.",
                "negligible": "Non-compete provisions are narrowly tailored and reasonable."
            },
            "governing_law": {
                "high": "Governing law/jurisdiction creates significant disadvantage.",
                "medium": "Governing law/jurisdiction may create some procedural challenges.",
                "low": "Governing law/jurisdiction provisions have minor concerns.",
                "negligible": "Governing law/jurisdiction terms are favorable or neutral."
            }
        }
        
        if clause_type not in explanations:
            return "This clause should be reviewed by legal counsel."
        
        if risk_score >= RISK_THRESHOLDS["high"]:
            return explanations[clause_type]["high"]
        elif risk_score >= RISK_THRESHOLDS["medium"]:
            return explanations[clause_type]["medium"]
        elif risk_score >= RISK_THRESHOLDS["low"]:
            return explanations[clause_type]["low"]
        else:
            return explanations[clause_type]["negligible"]
    
    def analyze_document(self, file_path: str) -> Dict:
        """
        Main function to analyze a document.
        Process: extract text -> detect type -> generate embeddings -> analyze risk
        """
        # Extract text from document
        full_text = self.extract_text(file_path)
        
        # Detect document type
        doc_type = self.detect_document_type(full_text)
        
        # Split text into chunks
        chunks = self.split_into_chunks(full_text)
        
        # Generate embeddings and identify clause types
        chunks_with_embeddings = self.generate_embeddings(chunks)
        
        # Insert document into database
        document_id = self.db_manager.insert_document(
            filename=os.path.basename(file_path),
            doc_type=doc_type,
            full_text=full_text,
            metadata={"length": len(full_text), "chunks": len(chunks)}
        )
        
        # Process each chunk for risk analysis
        risk_analyses = []
        important_clauses = []
        
        for chunk_data in chunks_with_embeddings:
            # Skip chunks without identified clause type
            if not chunk_data.get('type'):
                continue
            
            # Get similar clauses from database for comparison
            similar_clauses = self.db_manager.get_similar_clauses(
                embedding=chunk_data['embedding'],
                clause_type=chunk_data['type']
            )
            
            # Calculate risk score
            risk_analysis = self.calculate_risk_score(
                clause_text=chunk_data['text'],
                clause_type=chunk_data['type'],
                similar_clauses=similar_clauses
            )
            
            # Add risk score to chunk data
            chunk_data['risk_score'] = risk_analysis['risk_score']
            
            # Add to important clauses if it's a key clause type or high risk
            if chunk_data['type'] in IMPORTANT_CLAUSES or risk_analysis['risk_score'] >= RISK_THRESHOLDS["medium"]:
                important_clauses.append({
                    'type': chunk_data['type'],
                    'text': chunk_data['text'],
                    'risk_score': risk_analysis['risk_score'],
                    'risk_level': risk_analysis['risk_level'],
                    'explanation': risk_analysis['risk_explanation']
                })
            
            risk_analyses.append(risk_analysis)
        
        # Insert embeddings and risk analysis into database
        self.db_manager.insert_embeddings(document_id, chunks_with_embeddings)
        self.db_manager.insert_risk_analysis(document_id, risk_analyses)
        
        # Generate AI-based document summary
        brief_summary = self.generate_document_summary(full_text, doc_type, important_clauses)
        
        summary = {
            'document_id': document_id,
            'filename': os.path.basename(file_path),
            'document_type': doc_type,
            'summary': brief_summary,
            'important_clauses': important_clauses,
            'overall_risk_score': sum(a['risk_score'] for a in risk_analyses) / len(risk_analyses) if risk_analyses else 0,
            'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return summary
    
    def query_document(self, query: str, document_id: Optional[int] = None) -> Dict:
        """
        Query function that uses Together AI to answer questions about the document.
        """
        # Get document text
        document_text = ""
        document_info = {}
        
        if document_id:
            with self.db_manager.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT full_text, filename, doc_type FROM documents WHERE id = %s", 
                    (document_id,)
                )
                result = cursor.fetchone()
                if result:
                    document_text, filename, doc_type = result
                    document_info = {'filename': filename, 'doc_type': doc_type}
        else:
            # If no specific document_id, get the most recent document
            with self.db_manager.conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, full_text, filename, doc_type FROM documents ORDER BY upload_date DESC LIMIT 1"
                )
                result = cursor.fetchone()
                if result:
                    document_id, document_text, filename, doc_type = result
                    document_info = {'filename': filename, 'doc_type': doc_type}
        
        if not document_text:
            return {
                'query': query,
                'answer': "No document found to query.",
                'document_info': {},
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Get answer using Together AI
        answer = self.generate_together_answer(query, document_text)
        
        return {
            'query': query,
            'answer': answer,
            'document_info': document_info,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def generate_together_answer(self, query: str, document_text: str) -> str:
        """
        Generate an answer to the query using Together AI's LLM.
        """
        try:
            # Find potential relevant sections to reduce context size
            query_terms = query.lower().split()
            paragraphs = document_text.split('\n\n')
            
            # Score paragraphs by relevance
            scored_paragraphs = []
            for para in paragraphs:
                if len(para.strip()) < 10:  # Skip very short paragraphs
                    continue
                    
                # Simple relevance scoring
                score = sum(1 for term in query_terms if term in para.lower())
                scored_paragraphs.append((score, para))
            
            # Sort by relevance score
            scored_paragraphs.sort(reverse=True)
            
            # Take top relevant paragraphs that fit within context limits
            context = ""
            for _, para in scored_paragraphs[:7]:  # Limit to top 7 paragraphs
                if len(context) + len(para) < 4000:  # Keep context size manageable
                    context += para + "\n\n"
            
            # If we found no relevant context, use the beginning of the document
            if not context:
                context = document_text[:4000]
            # print(context)
            # print(query)
            # Prepare prompt for Together AI
            prompt = f"""I need you to answer a question about a document. document text is given ahead. give good answers(longer when required)"

question: {query}

Document text:
{context}

Answer: start point wise"""
            
            # Call Together AI
            response = together_client.chat.completions.create(
                model=TOGETHER_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.2  # Lower temperature for more factual responses
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
                
        except Exception as e:
            print(f"Together AI error: {str(e)}")
            
            # Very basic fallback with keyword matching if AI fails
            query_lower = query.lower()
            lines = document_text.split('\n')
            
            relevant_lines = []
            for line in lines:
                if any(term in line.lower() for term in query_lower.split()):
                    relevant_lines.append(line)
            
            if relevant_lines:
                return f"I found these relevant sections in the document:\n\n" + "\n".join(relevant_lines[:5])
            else:
                return "I couldn't find specific information related to your query in the document."


def print_analysis_summary(analysis: Dict):
    """Print a formatted summary of the document analysis."""
    print("\n" + "="*80)
    print(f"DOCUMENT ANALYSIS SUMMARY: {analysis['filename']}")
    print("="*80)
    print(f"Document Type: {analysis['document_type']}")
    print(f"Analysis Date: {analysis['analysis_date']}")
    print(f"Overall Risk Score: {analysis['overall_risk_score']:.2f}")
    print("-"*80)
    
    # Print LLM-generated summary if available
    if 'summary' in analysis:
        print("DOCUMENT SUMMARY:")
        print("-"*80)
        print(analysis['summary'])
        print("-"*80)
    
    print("IMPORTANT CLAUSES AND RISKS:")
    print("-"*80)
    
    # Group clauses by risk level for better readability
    risk_levels = ["high", "medium", "low", "negligible"]
    for level in risk_levels:
        level_clauses = [c for c in analysis['important_clauses'] if c['risk_level'] == level]
        
        if level_clauses:
            print(f"\n{level.upper()} RISK CLAUSES:")
            for clause in level_clauses:
                print(f"\n  • {clause['type'].replace('_', ' ').title()}:")
                print(f"    Risk Score: {clause['risk_score']:.2f}")
                print(f"    Explanation: {clause['explanation']}")
                print(f"    Text snippet: \"{clause['text'][:150]}...\"")
    
    print("\n" + "="*80)
    print("For more details or to query specific aspects, use the query function.")
    print("="*80 + "\n")


def interactive_query_mode(analyzer: ContractAnalyzer, document_id: Optional[int] = None):
    """Interactive mode for querying the document using Together AI."""
    print("\nEntering interactive query mode. Type 'exit' to quit.")
    print("Ask any question about the document and Together AI will search for relevant information.")
    
    while True:
        query = input("\nEnter your query about the document: ")
        
        if query.lower() in ['exit', 'quit', 'q']:
            print("Exiting query mode.")
            break
        
        print("\nProcessing query using Llama 3.3 70B model...")
        
        # Process query with Together AI
        response = analyzer.query_document(query, document_id)
        
        # Print answer from LLM
        print("\nANSWER:")
        print("-"*80)
        print(response['answer'])
        print("-"*80)
        
        # Print document information
        if response['document_info']:
            print(f"Source: {response['document_info'].get('filename', 'Unknown document')} "
                  f"({response['document_info'].get('doc_type', 'Unknown type')})")
            print("-"*80)


def main():
    """Main function to run the contract analyzer."""
    parser = argparse.ArgumentParser(description='Contract Analyzer')
    parser.add_argument('file_path', help='Path to the document file (PDF, JPG, PNG)')
    parser.add_argument('--query', '-q', action='store_true', help='Enter interactive query mode after analysis')
    parser.add_argument('--quiet', '-s', action='store_true', help='Suppress detailed output')
    
    args = parser.parse_args()
    
    # Initialize analyzer
    db_manager = DatabaseManager()
    analyzer = ContractAnalyzer(db_manager)
    
    try:
        # Analyze document
        analysis = analyzer.analyze_document(args.file_path)
        
        # Print analysis summary
        if not args.quiet:
            print_analysis_summary(analysis)
        
        # If query mode is enabled, enter interactive mode
        if args.query:
            interactive_query_mode(analyzer, analysis['document_id'])
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Close database connection
        db_manager.close()


if __name__ == "__main__":
    main()