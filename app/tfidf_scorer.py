from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re
from typing import List, Dict, Tuple

class TFIDFSentenceScorer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words=None,  # Handle both languages
            ngram_range=(1, 2),
            max_features=5000
        )
        
    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences for both Bangla and English"""
        # Split on common sentence endings
        sentences = re.split(r'[।.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences
    
    def calculate_sentence_importance(self, text: str) -> List[Dict[str, any]]:
        """Calculate TF-IDF importance scores for sentences"""
        # Clean corrupted characters
        text = re.sub(r'\(cid:\d+\)', '', text)
        text = re.sub(r'[\ufeff\u200b-\u200f\u202a-\u202e]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        sentences = self.split_sentences(text)
        
        if len(sentences) < 2:
            return [{"sentence": text, "score": 1.0, "rank": 1}]
        
        try:
            # Calculate TF-IDF matrix
            tfidf_matrix = self.vectorizer.fit_transform(sentences)
            
            # Calculate sentence scores (sum of TF-IDF values)
            sentence_scores = np.array(tfidf_matrix.sum(axis=1)).flatten()
            
            # Normalize scores to 0-1 range
            if sentence_scores.max() > 0:
                sentence_scores = sentence_scores / sentence_scores.max()
            
            # Create results with rankings
            results = []
            for i, (sentence, score) in enumerate(zip(sentences, sentence_scores)):
                results.append({
                    "sentence": sentence,
                    "score": float(score),
                    "rank": i + 1
                })
            
            # Sort by score (descending)
            results.sort(key=lambda x: x["score"], reverse=True)
            
            # Update ranks after sorting
            for i, result in enumerate(results):
                result["rank"] = i + 1
                
            return results
            
        except Exception as e:
            # Fallback: equal importance
            return [{"sentence": s, "score": 1.0/len(sentences), "rank": i+1} 
                   for i, s in enumerate(sentences)]
    
    def get_top_sentences(self, text: str, top_n: int = 3) -> List[str]:
        """Get top N most important sentences"""
        results = self.calculate_sentence_importance(text)
        return [r["sentence"] for r in results[:top_n]]
    
    def highlight_important_sentences(self, text: str, threshold: float = 0.5) -> str:
        """Highlight sentences above importance threshold"""
        results = self.calculate_sentence_importance(text)
        
        highlighted_text = text
        for result in results:
            if result["score"] >= threshold:
                sentence = result["sentence"]
                # Add markdown bold formatting for important sentences
                highlighted_text = highlighted_text.replace(
                    sentence, 
                    f"**{sentence}**"
                )
        
        return highlighted_text