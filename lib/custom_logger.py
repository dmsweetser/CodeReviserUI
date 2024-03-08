import time
import datetime
import os
import logging

class CustomLogger:
    _instance = None

    def __init__(self, log_folder):
        if not CustomLogger._instance:
            CustomLogger._instance = self            
            self.log_folder = log_folder     
            
            self.logger = logging.getLogger("CodeRevisorUI")
            self.logger.setLevel(logging.INFO)

    def log(self, message):
        self._instance.logger.handlers.clear()
        
        # Create the logs folder if it doesn't exist
        os.makedirs(self._instance.log_folder, exist_ok=True)              
        
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self._instance.file_path = os.path.join(self._instance.log_folder, f"log_{current_date}.txt")

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._instance.logger.addHandler(console_handler)

        file_handler = logging.FileHandler(self._instance.file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self._instance.logger.addHandler(file_handler)       
        
        self._instance.logger.info('{} - {}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message))

    def get_file_path(self):
        
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        self._instance.file_path = os.path.join(self._instance.log_folder, f"log_{current_date}.txt")
        
        return self._instance.file_path