#FROM python:3.13.5-slim
FROM python:3.11.2-slim-bullseye


RUN pip install streamlit
RUN pip install opencv-python-headless && pip install Pillow
RUN pip install --no-cache-dir torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cpu

ADD . /minigpt2_shakespeare
WORKDIR /minigpt2_shakespeare

EXPOSE 8501

#HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
