from typing import Iterable
import time
import threading

DELTA_TIME = 15
ARTICLE_TIME = 60

def countdown(get_parquets_function, duration: int):
    while True:
        temp_duration = duration
        while temp_duration > 0:
            time.sleep(1)
            temp_duration -= 1
            print(temp_duration)
        get_parquets_function()

def process_feed(rows: Iterable[dict]) -> None:
    print("Processing feed ...")

def get_articles_parquets() -> None:
    print("Parquets")

def get_delta_parquets() -> None:
    print("Delta Parquets")

def main() -> None:
    thread_articles = threading.Thread(target=countdown, args=(get_articles_parquets, ARTICLE_TIME))
    thread_delta = threading.Thread(target=countdown, args=(get_delta_parquets, DELTA_TIME))

    thread_articles.start()
    thread_delta.start()

    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
