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

    def load(self, output_dir, prefix, no):
        if output_dir != "":
            dir_path =  os.path.join(output_dir, prefix)
            if not os.path.exists(dir_path):
                print("Given path doesn't exist")
                return None
            path =  os.path.join(dir_path, str(no) + ".png")
            if not os.path.exists(path):
                print("No matching image found")
                return None
            image = cv2.imread(path)
            return image
        else:
            print("empty output dir")
            return None

    def get_last_file_number(self, path):
        files = os.listdir(path)
        if len(files) == 0:
            return 0
        last_file = max(files, key=lambda x: self.__get_match__(x))
        try:
            return int(last_file.split(".")[0])if last_file else 0
        except ValueError:
            return 0

    def __get_match__(self, item):
        match = re.search(r'\d+', item)
        if match:
            return int(match.group())
        else:
            return -1