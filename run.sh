pipenv lock --clear
pipenv install
pipenv run python plotting.py
#pipenv run python feature_extraction.py --max_df 0.1 --max_features 500
# pipenv run python find_centroids.py --max_df 0.1 --max_features 500 --k 60
#pipenv run python analyze_clusters.py --k 80 --trials 1