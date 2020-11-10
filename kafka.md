分布式消息队列-kafka
------

## 环境搭建

```bash
wget https://mirror.bit.edu.cn/apache/kafka/2.5.0/kafka_2.12-2.5.0.tgz
tar xf kafka_2.12-2.5.0.tgz
ln -sv kafka_2.12-2.5.0 kafka
cat >> env <<EOF
export KAFKA_HOME=/app/kafka
export PATH=\${KAFKA_HOME}/bin:\${PATH}
EOF

source ./env
```

```bash
cd kafka
bin/zookeeper-server-start.sh config/zookeeper.properties
cp config/server.properties config/server-1.properties
sed -i 's/broker.id=0/broker.id=1/g' config/server-1.properties
sed -i 's/PLAINTEXT:\/\/:9093/PLAINTEXT:\/\/:9093/g' config/server-1.properties
sed -i 's/log.dirs=\/tmp\/kafka-logs/log.dirs=\/tmp\/kafka-logs-1/g' config/server-1.properties
cp config/server.properties config/server-2.properties
sed -i 's/broker.id=0/broker.id=2/g' config/server-2.properties
sed -i 's/PLAINTEXT:\/\/:9093/PLAINTEXT:\/\/:9094/g' config/server-2.properties
sed -i 's/log.dirs=\/tmp\/kafka-logs/log.dirs=\/tmp\/kafka-logs-2/g' config/server-2.properties

bin/kafka-server-start.sh config/server.properties &
bin/kafka-server-start.sh config/server-1.properties &
bin/kafka-server-start.sh config/server-2.properties

jps #能看到3个kafka进程组成的集群
```

## kafka

```bash
# 创建topic
bin/kafka-topics.sh --create --bootstrap-server localhost:9092 --replication-factor 3 --partitions 1 --topic my-replicated-topic
# 查询topic
bin/kafka-topics.sh --describe --bootstrap-server localhost:9092 --topic my-replicated-topic
# -"leader": leader节点，负责对某一个分区进行数据读写。kafka会随机分配一部分分区到每个节点，使节点成为这些分区的leader。
# -"replicas": 负责复制数据的节点，这里列举所有的节点，无论是否在线
# -"isr": 同步节点（"in-sync" replicas）列表，即在线并且与leader保持复制进度的节点

# 发布消息
bin/kafka-console-producer.sh --bootstrap-server localhost:9092 --topic my-replicated-topic
> a
> b
> c
> d
...

# 在另一个窗口消费这个消息，将能看到上面输入的消息打印出来
bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --from-beginning --topic my-replicated-topic

```

## kafka高可用

```bash
# 通过describe 找到leader节点
bin/kafka-topics.sh --describe --bootstrap-server localhost:9092 --topic my-replicated-topic

# kill掉leader节点
kill -9 xx
```

可以看到集群正在重选leader, 尝试发消息，即可看到集群有一些warning信息发出来，稍等片刻又能正常工作了

## kafka connect

```bash
# 运行file connector和一个file sink
bin/connect-standalone.sh config/connect-standalone.properties config/connect-file-source.properties config/connect-file-sink.properties
# 打开新窗口，运行
echo 123 > test.txt
# 打开新窗口，运行
tail -f test.sink.txt

# 在第二个窗口运行命令，输入数据，将能看到tailf命令输出同样的内容
echo 234 >> test.txt
echo 2345 >> test.txt
echo 23456 >> test.txt
echo 234567 >> test.txt
```
