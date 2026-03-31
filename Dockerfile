FROM tensorflow/tensorflow:2.15.0-jupyter

ARG UID=1000
ARG GID=1000

ENV HOST 0.0.0.0
ENV PYTHONPATH /app

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g $GID developer && \
    useradd -m -u $UID -g developer developer

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

USER developer

EXPOSE 8888 5000 8501

CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser"]
