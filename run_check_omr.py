import sys, os
sys.stdout = open(os.path.join(os.path.dirname(__file__), 'scratch', 'check_omr_result.txt'), 'w')
sys.stderr = sys.stdout

exec(open(os.path.join(os.path.dirname(__file__), 'scratch', 'check_omr_data.py')).read())
