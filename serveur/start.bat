python3 -m venv env
env\Scripts\activate
pip install fastapi uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000