.PHONY: install run clean

install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

run:
	./venv/bin/python run.py

clean:
	rm -rf data/chroma_db data/uploads data/sources.json data/chat_history.json venv
	mkdir -p data/chroma_db data/uploads
