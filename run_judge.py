import os
import sys
from pathlib import Path

from judge_agent import JudgeAgent
from llm_client import LLMClient
from log_manager import LogManager


def main():
    runs_dir = Path("runs").resolve()
    if not runs_dir.exists():
        print(f"Error: 'runs' directory not found at {runs_dir}")
        sys.exit(1)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    llm_client = LLMClient(api_key=api_key)

    print(f"Scanning runs in {runs_dir}...")
    
    for run_dir in sorted(runs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
            
        # Check if it's a valid run with an app
        app_path = run_dir / "code" / "dist" / "app"
        if not app_path.exists():
            print(f"Skipping {run_dir.name}: No app found at code/dist/app")
            continue

        print(f"\nEvaluating run: {run_dir.name}")
        
        try:
            # Initialize LogManager pointing to the existing run directory
            # and using a separate log file for the judge
            log_manager = LogManager(
                base_dir="runs", 
                logger_name=f"judge_{run_dir.name}",
                existing_run_dir=str(run_dir),
                program_log_name="program_judge.log"
            )
            
            log_manager.info(f"Starting Judge Agent for run: {run_dir.name}")

            agent = JudgeAgent(
                run_path=str(run_dir),
                llm_client=llm_client,
                log_manager=log_manager,
            )

            log_manager.info("Judge Agent initialized. Starting evaluation...")
            agent.run()
            log_manager.info("Judge Agent finished.")
            
            print(f"Finished evaluating {run_dir.name}. Logs in {run_dir}/logs")
            
        except Exception as e:
            print(f"Error evaluating {run_dir.name}: {e}")


if __name__ == "__main__":
    main()
