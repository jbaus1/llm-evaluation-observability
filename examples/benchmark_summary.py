from evaluation.benchmark import CASES
from evaluation.evaluate import evaluate_case


def main() -> None:
    print(
        f"{'Case':<10} {'Coverage':>10} {'Attribution':>13} {'Alignment':>11}   Purpose"
    )
    for benchmark_case in CASES:
        scores = {
            result.metric_name: result.score
            for result in evaluate_case(benchmark_case.as_evaluation_case())
        }
        print(
            f"{benchmark_case.case_id:<10} "
            f"{scores['fact_coverage']:>10.2f} "
            f"{scores['evidence_attribution']:>13.2f} "
            f"{scores['human_alignment']:>11.2f}   "
            f"{benchmark_case.purpose}"
        )


if __name__ == "__main__":
    main()
