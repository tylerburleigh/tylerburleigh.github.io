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