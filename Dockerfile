FROM python:3.13-slim
WORKDIR /app
COPY app.py /app/
COPY static /app/static
COPY build_overlay.py /app/
ENV DATA_DIR=/data TZ=Europe/Sofia PYTHONUNBUFFERED=1
RUN python /app/build_overlay.py && rm /app/build_overlay.py && mkdir /data && chown -R 99:100 /data /app
USER 99:100
EXPOSE 8080
VOLUME /data
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"
CMD ["python", "app.py"]
