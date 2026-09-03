Flask API using Model-View-Controller architecture

Setup instructions

1. cd into stock_daddy_api
2. Start a virtual environment if desired. Or setup python paths
(venv\Scripts\Activate.ps1)
3. Install dependencies with pip install -r requirement.txt
4. create folder named .env put the below (.env uncommitted to be used in alongside .gitignore in case we ever have keys/pswrds we do not want shared)
DB_PATH=../frontend/stockdaddy.db
FLASK_DEBUG=True
5. Start flask server
python app.py
test with the below. May be different port. if you have 
http://127.0.0.1:5000/businesses


Running pytest. 

1. From the stock_daddy_api dir
python tests/run_all_tests.py

2. If desired, you can also run individual test 