"""
Embeddings generation module for Nexcomply application
Uses Sentence-BERT for generating embeddings
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class EmbeddingGenerator:
    """Class to handle embedding generation operations"""
    
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Initialize embedding generator with Sentence-BERT model
        
        Args:
            model_name: Name of the Sentence-BERT model
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load Sentence-BERT model"""
        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Error loading Sentence-BERT model: {str(e)}")
            self.model = None

    @property
    def has_model(self):
        """Return True if the neural embedding model is available."""
        return self.model is not None

    def generate_embedding(self, text):
        """
        Generate embedding for a single text
        
        Args:
            text: Text to generate embedding for
            
        Returns:
            np.ndarray: Embedding vector
        """
        if not text or not self.model:
            return np.array([])
        
        try:
            embedding = self.model.encode([text])
            return embedding[0]
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            return np.array([])
    
    def generate_embeddings(self, texts):
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts
            
        Returns:
            np.ndarray: Array of embedding vectors
        """
        if not texts or not self.model:
            return np.array([])
        
        try:
            embeddings = self.model.encode(texts)
            return embeddings
        except Exception as e:
            print(f"Error generating embeddings: {str(e)}")
            return np.array([])
    
    def batch_generate_embeddings(self, text_dict):
        """
        Generate embeddings for a dictionary of texts
        
        Args:
            text_dict: Dictionary of {key: text}
            
        Returns:
            dict: Dictionary of {key: embedding}
        """
        embeddings_dict = {}
        
        for key, text in text_dict.items():
            if isinstance(text, str) and len(text) > 0:
                embedding = self.generate_embedding(text)
                embeddings_dict[key] = embedding
        
        return embeddings_dict


class SimilarityCalculator:
    """Class to handle similarity calculations"""
    
    @staticmethod
    def calculate_cosine_similarity(embedding1, embedding2):
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score
        """
        if len(embedding1) == 0 or len(embedding2) == 0:
            return 0.0
        
        try:
            # Reshape embeddings if needed
            if len(embedding1.shape) == 1:
                embedding1 = embedding1.reshape(1, -1)
            if len(embedding2.shape) == 1:
                embedding2 = embedding2.reshape(1, -1)
            
            similarity = cosine_similarity(embedding1, embedding2)[0][0]
            return float(similarity)
        except Exception as e:
            print(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_similarity_matrix(embeddings1, embeddings2):
        """
        Calculate similarity matrix between two sets of embeddings
        
        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings
            
        Returns:
            np.ndarray: Similarity matrix
        """
        try:
            similarity_matrix = cosine_similarity(embeddings1, embeddings2)
            return similarity_matrix
        except Exception as e:
            print(f"Error calculating similarity matrix: {str(e)}")
            return np.array([])
    
    @staticmethod
    def find_most_similar(query_embedding, candidate_embeddings, top_k=5):
        """
        Find top-k most similar embeddings
        
        Args:
            query_embedding: Query embedding
            candidate_embeddings: Candidate embeddings
            top_k: Number of top results to return
            
        Returns:
            list: List of (index, similarity_score) tuples
        """
        if len(query_embedding) == 0 or len(candidate_embeddings) == 0:
            return []
        
        try:
            # Reshape if needed
            if len(query_embedding.shape) == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            results = [(int(idx), float(similarities[idx])) for idx in top_indices]
            return results
        except Exception as e:
            print(f"Error finding similar embeddings: {str(e)}")
            return []


# Singleton instance for reuse
_embedding_generator_instance = None


def get_embedding_generator(model_name='all-MiniLM-L6-v2'):
    """
    Get or create embedding generator instance (singleton pattern)
    
    Args:
        model_name: Name of the Sentence-BERT model
        
    Returns:
        EmbeddingGenerator: Embedding generator instance
    """
    global _embedding_generator_instance
    if _embedding_generator_instance is None:
        _embedding_generator_instance = EmbeddingGenerator(model_name)
    return _embedding_generator_instance


def generate_framework_embeddings(frameworks):
    """
    Generate embeddings for compliance frameworks
    
    Args:
        frameworks: Dictionary of frameworks
        
    Returns:
        dict: Dictionary of framework embeddings
    """
    generator = get_embedding_generator()
    embeddings = {}
    
    for framework_name, framework_content in frameworks.items():
        if isinstance(framework_content, str):
            embeddings[framework_name] = generator.generate_embedding(framework_content)
    
    return embeddings


def generate_policy_embeddings(policies):
    """
    Generate embeddings for internal policies
    
    Args:
        policies: Dictionary of policies
        
    Returns:
        dict: Dictionary of policy embeddings
    """
    generator = get_embedding_generator()
    embeddings = {}
    
    for policy_name, policy_content in policies.items():
        if isinstance(policy_content, str):
            embeddings[policy_name] = generator.generate_embedding(policy_content)
    
    return embeddings


def compare_texts(text1, text2):
    """
    Compare two texts using embeddings
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        float: Similarity score
    """
    generator = get_embedding_generator()
    calculator = SimilarityCalculator()
    
    embedding1 = generator.generate_embedding(text1)
    embedding2 = generator.generate_embedding(text2)
    
    similarity = calculator.calculate_cosine_similarity(embedding1, embedding2)
    return similarity
