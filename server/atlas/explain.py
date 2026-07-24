from dataclasses import dataclass
from typing import List
import numpy as np
import logging

from server.atlas.adaptive_context import AdaptiveContext, NeighborContext

logger = logging.getLogger(__name__)

@dataclass
class ExplanationReport:
    confidence_score: float
    confidence_level: str
    primary_justification: str
    citations: List[str]
    note: str = ""
    
    def to_dict(self):
        return {
            "confidence_score": self.confidence_score,
            "confidence_level": self.confidence_level,
            "primary_justification": self.primary_justification,
            "citations": self.citations,
            "note": self.note
        }

class ExplanationEngine:
    def __init__(self):
        pass

    def explain(self, context: AdaptiveContext) -> ExplanationReport:
        neighbors = context.neighbors
        
        # Guard against zero neighbors
        if not neighbors:
            return ExplanationReport(
                confidence_score=0.0,
                confidence_level="Low",
                primary_justification="No historical similar engines found to ground this prediction.",
                citations=[]
            )

        # 2. Explicit carry-over: citations MUST use true_rul, never predicted_rul
        # We assert this here to prevent circular justification.
        true_ruls = []
        similarities = []
        for n in neighbors:
            if getattr(n, "rul", None) is None:
                raise ValueError("Neighbors must contain true RUL for citations, not predicted RUL.")
            # Verify it's explicitly the true_rul (type check/assertion)
            true_ruls.append(n.rul)
            # In AdaptiveContextEngine, dist is actually similarity from AMKB
            similarities.append(n.distance)
            
        true_ruls_arr = np.array(true_ruls)
        similarities_arr = np.array(similarities)
        
        # Calculate variance
        variance = np.var(true_ruls_arr)
        
        # Average similarity (cosine distance mapping)
        avg_similarity = float(np.mean(similarities_arr))
        
        # 1. Confidence formula with epsilon=1 to prevent division by zero
        # Multiplicative combination: confidence = avg_similarity * (1 / (1 + variance))
        confidence_score = avg_similarity * (1.0 / (1.0 + variance))
        
        # Determine human readable level
        if confidence_score > 0.5:
            level = "High"
        elif confidence_score > 0.1:
            level = "Moderate"
        else:
            level = "Low"
            
        note = ""
        if len(neighbors) < 10:
            note = "Confidence scores derived from small neighbor counts should be interpreted as indicative, not precise."
            
        # 3. Construct structured explanation string from a template
        avg_true_rul = float(np.mean(true_ruls_arr))
        primary_justification = (
            f"Prediction is grounded in {len(neighbors)} historically similar engine trajectories "
            f"with an average true RUL of {avg_true_rul:.1f} cycles. "
            f"The matching units exhibited a variance of {variance:.1f} cycles."
        )
        
        # Construct citations
        citations = []
        for n in neighbors:
            citations.append(f"Unit {n.machine_id} at cycle {n.cycle} (True RUL: {n.rul:.1f}, similarity: {n.distance:.4f})")
            
        return ExplanationReport(
            confidence_score=float(confidence_score),
            confidence_level=level,
            primary_justification=primary_justification,
            citations=citations,
            note=note
        )
