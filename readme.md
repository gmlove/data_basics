# 数据库及SQL知识训练

有以下学生考试系统的数据库(student_examination_sys)，里面有三张表：

1. 学生表(student):

   |  id  | name | age  | sex  |
   | :--: | :--: | :--: | :--: |
   | 001  | 张三 |  18  |  男  |
   | 002  | 李四 |  20  |  女  |

2. 考试科目表(subject)：

   |  id  | subject | teacher |   description    |
   | :--: | :-----: | :-----: | :--------------: |
   | 1001 |  语文   | 王老师  | 本次考试比较简单 |
   | 1002 |  数学   | 刘老师  |  本次考试比较难  |

3. 成绩表(score)：

   |  id  | student_id | subject_id | score |
   | :--: | :--------: | :--------: | :---: |
   |  1   |    001     |    1001    |  80   |
   |  2   |    002     |    1001    |  75   |
   |  3   |    001     |    1002    |  70   |
   |  4   |    002     |    1002    | 60.5  |


请编写一个MySQL存储过程`calc_student_stat`计算统计数据并输出到一个新表`student_stat`中。其中需要统计的数据有：

1. avg_score: 该科目平均分
2. score: 学生在该科目下的得分
3. total_score: 学生总分
4. score_rate: 该科目得分占总分的比例

除了上述统计字段，`student_stat`表还包含字段：`name` `teacher` `subject`.