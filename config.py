import toml
import chardet


class Config:

    def __init__(self, filePath):
        self.config_file = filePath
        self.config = None

    @staticmethod
    def detect_charset(file, fallback="utf-8"):
        with open(file, "rb") as f:
            detector = chardet.UniversalDetector()
            for line in f.readlines():
                detector.feed(line)
                if detector.done:
                    return detector.result['encoding']
        return fallback

    def load_config(self):
        with open(self.config_file, "r", encoding=self.detect_charset(self.config_file)) as f:
            self.config = toml.load(f)
            f.close()

    def save_config(self):
        with open(self.config_file, "w", encoding=self.detect_charset(self.config_file)) as f:
            toml.dump(self.config, f)
            f.close()
