---
title: "Challenging SAMRE: Comparing multi-round debate-style LLM evaluation to a robust (and much simpler) baseline"
date: 2025-01-12
description: "In this post, I re-evaluate a method that was recently published in arXiv, critiquing their baseline model and then designing a new baseline model that implements standard best practices for comparison with the new method. I find that the new evaluation method proposed in the paper does not perform better than this robust baseline. This serves to highlight the importance of implementing best practices in baseline models for comparison with new methods, as well as being skeptical of claims in research papers that compare new methods to baseline."
options:
  categories:
    - prompt-engineering
    - python
    - LLM-as-judge
    - LLM-evals
---

I've been doing a lot of work with LLM-based evaluations lately, and I've been thinking about how to improve the quality of these evaluations.

I like to read research papers from arXiv for inspiration, and I recently came across a paper called [Adversarial Multi-Agent Evaluation of Large Language Models through Iterative Debates](https://arxiv.org/abs/2410.04663), which introduces a new method inspired by judicial process called Single Advocate Multi-Round Evaluation (SAMRE). Briefly, the SAMRE method evaluates the quality of different LLM outputs through an iterative debate process.

I was initially impressed by the results, which reported a gain of ~6-8% over baseline. Below I've reproduced an excerpt from one of the tables in the paper showing their results.


| Model | SAMRE w/o Juries | SAMRE w/o Juries (%) |
|-------|------------------|---------------------|
| Llama-3-8B | 0.05 | 6.3% |
| Qwen | 0.06 | 7.3% |
| Gemini | 0.06 | 7.2% |
| GPT-4-o | 0.07 | 8.3% |
| GPT-4-turbo | 0.07 | 8.2% |
| GPT-3.5-turbo | 0.05 | 6.2% |

: Excerpt from "Table 2: Performance Gains Compared to Baseline"

_Note that the authors had tested versions of SAMRE with and without the addition of "juries". In the table I've included only the version without juries, as it was both simpler and more performant. It is also this more performant version without juries that I am interested in testing. So with that said, in this blog post when I mention "SAMRE", I will be referring to the version without juries._

Despite the impressive results reported in the paper, I am often skeptical when researchers claim to have found that new methods outperform "baseline" models. I have observed that researchers often fail to implement standard best practices in their baseline models, and so their results are therefore not represenative of true gains over baseline. It is as if they are knocking down a straw man.

Given this skepticism of mine, I decided that it might be interesting to put it this skepticism the test: What if I implemented the SAMRE method (again, note that I am referring to the version without juries), and compared it to a baseline model that does implement standard best practices for prompt engineering? Would I find that the SAMRE method is indeed an improvement over the baseline? Or would I find that SAMRE is inferior to a properly implemented baseline?

## TL;DR: What I did and what I found

I tested three model variants:

1. SAMRE, as implemented in the paper (without juries)
2. Baseline-Weak: The baseline model used in the paper (which does not implement standard best practices for prompt engineering)
3. Baseline-Strong: A baseline model that implements standard best practices for prompt engineering as I understand them.

I evaluated each of these models using a sample of 300 conversations from MT-Bench for testing and evaluation. (MT-Bench was used in the original paper as well.)

After running the evaluations and calculating Krippendorff alpha agreement with human judge ground truth, I found that although SAMRE did yield better agreement than Baseline-Weak more importantly it was inferior to Baseline-Strong -- and by a fair margin. A similar result was found when examining binary classification accuracy using Matthews Correlation Coefficient (MCC).

These results serve to highlight the importance of implementing standard best practices in baseline models, as well as being skeptical of claims in research papers that compare new methods to a "baseline model". Prompt engineers need to remain cautious and resist the urge to use complex methods that may seem more sophisticated than standard best practices, without first testing them against a well-engineered baseline.

# Baseline model prompt inadequacies

Here I will consider some of the inadequacies in the Baseline model's prompt reported in the paper, and share a version of the prompt that addresses these inadequacies and implements standard best practices.

The "baseline" prompt used by the authors of the paper was as follows:

```prompt
You are a fair, impartial judge scoring a debate on the following question:
question.
Answer 1: answer_1
Answer 2: answer_2
Score each answer on a scale of 1-20 for each of the following criteria:
1. Relevance to the question
2. Accuracy of information and use of credible sources
3. Depth of analysis and completeness of argument
4. Clarity of expression and logical flow
5. Strength of reasoning and factual support
6. Effectiveness in addressing opponent's points
Provide scores as [answer_1_score, answer_2_score] for each criterion in a list format, then sum for final scores. Please keep an eye on the slightest difference that should make a difference in the scoring. Don't overthink!
Relevance:
Accuracy:
Depth:
Clarity:
Logic and Factuality:
Addressing opponent's points:
Final Scores (sum of above) as a tuple (example: (18, 9)):
Explain your scoring, focusing on why one answer is better than the other based on the criteria above. Keep your explanation concise but informative.
Finally, return the final score tuple (score1, score2) as a tuple (in parentheses).
Example: (18, 9)
Your scores and explanation:
```

Here are the issues I see with this prompt:

1. The prompt does not use delimiters for most of the inputs. I would enclose the inputs inside XML tags like `<Question></Question>`, `<Answer1></Answer1>`, and `<Answer2></Answer2>`, but in a pinch delimiters like triple backticks can be used.

2. The prompt instructs the model to first generate scores in list format, and then to sum them. But as we know, language models models often make arithmetic mistakes. It would be better to ask the model to generate scores for each criterion, and then to programmatically extract and summarize them in python (or another programming language) from which the routine is run.

3. Although the prompt asks the model to "explain your scoring", it is not clear if the model should be reasoning about each criterion before it scores them, or if it should provide reasoning at the end when giving its final score. I would ask the model to provide reasoning for each criterion that it is asked to score, and ask it to reason before scoring.

4. It's unclear why a scale of 1-20 is used. This is not a standard scale for scoring. I would use a scale of 1-10 which is likely more familiar to the model and can be expected to be used more consistently.

5. Although the prompt does suggest that the model provide its scores in tuple format, it would be better to provide more explicit format instructions.

6. The prompt includes an "Effectiveness in addressing opponent's points" criterion, but this is almost certainly irrelevant given that the answers to the question were not generated with the goal of addressing an opponent.

7. Finally, although this goes beyond the prompt itself, the authors of the paper are comparing a multi-round method to a single-round method. This is obviously an unfair comparison. Instead, it would be better to compare the SAMRE method to a baseline that uses the same number of rounds and then similarly averages its scores.

With all of that in mind, here's how I would rewrite the prompt:

```prompt
You are a fair, impartial judge scoring a debate on Question.

<Question>
{question}
</Question>

Two Answers have been given to the Question.

<Answer1>
{answer_1}
</Answer1>

<Answer2>
{answer_2}
</Answer2>

The Answers are being judged on the following Criteria:

<Criteria>
<Criterion1>Relevance to their task</Criterion1>
<Criterion2>Accuracy and credible sources</Criterion2>
<Criterion3>Depth and completeness</Criterion3>
<Criterion4>Clarity and logical flow</Criterion4>
<Criterion5>Reasoning and factual support</Criterion5>
</Criteria>

For each Criterion, briefly analyze the performance of
the two Answers, then give a score between 1 and 10.

Respond as follows:
<Criterion1>
<CriterionName>Relevance to their task</CriterionName>
<Analysis>
Answer 1: [Analysis of Answer 1 performance on the Criterion]
Answer 2: [Analysis of Answer 2 performance on the Criterion]
</Analysis>
<Scores>
<Answer1Score>[score between 1 and 10]</Answer1Score>
<Answer2Score>[score between 1 and 10]</Answer2Score>
</Scores>
</Criterion1>
<Criterion2>
<CriterionName>Accuracy and credible sources</CriterionName>
<Analysis>
Answer 1: [Analysis of Answer 1 performance on the Criterion]
Answer 2: [Analysis of Answer 2 performance on the Criterion]
</Analysis>
<Scores>
<Answer1Score>[score between 1 and 10]</Answer1Score>
<Answer2Score>[score between 1 and 10]</Answer2Score>
</Scores>
</Criterion2>
...
```

Notice that the prompt now uses XML tags to structure the instructions, that it asks the model to provide reasoning for each criterion before scoring, and that it gives the model a clear format for its response that reinforces analysis before scoring for each criterion.

I've also changed the scale from 1-20 to 1-10, removed the unnecessary "Effectiveness in addressing opponent's points" criterion, and removed the instruction to summarize the scores, as I would handle this within the code.

_Note the baseline could be improved even further by requesting the structured output using a mode like OpenAI's Structured Outputs. This would increase the likelihood of the model responding in the desired format. For this test, I will not be using structured outputs._

# Hypothesis and predictions

I hypothesize that SAMRE will NOT perform better than a baseline model that implements standard best practices for prompt engineering.

My predictions are as follows:

1. SAMRE will perform better than Baseline-Weak, as this was what the authors of the paper found and by implementing these methods faithfully from the paper, I can expect to replicate their results.
2. Baseline-Strong will perform better than Baseline-Weak, since the "Strong" variant implements best practices and can be expected to perform better than the "Weak" variant.
3. Baseline-Strong will perform equal to or better than SAMRE, as the best practices implemented in Baseline-Strong will close the gap that exists between SAMRE and Baseline-Weak due to the inadequacies in the Baseline-Weak prompt.

# My implementation of SAMRE and Baseline

Okay, so with those criticisms out of the way, let's design evaluators to implement three methods:

1. SAMRE, as implemented in the paper (without juries)
2. Baseline-Weak: The baseline model used in the paper (which does not implement standard best practices for prompt engineering)
3. Baseline-Strong: A baseline model that implements standard best practices for prompt engineering as I understand them.

Below is my python implementation of these evaluators. To the best of my ability, I have implemented the SAMRE and Baseline methods as described in the paper (I call the paper's Baseline method "Baseline-Weak"). And I have implemented a Baseline-Strong evaluator that implements what I would consider to be standard best practices for prompt engineering, as discussed in an earlier section.

<details><summary>Click to view the implementation code</summary>

```python
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
import os
from openai import AsyncOpenAI
import logging
import re
from contextlib import asynccontextmanager

# Define the prompts
PROMPTS = {
# Prompt for advocates to defend their assigned answer, used in SAMRE
"defend_prompt": """
You're an eloquent advocate (Advocate {advocate_id}) in a group defending this answer:
{answer} to the question: {question}. Your opponent group defends: {opponent_answer}.
Collaborate with your fellow advocates to convince the audience your argument is
better. Use the latest feedback, your opponent's last argument, and your team's previous
arguments to improve your case.
Latest feedback: {feedback}
Opponent's last argument: {opponent_argument}
Your team's previous arguments: team_arguments
Respond in under 80 words.
Your defense:
""",
# Prompt for judge to provide feedback on debate progress, used in SAMRE
"judge_prompt": """
You're a fair, impartial judge in a debate on: "{question}". Answer 1: "{answer_1}".
Answer 2: "{answer_2}". Your goal is to provide feedback that will help advocate groups
improve and differentiate their arguments more clearly.
Current round: {current_round}
Total rounds: {total_rounds}
Previous scores: {previous_scores}
Defense for 1st answer: {defense_1}
Defense for 2nd answer: {defense_2}
Provide specific, constructive feedback to help each advocate group strengthen their
unique position. Encourage them to address weaknesses and highlight distinctions. Aim
for your feedback to lead to more divergent scores in future rounds.
Give your feedback in under 50 words:
""",
# Prompt for SAMRE method scoring
"score_prompt_samre": """
You're a critical, impartial judge in a high-stakes debate on: "{question}". Answer
1: "{answer_1}". Answer 2: "{answer_2}". Your goal is to provide detailed, constructive
feedback that will push advocates to significantly improve their arguments.
Total rounds: {total_rounds}
Previous scores: {previous_scores}
Defense for 1st answer: {defense_1}
Defense for 2nd answer: {defense_2}
Analyze each argument meticulously. Be thorough and unbiased in your assessment of:
1. Relevance to the question
2. Accuracy of information and use of credible sources
3. Depth of analysis and completeness of argument
4. Clarity of expression and logical flow
5. Strength of reasoning and factual support
6. Effectiveness in addressing opponent's points
For each criterion, provide a score on a scale of 1-20 and detailed justification.
Scores should be given as [answer_1_score, answer_2_score] for each criterion.
Your comprehensive feedback for each advocate (50 words each):
Feedback for Advocate 1:
Feedback for Advocate 2:
Sum up the scores and return the final score tuple (score1, score2). Example: (95, 87)
Your detailed scores and final tally:
""",
# Prompt for Baseline-Weak method scoring, which represents the baseline model used in the paper
"score_prompt_baseline_weak": """
You are a fair, impartial judge scoring a debate on the following question:
question.
Answer 1: {answer_1}
Answer 2: {answer_2}
Score each answer on a scale of 1-20 for each of the following criteria:
1. Relevance to the question
2. Accuracy of information and use of credible sources
3. Depth of analysis and completeness of argument
4. Clarity of expression and logical flow
5. Strength of reasoning and factual support
6. Effectiveness in addressing opponent's points
Provide scores as [Answer1_score, Answer2_score] for each criterion in a list format,
then sum for final scores. Please keep an eye on the slightest difference that should
make a difference in the scoring. Don't overthink!
Relevance:
Accuracy:
Depth:
Clarity:
Logic and Factuality:
Addressing opponent's points:
Final Scores (sum of above) as a tuple (example: (18, 9)):
Explain your scoring, focusing on why one answer is better than the other based on the
criteria above. Keep your explanation concise but informative.
Finally, return the final score tuple (score1, score2) as a tuple (in parentheses).
Example: (18, 9)
Your scores and explanation:
""",
# Prompt for Baseline-Strong method scoring, which implements what I consider to be standard best practices for prompt engineering
"score_prompt_baseline_strong": """
You are a fair, impartial judge scoring a debate on Question.

<Question>
{question}
</Question>

Two Answers have been given to the Question.

<Answer1>
{answer_1}
</Answer1>

<Answer2>
{answer_2}
</Answer2>

The Answers are being judged on the following Criteria:

<Criteria>
<Criterion1>Relevance to their task</Criterion1>
<Criterion2>Accuracy and credible sources</Criterion2>
<Criterion3>Depth and completeness</Criterion3>
<Criterion4>Clarity and logical flow</Criterion4>
<Criterion5>Reasoning and factual support</Criterion5>
</Criteria>

For each Criterion, briefly analyze the performance of
the two Answers, then give a score between 1 and 10.

Respond as follows:
<Criterion1>
<CriterionName>Relevance to their task</CriterionName>
<Analysis>
Answer 1: [Analysis of Answer 1 performance on the Criterion]
Answer 2: [Analysis of Answer 2 performance on the Criterion]
</Analysis>
<Scores>
<Answer1Score>[score between 1 and 10]</Answer1Score>
<Answer2Score>[score between 1 and 10]</Answer2Score>
</Scores>
</Criterion1>
<Criterion2>
<CriterionName>Accuracy and credible sources</CriterionName>
<Analysis>
Answer 1: [Analysis of Answer 1 performance on the Criterion]
Answer 2: [Analysis of Answer 2 performance on the Criterion]
</Analysis>
<Scores>
<Answer1Score>[score between 1 and 10]</Answer1Score>
<Answer2Score>[score between 1 and 10]</Answer2Score>
</Scores>
</Criterion2>
...
"""
}

@dataclass
class Memory:
    """Stores debate history including arguments, scores, and feedback for each round, used in SAMRE"""
    arguments: List[Tuple[str, str]] = field(default_factory=list)
    scores: List[Tuple[float, float]] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)

class ModelEvaluator:
    @classmethod
    @asynccontextmanager
    async def create(cls, mode="samre", model="gpt-4o-mini", logging_level=logging.WARNING):
        """Factory method to create evaluator instance with proper async context management"""
        instance = cls(mode=mode, model=model, logging_level=logging_level)
        instance.client = AsyncOpenAI()
        try:
            yield instance
        finally:
            await instance.client.close()

    def _setup_logger(self, logging_level):
        """Setup logger with word wrapping."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging_level)
        if not logger.handlers:
            handler = logging.StreamHandler()
            class WrapFormatter(logging.Formatter):
                def format(self, record):
                    import textwrap
                    message = super().format(record)
                    return '\n'.join(textwrap.fill(line, width=80)
                                for line in message.split('\n'))

            formatter = WrapFormatter('%(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def __init__(self, mode="samre", model="gpt-4o-mini", logging_level=logging.WARNING):
        self.mode = mode
        self.model = model
        # Modify to handle both baseline modes
        self.max_rounds = 1 if mode.startswith("baseline") else 4
        self.logger = self._setup_logger(logging_level)

        # Initialize all prompts
        self.defend_prompt = PROMPTS["defend_prompt"]
        self.judge_prompt = PROMPTS["judge_prompt"]


    async def get_completion(self, prompt: str) -> str:
        """Get a completion from the OpenAI API."""
        if not self.client:
            raise RuntimeError("Evaluator must be created using 'async with ModelEvaluator.create() as evaluator:'")

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0
        )
        return response.choices[0].message.content

    def _extract_final_scores(self, score_response: str) -> Tuple[float, float]:
        """Extracts final scores from model response based on evaluation mode"""
        if self.mode == "samre":
            # Look for final tuple in format (score1, score2)
            tuple_pattern = r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)'
            match = re.search(tuple_pattern, score_response)
            if match:
                return (float(match.group(1)), float(match.group(2)))
            raise ValueError("Could not find score tuple in SAMRE response")

        elif self.mode == "baseline_weak":
            # Look for final tuple in format (score1, score2)
            tuple_pattern = r'\((\d+\.?\d*),\s*(\d+\.?\d*)\)'
            match = re.search(tuple_pattern, score_response)
            if match:
                return (float(match.group(1)), float(match.group(2)))
            raise ValueError("Could not find score tuple in weak baseline response")

        elif self.mode == "baseline_strong":
            # Use XML parsing for strong baseline
            score_a_pattern = r'<Answer1Score>\s*(\d+\.?\d*)\s*</Answer1Score>'
            score_b_pattern = r'<Answer2Score>\s*(\d+\.?\d*)\s*</Answer2Score>'

            scores_a = [float(match.group(1)) for match in re.finditer(score_a_pattern, score_response)]
            scores_b = [float(match.group(1)) for match in re.finditer(score_b_pattern, score_response)]

            if not scores_a or not scores_b:
                raise ValueError("Could not find scores for both candidates")

            if len(scores_a) != len(scores_b):
                raise ValueError(f"Mismatched number of scores: A={len(scores_a)}, B={len(scores_b)}")

            final_score_a = sum(scores_a) / len(scores_a)
            final_score_b = sum(scores_b) / len(scores_b)

            return (final_score_a, final_score_b)

        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    async def evaluate(self, question: str, answer_1: str, answer_2: str, num_rounds: int = 1) -> Dict:
        """Main evaluation entry point that routes to appropriate evaluation method based on mode"""
        if not self.client:
            raise RuntimeError("Evaluator must be created using 'async with ModelEvaluator.create() as evaluator:'")

        if self.mode.startswith("baseline"):
            self.logger.info(f"\n=== Starting {self.mode.title()} Evaluation ===\n")
            return await self._evaluate_baseline(question, answer_1, answer_2, num_rounds)
        else:
            self.logger.info("\n=== Starting SAMRE Evaluation ===\n")
            return await self._evaluate_samre(question, answer_1, answer_2)

    async def _evaluate_baseline(self, question: str, answer_1: str, answer_2: str, num_rounds: int = 1) -> Dict:
        """Implements baseline evaluation methods (both weak and strong)"""
        score_history = []

        num_rounds = 1 if self.mode == "baseline_weak" else num_rounds
        for _ in range(num_rounds):
            # Select appropriate prompt based on mode
            prompt_key = "score_prompt_" + self.mode
            score_prompt = PROMPTS[prompt_key].format(
                question=question,
                answer_1=answer_1,
                answer_2=answer_2
            )
            score_response = await self.get_completion(score_prompt)
            self.logger.info(f"Score response: {score_response}")

            try:
                round_scores = self._extract_final_scores(score_response)
                score_history.append(list(round_scores))
            except Exception as e:
                self.logger.error(f"Score parsing error: {e}")
                self.logger.error(f"Raw score response: {score_response}")
                score_history.append([10.0, 10.0])

        # Calculate average scores across all rounds
        avg_scores = [
            sum(scores[i] for scores in score_history) / len(score_history)
            for i in range(2)
        ]

        # Determine winner based on average scores
        winner = (
            'model_a' if avg_scores[0] > avg_scores[1]
            else 'model_b' if avg_scores[0] < avg_scores[1]
            else 'tie'
        )

        return {
            "winner": winner,
            "average_scores": [round(score, 2) for score in avg_scores] ,
            "rounds": len(score_history),
            "score_history": score_history,
            "full_response": score_response  # Include the final response for analysis
        }

    async def _evaluate_samre(self, question: str, answer_1: str, answer_2: str) -> Dict:
        """Implements SAMRE evaluation with multi-round debate process

        Flow:
        1. Get defenses from both advocates
        2. Judge provides feedback and scores
        3. Repeat until max rounds or convergence
        4. Return averaged results
        """
        local_memory = Memory()

        self.logger.info("\n=== Starting SAMRE Evaluation ===\n")

        for round_num in range(self.max_rounds):
            self.logger.info(f"\n--- Round {round_num + 1} ---")

            scores = await self._run_debate_round(
                question,
                answer_1,
                answer_2,
                round_num,
                local_memory
            )

            if self._has_scores_converged(round_num, local_memory):
                self.logger.info("\nScores have converged - ending debate early.")
                break

        return self._prepare_results(local_memory)

    async def defend_answer(self, question: str, answer_1: str, answer_2: str,
                        advocate_id: int, feedback: str = "",
                        opponent_argument: str = "",
                        team_arguments: List[str] = None) -> str:
        """Get defense from an advocate."""
        if team_arguments is None:
            team_arguments = []

        # Map answers based on advocate_id
        answer = answer_1 if advocate_id == 1 else answer_2
        opponent_answer = answer_2 if advocate_id == 1 else answer_1

        prompt = self.defend_prompt.format(
            question=question,
            advocate_id=advocate_id,
            answer=answer,
            opponent_answer=opponent_answer,
            feedback=feedback,
            opponent_argument=opponent_argument,
            team_arguments="\n".join(team_arguments)
        )
        return await self.get_completion(prompt)

    async def judge_debate(self, question: str, answer_1: str, answer_2: str,
                          defense_1: str, defense_2: str,
                          current_round: int,
                          memory: Memory) -> Tuple[str, Tuple[float, float]]:
        """Judge the debate between two answers."""
        feedback_prompt = self.judge_prompt.format(
            question=question,
            answer_1=answer_1,
            answer_2=answer_2,
            current_round=current_round,
            total_rounds=self.max_rounds,
            previous_scores=memory.scores,
            defense_1=defense_1,
            defense_2=defense_2
        )
        feedback = await self.get_completion(feedback_prompt)

        score_prompt = PROMPTS["score_prompt_samre"].format(
            question=question,
            answer_1=answer_1,
            answer_2=answer_2,
            defense_1=defense_1,
            defense_2=defense_2,
            total_rounds=self.max_rounds,
            previous_scores=memory.scores,
            feedback=feedback
        )
        score_response = await self.get_completion(score_prompt)
        self.logger.info(f"Score response: {score_response}")

        try:
            scores = self._extract_final_scores(score_response)
        except Exception as e:
            self.logger.error(f"Score parsing error: {e}")
            self.logger.error(f"Raw score response: {score_response}")
            scores = (10.0, 10.0)

        return feedback, scores

    async def _run_debate_round(self, question: str, answer_1: str, answer_2: str,
                               round_num: int, memory: Memory) -> Tuple[float, float]:
        """Executes single debate round in SAMRE evaluation"""
        defenses = await self._get_advocate_defenses(question, answer_1, answer_2, memory)
        memory.arguments.append(defenses)

        feedback, scores = await self.judge_debate(
            question, answer_1, answer_2, defenses[0], defenses[1], round_num + 1, memory
        )

        self._store_round_results(feedback, scores, memory)
        self._display_round_results(defenses, feedback, scores)

        return scores

    async def _get_advocate_defenses(self, question: str, answer_1: str, answer_2: str,
                                   memory: Memory) -> Tuple[str, str]:
        """Get defenses from both advocates."""
        defense_1 = await self.defend_answer(
            question, answer_1, answer_2, 1,
            feedback=memory.feedback[-1] if memory.feedback else "",
            opponent_argument=memory.arguments[-1][1] if memory.arguments else "",
            team_arguments=[args[0] for args in memory.arguments]
        )

        defense_2 = await self.defend_answer(
            question, answer_1, answer_2, 2,
            feedback=memory.feedback[-1] if memory.feedback else "",
            opponent_argument=memory.arguments[-1][0] if memory.arguments else "",
            team_arguments=[args[1] for args in memory.arguments]
        )

        return (defense_1, defense_2)

    def _store_round_results(self, feedback: str, scores: Tuple[float, float],
                           memory: Memory) -> None:
        """Store feedback and scores from the round."""
        memory.feedback.append(feedback)
        memory.scores.append(scores)

    def _display_round_results(self, defenses: Tuple[str, str],
                             feedback: str, scores: Tuple[float, float]) -> None:
        """Display the results of the current round."""
        self.logger.info(f"\nAdvocate 1's defense:\n{defenses[0]}")
        self.logger.info(f"\nAdvocate 2's defense:\n{defenses[1]}")
        self.logger.info(f"\nJudge's feedback:\n{feedback}")
        self.logger.info(f"Scores for this round: Answer 1 = {round(scores[0], 2)}, Answer 2 = {round(scores[1], 2)}")

    def _has_scores_converged(self, round_num: int, memory: Memory) -> bool:
        """Checks if debate scores have converged by comparing last two rounds"""
        if round_num > 0:
            prev_diff = memory.scores[-2][0] - memory.scores[-2][1]
            curr_diff = memory.scores[-1][0] - memory.scores[-1][1]
            return (prev_diff * curr_diff) > 0
        return False

    def _prepare_results(self, memory: Memory) -> Dict:
        """Prepare the final results dictionary."""
        avg_scores = [
            round(sum(scores[i] for scores in memory.scores) / len(memory.scores), 2)
            for i in range(2)
        ]

        winner = (
            'model_a' if avg_scores[0] > avg_scores[1]
            else 'model_b' if avg_scores[0] < avg_scores[1]
            else 'tie'
        )

        return {
            "winner": winner,
            "average_scores": avg_scores,
            "rounds": len(memory.scores),
            "score_history": [[round(s[0], 2), round(s[1], 2)] for s in memory.scores],
            "argument_history": memory.arguments,
            "feedback_history": memory.feedback
        }
```

</details>

# Load the MT-Bench dataset

For evaluation, I'll use MT-Bench which is the dataset used in the paper. MT-Bench is a dataset that contains human annotator judgments of preference between two alternative LLM responses.

I'll read the dataset from Llamahub [MtBenchHumanJudgementDataset](https://llamahub.ai/l/llama_datasets/MT%20Bench%20Human%20Judgement%20Dataset?from=), which has simplified the dataset by aggregating human judgments for repeated observations of the same model competitions.

> In the original version, there can be more than one human evaluator for a given example (query, two model responses). In this adapted version however, we aggregate these 'repeated' entries entries and convert the 'winner' column of the original schema to instead represent the proportion of times 'model_a' wins across all of the human evaluators. To adapt this to a llama-dataset, and to better consider ties (albeit with small samples) we set an uncertainty threshold for this proportion in that if it is between [0.4, 0.6] then we consider there to be no winner between the two models.

Although it's not entirely clear from this datacard description, the human evaluator judgments were encoded as "1" (model_a wins), "0" (model_b wins), or "0.5" (tie). Essentially, they were aggregated to represent the majority winner across repeated observations.

```python
# Commented out since the dataset is already downloaded
#!llamaindex-cli download-llamadataset MtBenchHumanJudgementDataset --download-dir ./data
```

<details><summary>Code to load the dataset</summary>

```python
import json
import pandas as pd
from llama_index.core.llama_dataset import LabelledPairwiseEvaluatorDataset

df = LabelledPairwiseEvaluatorDataset.from_json(
    "./data/pairwise_evaluator_dataset.json"
).to_pandas()

# Print the shape of the dataset
print(f'Dataset shape: {df.shape}')

# Print the reference_score value counts, just to confirm that this column is encoding the winner as I expect
print(f'\nReference score (winner) value counts: {df["reference_score"].value_counts()}')
```

</details>

```text
Dataset shape: (1204, 12)

Reference score (winner) value counts: reference_score
0.0    709
1.0    433
0.5     62
Name: count, dtype: int64
```

I'll rename some of the columns, and also encode a "human_winner" column to indicate whether model_a was preferred, model_b, or if there was a tie. (Note: This is just my own preference for how to represent the data).

<details><summary>Code to rename variables and encode a winner column</summary>

```python
df = df[['query', 'answer', 'second_answer', 'answer_by', 'second_answer_by', 'reference_score']]

# Rename as follows: query => question, answer => model_a_answer, second_answer => model_b_answer, answer_by => model_a, second_answer_by => model_b, reference_score => human_winner
df.rename(columns={'query': 'question', 'answer': 'model_a_answer', 'second_answer': 'model_b_answer', 'answer_by': 'model_a', 'second_answer_by': 'model_b', 'reference_score': 'human_winner'}, inplace=True)

# Reencode human winner as "model_a" if 1, "model_b" if 0, and "tie" if 0.5
df['human_winner'] = df['human_winner'].apply(lambda x: 'model_a' if x == 1 else 'model_b' if x == 0 else 'tie')
```

</details>

The original dataset contains ~1200 rows. I'll take a random sample of 300 rows for my testing to save on time and API costs.

<details><summary>Code to take a random sample of 300 rows</summary>

```python
# Take a random sample of 300 rows
df = df.sample(n=300, random_state=42)

df.head()
```

</details>

<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>question</th>
      <th>model_a_answer</th>
      <th>model_b_answer</th>
      <th>model_a</th>
      <th>model_b</th>
      <th>human_winner</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>76</th>
      <td>Write a descriptive paragraph about a bustling...</td>
      <td>The bustling marketplace teemed with life, a v...</td>
      <td>Here is a descriptive paragraph about a bustli...</td>
      <td>ai (gpt-4)</td>
      <td>ai (claude-v1)</td>
      <td>model_a</td>
    </tr>
    <tr>
      <th>158</th>
      <td>Embrace the role of Sheldon from "The Big Bang...</td>
      <td>As Sheldon, I am a staunch proponent of hand d...</td>
      <td>Well, I must say, I find hand dryers to be a r...</td>
      <td>ai (alpaca-13b)</td>
      <td>ai (vicuna-13b-v1.2)</td>
      <td>model_b</td>
    </tr>
    <tr>
      <th>717</th>
      <td>You are given two sorted lists of size m and n...</td>
      <td>One approach to solve this problem with linear...</td>
      <td>To find the kth smallest element in the union ...</td>
      <td>ai (gpt-3.5-turbo)</td>
      <td>ai (vicuna-13b-v1.2)</td>
      <td>model_a</td>
    </tr>
    <tr>
      <th>602</th>
      <td>Develop a Python program that reads all the te...</td>
      <td>Here is a Python program that reads all text f...</td>
      <td>Here's a Python program that reads all the tex...</td>
      <td>ai (claude-v1)</td>
      <td>ai (vicuna-13b-v1.2)</td>
      <td>model_b</td>
    </tr>
    <tr>
      <th>247</th>
      <td>Act as a math teacher. I will provide some mat...</td>
      <td>Probability is a branch of mathematics that de...</td>
      <td>Probability is the likelihood that an event wi...</td>
      <td>ai (vicuna-13b-v1.2)</td>
      <td>ai (alpaca-13b)</td>
      <td>tie</td>
    </tr>
  </tbody>
</table>
</div>

# Use methods to evaluate MT-Bench dataset

Using this sample of 300 rows from the MT-Bench dataset, I will run the three LLM models (Baseline-Weak, Baseline-Strong, and SAMRE) on each set of question and answers.

The code below is the main evaluation loop, designed to run multiple evaluations asynchronously (to save time). It will evaluate each item in the dataset, and save the results to disk as a checkpoint. If the evaluation is interrupted, the code can be resumed from the last checkpoint.

I'll use `gpt-4o-mini` for the evaluations. In the paper they had tested models like `gpt-4o` and `gpt-3.5-turbo`, and I would not expect `gpt-4o-mini` to be an exception.

<details><summary>Click to view the code that runs the evaluations</summary>

```python
import asyncio
from asyncio import Semaphore
import logging
import os
import hashlib
import json
logging.basicConfig(level=logging.WARNING)

async def evaluate_conversation_pair(row, evaluators, semaphore, idx, total):
    """Evaluate a single conversation pair with all evaluators"""
    async with semaphore:
        # Generate pair_id from conversation hash
        pair_id = f"{row['model_a']}_{row['model_b']}_{hashlib.sha256(str(row['question']).encode()).hexdigest()[:12]}"
        checkpoint_file = f'checkpoints/{pair_id}.json'

        # Return existing checkpoint if available
        if os.path.exists(checkpoint_file):
            logging.info(f"Found existing checkpoint file for {pair_id}")
            return json.load(open(checkpoint_file))

        logging.info(f"No checkpoint file found for {pair_id}")
        result = {
            'model_a': row['model_a'],
            'model_b': row['model_b'],
            'human_winner': row['human_winner'],
            'pair_id': pair_id
        }

        try:
            # First run SAMRE evaluation with retries
            for attempt in range(3):
                try:
                    samre_evaluator = evaluators['samre']
                    samre_result = await samre_evaluator.evaluate(
                        row['question'],
                        row['model_a_answer'],
                        row['model_b_answer']
                    )
                    result['samre_winner'] = samre_result['winner']
                    result.update({f'samre_{k}': samre_result[k] for k in ['average_scores', 'rounds', 'score_history']})
                    result.update({
                        'samre_argument_history': samre_result['argument_history'],
                        'samre_feedback_history': samre_result['feedback_history']
                    })
                    break
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        wait_time = (2 ** attempt) * 1
                        print(f"Rate limit hit on SAMRE, waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        if attempt == 2:
                            raise
                    else:
                        raise

            await asyncio.sleep(0.5)

            # Run baseline strong with same number of rounds as SAMRE
            for attempt in range(3):
                try:
                    baseline_strong_evaluator = evaluators['baseline_strong']
                    baseline_strong_result = await baseline_strong_evaluator.evaluate(
                        row['question'],
                        row['model_a_answer'],
                        row['model_b_answer'],
                        num_rounds=result['samre_rounds']
                    )
                    result['baseline_strong_winner'] = baseline_strong_result['winner']
                    result.update({f'baseline_strong_{k}': baseline_strong_result[k]
                                 for k in ['average_scores', 'rounds', 'score_history']})
                    result['baseline_strong_full_response'] = baseline_strong_result['full_response']
                    break
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        wait_time = (2 ** attempt) * 1
                        print(f"Rate limit hit on baseline strong, waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        if attempt == 2:
                            raise
                    else:
                        raise

            await asyncio.sleep(0.5)

            # Run baseline weak with 1 round
            for attempt in range(3):
                try:
                    baseline_weak_evaluator = evaluators['baseline_weak']
                    baseline_weak_result = await baseline_weak_evaluator.evaluate(
                        row['question'],
                        row['model_a_answer'],
                        row['model_b_answer'],
                        num_rounds=1
                    )
                    result['baseline_weak_winner'] = baseline_weak_result['winner']
                    result.update({f'baseline_weak_{k}': baseline_weak_result[k]
                                 for k in ['average_scores', 'rounds', 'score_history']})
                    result['baseline_weak_full_response'] = baseline_weak_result['full_response']
                    break
                except Exception as e:
                    if "rate limit" in str(e).lower():
                        wait_time = (2 ** attempt) * 1
                        print(f"Rate limit hit on baseline weak, waiting {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                        if attempt == 2:
                            raise
                    else:
                        raise

        except Exception as e:
            print(f"Error evaluating row {idx}: {str(e)}")
            result['samre_winner'] = None
            result['baseline_strong_winner'] = None
            result['baseline_weak_winner'] = None
            result['error'] = str(e)

        # Save checkpoint after each evaluation
        os.makedirs('checkpoints', exist_ok=True)
        json.dump(result, open(checkpoint_file, 'w'))

        if (idx + 1) % 10 == 0:
            print(f"Processed {idx + 1}/{total} conversations")

        return result

async def evaluate_conversations_async(df, evaluators, semaphore_limit=3):
    """Evaluate conversations asynchronously"""
    semaphore_limit = 1

    batch_size = 10
    results = []

    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i+batch_size]
        tasks = [
            evaluate_conversation_pair(row[1], evaluators, Semaphore(semaphore_limit), idx, len(df))
            for idx, row in enumerate(batch.iterrows(), start=i)
        ]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

        if i + batch_size < len(df):
            print(f"Completed batch {i//batch_size + 1}, waiting before next batch...")

    return pd.DataFrame(results)

async def main():
    async with ModelEvaluator.create(mode="samre") as samre_evaluator, \
               ModelEvaluator.create(mode="baseline_strong") as baseline_strong_evaluator, \
               ModelEvaluator.create(mode="baseline_weak") as baseline_weak_evaluator:
        return await evaluate_conversations_async(
            df,
            {
                'samre': samre_evaluator,
                'baseline_strong': baseline_strong_evaluator,
                'baseline_weak': baseline_weak_evaluator
            },
            semaphore_limit=1
        )

# Run evaluation with checkpoint recovery
try:
    eval_df = await main()
except Exception as e:
    print(f"Error during evaluation: {str(e)}\nRecovering from checkpoints...")
    eval_df = pd.DataFrame([json.load(open(f'checkpoints/{f}'))
                           for f in os.listdir('checkpoints')
                           if f.endswith('.json')])
finally:
    eval_df.to_csv('eval_df.csv', index=False)
    eval_df.head()

# Drop rows with any null values on the model winner columns
eval_df = eval_df.dropna(subset=['baseline_strong_winner', 'baseline_weak_winner', 'samre_winner'])
```

</details>

# Performance evaluation

Now that the evaluation is complete, I will evaluate the performance of each of the three methods by first looking at how well each method agreed with the human judgments.

I'll use Krippendorff's alpha to measure agreement, since it is a robust measure of agreement that can handle non-binary ratings (among other things).

<details><summary>Click to view the code that calculates agreement</summary>

```python
from krippendorff import alpha
import numpy as np
from sklearn.preprocessing import LabelEncoder

def calculate_agreement(df, rater1_col, rater2_col):
    """
    Calculate Krippendorff's alpha between two raters.

    Args:
        df: DataFrame containing the ratings
        rater1_col: Name of first rater's column
        rater2_col: Name of second rater's column

    Returns:
        float: Krippendorff's alpha score
    """
    # Create label encoder
    le = LabelEncoder()

    # Combine all unique values from both columns
    all_values = pd.concat([df[rater1_col], df[rater2_col]]).unique()
    le.fit(all_values)

    # Transform the ratings to numeric values
    ratings1 = le.transform(df[rater1_col].fillna('missing'))
    ratings2 = le.transform(df[rater2_col].fillna('missing'))

    # Reshape data for krippendorff alpha calculation
    # Each row represents one item, each column represents one rater
    reliability_data = np.vstack([ratings1, ratings2])

    return alpha(reliability_data=reliability_data, level_of_measurement='nominal')

# Calculate agreement scores for all methods
human_baseline_strong_agreement = calculate_agreement(eval_df, 'human_winner', 'baseline_strong_winner')
human_baseline_weak_agreement = calculate_agreement(eval_df, 'human_winner', 'baseline_weak_winner')
human_samre_agreement = calculate_agreement(eval_df, 'human_winner', 'samre_winner')

# Create a DataFrame with the agreement scores
agreement_df = pd.DataFrame({
    'Evaluator Pair': ['Baseline-Strong Agreement with Humans', 'Baseline-Weak Agreement with Humans', 'SAMRE Agreement with Humans'],
    'Krippendorff Alpha': [human_baseline_strong_agreement, human_baseline_weak_agreement, human_samre_agreement]
})

# Round the scores to 3 decimal places
agreement_df['Krippendorff Alpha'] = agreement_df['Krippendorff Alpha'].round(3)

# Calculate the percent difference between Baseline-Strong and Baseline-Weak, and SAMRE and Baseline-Strong
baseline_strong_baseline_weak_diff = (human_baseline_strong_agreement - human_baseline_weak_agreement) / human_baseline_strong_agreement
baseline_strong_samre_diff = (human_baseline_strong_agreement - human_samre_agreement) / human_baseline_strong_agreement
samre_baseline_weak_diff = (human_samre_agreement - human_baseline_weak_agreement) / human_samre_agreement

# Print raw values
print(agreement_df)

# Display the percent difference
print("\nKrippendorff Alpha Improvements:")
print(f"SAMRE vs. Baseline-Weak: {samre_baseline_weak_diff:.0%}")
print(f"Baseline-Strong vs. Baseline-Weak: {baseline_strong_baseline_weak_diff:.0%}")
print(f"Baseline-Strong vs. SAMRE: {baseline_strong_samre_diff:.0%}")
```

</details>

```text
                          Evaluator Pair  Krippendorff Alpha
0  Baseline-Strong Agreement with Humans               0.411
1    Baseline-Weak Agreement with Humans               0.321
2            SAMRE Agreement with Humans               0.369

Krippendorff Alpha Improvements:
SAMRE vs. Baseline-Weak: 13%
Baseline-Strong vs. Baseline-Weak: 22%
Baseline-Strong vs. SAMRE: 10%
```

Although none of the methods yielded particularly strong agreement with the human judges in an absolute sense, their relative performance is in line with my predictions:

1. As reported in the paper, SAMRE yielded significantly better agreement than Baseline-Weak (0.369 vs. 0.321, an increase of ~13%).
2. Baseline-Strong yielded significantly better agreement than Baseline-Weak (0.411 vs. 0.321, an increase of ~22%).
3. Importantly, Baseline-Strong also yielded significantly better agreement than SAMRE (0.411 vs. 0.321, an increase of ~10%)!

Next, we can also measure performance in terms of binary classification accuracy using Matthews Correlation Coefficient (MCC) as a balanced accuracy metric, while re-encoding the "winner" columns to indicate whether model_a was selected as better (1) or not better (0) in each case.

<details><summary>Click to view the code that calculates Matthews Correlation Coefficient (MCC)</summary>

```python
# Encode winner as binary
def encode_winner_as_binary(winner):
    return 1 if winner == 'model_a' else 0

# Create binary columns for each evaluator
eval_df['human_model_a_better'] = eval_df['human_winner'].apply(encode_winner_as_binary)
eval_df['baseline_strong_model_a_better'] = eval_df['baseline_strong_winner'].apply(encode_winner_as_binary)
eval_df['baseline_weak_model_a_better'] = eval_df['baseline_weak_winner'].apply(encode_winner_as_binary)
eval_df['samre_model_a_better'] = eval_df['samre_winner'].apply(encode_winner_as_binary)

from sklearn.metrics import matthews_corrcoef

# Calculate MCC for each method
metrics_df = pd.DataFrame({
    'Method': ['Baseline-Strong', 'Baseline-Weak', 'SAMRE'],
    'MCC': [
        matthews_corrcoef(
            eval_df['human_model_a_better'],
            eval_df['baseline_strong_model_a_better']
        ),
        matthews_corrcoef(
            eval_df['human_model_a_better'],
            eval_df['baseline_weak_model_a_better']
        ),
        matthews_corrcoef(
            eval_df['human_model_a_better'],
            eval_df['samre_model_a_better']
        )
    ]
})

# Round the scores to 3 decimal places
metrics_df['MCC'] = metrics_df['MCC'].round(3)

# Calculate the percent differences
def calc_percent_diff(new, old):
    return (new - old) / old * 100

# MCC differences
samre_baseline_weak_mcc_diff = calc_percent_diff(
    metrics_df.loc[metrics_df['Method'] == 'SAMRE', 'MCC'].iloc[0],
    metrics_df.loc[metrics_df['Method'] == 'Baseline-Weak', 'MCC'].iloc[0]
)
baseline_strong_baseline_weak_mcc_diff = calc_percent_diff(
    metrics_df.loc[metrics_df['Method'] == 'Baseline-Strong', 'MCC'].iloc[0],
    metrics_df.loc[metrics_df['Method'] == 'Baseline-Weak', 'MCC'].iloc[0]
)
baseline_strong_samre_mcc_diff = calc_percent_diff(
    metrics_df.loc[metrics_df['Method'] == 'Baseline-Strong', 'MCC'].iloc[0],
    metrics_df.loc[metrics_df['Method'] == 'SAMRE', 'MCC'].iloc[0]
)

# Print raw values
print(metrics_df)

print("\nMCC Improvements:")
print(f"SAMRE vs. Baseline-Weak: {samre_baseline_weak_mcc_diff:.0f}%")
print(f"Baseline-Strong vs. Baseline-Weak: {baseline_strong_baseline_weak_mcc_diff:.0f}%")
print(f"Baseline-Strong vs. SAMRE: {baseline_strong_samre_mcc_diff:.0f}%")
```

</details>

```text
            Method    MCC
0  Baseline-Strong  0.482
1    Baseline-Weak  0.417
2            SAMRE  0.401

MCC Improvements:
SAMRE vs. Baseline-Weak: -4%
Baseline-Strong vs. Baseline-Weak: 16%
Baseline-Strong vs. SAMRE: 20%
```

Looking at MCC values, we observe a similar pattern of findings to the Krippendorff alphas:

1. SAMRE did not perform better than Baseline-Weak, in fact it performed slightly worse (0.401 vs. 0.417, a decrease of 4%). This is a bit different than what we saw with Krippendorff alpha.
2. Baseline-Strong performed better than Baseline-Weak (0.482 vs. 0.401, an increase of 16%).
3. Baseline-Strong performed better than SAMRE (0.464 vs. 0.401, an increase of 20%).

_Side-note: Why does MCC disagree with the Krippendorff alpha on the SAMRE vs. Baseline-Weak comparison? I would guess this is due to how ties were resolved when encoding the winner as binary._

Finally, we can look at accuracy in terms of percentage agreement. Percentage agreement is not a "balanced" accuracy metric and therefore needs to be used with caution (for example, if the classes are imbalanced, then percentage agreement accuracy can be misleading). But it is the metric used in the paper.

<details><summary>Click to view the code that calculates percentage agreement</summary>

```python
# Calculate percentage agreement for each method
def calculate_percent_agreement(df, rater1_col, rater2_col):
    """Calculate percentage agreement between two raters"""
    return (df[rater1_col] == df[rater2_col]).mean()

# Calculate agreement percentages
agreement_percentages = pd.DataFrame({
    'Method': ['Baseline-Strong', 'Baseline-Weak', 'SAMRE'],
    'Agreement': [
        calculate_percent_agreement(eval_df, 'human_winner', 'baseline_strong_winner'),
        calculate_percent_agreement(eval_df, 'human_winner', 'baseline_weak_winner'),
        calculate_percent_agreement(eval_df, 'human_winner', 'samre_winner')
    ]
})

# Round to 3 decimal places and convert to percentage
agreement_percentages['Agreement'] = (agreement_percentages['Agreement'] * 100).round(1)

# Calculate the percentage point differences
samre_baseline_weak_diff = (
    agreement_percentages.loc[agreement_percentages['Method'] == 'SAMRE', 'Agreement'].iloc[0] -
    agreement_percentages.loc[agreement_percentages['Method'] == 'Baseline-Weak', 'Agreement'].iloc[0]
)
baseline_strong_baseline_weak_diff = (
    agreement_percentages.loc[agreement_percentages['Method'] == 'Baseline-Strong', 'Agreement'].iloc[0] -
    agreement_percentages.loc[agreement_percentages['Method'] == 'Baseline-Weak', 'Agreement'].iloc[0]
)
baseline_strong_samre_diff = (
    agreement_percentages.loc[agreement_percentages['Method'] == 'Baseline-Strong', 'Agreement'].iloc[0] -
    agreement_percentages.loc[agreement_percentages['Method'] == 'SAMRE', 'Agreement'].iloc[0]
)

# Print raw values
print("Percentage Agreement with Human Judgments:")
print(agreement_percentages)

print("\nPercentage Point Differences:")
print(f"SAMRE vs. Baseline-Weak: {samre_baseline_weak_diff:+.1f}")
print(f"Baseline-Strong vs. Baseline-Weak: {baseline_strong_baseline_weak_diff:+.1f}")
print(f"Baseline-Strong vs. SAMRE: {baseline_strong_samre_diff:+.1f}")
```

</details>

```text
Percentage Agreement with Human Judgments:
            Method  Agreement
0  Baseline-Strong       68.4
1    Baseline-Weak       62.8
2            SAMRE       67.0

Percentage Point Differences:
SAMRE vs. Baseline-Weak: +4.2
Baseline-Strong vs. Baseline-Weak: +5.6
Baseline-Strong vs. SAMRE: +1.4
```

Overall across these three metrics, the story is the same: SAMRE did not perform better than a baseline that is designed with best practices.

# Conclusion

In this post, I have shown that SAMRE does not perform better than a well-engineered baseline method. Prompt engineers need to remain cautious and resist the urge to use complex methods that may seem more sophisticated than standard best practices, without first testing them against a well-engineered baseline.