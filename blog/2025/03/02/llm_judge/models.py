from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

@dataclass
class QAPair:
    question: str
    answer: str
    model_name: str

@dataclass
class DimensionAnalysis:
    thinking: str
    score: int

@dataclass
class DetailedJudgmentScores:
    helpfulness: DimensionAnalysis
    relevance: DimensionAnalysis
    accuracy: DimensionAnalysis
    depth: DimensionAnalysis
    creativity: DimensionAnalysis
    level_of_detail: DimensionAnalysis
    
    def __str__(self) -> str:
        result = []
        for dimension in ['helpfulness', 'relevance', 'accuracy', 'depth', 'creativity', 'level_of_detail']:
            analysis = getattr(self, dimension)
            result.extend([
                f"\n{dimension.title()}:",
                f"Thinking: {analysis.thinking}",
                f"Score: {analysis.score}/10",
                ""
            ])
        return "\n".join(result)

@dataclass
class QAPairTokens:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    dimension_tokens: Optional[Dict[str, Tuple[int, int]]] = None

@dataclass
class QAPairTiming:
    qa_index: int
    question: str
    total_time: float
    tokens: QAPairTokens
    dimension_times: Optional[Dict[str, float]] = None

@dataclass
class ExperimentRun:
    combined_time: float
    parallel_time: float
    combined_pair_times: List[QAPairTiming]
    parallel_pair_times: List[QAPairTiming]
    
    @property
    def time_difference(self) -> float:
        """B - A: Positive means parallel was slower"""
        return self.parallel_time - self.combined_time
    
    @property
    def percent_difference(self) -> float:
        """((B - A) / A) * 100: Positive means parallel was slower"""
        if self.combined_time == 0:
            return float('inf') if self.parallel_time > 0 else 0.0
        return (self.time_difference / self.combined_time) * 100

    @property
    def combined_tokens(self) -> Tuple[int, int, int]:
        """Returns (input_tokens, output_tokens, total_tokens) for combined approach"""
        input_tokens = sum(pt.tokens.input_tokens for pt in self.combined_pair_times)
        output_tokens = sum(pt.tokens.output_tokens for pt in self.combined_pair_times)
        return input_tokens, output_tokens, input_tokens + output_tokens

    @property
    def parallel_tokens(self) -> Tuple[int, int, int]:
        """Returns (input_tokens, output_tokens, total_tokens) for parallel approach"""
        input_tokens = sum(pt.tokens.input_tokens for pt in self.parallel_pair_times)
        output_tokens = sum(pt.tokens.output_tokens for pt in self.parallel_pair_times)
        return input_tokens, output_tokens, input_tokens + output_tokens 