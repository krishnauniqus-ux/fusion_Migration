"""
Mapping Engine - EXACT from vnew.py
"""
from typing import List, Dict
from difflib import SequenceMatcher
from core.models import ColumnMapping
import hashlib
from datetime import datetime

# =============================================================================
# MAPPING ENGINE
# =============================================================================

class MappingEngine:
    """AI-powered column mapping engine"""
    
    @staticmethod
    def calculate_similarity(source: str, target: str) -> float:
        """Calculate similarity score between two column names (0-100)"""
        source_clean = source.lower().replace('_', ' ').replace('-', ' ').strip()
        target_clean = target.lower().replace('_', ' ').replace('-', ' ').strip()
        
        # Exact match
        if source_clean == target_clean:
            return 100.0
        
        # Contains match
        if source_clean in target_clean or target_clean in source_clean:
            return 90.0
        
        # Word overlap
        source_words = set(source_clean.split())
        target_words = set(target_clean.split())
        
        if source_words and target_words:
            intersection = source_words.intersection(target_words)
            union = source_words.union(target_words)
            jaccard = len(intersection) / len(union) if union else 0
            return jaccard * 100
        
        return 0.0
    
    @staticmethod
    def auto_map_columns(source_cols: List[str], target_cols: List[str], 
                        threshold: float = 60.0) -> List[ColumnMapping]:
        """Generate automatic column mappings"""
        mappings = []
        used_targets = set()
        
        for source in source_cols:
            best_match = None
            best_score = 0
            
            for target in target_cols:
                if target in used_targets:
                    continue
                
                score = MappingEngine.calculate_similarity(source, target)
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = target
            
            if best_match:
                mapping = ColumnMapping(
                    source_column=source,
                    target_column=best_match,
                    confidence_score=best_score / 100
                )
                mappings.append(mapping)
                used_targets.add(best_match)
        
        return mappings
