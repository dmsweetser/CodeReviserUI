import time
import datetime
import os
import logging

class CustomLogger:
    def __init__(self, log_folder):
        self.logger = logging.getLogger("CodeRevisorUI")
        self.logger.setLevel(logging.INFO)
        
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.log_folder = log_folder
        self.file_path = os.path.join(self.log_folder, f"log_{current_date}.txt")

        # Create the logs folder if it doesn't exist
        os.makedirs(self.log_folder, exist_ok=True)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        file_handler = logging.FileHandler(self.file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def log(self, message):
        self.logger.info('{} - {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))