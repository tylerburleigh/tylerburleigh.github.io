from typing import List, Optional, Tuple
import random
import asyncio
from statistics import mean, stdev

from .models import QAPair, DetailedJudgmentScores, ExperimentRun
from .judge import LLMJudge
from .results import ResultWriter
from .config import FileConfig

class ExperimentRunner:
    def __init__(self, sample_size: int = 16, seed: int = 42):
        self.sample_size = sample_size
        random.seed(seed)
        self.judge = LLMJudge()
        self.result_writer = ResultWriter()
        self.config = FileConfig()

    async def _load_pairwise_data(self) -> List[QAPair]:
        """Load QA pairs from the dataset file"""
        import json
        
        try:
            with open(self.config.DATASET_PATH, 'r') as f:
                data = json.load(f)
            
            qa_pairs = []
            
            # Extract both answers from each example
            for example in data['examples']:
                question = example['query']
                
                # First answer
                answer1 = example['answer']
                model1 = example['answer_by']['model_name'] or 'unknown'
                qa_pairs.append(QAPair(
                    question=question, 
                    answer=answer1,
                    model_name=model1
                ))
                
                # Second answer
                answer2 = example['second_answer']
                model2 = example['second_answer_by']['model_name'] or 'unknown'
                qa_pairs.append(QAPair(
                    question=question, 
                    answer=answer2,
                    model_name=model2
                ))
            
            return qa_pairs
        
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading pairwise evaluator dataset: {e}")
            return None

    def _sample_qa_pairs(self, qa_pairs: List[QAPair]) -> List[QAPair]:
        """Sample QA pairs from the dataset"""
        # Group QA pairs by unique question text
        unique_questions = {}
        for qa in qa_pairs:
            if qa.question not in unique_questions:
                unique_questions[qa.question] = []
            unique_questions[qa.question].append(qa)
        
        # Sample from unique questions
        sampled_questions = random.sample(list(unique_questions.keys()), self.sample_size)
        
        # For each sampled question, take just the first two QA pairs
        sampled_pairs = []
        for question in sampled_questions:
            sampled_pairs.extend(unique_questions[question][:2])
        
        return sampled_pairs

    async def _run_single_experiment(
        self, 
        qa_pairs: List[QAPair], 
        run_number: int
    ) -> Tuple[ExperimentRun, List[DetailedJudgmentScores], List[DetailedJudgmentScores]]:
        """Run a single experiment with both combined and parallel approaches"""
        combined_scores, combined_time, combined_timings = await self.judge.judge_combined(qa_pairs)
        parallel_scores, parallel_time, parallel_timings = await self.judge.judge_parallel(qa_pairs)
        
        run = ExperimentRun(
            combined_time=combined_time,
            parallel_time=parallel_time,
            combined_pair_times=combined_timings,
            parallel_pair_times=parallel_timings
        )
        
        return run, combined_scores, parallel_scores

    def _print_detailed_timing(self, run: ExperimentRun):
        """Print detailed timing information for a run"""
        print("\nDetailed Timing and Token Analysis:")
        
        print("\nCombined Approach QA Pair Times:")
        for timing in run.combined_pair_times:
            print(f"  QA Pair {timing.qa_index}: {timing.total_time:.2f}s")
            print(f"    Tokens: {timing.tokens.input_tokens} in, {timing.tokens.output_tokens} out")
            
        print("\nParallel Approach QA Pair Times:")
        for timing in run.parallel_pair_times:
            print(f"  QA Pair {timing.qa_index}: {timing.total_time:.2f}s")
            if timing.dimension_times:
                for dim, time in timing.dimension_times.items():
                    tokens_in, tokens_out = timing.tokens.dimension_tokens[dim]
                    print(f"    {dim}: {time:.2f}s, {tokens_in} in, {tokens_out} out")

    async def load_qa_pairs(self) -> List[QAPair]:
        """Load and sample QA pairs from dataset"""
        try:
            qa_pairs = await self._load_pairwise_data()
            if not qa_pairs:
                return self._get_fallback_pairs()
            
            return self._sample_qa_pairs(qa_pairs)
        except Exception as e:
            print(f"Error loading QA pairs: {e}")
            return self._get_fallback_pairs()

    async def run_experiment(self, qa_pairs: List[QAPair], num_runs: int = 1) -> List[ExperimentRun]:
        """Run the experiment with specified number of runs"""
        runs = []
        combined_scores = None
        parallel_scores = None

        for i in range(num_runs):
            run, combined_scores, parallel_scores = await self._run_single_experiment(qa_pairs, i + 1)
            runs.append(run)
            
            # Write results after each run
            self.result_writer.write_run_results(
                qa_pairs, run, combined_scores, parallel_scores
            )

        return runs

    @staticmethod
    def _get_fallback_pairs() -> List[QAPair]:
        """Return fallback QA pairs if dataset loading fails"""
        return [
            QAPair(
                question="What is Python?",
                answer="Python is a high-level programming language known for its simplicity and readability.",
                model_name="fallback"
            ),
            QAPair(
                question="How does a for loop work?",
                answer="A for loop iterates over a sequence of elements, executing code for each element.",
                model_name="fallback"
            ),
        ] 