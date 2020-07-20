import unittest
import json

from student_io import convert_file_format


class StudentIOTest(unittest.TestCase):
    def test_convert_file_format(self):
        convert_file_format('./student.csv', './student.json', 'csv', 'json')

        with open('./student.json', 'r', encoding='utf8') as f:
            students = json.load(f)

        self.assertDictEqual(students[0], {
            'name': '张三', 'age': 18, 'gender': '男', 'class': '高三三班', 'score': 98
        })


if __name__ == '__main__':
    unittest.main()
