import os
import cv2
import re

class Filesaver():

    def save(self, output_dir, prefix, no, image):
        if output_dir != "":
            dir_path =  os.path.join(output_dir, prefix)
            try:
                os.mkdir(dir_path)
            except FileExistsError:
                pass
            path =  os.path.join(dir_path, str(no) + ".png")
            cv2.imwrite(path, image)
            print("saving " + path)
        else:
            print("empty output dir")

    def get_last_file_number(self, path):
        files = os.listdir(path)
        last_file = max(files, key=lambda x: self.__get_match__(x))
        return int(last_file.split(".")[0])if last_file else 0

    def __get_match__(self, item):
        match = re.search(r'\d+', item)
        if match:
            return int(match.group())
        else:
            return -1