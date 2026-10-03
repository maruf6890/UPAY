"""python -m scripts.train   (trains LightGBM quantile models + Isolation Forest, evaluates, saves artifacts/)"""
from app.ml.pipeline import run_training

if __name__ == "__main__":
    run_training()
