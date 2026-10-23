FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN rm -f /app/*.db /app/*.sqlite /app/*.sqlite3
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 3001
ENV PORT=3001
ENV TZ=Asia/Tashkent
CMD ["python", "bot.py"]
