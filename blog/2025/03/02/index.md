---
title: "Using a multi-threaded prompt architecture to speed up LLM Judge evaluation of orthogonal quality dimensions"
date: 2025-03-02
description: |
  In this post, I explore how multi-threading can improve the latency of LLM Judges. I introduce the concept of "orthogonality" as a key heuristic for determining when LLM Judge evaluation tasks can be parallelized without sacrificing quality. Then, I run a controlled experiment using MT Bench data to demonstrate the latency benefits of multi-threading, finding that the multi-threaded approach reduced latency by 38% compared to the single-threaded approach. The code used to run this experiment is also provided.
categories:
  - prompt-engineering
  - python
  - LLM
  - multi-threading
  - orthogonality
---

# Introduction

Response latency is an important factor when engineering many LLM applications. There are many ways to reduce latency, such as by reducing task complexity through simpler task requirements, setting `max_tokens` to a lower value, or using a smaller language model (e.g., `gpt-4o-mini` vs. `gpt-4o`). However, many of these approaches may sacrifice quality for speed. One approach to reducing latency that is unlikely to sacrifice quality (and in many cases may even improve it) is breaking the task down into sub-tasks that can be run in parallel.

In this post, I run an experiment using the MT Bench dataset to demonstrate the latency benefits of a multi-threaded LLM Judge. I engineer the same judge using two architectural approaches:

1. **Single-threaded (Combined) Approach**: Evaluate all quality dimensions in a single LLM call
2. **Multi-threaded (Parallel) Approach**: Evaluate each quality dimension in parallel using separate asynchronous LLM calls

Using the LLM Judge, I evaluate answers to questions in the MT Bench dataset across six dimensions:

- **Helpfulness**: How useful the answer is in addressing the user's needs
- **Relevance**: How well the answer addresses the specific question asked
- **Accuracy**: Whether the information provided is factually correct
- **Depth**: How thoroughly the answer explores the topic
- **Creativity**: The originality and innovative approach in presenting the answer
- **Level of Detail**: The granularity and specificity of information provided

Each dimension is scored on a scale of 1-10 with a rubric for what scores mean.

# Orthogonality

When designing an LLM Judge that evaluates multiple dimensions of quality, "orthogonality" provides a useful heuristic for determining when a multi-threaded approach might be appropriate. In this context, orthogonality refers to the degree to which different evaluation dimensions can be assessed independently without requiring knowledge of the assessments made in other dimensions.

Theoretically, two evaluation dimensions can be considered orthogonal if:

- They measure conceptually distinct aspects of quality
- Evaluating one dimension doesn't significantly benefit from knowledge of the evaluation of other dimensions
- The dimensions can be assessed independently without compromising the quality of the assessment

The degree of orthogonality can also be quantified: If changes in the scores on one dimension have no correlation with changes in scores on the other dimension, then the dimensions are orthogonal. In practice, most evaluation dimensions in natural language tasks aren't perfectly orthogonal, but the degree of orthogonality can help determine their suitability for parallel evaluation.

This statistical definition is precisely what makes orthogonality such a useful heuristic for determining parallelization potential -- dimensions with low correlation coefficients can be evaluated independently without losing meaningful information that would be gained from evaluating them together.

The six dimensions in our experiment -- Helpfulness, Relevance, Accuracy, Depth, Creativity, and Level of Detail -- are largely orthogonal. For example, an answer can be highly accurate (factually correct) while lacking depth (not exploring the topic thoroughly). Similarly, an answer can be highly creative while being less helpful for the user's specific needs. Therefore, a multi-threaded approach that evaluates each dimension in parallel does seem appropriate.

# Additional benefits

In addition to improving the latency of LLM Judge evaluations, by breaking the task down into smaller tasks, it's also possible that the following benefits would be realized:

- **Higher quality / accuracy**: By breaking the task down into smaller tasks that can be evaluated in parallel, it's possible that the quality / accuracy of the LLM Judge evaluations would be improved, due to the singular focus of each task.
- **Smaller language models**: By breaking the task down into smaller tasks, it's possible that smaller language models could be used without sacrificing quality.

# Code Structure

The code for this experiment is organized into several Python modules:

```
llm_judge/
├── config.py
├── experiment.py
├── judge.py
├── LLMClient.py
├── main.py
├── models.py
└── results.py
```

Let's consider these code modules one by one:

## Configuration

The `Configuration` module (`config.py`) defines parameters for our experiment:

```python
from dataclasses import dataclass
from pathlib import Path

# Get the project root directory (parent of llm_judge directory)
PROJECT_ROOT = Path(__file__).parent.parent.absolute()

@dataclass
class ExperimentConfig:
    SAMPLE_SIZE: int = 32
    RANDOM_SEED: int = 42
    MAX_TOKENS: int = 256
    NUM_RUNS: int = 1
    RESULTS_JSONL: Path = PROJECT_ROOT / 'experiment_results.jsonl'
    RESULTS_TXT: Path = PROJECT_ROOT / 'experiment_results.txt'

@dataclass
class FileConfig:
    DATASET_PATH: Path = PROJECT_ROOT / 'data/pairwise_evaluator_dataset.json'
    RESULTS_JSONL: Path = PROJECT_ROOT / 'experiment_results.jsonl'
    RESULTS_TXT: Path = PROJECT_ROOT / 'experiment_results.txt' 
```

## The LLM Judge

The core module is the `LLMJudge` class (`judge.py`), which implements the single-threaded and multi-threaded approaches, and includes the prompts for the LLM.

<details><summary>Click to view the LLM Judge code</summary>

```python
import asyncio
import time
from typing import List, Tuple
import re
import json
from pathlib import Path

from .models import (
    QAPair, DetailedJudgmentScores, DimensionAnalysis, 
    QAPairTiming, QAPairTokens, ExperimentRun
)
from .LLMClient import LLMClient
from .config import ExperimentConfig
from .results import ResultWriter

class LLMJudge:
    def __init__(self):
        self.client = LLMClient()
        self.config = ExperimentConfig()
        self.result_writer = ResultWriter()

    def _parse_scores(self, response: str) -> DetailedJudgmentScores:
        """Parse the LLM response into scores and thinking steps using XML format"""
        def extract_dimension_analysis(dimension: str) -> DimensionAnalysis:
            thinking_pattern = f"<{dimension}>.*?<StepByStepThinking>(.*?)</StepByStepThinking>"
            score_pattern = f"<{dimension}>.*?<Score>(\d+)</Score>.*?</{dimension}>"
            
            thinking_match = re.search(thinking_pattern, response, re.DOTALL)
            score_match = re.search(score_pattern, response, re.DOTALL)
            
            thinking = thinking_match.group(1).strip() if thinking_match else "No analysis provided"
            score = int(score_match.group(1)) if score_match else 0
            
            return DimensionAnalysis(thinking=thinking, score=score)
        
        return DetailedJudgmentScores(
            helpfulness=extract_dimension_analysis("Helpfulness"),
            relevance=extract_dimension_analysis("Relevance"),
            accuracy=extract_dimension_analysis("Accuracy"),
            depth=extract_dimension_analysis("Depth"),
            creativity=extract_dimension_analysis("Creativity"),
            level_of_detail=extract_dimension_analysis("Level_of_Detail")
        )

    def _has_existing_result(self, qa_pair: QAPair, judge_type: str) -> bool:
        """Check if this QA pair has already been evaluated by this judge type"""
        results_file = Path(self.config.RESULTS_JSONL)
        if not results_file.exists():
            return False
        
        try:
            with results_file.open('r', encoding='utf-8') as f:  # Use Path.open() instead of open()
                for line in f:
                    if not line.strip():  # Skip empty lines
                        continue
                    try:
                        result = json.loads(line)
                        if (result['judge_type'] == judge_type and 
                            result['question'] == qa_pair.question and
                            result['answer'] == qa_pair.answer and 
                            result['model'] == qa_pair.model_name):
                            print(f"Found existing result for {qa_pair.model_name} - {qa_pair.question[:50]}...")
                            return True
                    except json.JSONDecodeError:
                        continue  # Skip invalid JSON lines
        except (FileNotFoundError, KeyError):
            return False
        
        return False

    async def judge_combined(self, qa_pairs: List[QAPair]) -> Tuple[List[DetailedJudgmentScores], float, List[QAPairTiming]]:
        """Judge each QA pair independently with all dimensions at once"""
        start_time = time.time()
        all_scores = []
        pair_timings = []

        # Define scoring guidelines
        scoring_guidelines = """
        Scoring Guidelines:
        1-2: Poor - Major issues or completely misses the mark
        3-4: Below Average - Significant room for improvement
        5-6: Average - Meets basic expectations
        7-8: Good - Strong performance with minor issues
        9-10: Excellent - Nearly perfect or perfect performance
        """

        dimension_definitions = {
            'Helpfulness': 'How useful and beneficial the answer is in addressing the user\'s needs. A helpful answer provides practical, actionable information that serves the user\'s purpose.',
            'Relevance': 'How well the answer addresses the specific question asked. A relevant answer stays on topic and provides information that directly answers the question.',
            'Accuracy': 'Whether the information provided is factually correct. Check for any errors, misleading statements, or questionable claims.',
            'Depth': 'How thoroughly the answer explores the topic, including underlying concepts and relationships. A deep answer goes beyond surface-level explanations.',
            'Creativity': 'The originality and innovative approach in presenting the answer. Consider unique perspectives, examples, or explanations used.',
            'Level_of_Detail': 'The granularity and specificity of information provided. A detailed answer includes specific examples, explanations, and supporting information.'
        }

        for i, qa_pair in enumerate(qa_pairs, 1):
            # Skip if already evaluated
            if self._has_existing_result(qa_pair, "combined"):
                print(f"\nSkipping QA pair {i}/{len(qa_pairs)} (combined approach) - already evaluated")
                continue
                
            pair_start_time = time.time()
            print(f"\nProcessing QA pair {i}/{len(qa_pairs)} (combined approach)")
            print(f"Question: {qa_pair.question[:50]}...")

            system_message = f"""You are an expert judge evaluating question-answer pairs.
            For each dimension, think step by step about your evaluation before giving a score (1-10).
            
            {scoring_guidelines}
            
            Evaluation dimensions:
            - Helpfulness: {dimension_definitions['Helpfulness']}
            - Relevance: {dimension_definitions['Relevance']}
            - Accuracy: {dimension_definitions['Accuracy']}
            - Depth: {dimension_definitions['Depth']}
            - Creativity: {dimension_definitions['Creativity']}
            - Level of Detail: {dimension_definitions['Level_of_Detail']}
            
            Question: ```{qa_pair.question}```
            Answer: ```{qa_pair.answer}```
            
            For each dimension, follow these steps in your evaluation:
            1. First, carefully analyze the question and answer
            2. Consider specific strengths and weaknesses related to the dimension
            3. Provide concrete examples from the answer to support your analysis
            4. Assign a score based on the scoring guidelines
            
            Provide your analysis and scores in this XML format:

            <Helpfulness>
            <StepByStepThinking>[your detailed analysis for helpfulness]</StepByStepThinking>
            <Score>[score from 1-10]</Score>
            </Helpfulness>

            <Relevance>
            <StepByStepThinking>[your detailed analysis for relevance]</StepByStepThinking>
            <Score>[score from 1-10]</Score>
            </Relevance>

            <Accuracy>
            <StepByStepThinking>[your detailed analysis for accuracy]</StepByStepThinking>
            <Score>[score from 1-10]</Score>
            </Accuracy>

            <Depth>
            <StepByStepThinking>[your detailed analysis for depth]</StepByStepThinking>
            <Score>[score from 1-10]</Score>
            </Depth>

            <Creativity>
            <StepByStepThinking>[your detailed analysis for creativity]</StepByStepThinking>
            <Score>[score from 1-10]</Score>
            </Creativity>

            <Level_of_Detail>
            <StepByStepThinking>[your detailed analysis for level of detail]</StepByStepThinking>
            <Score>[score from 1-10]</Score>
            </Level_of_Detail>"""

            print("Sending prompt to LLM for all dimensions...")
            result = await self.client.get_completion(
                system_message=system_message,
                prompt="",
                max_tokens=self.config.MAX_TOKENS*6
            )
            print("Received response from LLM")

            scores = self._parse_scores(result.content)
            all_scores.append(scores)

            timing = QAPairTiming(
                qa_index=i,
                question=qa_pair.question,
                total_time=time.time() - pair_start_time,
                tokens=QAPairTokens(
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    total_tokens=result.input_tokens + result.output_tokens
                )
            )
            pair_timings.append(timing)

            # Write result immediately after each QA pair
            current_time = time.time() - start_time
            self.result_writer.write_run_results(
                [qa_pair],  # Single QA pair
                ExperimentRun(
                    combined_time=current_time,
                    parallel_time=current_time,  # Use same time instead of 0
                    combined_pair_times=[timing],
                    parallel_pair_times=[]
                ),
                [scores],  # Single score
                []  # No parallel scores
            )

            print(f"Parsed scores for all dimensions (took {timing.total_time:.2f}s)")
            print(f"Token usage: {result.input_tokens} in, {result.output_tokens} out")

        elapsed_time = time.time() - start_time
        print(f"\nCompleted all evaluations in {elapsed_time:.2f} seconds")
        return all_scores, elapsed_time, pair_timings

    async def judge_dimension(self, qa_pair: QAPair, dimension: str, scoring_guidelines: str = "") -> Tuple[DimensionAnalysis, float, Tuple[int, int]]:
        dim_start_time = time.time()
        
        dimension_definitions = {
            'Helpfulness': 'How useful and beneficial the answer is in addressing the user\'s needs. A helpful answer provides practical, actionable information that serves the user\'s purpose.',
            'Relevance': 'How well the answer addresses the specific question asked. A relevant answer stays on topic and provides information that directly answers the question.',
            'Accuracy': 'Whether the information provided is factually correct. Check for any errors, misleading statements, or questionable claims.',
            'Depth': 'How thoroughly the answer explores the topic, including underlying concepts and relationships. A deep answer goes beyond surface-level explanations.',
            'Creativity': 'The originality and innovative approach in presenting the answer. Consider unique perspectives, examples, or explanations used.',
            'Level_of_Detail': 'The granularity and specificity of information provided. A detailed answer includes specific examples, explanations, and supporting information.'
        }

        system_message = f"""You are an expert judge evaluating a specific dimension of a question-answer pair.
        Think step by step about your evaluation before giving a score (1-10).
        
        You are evaluating the {dimension.lower()} dimension:
        {dimension_definitions[dimension]}
        
        {scoring_guidelines}

        Question: ```{qa_pair.question}```
        Answer: ```{qa_pair.answer}```
        
        Follow these steps in your evaluation:
        1. First, carefully analyze the question and answer
        2. Consider specific strengths and weaknesses related to {dimension.lower()}
        3. Provide concrete examples from the answer to support your analysis
        4. Assign a score based on the scoring guidelines
        
        Provide your analysis and score in this XML format:

        <{dimension}>
        <StepByStepThinking>[your detailed analysis for {dimension.lower()}]</StepByStepThinking>
        <Score>[score from 1-10]</Score>
        </{dimension}>"""

        result = await self.client.get_completion(
            system_message=system_message,
            prompt="",
            max_tokens=self.config.MAX_TOKENS
        )

        analysis = self._parse_scores(result.content).__getattribute__(dimension.lower())
        return analysis, time.time() - dim_start_time, (result.input_tokens, result.output_tokens)

    async def judge_parallel(self, qa_pairs: List[QAPair]) -> Tuple[List[DetailedJudgmentScores], float, List[QAPairTiming]]:
        """Judge dimensions in parallel for each QA pair"""
        start_time = time.time()
        all_scores = []
        pair_timings = []

        # Add scoring guidelines
        scoring_guidelines = """
        Scoring Guidelines:
        1-2: Poor - Major issues or completely misses the mark
        3-4: Below Average - Significant room for improvement
        5-6: Average - Meets basic expectations
        7-8: Good - Strong performance with minor issues
        9-10: Excellent - Nearly perfect or perfect performance
        """

        for i, qa_pair in enumerate(qa_pairs, 1):
            # Skip if already evaluated
            if self._has_existing_result(qa_pair, "parallel"):
                print(f"\nSkipping QA pair {i}/{len(qa_pairs)} (parallel approach) - already evaluated")
                continue
                
            pair_start_time = time.time()
            print(f"\nProcessing QA pair {i}/{len(qa_pairs)} (parallel approach)")
            print(f"Question: {qa_pair.question[:50]}...")

            dimensions = ['Helpfulness', 'Relevance', 'Accuracy', 'Depth', 'Creativity', 'Level_of_Detail']
            tasks = [self.judge_dimension(qa_pair, dim, scoring_guidelines) for dim in dimensions]
            results = await asyncio.gather(*tasks)

            analyses, times, tokens = zip(*results)
            dimension_times = dict(zip(dimensions, times))
            dimension_tokens = dict(zip(dimensions, tokens))

            scores = DetailedJudgmentScores(
                helpfulness=analyses[0],
                relevance=analyses[1],
                accuracy=analyses[2],
                depth=analyses[3],
                creativity=analyses[4],
                level_of_detail=analyses[5]
            )
            all_scores.append(scores)

            total_time = time.time() - pair_start_time
            timing = QAPairTiming(
                qa_index=i,
                question=qa_pair.question,
                total_time=total_time,
                tokens=QAPairTokens(
                    input_tokens=sum(t[0] for t in tokens),
                    output_tokens=sum(t[1] for t in tokens),
                    total_tokens=sum(sum(t) for t in tokens),
                    dimension_tokens=dimension_tokens
                ),
                dimension_times=dimension_times
            )
            pair_timings.append(timing)

            # Write result immediately after each QA pair
            current_time = time.time() - start_time
            self.result_writer.write_run_results(
                [qa_pair],  # Single QA pair
                ExperimentRun(
                    combined_time=current_time,  # Use same time instead of 0
                    parallel_time=current_time,
                    combined_pair_times=[],
                    parallel_pair_times=[timing]
                ),
                [],  # No combined scores
                [scores]  # Single parallel score
            )

            print(f"Completed parallel evaluation in {total_time:.2f}s")
            for dim, t in dimension_times.items():
                in_tokens, out_tokens = dimension_tokens[dim]
                print(f"  {dim}: {t:.2f}s, {in_tokens} in, {out_tokens} out")

        elapsed_time = time.time() - start_time
        print(f"\nCompleted all evaluations in {elapsed_time:.2f} seconds")
        return all_scores, elapsed_time, pair_timings 
```

</details>

## The Experiment Runner

The `Experiment Runner` (`experiment.py`) coordinates the evaluation process:

<details><summary>Click to view the Experiment Runner code</summary>

```python
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
```

</details>

And we can run the experiment with the following code in the `Main` module (`main.py`)

<details><summary>Click to view the Main module code</summary>

```python
from llm_judge.experiment import ExperimentRunner
from llm_judge.config import ExperimentConfig

async def run():
    config = ExperimentConfig()
    runner = ExperimentRunner(
        sample_size=config.SAMPLE_SIZE,
        seed=config.RANDOM_SEED
    )
    
    qa_pairs = await runner.load_qa_pairs()
    await runner.run_experiment(qa_pairs, config.NUM_RUNS)

# Run it
await run()
```

</details>

## Other modules

The `Result Writer` module (`results.py`) is responsible for writing the results to a JSONL file.

<details><summary>Click to view the Result Writer code</summary>

```python

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
        """Write results for a single experiment run to bJSONL file"""
        self._write_to_jsonl(qa_pairs, run, combined_scores, parallel_scores)

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

```

</details>

And the `Models` module (`models.py`) defines the data structures.

<details><summary>Click to view the Models code</summary>

```python
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
```

</details>

## Analysis

### Latency

After running the experiment, we can analyze the latency distributions to determine if the multi-threaded approach was faster:

```python
import json
import pandas as pd
from scipy import stats
import plotly.graph_objects as go
import numpy as np

data = []
with open('experiment_results.jsonl', 'r') as file:
    for line in file:
        data.append(json.loads(line))

# Separate data by judge type and convert to seconds
parallel_times = [entry['overall_time_ms']/1000 for entry in data if entry['judge_type'] == 'parallel']
combined_times = [entry['overall_time_ms']/1000 for entry in data if entry['judge_type'] == 'combined']

# Calculate medians
median_parallel = sorted(parallel_times)[len(parallel_times)//2]
median_combined = sorted(combined_times)[len(combined_times)//2]

# Calculate pairwise percentage differences
pct_diffs = []
for entry_parallel in data:
    if entry_parallel['judge_type'] == 'parallel':
        for entry_combined in data:
            if (entry_combined['judge_type'] == 'combined' and 
                entry_parallel['question'] == entry_combined['question'] and 
                entry_parallel.get('model') == entry_combined.get('model')):
                pct_diff = ((entry_parallel['overall_time_ms'] - entry_combined['overall_time_ms']) / 
                          entry_combined['overall_time_ms'] * 100)
                pct_diffs.append(pct_diff)

median_pct_diff = sorted(pct_diffs)[len(pct_diffs)//2]

# Create kernel density estimation
kernel_parallel = stats.gaussian_kde(parallel_times)
kernel_combined = stats.gaussian_kde(combined_times)

# Create x range for smooth plotting
x_range = np.linspace(min(min(parallel_times), min(combined_times)),
                      max(max(parallel_times), max(combined_times)),
                      200)

# Create figure
fig = go.Figure()

# Add density plots
fig.add_trace(go.Scatter(x=x_range, 
                        y=kernel_parallel(x_range),
                        name='Multiple Threads',
                        fill='tozeroy',
                        line=dict(color='blue'),
                        opacity=0.6))

fig.add_trace(go.Scatter(x=x_range, 
                        y=kernel_combined(x_range),
                        name='Single Thread',
                        fill='tozeroy',
                        line=dict(color='red'),
                        opacity=0.6))

# Add statistics box
stats_text = (
    f"Median response times:<br>"
    f"Multiple Threads: {median_parallel:.0f}s<br>"
    f"Single Thread: {median_combined:.0f}s<br><br>"
    f"Median % difference: {median_pct_diff:.0f}%"
)

fig.add_annotation(
    x=0.98,  # Changed from 0.02 to 0.98 to move to right side
    y=0.98,
    xref="paper",
    yref="paper",
    text=stats_text,
    showarrow=False,
    font=dict(size=12),
    align="left",
    bgcolor="white",
    bordercolor="black",
    borderwidth=1,
    xanchor="right",  # Changed from 'left' to 'right'
    yanchor="top"
)

# Update layout
fig.update_layout(
    title='Density Plot of Overall Time by Judge Type',
    xaxis_title='Time (seconds)',
    yaxis_title='Density',
    showlegend=True,
    width=600,
    height=400
)

fig.show()
```

<div>                            <div id="fc69afac-2f68-42f0-90ad-06d3bcdc82bd" class="plotly-graph-div" style="height:400px; width:600px;"></div>            <script type="text/javascript">                require(["plotly"], function(Plotly) {                    window.PLOTLYENV=window.PLOTLYENV || {};                                    if (document.getElementById("fc69afac-2f68-42f0-90ad-06d3bcdc82bd")) {                    Plotly.newPlot(                        "fc69afac-2f68-42f0-90ad-06d3bcdc82bd",                        [{"fill":"tozeroy","line":{"color":"blue"},"name":"Multiple Threads","opacity":0.6,"x":[2.954,3.0147939698492463,3.0755879396984924,3.136381909547739,3.197175879396985,3.2579698492462312,3.3187638190954774,3.379557788944724,3.44035175879397,3.501145728643216,3.5619396984924623,3.6227336683417084,3.683527638190955,3.744321608040201,3.805115577889447,3.8659095477386938,3.92670351758794,3.987497487437186,4.048291457286432,4.109085427135678,4.169879396984925,4.230673366834171,4.291467336683417,4.352261306532664,4.413055276381909,4.473849246231156,4.534643216080402,4.595437185929648,4.656231155778895,4.71702512562814,4.777819095477387,4.8386130653266335,4.899407035175879,4.960201005025126,5.020994974874371,5.081788944723618,5.1425829145728645,5.203376884422111,5.264170854271357,5.3249648241206025,5.385758793969849,5.446552763819096,5.507346733668342,5.568140703517588,5.6289346733668335,5.68972864321608,5.750522613065327,5.811316582914573,5.872110552763819,5.932904522613065,5.993698492462311,6.054492462311558,6.115286432160804,6.17608040201005,6.2368743718592965,6.297668341708542,6.358462311557789,6.419256281407035,6.480050251256282,6.5408442211055275,6.601638190954773,6.66243216080402,6.723226130653266,6.784020100502513,6.844814070351759,6.905608040201004,6.966402010050251,7.027195979899497,7.087989949748744,7.1487839195979905,7.209577889447235,7.270371859296482,7.3311658291457285,7.391959798994975,7.452753768844222,7.513547738693466,7.574341708542713,7.6351356783919595,7.695929648241206,7.756723618090453,7.817517587939697,7.878311557788944,7.9391055276381906,7.999899497487437,8.060693467336684,8.121487437185928,8.182281407035175,8.243075376884422,8.303869346733668,8.364663316582915,8.425457286432161,8.486251256281406,8.547045226130653,8.6078391959799,8.668633165829146,8.729427135678392,8.790221105527637,8.851015075376884,8.91180904522613,8.972603015075377,9.033396984924623,9.094190954773868,9.154984924623115,9.215778894472361,9.276572864321608,9.337366834170854,9.3981608040201,9.458954773869346,9.519748743718592,9.580542713567839,9.641336683417085,9.702130653266332,9.762924623115577,9.823718592964823,9.88451256281407,9.945306532663317,10.006100502512563,10.066894472361808,10.127688442211054,10.188482412060301,10.249276381909548,10.310070351758794,10.370864321608039,10.431658291457286,10.492452261306532,10.553246231155779,10.614040201005025,10.67483417085427,10.735628140703517,10.796422110552763,10.85721608040201,10.918010050251256,10.978804020100503,11.03959798994975,11.100391959798994,11.16118592964824,11.221979899497487,11.282773869346734,11.34356783919598,11.404361809045225,11.465155778894472,11.525949748743718,11.586743718592965,11.647537688442211,11.708331658291456,11.769125628140703,11.82991959798995,11.890713567839196,11.951507537688443,12.012301507537687,12.073095477386934,12.13388944723618,12.194683417085427,12.255477386934674,12.31627135678392,12.377065326633165,12.437859296482412,12.498653266331658,12.559447236180905,12.620241206030151,12.681035175879396,12.741829145728643,12.80262311557789,12.863417085427136,12.924211055276382,12.985005025125627,13.045798994974874,13.10659296482412,13.167386934673367,13.228180904522613,13.288974874371858,13.349768844221105,13.410562814070351,13.471356783919598,13.532150753768844,13.592944723618091,13.653738693467336,13.714532663316582,13.775326633165829,13.836120603015075,13.896914572864322,13.957708542713567,14.018502512562813,14.07929648241206,14.140090452261306,14.200884422110553,14.261678391959798,14.322472361809044,14.383266331658291,14.444060301507538,14.504854271356784,14.565648241206029,14.626442211055275,14.687236180904522,14.748030150753769,14.808824120603015,14.86961809045226,14.930412060301506,14.991206030150753,15.052],"y":[0.09808677938842676,0.10633477286607379,0.11482930159929325,0.1235276235759245,0.13238237950926224,0.14134200317719617,0.15035122530190315,0.15935166639372828,0.16828251179871578,0.17708125997303417,0.18568453281255148,0.19402893475613042,0.2020519454303083,0.2096928288913299,0.2168935411318009,0.22359961653646743,0.22976101347187175,0.23533289924403694,0.24027635530697974,0.2445589848821696,0.24815540705982234,0.2510476239743828,0.2532252507267295,0.25468560128313333,0.25543362750637705,0.25548171263328523,0.25484932475065597,0.25356253996984773,0.25165344888473373,0.24915946334703318,0.24612254344842743,0.2425883667238859,0.23860546288033435,0.23422433774348672,0.22949660958289944,0.2244741795489399,0.21920845571167796,0.21374964725199097,0.20814614187893696,0.2024439757226997,0.19668640098335752,0.1909135527093033,0.18516221243092454,0.17946566315639165,0.17385362758295342,0.1683522793814693,0.16298431611878977,0.15776908178890114,0.1527227269820799,0.1478583953472577,0.1431864260847037,0.13871456361648535,0.13444816718931116,0.13039041484343616,0.1265424978232985,0.12290380302372836,0.11947208239892221,0.1162436093749017,0.11321332318842638,0.11037496273369087,0.10772119195277183,0.10524371908308121,0.10293341220143669,0.10078041350134946,0.09877425462122937,0.09690397511082519,0.09515824577777417,0.09352549818711305,0.09199406098506084,0.09055230298028555,0.08918878204745921,0.08789239794035637,0.08665254605435518,0.08545926811946503,0.08430339481133141,0.08317667442935014,0.08207188120580522,0.08098289657444947,0.07990475692676348,0.07883366208333722,0.07776693993915257,0.07670296449818054,0.07564102674281585,0.07458116038861491,0.0735239274115754,0.07247017112332457,0.07142074730240147,0.07037624624926314,0.06933672040670871,0.06830143318864526,0.0672686447435544,0.06623544945784632,0.0651976780615246,0.06414987429344782,0.06308535235152708,0.061996336999955645,0.06087418349368455,0.05970966971150947,0.05849334838179884,0.05721594335004857,0.055868770754238024,0.05444416396745136,0.05293588039029251,0.051339468696497824,0.04965257693182201,0.04787518482809319,0.046009747630710404,0.04406124339319899,0.04203712076594114,0.0399471494747296,0.037803180626924296,0.03561882840206728,0.033409088328308044,0.031189910025517624,0.028977743891929288,0.026789081681351825,0.024640010295386403,0.022545796500757484,0.020520517833699622,0.018576751871017184,0.01672533255565546,0.014975178595771195,0.01333319533398948,0.011804248108316154,0.010391202164136028,0.009095021751774422,0.007914919234023897,0.006848543864251951,0.005892199366386119,0.00504107950394161,0.004289511387376968,0.0036311972377758707,0.0030594465890412155,0.00256739235679466,0.0021481857217190755,0.0017951662717712346,0.0015020052418414382,0.0012628209210854347,0.0010722663283283538,0.0009255900663069153,0.0008186718566796428,0.0007480346464664441,0.0007108353922989346,0.0007048367096884066,0.0007283615631642319,0.0007802331129294748,0.0008597017649018459,0.0009663614277299509,0.001100056987942285,0.0012607850876362847,0.0014485904314020818,0.0016634600522502675,0.0019052182110503668,0.0021734248619420943,0.0024672808519022285,0.00278554319662372,0.003126453846940348,0.003487685293111409,0.003866306118009632,0.004258769184440789,0.004660924519298813,0.0050680581458934495,0.005474957139417494,0.005876000078634982,0.006265270892957974,0.006636692922674558,0.006984178892683548,0.0073017915201397,0.007583908703851993,0.007825386738940567,0.00802171481072096,0.008169154175058995,0.008264855934971215,0.008306952158501132,0.008294616211748184,0.008228089543818087,0.008108673681297814,0.007938687781209066,0.0077213936606920315,0.007460891677818971,0.007161992097802278,0.006830067573095486,0.006470893043596899,0.006090479695076186,0.005694909593793482,0.005290177259433455,0.0048820437838084235,0.004475908203117342,0.004076699752980225,0.0036887934510563395,0.0033159502363107577,0.0029612817176614776,0.0026272385102540036,0.002315620215552228,0.002027604368173764,0.0017637911490195732,0.001524260356702238,0.0013086370296391489,0.0011161621997699445,0.0009457655069932856],"type":"scatter"},{"fill":"tozeroy","line":{"color":"red"},"name":"Single Thread","opacity":0.6,"x":[2.954,3.0147939698492463,3.0755879396984924,3.136381909547739,3.197175879396985,3.2579698492462312,3.3187638190954774,3.379557788944724,3.44035175879397,3.501145728643216,3.5619396984924623,3.6227336683417084,3.683527638190955,3.744321608040201,3.805115577889447,3.8659095477386938,3.92670351758794,3.987497487437186,4.048291457286432,4.109085427135678,4.169879396984925,4.230673366834171,4.291467336683417,4.352261306532664,4.413055276381909,4.473849246231156,4.534643216080402,4.595437185929648,4.656231155778895,4.71702512562814,4.777819095477387,4.8386130653266335,4.899407035175879,4.960201005025126,5.020994974874371,5.081788944723618,5.1425829145728645,5.203376884422111,5.264170854271357,5.3249648241206025,5.385758793969849,5.446552763819096,5.507346733668342,5.568140703517588,5.6289346733668335,5.68972864321608,5.750522613065327,5.811316582914573,5.872110552763819,5.932904522613065,5.993698492462311,6.054492462311558,6.115286432160804,6.17608040201005,6.2368743718592965,6.297668341708542,6.358462311557789,6.419256281407035,6.480050251256282,6.5408442211055275,6.601638190954773,6.66243216080402,6.723226130653266,6.784020100502513,6.844814070351759,6.905608040201004,6.966402010050251,7.027195979899497,7.087989949748744,7.1487839195979905,7.209577889447235,7.270371859296482,7.3311658291457285,7.391959798994975,7.452753768844222,7.513547738693466,7.574341708542713,7.6351356783919595,7.695929648241206,7.756723618090453,7.817517587939697,7.878311557788944,7.9391055276381906,7.999899497487437,8.060693467336684,8.121487437185928,8.182281407035175,8.243075376884422,8.303869346733668,8.364663316582915,8.425457286432161,8.486251256281406,8.547045226130653,8.6078391959799,8.668633165829146,8.729427135678392,8.790221105527637,8.851015075376884,8.91180904522613,8.972603015075377,9.033396984924623,9.094190954773868,9.154984924623115,9.215778894472361,9.276572864321608,9.337366834170854,9.3981608040201,9.458954773869346,9.519748743718592,9.580542713567839,9.641336683417085,9.702130653266332,9.762924623115577,9.823718592964823,9.88451256281407,9.945306532663317,10.006100502512563,10.066894472361808,10.127688442211054,10.188482412060301,10.249276381909548,10.310070351758794,10.370864321608039,10.431658291457286,10.492452261306532,10.553246231155779,10.614040201005025,10.67483417085427,10.735628140703517,10.796422110552763,10.85721608040201,10.918010050251256,10.978804020100503,11.03959798994975,11.100391959798994,11.16118592964824,11.221979899497487,11.282773869346734,11.34356783919598,11.404361809045225,11.465155778894472,11.525949748743718,11.586743718592965,11.647537688442211,11.708331658291456,11.769125628140703,11.82991959798995,11.890713567839196,11.951507537688443,12.012301507537687,12.073095477386934,12.13388944723618,12.194683417085427,12.255477386934674,12.31627135678392,12.377065326633165,12.437859296482412,12.498653266331658,12.559447236180905,12.620241206030151,12.681035175879396,12.741829145728643,12.80262311557789,12.863417085427136,12.924211055276382,12.985005025125627,13.045798994974874,13.10659296482412,13.167386934673367,13.228180904522613,13.288974874371858,13.349768844221105,13.410562814070351,13.471356783919598,13.532150753768844,13.592944723618091,13.653738693467336,13.714532663316582,13.775326633165829,13.836120603015075,13.896914572864322,13.957708542713567,14.018502512562813,14.07929648241206,14.140090452261306,14.200884422110553,14.261678391959798,14.322472361809044,14.383266331658291,14.444060301507538,14.504854271356784,14.565648241206029,14.626442211055275,14.687236180904522,14.748030150753769,14.808824120603015,14.86961809045226,14.930412060301506,14.991206030150753,15.052],"y":[8.221130007424659e-9,1.4168787683209236e-8,2.418149872663507e-8,4.086943550077876e-8,6.840617733827488e-8,1.1339409022407469e-7,1.8616665737361049e-7,3.0272516831017336e-7,4.875844694135113e-7,7.779044127249154e-7,1.2294155912424625e-6,1.9248154156257404e-6,2.985518650618157e-6,4.587899069589625e-6,6.98545750480269e-6,0.00001053869420315848,0.000015754842605365766,0.000023340022674165375,0.00003426677045372416,0.00004986026079484384,0.00007190681281106894,0.00010278838860924842,0.0001456466862423755,0.0002045799952668261,0.0002848751254882187,0.0003932753307071394,0.0005382831299758871,0.0007304941989553075,0.0009829550195986569,0.0013115327498641313,0.0017352808964075054,0.002276779031066891,0.002962419292083357,0.0038226071866809077,0.004891839822993134,0.0062086218164995105,0.007815178482266245,0.009756928295957135,0.012081682671569779,0.014838551379765171,0.01807654665202832,0.02184289802202713,0.026181112595100108,0.03112884050803262,0.036715631086648506,0.04296068938030689,0.04987076275755408,0.05743830037465595,0.06564003204233601,0.07443610529001103,0.08376989908433473,0.09356859966629072,0.10374457963752864,0.114197568463246,0.12481754496544979,0.13548822514723696,0.14609096732916788,0.15650887653389564,0.16663086603901922,0.17635542938815862,0.1855938923947828,0.19427295109812429,0.20233635530632074,0.20974566335943573,0.21648006564342387,0.22253534499945296,0.22792210440266247,0.23266343998386613,0.23679226619835328,0.24034850751713896,0.24337635773051014,0.2459217765236121,0.24803034812991734,0.24974557466246783,0.2511076237687617,0.2521525028279738,0.25291159517068446,0.25341147119948987,0.2536738802139905,0.2537158364746438,0.2535497329715384,0.2531834444655126,0.2526204127967572,0.25185973722821203,0.2508963162307642,0.24972110118545865,0.24832152494053875,0.2466821585611497,0.2447856290444493,0.242613801699725,0.2401491968003713,0.23737657510801044,0.2342845952194106,0.2308674213835002,0.2271261467814859,0.223069896539846,0.21871648797210977,0.2140925523412287,0.2092330610077639,0.20418024608744542,0.19898195753056339,0.1936895499950325,0.1883554389001646,0.18303050076142838,0.17776151424024264,0.1725888424782857,0.16754454303628633,0.16265105978346164,0.15792060391128704,0.15335527306831476,0.1489478938952025,0.144683510152086,0.14054138239000863,0.13649732130274628,0.1325261498278429,0.1286040813369733,0.12471081345004516,0.12083116765995734,0.11695615074435081,0.11308337008640748,0.10921679583678083,0.10536592234758438,0.10154443386855892,0.09776852039539694,0.09405501542334292,0.09041953641779964,0.08687480099380464,0.08342926862525324,0.08008622206638602,0.07684335844311165,0.07369291160994332,0.07062227943857638,0.06761508646711557,0.06465257737911773,0.0617152127267091,0.05878432665770224,0.055843707453764935,0.05288097458918444,0.04988864893159344,0.046864843009180916,0.04381353285769649,0.040744408553999946,0.03767233399527584,0.034616475063635146,0.03159917693278123,0.02864468462232002,0.025777805532052958,0.023022608964584933,0.02040124666237666,0.017932961790632345,0.01563333357968477,0.013513783108176539,0.011581344473095471,0.00983868658663751,0.00828435538075235,0.006913195115680388,0.005716901099978191,0.004684654289354486,0.0038037904058896652,0.0030604615957160637,0.0024402562528954464,0.0019287514716350377,0.0015119817022709746,0.0011768157728629294,0.0009112418813965404,0.0007045660574767649,0.00054753373769753,0.00043238648035322637,0.0003528665969733693,0.00030418184390539006,0.00028294061031067957,0.00028706560779410967,0.00031569126628607554,0.0003690472108345265,0.00044832764478814306,0.0005555444655140274,0.0006933607079751329,0.0008649006082268292,0.0010735332922957284,0.0013226288341127667,0.0016152881059271012,0.0019540512840475486,0.0023405937904931572,0.002775422475071166,0.0032575885304184935,0.0037844365062690687,0.004351410379760733,0.00495193754081468,0.005577409481146036,0.006217273821138216,0.006859246172141534,0.007489642545662599,0.008093824141742804,0.008656737118884547,0.009163521229652987,0.00960015389383773,0.00995409119958353,0.010214865125844219,0.010374597361344785,0.010428394529631891],"type":"scatter"}],                        {"template":{"data":{"histogram2dcontour":[{"type":"histogram2dcontour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"choropleth":[{"type":"choropleth","colorbar":{"outlinewidth":0,"ticks":""}}],"histogram2d":[{"type":"histogram2d","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmap":[{"type":"heatmap","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"heatmapgl":[{"type":"heatmapgl","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"contourcarpet":[{"type":"contourcarpet","colorbar":{"outlinewidth":0,"ticks":""}}],"contour":[{"type":"contour","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"surface":[{"type":"surface","colorbar":{"outlinewidth":0,"ticks":""},"colorscale":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]]}],"mesh3d":[{"type":"mesh3d","colorbar":{"outlinewidth":0,"ticks":""}}],"scatter":[{"fillpattern":{"fillmode":"overlay","size":10,"solidity":0.2},"type":"scatter"}],"parcoords":[{"type":"parcoords","line":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolargl":[{"type":"scatterpolargl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"bar":[{"error_x":{"color":"#2a3f5f"},"error_y":{"color":"#2a3f5f"},"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"bar"}],"scattergeo":[{"type":"scattergeo","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterpolar":[{"type":"scatterpolar","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"histogram":[{"marker":{"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"histogram"}],"scattergl":[{"type":"scattergl","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatter3d":[{"type":"scatter3d","line":{"colorbar":{"outlinewidth":0,"ticks":""}},"marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattermapbox":[{"type":"scattermapbox","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scatterternary":[{"type":"scatterternary","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"scattercarpet":[{"type":"scattercarpet","marker":{"colorbar":{"outlinewidth":0,"ticks":""}}}],"carpet":[{"aaxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"baxis":{"endlinecolor":"#2a3f5f","gridcolor":"white","linecolor":"white","minorgridcolor":"white","startlinecolor":"#2a3f5f"},"type":"carpet"}],"table":[{"cells":{"fill":{"color":"#EBF0F8"},"line":{"color":"white"}},"header":{"fill":{"color":"#C8D4E3"},"line":{"color":"white"}},"type":"table"}],"barpolar":[{"marker":{"line":{"color":"#E5ECF6","width":0.5},"pattern":{"fillmode":"overlay","size":10,"solidity":0.2}},"type":"barpolar"}],"pie":[{"automargin":true,"type":"pie"}]},"layout":{"autotypenumbers":"strict","colorway":["#636efa","#EF553B","#00cc96","#ab63fa","#FFA15A","#19d3f3","#FF6692","#B6E880","#FF97FF","#FECB52"],"font":{"color":"#2a3f5f"},"hovermode":"closest","hoverlabel":{"align":"left"},"paper_bgcolor":"white","plot_bgcolor":"#E5ECF6","polar":{"bgcolor":"#E5ECF6","angularaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"radialaxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"ternary":{"bgcolor":"#E5ECF6","aaxis":{"gridcolor":"white","linecolor":"white","ticks":""},"baxis":{"gridcolor":"white","linecolor":"white","ticks":""},"caxis":{"gridcolor":"white","linecolor":"white","ticks":""}},"coloraxis":{"colorbar":{"outlinewidth":0,"ticks":""}},"colorscale":{"sequential":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"sequentialminus":[[0.0,"#0d0887"],[0.1111111111111111,"#46039f"],[0.2222222222222222,"#7201a8"],[0.3333333333333333,"#9c179e"],[0.4444444444444444,"#bd3786"],[0.5555555555555556,"#d8576b"],[0.6666666666666666,"#ed7953"],[0.7777777777777778,"#fb9f3a"],[0.8888888888888888,"#fdca26"],[1.0,"#f0f921"]],"diverging":[[0,"#8e0152"],[0.1,"#c51b7d"],[0.2,"#de77ae"],[0.3,"#f1b6da"],[0.4,"#fde0ef"],[0.5,"#f7f7f7"],[0.6,"#e6f5d0"],[0.7,"#b8e186"],[0.8,"#7fbc41"],[0.9,"#4d9221"],[1,"#276419"]]},"xaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"yaxis":{"gridcolor":"white","linecolor":"white","ticks":"","title":{"standoff":15},"zerolinecolor":"white","automargin":true,"zerolinewidth":2},"scene":{"xaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"yaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2},"zaxis":{"backgroundcolor":"#E5ECF6","gridcolor":"white","linecolor":"white","showbackground":true,"ticks":"","zerolinecolor":"white","gridwidth":2}},"shapedefaults":{"line":{"color":"#2a3f5f"}},"annotationdefaults":{"arrowcolor":"#2a3f5f","arrowhead":0,"arrowwidth":1},"geo":{"bgcolor":"white","landcolor":"#E5ECF6","subunitcolor":"white","showland":true,"showlakes":true,"lakecolor":"white"},"title":{"x":0.05},"mapbox":{"style":"light"},"margin":{"b":0,"l":0,"r":0,"t":30}}},"annotations":[{"align":"left","bgcolor":"white","bordercolor":"black","borderwidth":1,"font":{"size":12},"showarrow":false,"text":"Median response times:<br>Multiple Threads: 5s<br>Single Thread: 8s<br><br>Median % difference: -38%","x":0.98,"xanchor":"right","xref":"paper","y":0.98,"yanchor":"top","yref":"paper"}],"title":{"text":"Density Plot of Overall Time by Judge Type"},"xaxis":{"title":{"text":"Time (seconds)"}},"yaxis":{"title":{"text":"Density"}},"showlegend":true,"width":600,"height":400},                        {"responsive": true}                    ).then(function(){
                            
var gd = document.getElementById('fc69afac-2f68-42f0-90ad-06d3bcdc82bd');
var x = new MutationObserver(function (mutations, observer) {{
        var display = window.getComputedStyle(gd).display;
        if (!display || display === 'none') {{
            console.log([gd, 'removed!']);
            Plotly.purge(gd);
            observer.disconnect();
        }}
}});

// Listen for the removal of the full notebook cells
var notebookContainer = gd.closest('#notebook-container');
if (notebookContainer) {{
    x.observe(notebookContainer, {childList: true});
}}

// Listen for the clearing of the current output cell
var outputEl = gd.closest('.output');
if (outputEl) {{
    x.observe(outputEl, {childList: true});
}}

                        })                };                });            </script>        </div>

The density plot above shows the distribution of response times for both approaches. The multi-threaded approach was indeed faster -- it reduced latency by ~38% on average (median difference) compared to the single-threaded approach.

### Token Usage

```python
# Separate token data by judge type
parallel_input_tokens = [entry['sum_input_tokens'] for entry in data if entry['judge_type'] == 'parallel']
parallel_output_tokens = [entry['sum_output_tokens'] for entry in data if entry['judge_type'] == 'parallel']
combined_input_tokens = [entry['sum_input_tokens'] for entry in data if entry['judge_type'] == 'combined']
combined_output_tokens = [entry['sum_output_tokens'] for entry in data if entry['judge_type'] == 'combined']

# Calculate medians
median_parallel_input = sorted(parallel_input_tokens)[len(parallel_input_tokens)//2]
median_parallel_output = sorted(parallel_output_tokens)[len(parallel_output_tokens)//2]
median_combined_input = sorted(combined_input_tokens)[len(combined_input_tokens)//2]
median_combined_output = sorted(combined_output_tokens)[len(combined_output_tokens)//2]

# Calculate pairwise percentage differences
input_pct_diffs = []
output_pct_diffs = []
for entry_parallel in data:
    if entry_parallel['judge_type'] == 'parallel':
        for entry_combined in data:
            if (entry_combined['judge_type'] == 'combined' and 
                entry_parallel['question'] == entry_combined['question'] and 
                entry_parallel.get('model') == entry_combined.get('model')):
                # Input tokens difference
                input_pct_diff = ((entry_parallel['sum_input_tokens'] - entry_combined['sum_input_tokens']) / 
                                entry_combined['sum_input_tokens'] * 100)
                input_pct_diffs.append(input_pct_diff)
                
                # Output tokens difference
                output_pct_diff = ((entry_parallel['sum_output_tokens'] - entry_combined['sum_output_tokens']) / 
                                 entry_combined['sum_output_tokens'] * 100)
                output_pct_diffs.append(output_pct_diff)

median_input_pct_diff = sorted(input_pct_diffs)[len(input_pct_diffs)//2]
median_output_pct_diff = sorted(output_pct_diffs)[len(output_pct_diffs)//2]

# Print results
print("\nToken Usage Summary:")
print(f"Multiple Threads:")
print(f"  Median Input Tokens:  {median_parallel_input:,}")
print(f"  Median Output Tokens: {median_parallel_output:,}")
print(f"\nSingle Thread:")
print(f"  Median Input Tokens:  {median_combined_input:,}")
print(f"  Median Output Tokens: {median_combined_output:,}")

print(f"\nMedian Pairwise Differences:")
print(f"  Input Tokens:  {median_input_pct_diff:+.1f}%")
print(f"  Output Tokens: {median_output_pct_diff:+.1f}%")
```

```text

Token Usage Summary:
Multiple Threads:
  Median Input Tokens:  2,751
  Median Output Tokens: 1,270

Single Thread:
  Median Input Tokens:  807
  Median Output Tokens: 518

Median Pairwise Differences:
  Input Tokens:  +240.9%
  Output Tokens: +139.5%
```

As expected, token usage increased for the multi-threaded approach. This is due to many of the same input tokens being used for each thread, but also due to the additional output tokens generated by each thread. More output tokens may reflect the additional reasoning and analysis performed by the LLM for each dimension, which may result in higher quality evaluations -- but this was not evaluated here.

## Limitations

This analysis has some limitations that are worth noting. Namely, I didn't evaluate the quality / accuracy of the LLM Judge evaluations. I focused only on the latency and token usage of the LLM Judges. I expect that the quality would be equal (or possibly even better) when using the multi-threaded approach, but I didn't evaluate that here.

## Conclusion

This experiment demonstrated the significant performance benefits of a multi-threaded approach when implementing an LLM judge to evaluate text quality across multiple dimensions. By breaking down the evaluation task into six orthogonal dimensions and processing them in parallel, latency was reduced by ~38% compared to evaluating all dimensions in a single LLM call. At the same time, token usage increased, which may result in higher quality evaluations -- but this was not here.

<script src="https://giscus.app/client.js"
        data-repo="tylerburleigh/tylerburleigh.github.io"
        data-repo-id="R_kgDOKMo8ww"
        data-category="Blog comments"
        data-category-id="DIC_kwDOIg6EJc4CSz92"
        data-mapping="pathname"
        data-strict="0"
        data-reactions-enabled="1"
        data-emit-metadata="0"
        data-input-position="bottom"
        data-theme="light"
        data-lang="en"
        crossorigin="anonymous"
        async>
</script>
