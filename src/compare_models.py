
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from recommender import build_recommendations, evaluate
from baseline import build_popularity_recommendations


print("Building popularity baseline...")
baseline = build_popularity_recommendations(top_k=5)
baseline_metrics = evaluate(baseline, k=5)

print("\nBuilding hybrid recommender...")
hybrid = build_recommendations(top_k=5)
hybrid_metrics = evaluate(hybrid, k=5)

print("\n========== MODEL COMPARISON ==========")

print("\nPopularity Baseline:")
for key, value in baseline_metrics.items():
    print(f"{key}: {value}")

print("\nHybrid Recommender:")
for key, value in hybrid_metrics.items():
    print(f"{key}: {value}")

print("\n========== COMPARISON COMPLETE ==========")
