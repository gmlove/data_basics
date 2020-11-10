hive 演示
---------------

## 环境准备

为了降低系统的负载，我们先把集群恢复成单NN的形式。参考[集群搭建](简单hdfs集群搭建.md)完成。

1. 修改`core-site.xml`和`hdfs-site.xml`。
2. 删除已有的文件`rm -rf data/hd01-1/* data/hd01-2/*`。
3. 重新格式化并启动集群：`hdfs namenode format && start-all.sh`

### 安装

```bash
wget https://mirror.bit.edu.cn/apache/hive/hive-3.1.2/apache-hive-3.1.2-bin.tar.gz
tar xf apache-hive-3.1.2-bin.tar.gz
ln -sv apache-hive-3.1.2-bin hive
cat >> env <<EOF
export HIVE_HOME=/app/hive
export PATH=\${HIVE_HOME}/bin:\${PATH}
EOF
source ./env

yum install -y mariadb-server
/usr/libexec/mariadb-prepare-db-dir mariadb.service
cd /hd && (/usr/bin/mysqld_safe --basedir=/usr 2>&1 1>hive/hive.metastore.mysql.log &)
mysql -uroot -e "create user 'hive'@'localhost' identified by '123456'; grant all on *.* to hive@'localhost';"
wget https://cdn.mysql.com/archives/mysql-connector-java-8.0/mysql-connector-java-8.0.20.tar.gz
tar xf mysql-connector-java-8.0.20.tar.gz
cp mysql-connector-java-8.0.20/mysql-connector-java-8.0.20.jar hive/lib/

schematool --dbType mysql -initSchema
mkdir hive/logs
hive --service metastore 2>&1 1>hive/logs/hive-metastore.log &
hiveserver2 2>&1 1>hive/logs/hive-server.log &
```

### 设置数据库

```bash
docker run -d -e MYSQL_ROOT_PASSWORD=123456 --name minkbank-db mysql:8
IP=${docker inspect --format '{{ .NetworkSettings.IPAddress }}' minkbank-db}
echo $IP
docker cp minibank.sql.gz minkbank-db:/tmp
docker exec minkbank-db bash -c 'mysql -uroot -p123456 -e "create database minibank1 default charset utf8"'
docker exec minkbank-db bash -c 'cd /tmp && gunzip minibank.sql.gz && mysql -uroot -p123456 < minibank.sql'
```

### 和spark共享元数据(使用derby metastore)

```bash
mkdir metastore_db
cd hive/ && mv metastore_db metastore_db.bak && ln -sv ../metastore_db metastore_db
cd spark/ && mv metastore_db metastore_db.bak && ln -sv ../metastore_db metastore_db
```

### 用spark将数据导入到hive:

在`spark-shell`中执行以下脚本（需要先停止hive `make stop-hive`）：

```scala
import org.apache.spark.sql._
List(
    "loan_account", "loan_accountchangehistory", "loan_address", "loan_badloan", 
    "loan_car", "loan_carloan", "loan_carmodel", "loan_chattel", "loan_company", "loan_customer", 
    "loan_customercreditscore", "loan_dates", "loan_estate", "loan_job", "loan_loan", "loan_loanapproval", 
    "loan_loancollection", "loan_loanguarantee", "loan_loanmortgage", "loan_loanpayment", "loan_overdue_rates"
).foreach(table => {
val jdbcDF = spark.read
  .format("jdbc")
  .option("url", "jdbc:mysql://172.17.0.16:3306/minibank")
  .option("dbtable", s"minibank.${table}")
  .option("user", "root")
  .option("password", "123456")
  .load()
jdbcDF.write.mode(SaveMode.Overwrite).saveAsTable(s"minibank.${table}")
})
```

### 用sqoop将数据导入到hive:

```bash
wget https://mirror.bit.edu.cn/apache/sqoop/1.4.7/sqoop-1.4.7.bin__hadoop-2.6.0.tar.gz
tar xf sqoop-1.4.7.bin__hadoop-2.6.0.tar.gz
ln -sv sqoop-1.4.7.bin__hadoop-2.6.0 sqoop

cat >> env <<EOF
export SQOOP_HOME=/app/sqoop
export HADOOP_CLASSPATH=\${HIVE_HOME}/lib/*
export PATH=\${SQOOP_HOME}/bin:\${PATH}
EOF

source ./env

sqoop import --table loan_loan --connect jdbc:mysql://172.17.0.16:3306/minibank --username root --password 123456 --hive-import --hive-overwrite --hive-database minibank --warehouse-dir /user/hive/warehouse --hive-table loan_loan
sqoop import --table loan_loanpayment --connect jdbc:mysql://172.17.0.16:3306/minibank --username root --password 123456 --hive-import --hive-overwrite --hive-database minibank --warehouse-dir /user/hive/warehouse --hive-table loan_loanpayment
```

## 演示`explain`

1. 进入hive cli: `hive`

2. 确认变量（确保mapreduce在yarn上面运行）：`set mapreduce.framework.name=yarn;`

3. 执行`select * from loan_loan limit 10;`，观察输出的日志。

4. 执行`explain select * from loan_loan;`，观察提交的MR任务详情。

5. 执行`explain select payment_periods, count(*) from loan_loan group by payment_periods order by count(*);`，观察提交的MR任务详情。观察可以发现，此时有两个MR任务生成。

可以观察到每一个MR任务的Reduce最后一步都是FileOutputOperator，它将把运行的结果输出到文件中。只要查询被分拆为多个MR任务，整个查询效率就将大大降低，因为读写文件，启动任务耗费了很多时间。

## 演示`hive on tez`

由于tez没有提供hadoop 3兼容的二进制包，所以我们在hdp里面进行演示。

1. 进入hdp的容器`docker exec -it sandbox-hdp bash`

2. 运行`hive`进入命令行，执行`set hive.execution.engine;`查看当前的引擎。这里应该会显示`tez`。

3. 接着执行`explain select payment_periods, count(*) from loan_loan group by payment_periods order by count(*);`，这里将会观察到只有一个stage，同时我们可以看到DAG的一些边的定义。

```
Vertex dependency in root stage
Reducer 2 <- Map 1 (SIMPLE_EDGE)
Reducer 3 <- Reducer 2 (SIMPLE_EDGE)
...
```

4. 执行上述查询`select payment_periods, count(*) from loan_loan group by payment_periods order by count(*);`，将看到查询很快完成，在进度监控里面能看到下述信息：

```
----------------------------------------------------------------------------------------------
        VERTICES      MODE        STATUS  TOTAL  COMPLETED  RUNNING  PENDING  FAILED  KILLED
----------------------------------------------------------------------------------------------
Map 1 .......... container     SUCCEEDED      1          1        0        0       0       0
Reducer 2 ...... container     SUCCEEDED      2          2        0        0       0       0
Reducer 3 ...... container     SUCCEEDED      1          1        0        0       0       0
----------------------------------------------------------------------------------------------
VERTICES: 03/03  [==========================>>] 100%  ELAPSED TIME: 2.81 s
----------------------------------------------------------------------------------------------
INFO  : Status: DAG finished successfully in 2.77 seconds
INFO  :
INFO  : Query Execution Summary
INFO  : ----------------------------------------------------------------------------------------------
INFO  : OPERATION                            DURATION
INFO  : ----------------------------------------------------------------------------------------------
INFO  : Compile Query                           0.18s
INFO  : Prepare Plan                            2.98s
INFO  : Get Query Coordinator (AM)              0.00s
INFO  : Submit Plan                             0.23s
INFO  : Start DAG                               0.88s
INFO  : Run DAG                                 2.77s
INFO  : ----------------------------------------------------------------------------------------------
INFO  :
INFO  : Task Execution Summary
INFO  : ----------------------------------------------------------------------------------------------
INFO  :   VERTICES      DURATION(ms)   CPU_TIME(ms)    GC_TIME(ms)   INPUT_RECORDS   OUTPUT_RECORDS
INFO  : ----------------------------------------------------------------------------------------------
INFO  :      Map 1           1512.00          3,280             72           2,000                3
INFO  :  Reducer 2            243.00            790              9               3                6
INFO  :  Reducer 3              0.00            290              0               3                0
INFO  : ----------------------------------------------------------------------------------------------
```

可以看到整个查询花费了10s左右，DAG执行时间3s左右，速度是很快的。对比之前的结果，之前整个查询需要花费30s。

5. hdp配置的环境不兼容mr引擎，所以我们只是执行`explain`查看一下在mr引擎下面的任务。先运行`set hive.execution.engine=mr;`将当前引擎设置为mr，接着执行`explain select payment_periods, count(*) from loan_loan group by payment_periods order by count(*);`查看生成的任务，将能看到如下的信息：

```
| STAGE DEPENDENCIES:                                |
|   Stage-1 is a root stage                          |
|   Stage-2 depends on stages: Stage-1               |
|   Stage-0 depends on stages: Stage-2               |
...
```

