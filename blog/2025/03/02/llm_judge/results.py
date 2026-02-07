from typing import List
import json
from statistics import mean, stdev
from pathlib import Path

from .models import (
    QAPair, 
    DetailedJudgmentScores, 
    ExperimentRun,
    QAPairTiming
)
from .config import FileConfig

class ResultWriter:
    def __init__(self, config: FileConfig = None):
        self.config = config or FileConfig()
        
        # Ensure the results directories exist
        jsonl_path = Path(self.config.RESULTS_JSONL)
        txt_path = Path(self.config.RESULTS_TXT)
        
        # Create parent directories if they don't exist
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create files if they don't exist (but don't clear them)
        if not jsonl_path.exists():
            jsonl_path.touch()
        if not txt_path.exists():
            txt_path.touch()

    def write_run_results(
        self,
        qa_pairs: List[QAPair],
        run: ExperimentRun,
        combined_scores: List[DetailedJudgmentScores],
        parallel_scores: List[DetailedJudgmentScores]
    ) -> None:
        """Write results for a single experiment run to both JSONL and TXT files"""
        self._write_to_jsonl(qa_pairs, run, combined_scores, parallel_scores)
        self._write_to_txt(qa_pairs, run, combined_scores, parallel_scores)

    def _write_to_jsonl(
        self,
        qa_pairs: List[QAPair],
        run: ExperimentRun,
        combined_scores: List[DetailedJudgmentScores],
        parallel_scores: List[DetailedJudgmentScores]
    ) -> None:
        """Write results to JSONL file"""
        def format_dimension_data(dimension_name: str, scores: DetailedJudgmentScores, timing: QAPairTiming, is_parallel: bool):
            dimension_data = {
                "thinking": getattr(scores, dimension_name.lower()).thinking,
                "score": getattr(scores, dimension_name.lower()).score,
            }
            
            if is_parallel and timing.dimension_times:
                dimension_data.update({
                    "input_tokens": timing.tokens.dimension_tokens[dimension_name][0],
                    "output_tokens": timing.tokens.dimension_tokens[dimension_name][1],
                    "time_ms": int(timing.dimension_times[dimension_name] * 1000)
                })
            else:
                dimension_data.update({
                    "input_tokens": None,
                    "output_tokens": None,
                    "time_ms": None
                })
                
            return dimension_data

        def create_result_entry(qa_pair: QAPair, scores: DetailedJudgmentScores, timing: QAPairTiming, is_parallel: bool):
            dimensions = ['Helpfulness', 'Relevance', 'Accuracy', 'Depth', 'Creativity', 'Level_of_Detail']
            
            entry = {
                "judge_type": "parallel" if is_parallel else "combined",
                "question": qa_pair.question,
                "answer": qa_pair.answer,
                "model": qa_pair.model_name
            }
            
            for dim in dimensions:
                entry[dim.lower()] = format_dimension_data(dim, scores, timing, is_parallel)
            
            entry.update({
                "sum_input_tokens": timing.tokens.input_tokens,
                "sum_output_tokens": timing.tokens.output_tokens,
                "overall_time_ms": int(timing.total_time * 1000)
            })
            
            return entry

        with Path(self.config.RESULTS_JSONL).open('a', encoding='utf-8') as f:
            # Write combined approach results
            for i, (qa_pair, scores, timing) in enumerate(zip(qa_pairs, combined_scores, run.combined_pair_times)):
                entry = create_result_entry(qa_pair, scores, timing, is_parallel=False)
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            # Write parallel approach results
            for i, (qa_pair, scores, timing) in enumerate(zip(qa_pairs, parallel_scores, run.parallel_pair_times)):
                entry = create_result_entry(qa_pair, scores, timing, is_parallel=True)
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    def _write_to_txt(
        self,
        qa_pairs: List[QAPair],
        run: ExperimentRun,
        combined_scores: List[DetailedJudgmentScores],
        parallel_scores: List[DetailedJudgmentScores]
    ) -> None:
        """Write detailed results to text file"""
        with open(self.config.RESULTS_TXT, 'a') as f:
            f.write("\n=== New Experiment Run ===\n")
            
            # Write QA pairs and their scores
            f.write("\nCondition A (Combined):\n")
            for i, (qa_pair, scores) in enumerate(zip(qa_pairs, combined_scores)):
                f.write(f"\n--- QA Pair {i+1} ---\n")
                f.write(f"Q: {qa_pair.question}\n")
                f.write(f"A ({qa_pair.model_name}): {qa_pair.answer}\n")
                f.write(str(scores) + "\n")
            
            f.write("\nCondition B (Parallel):\n")
            for i, (qa_pair, scores) in enumerate(zip(qa_pairs, parallel_scores)):
                f.write(f"\n--- QA Pair {i+1} ---\n")
                f.write(f"Q: {qa_pair.question}\n")
                f.write(f"A ({qa_pair.model_name}): {qa_pair.answer}\n")
                f.write(str(scores) + "\n")
            
            # Write timing and token statistics
            self._write_statistics(f, run)

    def _write_statistics(self, f, run: ExperimentRun) -> None:
        """Write timing and token statistics to the given file handle"""
        f.write("\n=== Performance Statistics ===\n")
        f.write(f"\nCombined Approach Time: {run.combined_time:.2f}s")
        f.write(f"\nParallel Approach Time: {run.parallel_time:.2f}s")
        f.write(f"\nTime Difference (B-A): {run.time_difference:.2f}s")
        f.write(f"\nPercentage Difference: {run.percent_difference:.1f}%\n")

        f.write("\n=== Token Usage ===\n")
        combined_in, combined_out, combined_total = run.combined_tokens
        parallel_in, parallel_out, parallel_total = run.parallel_tokens
        
        f.write(f"\nCombined Approach: {combined_in} in, {combined_out} out ({combined_total} total)")
        f.write(f"\nParallel Approach: {parallel_in} in, {parallel_out} out ({parallel_total} total)")
        
        token_diff = parallel_total - combined_total
        token_percent = (token_diff / combined_total) * 100 if combined_total else 0
        f.write(f"\nToken Difference (B-A): {token_diff:,} ({token_percent:.1f}%)\n") 