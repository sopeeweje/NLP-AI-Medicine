import csv
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib
matplotlib.use('TkAgg')
import pickle
import numpy as np
from nltk import word_tokenize
from nltk.stem import WordNetLemmatizer, PorterStemmer
import argparse

def mk_int(s):
    """
    Parameters
    ----------
    s : string

    Returns
    -------
    int
        string to int conversion.
    """
    s = s.strip()
    return int(float(s)) if s else 0

def process_data(data_file):
    """
    

    Parameters
    ----------
    data_file : path to csv
        Raw data file

    Returns
    -------
    data : list of dictionaries representing awards until 2020
    test_data : list of dictionaries representing awards in 2021

    """
    data = []
    with open(data_file, newline='', encoding='utf8') as csvfile:
        reader = csv.reader(x.replace('\0', '') for x in csvfile)
        raw_data = list(reader)
        ids = []
        print("Raw data N: {}".format(str(len(raw_data))))
        c = {}
        for j in range(len(raw_data[0])):
            c[raw_data[0][j]] = j
        for i in range(1,len(raw_data)):
            if len(raw_data[i][c["direct_cost_amt"]]) <= 1:
                continue
            elif ("No abstract available" in raw_data[i][c["abstract_text"]]) or len(raw_data[i][c["abstract_text"]])==0:
                continue
            elif (raw_data[i][c["appl_id"]] in ids) or (raw_data[i][c["activity_code"]][0] in ['Z','T']):
                continue
            else:
                ids.append(raw_data[i][c["appl_id"]])
            abstract = raw_data[i][c["abstract_text"]].replace('\n',' ')
            title = raw_data[i][c["project_title"]]
            relevance = raw_data[i][c["phr_text"]].replace('\n',' ')
            data.append({
                "text": title + " " + abstract + " " + relevance,
                "title": title,
                "id": raw_data[i][c["appl_id"]],
                "project_number": raw_data[i][c["project_num"]][1:].split("-")[0],
                "terms": raw_data[i][c["terms"]].split(";"),
                "administration": raw_data[i][c["agency_ic_admin_abbreviation"]],
                "organization": raw_data[i][c["organization_org_name"]],
                "mechanism": raw_data[i][c["activity_code"]],
                "year": raw_data[i][c["fiscal_year"]],
                "award_amount": mk_int(raw_data[i][c["award_amount"]]),
                "cong_dist": raw_data[i][c["cong_dist"]]
                })

    new_data = []
    for item in data:
        if item["award_amount"] != 0:
            new_data.append(item)

    data = []
    test_data = []
    for item in new_data:
        if item["year"] != "2021":
            data.append(item)
        else:
            test_data.append(item)

    with open("data/data.pkl", 'wb') as handle:
        pickle.dump(data, handle)

    with open("data/test-data.pkl", 'wb') as handle:
        pickle.dump(test_data, handle)

    print("Processed data N: {}".format(str(len(data))))
    return data, test_data

class LemmaStemmerTokenizer:
    """
    Tokenizer that lemmatizes and stems words
    """
    def __init__(self):
        self.wnl = WordNetLemmatizer()
        self.ps = PorterStemmer()
    def __call__(self, doc):
        # leaving out stemming for now
        return [self.wnl.lemmatize(t).lower() for t in word_tokenize(doc) if (t.isalpha() and len(t) > 1)]

def feature_extraction(data, num_features, max_df):
    """

    Parameters
    ----------
    data : parallels "data" from process_data

    Returns
    -------
    features:
        funding - institution's funding in 2020
        year - one-hot encoded year
        text - tfidf for all text data
    """
    input_text = [item["text"] for item in data]
    print("Vectorizing...")
    vectorizer = TfidfVectorizer(tokenizer=LemmaStemmerTokenizer(), stop_words='english', ngram_range=(1,2), max_df=max_df, max_features=num_features).fit(input_text)
    processed_text = vectorizer.transform(input_text)

    with open("data/processed-data.pkl", 'wb') as handle:
        pickle.dump(processed_text, handle)

    with open("data/vectorizer.pkl", 'wb') as handle:
        pickle.dump(vectorizer, handle)
    print("Data vectorized.")

def get_features():
    """
    Parameters
    ----------
    None

    Returns
    -------
    A text file with a list of TF-IDF feature names
    """
    # Vectorizer to convert raw documents to TF-IDF features
    vector = pickle.load(open("data/vectorizer.pkl","rb"))

    # Get feature names and save to text file
    centroid_file = open("data/features", "w", encoding='utf8')
    for i in vector.get_feature_names_out():
        centroid_file.write(i)
        centroid_file.write("\n")
    centroid_file.close()

if __name__ == "__main__":
    # Arguments: maximum number of features and maximum document frequency 
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--max_features',
        type=int,
        required=True,
        help='number of features',
        default=2000,
        )
    parser.add_argument(
        '--max_df',
        type=float,
        required=True,
        help='maximum document frequency',
        default=0.5,
        )
    FLAGS, unparsed = parser.parse_known_args()
    
    
    # Feature extraction
    file = 'data/raw_data.csv'
    data, test_data = process_data(file)
    feature_extraction(data, FLAGS.max_features, FLAGS.max_df)
    get_features()
    # data = data + test_data

    # By Funder
    funder_map = {}
    with open("data/nih_institutes.csv", newline='', encoding='utf8') as csvfile:
        raw_data = list(csv.reader(csvfile))
        for i in range(1, len(raw_data)):
            funder_map[raw_data[i][0]] = raw_data[i][1]
    
    funders = np.unique(np.array([item["administration"] for item in data]))
    output = [["Funder", "Number of awards", "Value of awards"]]
    for funder in funders:
        count = len([item for item in data if item["administration"] == funder])
        amount = sum([item["award_amount"] for item in data if item["administration"] == funder])
        funder = funder_map[funder] if (funder in funder_map) else funder
        output.append([funder, count, amount])
    with open('data/by_funder.csv', 'w', newline='', encoding='utf8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(output)

    # By Year
    years = np.unique(np.array([item["year"] for item in data]))
    output = [["Year", "Number of awards", "Value of awards"]]
    for year in years:
        count = len([item for item in data if item["year"] == year])
        amount = sum([item["award_amount"] for item in data if item["year"] == year])
        output.append([year, count, amount])
    with open('data/by_year.csv', 'w', newline='', encoding='utf8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(output)
    
    # By Mechanism
    mechanisms = np.unique(np.array([item["mechanism"] for item in data]))
    output = [["Mechanism", "Number of awards", "Value of awards"]]
    for mech in mechanisms:
        count = len([item for item in data if item["mechanism"] == mech])
        amount = sum([item["award_amount"] for item in data if item["mechanism"] == mech])
        output.append([mech, count, amount])
    with open('data/by_mechanism.csv', 'w', newline='', encoding='utf8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(output)
