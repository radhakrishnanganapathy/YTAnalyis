# YTAnalyis
scraping youtube 

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

streamlit run src/app.py

# To create database
chmod +x script/init_postgres_db.sh
./script/init_postgres_db.sh

