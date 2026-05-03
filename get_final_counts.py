import classifier
import json

def get_counts():
    p = classifier.load_user_profile(email='shreyas6504@gmail.com')
    c = classifier.load_conditions()
    res = classifier.evaluate_all_schemes(p, c)
    print(f"Eligible: {len(res['eligible'])}")
    print(f"Possibly: {len(res['possibly_eligible'])}")

if __name__ == "__main__":
    get_counts()
