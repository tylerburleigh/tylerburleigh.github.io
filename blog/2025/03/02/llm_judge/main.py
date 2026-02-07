import asyncio
from .experiment import ExperimentRunner
from .config import ExperimentConfig

async def main():
    config = ExperimentConfig()
    runner = ExperimentRunner(
        sample_size=config.SAMPLE_SIZE,
        seed=config.RANDOM_SEED
    )
    
    qa_pairs = await runner.load_qa_pairs()
    runs = await runner.run_experiment(qa_pairs, config.NUM_RUNS)
    runner.print_statistics(runs)

if __name__ == "__main__":
    asyncio.run(main()) 